# Local Development

## Requirements

- Python environment compatible with `backend/requirements.txt`
- Node.js and npm
- MongoDB local instance or MongoDB Atlas cluster
- Gemini API key for LLM-powered boardroom functionality

## Backend

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Install and run:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend local URL: `http://127.0.0.1:8000`

API docs: `http://127.0.0.1:8000/docs`

## Environment variables

The supplied settings module defines these names:

| Variable | Required | Purpose |
|---|---:|---|
| `MONGODB_URI` | Yes | MongoDB connection URI |
| `MONGODB_DATABASE` | No | Database name; default `founderverse` |
| `GEMINI_API_KEY` | For LLM features | Gemini API credential |
| `GEMINI_MODEL` | No | Model identifier; snapshot default `gemini-3.8-flash` |
| `JWT_SECRET_KEY` | Yes | Secret used to sign JWTs |
| `JWT_ALGORITHM` | No | Snapshot default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Token lifetime; snapshot default 60 |
| `ENVIRONMENT` | No | Environment label; snapshot default `development` |
| `CORS_ORIGINS` | No | Comma-separated allowed frontend origins; snapshot setting default is localhost |

The supplied source uses a `.env` file resolved relative to the backend application directory. Confirm the exact path against `backend/app/config/settings.py` in your current checkout. Never commit the actual `.env`.

## Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server normally uses `http://localhost:5173`.

### Backend URL configuration

The supplied frontend API helper hard-codes `http://127.0.0.1:8000`. For a maintainable setup, change it to read:

```js
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
```

Then create `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Ensure `.env.local` is ignored by Git.

## Troubleshooting

### MongoDB connection failure

- Confirm `MONGODB_URI` is correct.
- Check Atlas network access/IP allow-list.
- Confirm database user credentials and permissions.
- Check that the deployed/local environment can establish TLS connections.
- Do not paste credentials into issue reports.

### Browser CORS error

- Confirm the frontend origin exactly matches a backend allowed origin.
- Include both scheme and host, and port for local development.
- Restart the backend after changing environment configuration.

### Gemini request failure

- Confirm the API key is present in the backend environment.
- Verify that the configured model identifier is currently available to the account.
- Check quota, billing, and provider error details.
- Do not expose the key in frontend code.

### Python dependency/model download issue

The memory module loads a Sentence Transformers model. The first run may need to download model files and may require additional disk space/network access.
