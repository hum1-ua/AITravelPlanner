import os 
import certifi
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from typing import TypedDict, Annotated
import operator
import uuid
import asyncio
import json
import psycopg
from psycopg.rows import dict_row

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langchain_groq import ChatGroq
# from tools.tavily_tool import tavily_search
# from tools.flight_tool import search_flights
from mcp_client import tavily_mcp_search, aviation_mcp_call, extract_destination, forecast_mcp_search, weather_mcp_search


def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing. Please add your Render PostgreSQL External Database URL to .env"
        )

    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

    return database_url


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Please add it to your .env file.")


# =========================
# LLM
# =========================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY
)


# =========================
# State
# =========================

class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: Annotated[int, operator.add]
    weather_results: str


def _limit_prompt_text(value: object, max_chars: int = 1000) -> str:
    text = str(value)
    if len(text) > max_chars:
        return f"{text[:max_chars]}\n[truncated]"
    return text


def _aviation_tool_error(result) -> str | None:
    if not isinstance(result, list):
        return None

    for item in result:
        if not isinstance(item, dict):
            continue

        text = item.get("text")
        if not isinstance(text, str):
            continue

        try:
            response_data = json.loads(text)
        except json.JSONDecodeError:
            continue

        if isinstance(response_data, dict) and response_data.get("ok") is False:
            return str(response_data.get("error", "AviationStack request failed."))

    return None


# =========================
# Flight Agent
# =========================

# def flight_agent(state: TravelState):
#     query = state["user_query"]
#     flight_data = search_flights(query)

#     return {
#         "flight_results": flight_data,
#         "messages": [
#             AIMessage(content="Flight results fetched.")
#         ],
#         "llm_calls": 1
#     }




# Flight Tool Router Prompt
FLIGHT_AGENT_PROMPT = """
You are a travel flight expert.

User Query:
{query}

Airport Information:
{airport_data}

Airline Information:
{airline_data}

Generate:

1. Likely departure airport
2. Likely arrival airport
3. Airlines serving this route
4. Typical flight duration
5. Estimated airfare range
6. Peak season pricing warning
7. Booking advice

Return concise travel guidance.
"""




# Flight Agent
async def flight_agent(state: TravelState):
    query = state["user_query"]

    try:
        airports, airlines = await asyncio.gather(
            aviation_mcp_call("list_airports"),
            aviation_mcp_call("list_airlines"),
            return_exceptions=True
        )

        if isinstance(airports, Exception):
            airports = [{"text": json.dumps({"ok": False, "error": str(airports)})}]
        if isinstance(airlines, Exception):
            airlines = [{"text": json.dumps({"ok": False, "error": str(airlines)})}]

        #La información de vuelos depende del plan de AviationStack, que puede no permitir búsquedas de aeropuertos y aerolíneas. Si ambos están restringidos, se devuelve un mensaje de error.
        airport_error = _aviation_tool_error(airports)
        airline_error = _aviation_tool_error(airlines)

        if airport_error and airline_error:
            flight_data = (
                "Flight information is unavailable because the current "
                "AviationStack plan restricts airport and airline lookups."
            )
        else:
            prompt = FLIGHT_AGENT_PROMPT.format(
                query=_limit_prompt_text(query),
                airport_data=(
                    f"Unavailable: {airport_error}"
                    if airport_error
                    else str(airports)[:100]
                ),
                airline_data=(
                    f"Unavailable: {airline_error}"
                    if airline_error
                    else str(airlines)[:100]
                )
            )

            response = await llm.ainvoke([
                SystemMessage(
                    content="You are an expert travel flight planner."
                ),
                HumanMessage(content=prompt)
            ], max_tokens=512)

            flight_data = response.content

    except Exception as e:

        flight_data = f"Flight information unavailable: {str(e)}"

    return {
        "flight_results": flight_data,
        "messages": [
            AIMessage(
                content="Flight recommendations generated"
            )
        ],
        "llm_calls": 1
    }





# =========================
# Hotel Agent
# =========================

async def hotel_agent(state: TravelState):
    query = f"Best hotels for {state['user_query']}"
    try:
        hotel_results = await tavily_mcp_search(query)
    except Exception as e:
        hotel_results = f"Hotel information unavailable: {str(e)}"

    return {
        "hotel_results": hotel_results,
        "messages": [
            AIMessage(content="Hotel information fetched.")
        ],
        "llm_calls": 1
    }




# =========================
# Weather Agent
# =========================

