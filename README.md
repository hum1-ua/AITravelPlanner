# AI Travel Planner

An AI-powered travel planner with a web interface and a FastAPI backend. Describe a trip to get flight information, hotel search results, weather and forecast data, and a personalized itinerary.

![TripMate AI frontend](frontend.png)

## Features

- Web form for trip requests and a responsive interface.
- Flight and airline information through the AviationStack MCP server.
- Hotel and web search through Tavily MCP.
- Current weather and forecast through a local OpenWeather MCP server.
- Trip planning and itinerary generation with Groq's `openai/gpt-oss-120b` model.
- Conversation state persistence in PostgreSQL using LangGraph.

> Flight information depends on AviationStack's API and plan. It may not include ticket prices for the requested travel dates.

## Technology stack

- Python, FastAPI, and Uvicorn
- LangGraph, LangChain, and `langchain-mcp-adapters`
- MCP Python SDK (`mcp`)
- Groq, Tavily, AviationStack, and OpenWeather
- PostgreSQL and `langgraph-checkpoint-postgres`
- HTML, CSS, and JavaScript

## Requirements

- Python 3.10 or later.
- A PostgreSQL database accessible from the environment where the app runs.
- API keys for Groq, Tavily, AviationStack, and OpenWeather.
- Astral `uv` installed and available on `PATH`. The AviationStack MCP server is launched with `uvx aviationstack-mcp`.

The pinned Python dependencies are listed in `requirements.txt`. In particular, `langchain-mcp-adapters==0.3.0` connects LangChain to MCP servers, and `mcp==1.28.1` provides the MCP SDK used by the local weather server.

## Installation

From the project root, create and activate a virtual environment in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install Astral `uv` separately if it is not already installed, and confirm that `uvx` is available on `PATH`; `uv` is not a Python dependency in `requirements.txt`.

If PowerShell prevents environment activation, run commands directly with `.\.venv\Scripts\python.exe`.

## Configuration

Create a `.env` file in the project root with your own credentials:

```dotenv
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
AVIATIONSTACK_API_KEY=your_aviationstack_api_key
OPENWEATHER_API_KEY=your_openweather_api_key
DATABASE_URL=postgresql://user:password@host:5432/database_name
```

Use these variable names exactly:

- `GROQ_API_KEY` configures the Groq model.
- `TAVILY_API_KEY` is used by the remote Tavily MCP endpoint.
- `AVIATIONSTACK_API_KEY` is read by the app and passed to the AviationStack MCP process as `AVIATION_STACK_API_KEY`.
- `OPENWEATHER_API_KEY` is passed to the local Weather MCP server.
- `DATABASE_URL` is the PostgreSQL connection string.

`DATABASE_URL` must point to an active, reachable database. For a database hosted on Render, use its **External Database URL** when running locally. The backend adds `sslmode=require` if the URL does not already include an `sslmode` parameter. Keep `.env` private; do not commit it or share credentials.

## MCP servers

The MCP client is configured in `mcp_client.py` and connects to each server independently:

| Server | Transport | Purpose |
| --- | --- | --- |
| Tavily | Remote Streamable HTTP | Web search, including hotel research (`tavily_search`). |
| AviationStack | Local stdio process launched by `uvx aviationstack-mcp` | Flight-related information, including airport and airline data. |
| Weather | Local stdio process launched with the active Python interpreter | Current conditions (`get_current_weather`) and forecast (`get_forecast`) from OpenWeather. |

The Weather server implementation is in `custom_weather_mcp_server.py`. Its path is resolved from the project directory, and its API key is passed through the server process environment.

## Run the application

With the virtual environment activated:

```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. You can also start the app with `python app.py`.

The backend connects to PostgreSQL during import, so the database and required environment variables must be configured before starting the app. MCP processes are started when their tools are requested.

## API

### `POST /api/travel`

Send a travel request as JSON:

```json
{
  "message": "I want to travel from New York to Paris from June 10 to June 17 with a budget of USD 2,000."
}
```

The response includes `answer`, `flight_results`, `hotel_results`, `weather_results`, `itinerary`, `thread_id`, and `llm_calls`.

### `GET /health`

Returns the basic API status.

## Project structure

```text
AITravelPlanner/
├── app.py                       # FastAPI application and endpoints
├── backend.py                   # LangGraph agents and PostgreSQL persistence
├── mcp_client.py                # Tavily, AviationStack, and Weather MCP clients
├── custom_weather_mcp_server.py # Local OpenWeather MCP server
├── requirements.txt             # Pinned Python dependencies
├── static/
│   ├── script.js                # Form submission and result rendering
│   └── style.css                # Interface styles
├── templates/
│   └── index.html               # Travel planner page
├── tests/
└── tools/                       # Legacy direct API integrations
```

![AI Travel Planner architecture](schema.jpg)

## Troubleshooting

- **PostgreSQL connection error:** Confirm the database is running, the URL is correct, and the host and port are reachable.
- **Missing API key:** Check that `.env` is in the project root and that the variable names above match exactly.
- **AviationStack MCP cannot start:** Check that `uvx` is available on `PATH` and that the AviationStack key is valid.
- **Weather data is unavailable:** Verify the OpenWeather key and the destination name sent to the server.
- **No flight prices returned:** AviationStack may provide flight information without fares, depending on the route and API plan.
