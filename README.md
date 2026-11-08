# FounderVerse

### AI-Powered Startup Simulation & Multi-Agent Decision Support

**Build. Decide. Evolve.**

FounderVerse is an AI-powered startup simulation platform designed to help founders explore business decisions through a virtual executive boardroom. It brings together five role-specialized AI agents — CTO, Finance, Marketing, Sales, and Legal — to analyse strategic questions, provide independent perspectives, and collaborate on recommendations.

By combining multi-agent orchestration, persistent agent memory, company-specific context, and a startup simulation engine, FounderVerse aims to create an interactive environment for exploring startup decisions and their potential business implications.

---

## Architecture

```text
                   FOUNDER
                      |
                      v
               React Frontend
                      |
                      v
                FastAPI Backend
                      |
                      v
              Agent Orchestrator
                      |
           +----------+----------+
           |          |          |
           v          v          v
          CTO       Finance    Marketing
           |          |          |
           v          v          v
         Sales       Legal    Agent Memory
           |          |          |
           +----------+----------+
                      |
                      v
             Agent Data Assistant
                      |
                      v
             MongoDB / Knowledge
                      |
                      v
              Simulation Engine
                      |
                      v
             Founder Decision History
```

## Core Features

### 1. Multi-Agent Executive Boardroom
A virtual executive team consisting of five specialized AI agents:

- **CTO:** Technology strategy, engineering, and infrastructure.
- **Finance:** Financial planning, cash flow, costs, and runway.
- **Marketing:** Market positioning, customer acquisition, and growth.
- **Sales:** Sales strategy, customer conversion, and revenue generation.
- **Legal:** Legal considerations, compliance, contracts, and risk.

Agents contribute perspectives within their respective domains to help founders evaluate business decisions.

### 2. Individual & Collaborative Consultations
FounderVerse supports different consultation workflows:

- **Individual Opinions:** Obtain independent recommendations from specialized agents.
- **Collaborative Boardroom:** Continue the discussion through agent collaboration and generate a consolidated recommendation.
- **Single-LLM Baseline:** A separate baseline workflow for generating recommendations without the full specialist-agent discussion.

### 3. Persistent Agent Memory
An agent memory system stores company-specific information and previous agent experiences.

- Memory persistence using MongoDB.
- Text embeddings generated using `all-MiniLM-L6-v2`.
- Similarity-based retrieval of relevant memories.
- Agent- and company-scoped memory retrieval.
- Context-aware memory selection for subsequent consultations.

### 4. Agent Data Assistant & Knowledge Retrieval
An internal data-assistance layer is part of the system architecture, intended to help agents access relevant company information and knowledge when generating recommendations.

### 5. Startup Simulation Engine
A data-informed simulation engine models the evolution of a startup over successive months.

The simulation state includes:
- Cash and revenue
- Expenses and profit
- Customer count
- Churn rate
- Runway
- Valuation

Founders can retrieve and advance their company's simulation state to explore how business conditions evolve under the implemented model assumptions.

### 6. Company & Decision Management
- User registration and authentication.
- Company profile creation and persistence.
- Company-specific business context.
- Founder decision submission and storage.
- Decision history retrieval.
- Monthly boardroom consultation usage tracking.

---

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, JavaScript, Vite |
| Backend | Python, FastAPI |
| Database | MongoDB Atlas, PyMongo |
| LLM Integration | Google Gemini API |
| Agent Memory | Sentence Transformers, NumPy |
| Authentication | JWT, Argon2 password hashing |
| API Communication | REST APIs, JSON |

---

## Project Structure

```text
FounderVerse/
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── config/
│   │   ├── database/
│   │   │   ├── models/
│   │   │   └── repositories/
│   │   ├── llm/
│   │   ├── memory/
│   │   ├── orchestration/
│   │   ├── simulation/
│   │   └── main.py
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
│
├── docs/
│   ├── agent-specifications.md
│   ├── architecture.md
│   ├── database-schema.md
│   ├── api-reference.md
│   ├── local-development.md
│   └── deployment.md
│
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js and npm
- MongoDB Atlas account or a MongoDB instance
- Google Gemini API key

### 1. Clone the Repository

```bash
git clone <repository-url>
cd FounderVerse
```

### 2. Set Up the Backend

```bash
cd backend

python -m venv .venv
```

Activate the virtual environment:

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**Linux / macOS**
```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure the required environment variables in the backend `.env` file:

```env
MONGODB_URI=<your_mongodb_connection_string>
MONGODB_DATABASE=founderverse
GEMINI_API_KEY=<your_gemini_api_key>
GEMINI_MODEL=<your_configured_gemini_model>
JWT_SECRET_KEY=<your_secret_key>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173
```

Start the backend:

```bash
uvicorn app.main:app --reload
```

Backend: `http://127.0.0.1:8000`

API documentation: `http://127.0.0.1:8000/docs`

### 3. Set Up the Frontend

Open another terminal:

```bash
cd frontend

npm install
npm run dev
```

Frontend: `http://localhost:5173`

---

## Development Status

FounderVerse is under active development.

**Implemented foundations**
- React frontend and FastAPI backend.
- MongoDB integration and company persistence.
- User authentication and company management.
- Gemini-based LLM integration.
- Five role-specialized agent architecture.
- Individual and collaborative boardroom workflows.
- Structured agent responses.
- Persistent, embedding-based agent memory.
- Startup simulation and state persistence.
- Founder decision management.
- Single-LLM baseline and consultation usage tracking.

**Ongoing development**
- Internal agent data assistant and expanded knowledge retrieval.
- Reinforcement learning pipeline for agent improvement.
- Further evaluation, optimization, and deployment hardening.

---

## Documentation

Detailed technical documentation is available in the [`docs/`](docs/) directory:

- [System Architecture](docs/architecture.md)
- [Agent Specifications](docs/agent-specifications.md)
- [Database Schema](docs/database-schema.md)
- [API Reference](docs/api-reference.md)
- [Local Development Guide](docs/local-development.md)
- [Deployment Guide](docs/deployment.md)

---

## Note

FounderVerse is an experimental AI-driven decision-support and startup simulation platform. Its recommendations and simulated outcomes are intended for exploration and learning, not as substitutes for professional business, financial, or legal advice.

**FounderVerse — Build. Decide. Evolve.**