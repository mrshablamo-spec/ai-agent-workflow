# NEXUS — Macro & Geopolitical Intelligence Platform

A Palantir-style local intelligence dashboard aggregating news, economics, and market data into a single dark-theme interface.

## Features

- **News & Geopolitics Feed** — NewsAPI + RSS (Reuters, Al Jazeera, FT) with Groq-powered AI summaries (cached)
- **Economic Indicators** — Fed Funds Rate, CPI YoY, GDP, Unemployment, 10Y Treasury, WTI Oil via FRED API
- **Markets Overview** — SPY, QQQ, DXY, GLD, USO, TLT with 5-day sparklines via yfinance
- **AI Signal Engine** — Groq/llama-3.1-8b-instant macro signal: sentiment, risks, opportunities, geopolitical brief
- **Watchlist** — NVDA, PLTR, ANET, MU, COHR, CEG, SPY, XLE with price, % change, and market cap

## Setup

### 1. API Keys

Copy `.env.example` to `.env` and fill in your keys:

```bash
cp .env.example .env
```

```env
NEWS_API_KEY=your_newsapi_key        # https://newsapi.org (free tier)
FRED_API_KEY=your_fred_api_key       # https://fred.stlouisfed.org/docs/api/api_key.html (free)
GROQ_API_KEY=your_groq_api_key       # https://console.groq.com (free)
```

> **Note:** All three APIs have free tiers. yfinance requires no API key.

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs available at `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

Opens at `http://localhost:3000`

## Architecture

```
nexus/
├── backend/
│   ├── main.py                  # FastAPI app, CORS, router registration
│   ├── requirements.txt
│   └── routers/
│       ├── news.py              # NewsAPI + RSS + Groq summaries (cached)
│       ├── economics.py         # FRED API indicators
│       ├── markets.py           # yfinance markets + sparklines
│       ├── signals.py           # Groq macro signal engine
│       └── watchlist.py         # yfinance watchlist
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main layout, data orchestration, 15-min refresh
│   │   ├── components/
│   │   │   ├── NewsFeed.jsx
│   │   │   ├── EconomicIndicators.jsx
│   │   │   ├── MarketsOverview.jsx
│   │   │   ├── AISignalEngine.jsx
│   │   │   └── Watchlist.jsx
│   └── ...
├── .env                         # API keys (git-ignored)
└── .env.example
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /news/?category=geopolitics` | News feed, filtered by category |
| `GET /economics/` | FRED economic indicators |
| `GET /markets/` | Market prices + sparklines |
| `GET /watchlist/` | Watchlist ticker data |
| `POST /signals/analyze` | Groq AI macro signal |
| `GET /health` | API key status check |

## Caching

- **News summaries**: Persistent in-memory dict keyed by article URL hash. Groq only called for new articles.
- **API responses**: TTLCache with 15-minute TTL matches frontend refresh interval.
- **Frontend**: Auto-refreshes all panels every 15 minutes; manual refresh button available.

## Tech Stack

- **Backend**: Python 3.11+ · FastAPI · uvicorn · httpx · yfinance · feedparser · groq · cachetools
- **Frontend**: React 18 · Tailwind CSS 3 · Recharts · Axios · date-fns · lucide-react
