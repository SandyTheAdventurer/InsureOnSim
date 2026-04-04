# InsureOnSim Documentation

InsureOnSim is a configurable insurance risk simulation engine exposed as a REST API. It models a world of interconnected geographic zones populated by workers, and simulates day-by-day events such as civil lockdowns, weather disasters, and worker behaviour including fraudulent claims.

Complete documentation is available [here](https://sandytheadventurer.github.io/InsureOnSim/)

## Project Layout

```
InsureOnSim/
├── main.py           # FastAPI application and all API endpoints
├── config.json       # Simulation parameters and defaults
├── requirements.txt  # Python dependencies
├── mkdocs.yml        # MkDocs site configuration
├── classes/
│   ├── world.py      # Zone and World simulation logic
│   ├── worker.py     # Worker agent logic
│   ├── models.py     # Pydantic request/response models
│   └── utils.py      # Probability distribution utility
└── docs/             # This documentation
```

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API server:

```bash
uvicorn main:app
```

The API will be available at `http://localhost:8000`. Interactive Swagger docs are at `http://localhost:8000/docs`.

## Quick Start Workflow

A typical simulation session follows this sequence:

1. **POST `/init`** — Initialise the world (zones and workers) from `config.json`.
2. **POST `/run_day`** — Advance the simulation by one day.
3. **GET `/weather_alerts`** / **GET `/government_alerts`** — Query active alerts.
4. **GET `/zone/{zone_id}`** / **GET `/worker/{worker_id}`** / **GET `/world_state`** — Inspect entity state.
5. **POST `/reset`** — Tear down the world to start a new simulation.

## Dependencies

| Package  | Purpose                                       |
|----------|-----------------------------------------------|
| fastapi  | Web framework for the REST API                |
| uvicorn  | ASGI server to run the FastAPI application    |
| numpy    | Random number generation and probability math |
| pydantic | Data validation and response serialisation    |
| httpx    | Calls InsureOn backend APIs                   |

## Backend Integration (Testing)

InsureOnSim can now onboard simulated workers into the backend and trigger backend claim opening from simulated events.

### 1. Configure env vars

Set these before running InsureOnSim:

```bash
export INSUREON_BACKEND_URL="http://127.0.0.1:8000"
export SIM_TEST_API_KEY="replace-with-your-shared-key"
```

Use the same `SIM_TEST_API_KEY` value in backend env for the new `/claims/sim/trigger` endpoint.

### 2. Flow

1. `POST /init`
2. `POST /backend/onboard` (creates users, profiles, and active paid policies in backend)
3. `POST /backend/test_day` (runs one sim day, pushes event triggers, returns backend test metrics)

### 3. Utility endpoints

- `GET /backend/status` — confirms bridge config is complete
- `POST /backend/trigger` — trigger backend from today’s simulated claims (after `run_day`)
- `POST /backend/sync_weather` — trigger backend directly from simulation weather alerts (after `run_day`)