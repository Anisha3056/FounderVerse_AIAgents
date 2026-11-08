# FounderVerse — API Reference

## Base URL

Local development: `http://127.0.0.1:8000`

FastAPI's interactive schema is available at `/docs` when the backend is running. Use it as the authoritative source for request bodies, response schemas, status codes, and authentication requirements.

## Authentication

Protected routes use a JWT access token in the HTTP header:

```http
Authorization: Bearer <access_token>
```

## Routes in the supplied source snapshot

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Register an account |
| POST | `/api/auth/login` | Log in and receive an access token |
| GET | `/api/auth/me` | Retrieve the current authenticated user |
| GET | `/api/health` | Health check |
| POST | `/api/companies/` | Create a company |
| GET | `/api/companies/{company_id}` | Retrieve a company |
| GET | `/api/simulation/{company_id}/state` | Retrieve current simulation state |
| POST | `/api/simulation/{company_id}/advance` | Advance simulation by one month |
| GET | `/api/boardroom/usage` | Retrieve monthly consultation usage |
| POST | `/api/boardroom/{company_id}/ask` | Submit a boardroom question |
| POST | `/api/boardroom/{company_id}/continue` | Continue a boardroom discussion |
| POST | `/api/decisions/{company_id}` | Save a founder decision |
| GET | `/api/decisions/{company_id}` | Retrieve decision history |
| POST | `/api/experiments/{company_id}/single-llm` | Run a single-LLM baseline consultation |

## Typical workflow

1. Register or log in.
2. Store the returned access token securely on the client.
3. Create a company.
4. Ask the boardroom a question for that company.
5. Review the response and submit the founder's selected decision.
6. Retrieve decision history.
7. Retrieve and advance the simulation state.

## Example: create a company

The exact required and optional fields are defined by the `CompanyCreate` Pydantic model. A representative payload based on that model is:

```json
{
  "company_name": "Northstar SaaS",
  "industry": "SaaS",
  "stage": "idea",
  "region": "India",
  "team_size": 3,
  "initial_capital": 1000000,
  "initial_customers": 0,
  "monthly_revenue": 0,
  "monthly_revenue_status": "known",
  "monthly_expenses": 50000
}
```

Use only fields supported by the live API schema. This example is illustrative and does not represent a real company.

## Example: health check

```bash
curl http://127.0.0.1:8000/api/health
```

## Notes

- Company-scoped routes should require authentication and verify company ownership.
- Do not publish real access tokens, request logs containing personal data, or production identifiers.
- The route list is derived from the supplied source snapshot; confirm all paths in the current branch and `/docs` before release.
