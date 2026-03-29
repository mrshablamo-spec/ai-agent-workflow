# Mini-Palantir Supply Chain Intelligence Engine

This repository now focuses on a lightweight supply chain intelligence workflow inspired by Palantir's information-asymmetry model: pull public 10-K filings, isolate dependency language, map supplier and geographic exposure, enrich with free news, and output a graph you can act on before the crowd catches up.

## What It Does

- Pulls the latest 10-K for a public company directly from the SEC with a descriptive User-Agent, throttling, and local caching.
- Extracts `Item 1. Business` and `Item 1A. Risk Factors` from the filing text.
- Detects dependency clues such as sole-source relationships, constrained suppliers, and manufacturing partners.
- Flags geographic exposure and risk categories like geopolitics, supplier concentration, manufacturing disruptions, logistics, and commodity bottlenecks.
- Builds a NetworkX graph linking the target company to suppliers, geographies, risks, and matching news stories.
- Exposes both a FastAPI endpoint and a simple CLI workflow.

## Project Layout

```text
backend/
  main.py
  run_workflow.py
  supply_chain_intel/
    config.py
    models.py
    scrapers/
    parsers/
    analysts/
    graph/
    pipelines/
    utils/
PROJECT_STRUCTURE.md
AGENTS.md
PLAN.md
requirements.txt
```

## Setup

1. Create a virtual environment and install dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy the environment template and set a real email address for SEC Fair Access compliance.

```bash
cp .env.example .env
```

3. Run the website.

```bash
./start.sh
```

This builds the frontend and serves the full website at `http://localhost:8000`.

4. Or run the API by itself.

```bash
cd backend
uvicorn main:app --reload --port 8000
```

5. Or run the workflow from the command line.

```bash
cd backend
python run_workflow.py NVDA
```

## Website

- Website UI: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## API

- `GET /health`
- `GET /supply-chain/health`
- `POST /supply-chain/analyze`

Example request:

```json
{
  "ticker": "NVDA",
  "include_news": true
}
```

## Notes on SEC Access

The engine is intentionally conservative:

- It uses a descriptive `User-Agent` composed from `SEC_CONTACT_NAME` and `SEC_CONTACT_EMAIL`.
- It throttles outbound SEC requests.
- It caches SEC responses locally under `.cache/supply_chain`.
- It does not assume any paid API keys.

## Current Limits

This is a strong Phase 1 foundation, but the extraction logic is still heuristic. It is good at surfacing candidate dependencies and risk pathways quickly, not replacing human due diligence. The next best improvements would be richer entity normalization, supplier alias resolution, and a small UI on top of the API payload.


## Render Deploy

1. Push the `codex/website-single-url` branch to GitHub.
2. In Render, create a new `Blueprint` and connect this repository.
3. Render will read `render.yaml`, build the frontend, and run the FastAPI app on one HTTPS URL.
4. Set a real `SEC_CONTACT_EMAIL` and optionally `SEC_CONTACT_NAME` in the Render environment before production use.
