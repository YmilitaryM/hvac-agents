# HVAC Chiller Plant Multi-Agent System

A production-grade multi-agent AI system for real-time optimization and control of chiller plants. Seven specialized agents collaborate through a LangGraph workflow to monitor equipment health, forecast cooling loads, optimize chiller dispatch, review strategies for safety/compliance/efficiency, and execute parameter adjustments.

## Architecture

```
Monitor → Predict → Strategy → Advocates (3x parallel) → Coordinator → Safety → Parameter → Execute
   │                                                                          │
   └──────────────────── re-optimization loop ───────────────────────────────┘
```

### 7-Stage Pipeline

| Stage | Agent | Responsibility |
|-------|-------|---------------|
| 1 | **Monitor** | Anomaly detection, equipment health scoring |
| 2 | **Predict** | Multi-horizon load forecasting (15min–24h) |
| 3 | **Strategy** | Mixed-integer optimization for chiller dispatch |
| 4 | **Advocates** | Parallel review: Reliability, Efficiency, Compliance |
| 5 | **Coordinator** | Arbitration, conflict resolution, debate facilitation |
| 6 | **Safety** | Hard constraint checks (surge, overload, carbon) |
| 7 | **Parameter** | PID, deadband, rate limiting, interlock sequences |

### Key Components

- **Optimization**: MILP solver with Pareto front generation, equipment wear costs, carbon pricing
- **Simulation**: Physics-based chiller plant models (centrifugal chillers, cooling towers, pumps)
- **Control Layer**: PID controllers, deadband filters, rate limiters, interlock sequences
- **RL Audit**: Contextual bandit for strategy review, safety gates with confidence thresholds
- **RAG System**: TF-IDF document retrieval for operational knowledge
- **Memory & Reflection**: Strategy history logging with periodic reflection insights
- **Event Bus**: In-process pub/sub for decoupled agent communication
- **REST API**: FastAPI with monitoring, strategy CRUD, KPI endpoints, WebSocket streaming
- **Database**: SQLAlchemy + Alembic migrations (PostgreSQL), Redis for caching

## Project Structure

```
src/
├── agents/          # 7 core agents + 3 advocate agents
│   └── advocates/   # Reliability, Efficiency, Compliance
├── api/             # FastAPI REST API + WebSocket
├── control/         # PID, deadband, interlock sequences
├── curves/          # Online equipment curve identification
├── db/              # SQLAlchemy models, repositories, migrations
├── graph/           # LangGraph workflow, conditional routing, debate
├── memory/          # Strategy history log, reflection engine
├── messaging/       # In-process event bus (pub/sub)
├── optimization/    # MILP solver, constraints, Pareto front
├── rag/             # Document loader, TF-IDF retriever
├── reports/         # KPI calculator, report generator, renderer (PDF/Excel)
├── rl/              # Contextual bandit, feature engineering, safety gates
├── schemas/         # Pydantic models for state, strategy, equipment
└── simulation/      # Physics models for chillers, towers, pumps
```

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install

```bash
git clone <repo-url> && cd hvac-agents
uv sync
cp .env.example .env   # edit with your API keys
```

### Run

```bash
# Start API server
uv run python -m src

# Run a single pipeline cycle (headless)
uv run python -m src --run-once

# With debug logging
uv run python -m src --debug --run-once
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/status` | System status |
| POST/GET | `/api/monitoring/snapshot` | Plant snapshot |
| GET | `/api/monitoring/kpi` | Real-time KPIs |
| POST/GET | `/api/monitoring/alerts` | Alert management |
| POST/GET | `/api/strategies/` | Strategy CRUD |
| PUT | `/api/strategies/{id}/status` | Update strategy status |
| POST | `/api/reports/generate` | Generate PDF/Excel reports |
| WS | `/ws` | WebSocket streaming |

### Configuration

```bash
LLM_PROVIDER=anthropic          # or openai
ANTHROPIC_API_KEY=sk-...        # your API key
DEBUG=true                      # enable debug logging
DATABASE_URL=postgresql+asyncpg://...  # enable persistence
```

## Testing

```bash
uv run pytest                    # 488 tests
uv run pytest tests/integration/ # 85 integration tests
```

## Technology Stack

- **Orchestration**: LangGraph (StateGraph with conditional routing)
- **LLM**: LangChain + Anthropic Claude / OpenAI
- **Optimization**: SciPy (MILP via `milp`)
- **API**: FastAPI + WebSocket
- **Database**: SQLAlchemy 2.0 + Alembic
- **RL**: Custom contextual bandit (epsilon-greedy + Thompson sampling)
- **Simulation**: Physics-based equipment models