async def weather_agent(state: TravelState):
    city = await extract_destination(state["user_query"])

    try:
        weather_data, forecast_data = await asyncio.gather(
            weather_mcp_search(city),
            forecast_mcp_search(city),
            return_exceptions=True
        )
        if isinstance(weather_data, Exception):
            weather_data = f"Unavailable: {weather_data}"
        if isinstance(forecast_data, Exception):
            forecast_data = f"Unavailable: {forecast_data}"
    except Exception as e:
        weather_data = f"Unavailable: {e}"
        forecast_data = f"Unavailable: {e}"

    return {
        "weather_results": f"""
        Current Weather:
        {weather_data}

        Forecast:
        {forecast_data}
        """,
        "messages": [
            AIMessage(
                content="Weather information fetched"
            )
        ]
    }



# =========================
# Itinerary Agent
# =========================

async def itinerary_agent(state: TravelState):
    prompt = f"""
Create a complete travel itinerary.

User Query:
{_limit_prompt_text(state['user_query'])}

Flight Results:
{_limit_prompt_text(state['flight_results'])}

Hotel Results:
{_limit_prompt_text(state['hotel_results'])}

Weather Results:
{_limit_prompt_text(state['weather_results'])}

Make the itinerary practical, budget-aware, and easy to follow.
"""

    response = await llm.ainvoke([
        SystemMessage(content="You are an expert travel planner."),
        HumanMessage(content=prompt)
    ], max_tokens=1024)

    return {
        "itinerary": response.content,
        "messages": [response],
        "llm_calls": 1
    }



# =========================
# Final Response Agent
# =========================

async def final_agent(state: TravelState):
    final_prompt = f"""
Generate the final travel response for the user.

User Request:
{_limit_prompt_text(state['user_query'])}

Flights:
{_limit_prompt_text(state['flight_results'])}

Hotels:
{_limit_prompt_text(state['hotel_results'])}

Weather:
{_limit_prompt_text(state['weather_results'])}

Itinerary:
{_limit_prompt_text(state['itinerary'])}

Format the final answer beautifully using these sections:

1. Trip Summary
2. Flight Information
3. Hotel Suggestions
4. Weather Information
5. Day-by-Day Itinerary
6. Estimated Budget
7. Final Recommendations


Important:
- Be clear and practical.
- Mention that live flight API may not provide ticket prices if pricing is unavailable.
- Include weather-based travel advice.
- Keep the response useful for real travel planning.
"""

    response = await llm.ainvoke([
        SystemMessage(content="You are a professional AI travel booking assistant."),
        HumanMessage(content=final_prompt)
    ], max_tokens=1024)

    return {
        "messages": [response],
        "llm_calls": 1
    }


# =========================
# Build Graph
# =========================

graph = StateGraph(TravelState)

graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("weather_agent", weather_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)

graph.add_edge(START, "flight_agent")
graph.add_edge(START, "hotel_agent")
graph.add_edge(START, "weather_agent")
graph.add_edge("flight_agent", "itinerary_agent")
graph.add_edge("hotel_agent", "itinerary_agent")
graph.add_edge("weather_agent", "itinerary_agent")
graph.add_edge("itinerary_agent", "final_agent")
graph.add_edge("final_agent", END)


# =========================
# PostgreSQL Checkpointer
# =========================
DATABASE_URL = get_database_url()

try:
    _conn = psycopg.connect(
        DATABASE_URL,
        autocommit=True,
        row_factory=dict_row,
        connect_timeout=5
    )
    checkpointer = PostgresSaver(_conn)
    checkpointer.setup()
except Exception as e:
    print(f"WARNING: PostgreSQL checkpointer unavailable: {e}")
    checkpointer = None

travel_graph = graph.compile(checkpointer=checkpointer)



# =========================
# Function for FastAPI
# =========================

async def run_travel_agent(user_input: str, thread_id: str | None = None):
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    result = await travel_graph.ainvoke(
        {
            "messages": [
                HumanMessage(content=user_input)
            ],
            "user_query": user_input,
            "flight_results": "",
            "hotel_results": "",
            "weather_results": "",
            "itinerary": "",
            "llm_calls": 0
        },
        config=config
    )

    final_answer = result["messages"][-1].content

    return {
        "thread_id": thread_id,
        "answer": final_answer,
        "flight_results": result.get("flight_results", ""),
        "hotel_results": result.get("hotel_results", ""),
        "weather_results": result.get("weather_results", ""),
        "itinerary": result.get("itinerary", ""),
        "llm_calls": result.get("llm_calls", 0),
    }