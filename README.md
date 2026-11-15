# AI Travel Planner

An AI-powered travel planner with a web interface and a backend built with FastAPI and LangGraph. Enter a destination, budget, and travel dates to get flight and hotel suggestions plus a personalized itinerary.

## Features

- Web form for destination, budget, and travel dates.
- Flight information search through AviationStack.
- Hotel web search through Tavily.
- Itinerary and final response generation with Groq.
- Conversation state persistence in PostgreSQL using LangGraph.
- Responsive interface for mobile screens.

> AviationStack primarily provides live flight and status information; it does not guarantee ticket prices for selected travel dates. Available results depend on the API and its plan.

## Technology stack

- Python, FastAPI, and Uvicorn
- LangGraph and LangChain
- Groq
- PostgreSQL and `langgraph-checkpoint-postgres`
- AviationStack and Tavily
- HTML, CSS, and JavaScript

## Requirements

- Python 3.10 or later.
- A PostgreSQL database accessible from the environment where the application runs.
- API keys for Groq, Tavily, and AviationStack.

## Installation

From the project root, create and activate a virtual environment in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell prevents environment activation, you can run commands directly with `.\.venv\Scripts\python.exe`.

## Configuration

Create a `.env` file in the project root and add your own values:

```dotenv
GROQ_API_KEY=your_groq_api_key
TAVILI_API_KEY=your_tavily_api_key
AVIATIONSTACK_API_KEY=your_aviationstack_api_key
DATABASE_URL=postgresql://user:password@host:5432/database_name

# Optional: default departure airport in IATA format.
# The code defaults to DAC (Dhaka) if this variable is not set.
DEFAULT_ORIGIN_IATA=JFK
```

The code currently reads the Tavily API key from `TAVILI_API_KEY`.

`DATABASE_URL` must point to an active, reachable PostgreSQL database. For a database hosted on Render, use its **External Database URL** when running the application locally. The backend adds `sslmode=require` if the URL does not already contain an `sslmode` parameter. Do not publish your `.env` file or commit API keys.

## Run the application

With the virtual environment activated:

```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. You can also start the server with `python app.py`.

The backend connects to PostgreSQL during import, so the database and required environment variables must be configured before starting the server.

## API

### `POST /api/travel`

Send a travel request as JSON:

```json
{
  "message": "I want to travel from New York to Paris from June 10 to June 17 with a budget of USD 2,000."
}
```

The response includes `answer`, `flight_results`, `hotel_results`, `itinerary`, `thread_id`, and `llm_calls`.

### `GET /health`

Returns the basic API status.

## Project structure

```text
AITravelPlanner/
├── app.py                 # FastAPI application and endpoints
├── backend.py             # LangGraph, agents, and persistence
├── main.py
├── test.py                # Example agent invocation
├── requirements.txt
├── static/
│   ├── script.js          # Form submission and result rendering
│   └── style.css          # Interface styles
├── templates/
│   └── index.html         # Travel planner page
└── tools/
    ├── flight_tool.py     # AviationStack integration
    └── tavily_tool.py     # Hotel search with Tavily
```

## Troubleshooting

- **PostgreSQL connection error:** Confirm that the database is active, the URL is correct, and your network can reach the configured host and port. Do not share the URL if it contains credentials.
- **Missing API key:** Make sure `.env` is in the project root and that variable names match exactly.
- **No flights or prices returned:** The API may not have data for the route. AviationStack focuses on live flight information and may not provide fares.
