# Deployment Guide

This guide explains how FounderVerse is deployed to the cloud: the **backend on Render**, the **frontend on Vercel** and the **database on MongoDB Atlas**. For running the project on your own machine, see [local-development.md](local-development.md).

| | |
|---|---|
| **Live frontend** | https://founderverse-chi.vercel.app |
| **Live backend** | https://founderverse-backend.onrender.com |
| **API docs** | https://founderverse-backend.onrender.com/docs |

---

## 1. Overview

```text
 Browser
    |  HTTPS
    v
 Vercel  (React + Vite, static build)
    |  HTTPS, REST + JWT
    v
 Render  (FastAPI + Uvicorn, 2 GB RAM)
    |                       |
    | PyMongo (TLS)         | HTTPS
    v                       v
 MongoDB Atlas          Google Gemini API
```

Each part is hosted separately, so the interface, the API and the database can be updated and scaled independently.

| Part | Platform | What it serves |
|---|---|---|
| Frontend | Vercel | The React single-page application as static files |
| Backend | Render web service | The FastAPI REST API, agent orchestration, simulation and memory |
| Database | MongoDB Atlas | Users, companies, simulation snapshots, decisions and agent memories |
| LLM | Google Gemini API | Agent responses (called from the backend only) |

> **Important:** the Gemini API key and the MongoDB connection string live only on the backend. The frontend never sees them.

---

## 2. Prerequisites

- A GitHub repository containing the project (Render and Vercel deploy from it).
- A [MongoDB Atlas](https://www.mongodb.com/atlas) account.
- A [Render](https://render.com) account.
- A [Vercel](https://vercel.com) account.
- A Google Gemini API key.

---

## 3. Deployment order

Deploy in this order, because each step needs a value from the previous one:

1. **MongoDB Atlas** gives you a connection string.
2. **Render backend** needs that connection string and gives you the backend URL.
3. **Vercel frontend** needs the backend URL and gives you the frontend URL.
4. **Back to Render:** add the frontend URL to `CORS_ORIGINS` so the browser is allowed to call the API.

---

## 4. Step 1: MongoDB Atlas

1. Create a cluster (a free shared cluster is enough for this project).
2. Under **Database Access**, create a database user with a strong password and read/write access.
3. Under **Network Access**, allow connections from your backend. Either:
   - add the outbound IP addresses shown for your Render service, or
   - allow `0.0.0.0/0` (any IP). This is simpler but relies entirely on a strong database password, so use a long random one.
4. Click **Connect**, choose **Drivers**, and copy the connection string. It looks like `mongodb+srv://<user>:<password>@<cluster>.mongodb.net/...`. Replace `<password>` with the real password (URL-encode special characters).

The application creates its collections automatically on first use (`users`, `companies`, `simulation_states`, `decisions`, `agent_memories`).

---

## 5. Step 2: Backend on Render

### 5.1 Create the web service

1. In Render, choose **New > Web Service** and connect the GitHub repository.
2. Use these settings:

| Setting | Value |
|---|---|
| **Root Directory** | `backend` |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/health` |
| **Instance type** | **2 GB RAM or more** (see section 5.3) |

3. Do **not** add `--workers` greater than 1 (see section 5.3).

### 5.2 Environment variables

Add these under **Environment** on the Render service. Never commit real values to the repository.

| Variable | Example / meaning |
|---|---|
| `MONGODB_URI` | Atlas connection string from Step 1 |
| `MONGODB_DATABASE` | `founderverse` |
| `GEMINI_API_KEY` | Your Gemini API key |
| `GEMINI_MODEL` | The Gemini model name you want the agents to use |
| `JWT_SECRET_KEY` | A long random secret (for example `openssl rand -hex 32`) |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` |
| `ENVIRONMENT` | `production` |
| `CORS_ORIGINS` | The frontend origin, for example `https://founderverse-chi.vercel.app` (comma-separated if more than one, no trailing slash) |
| `PYTHON_VERSION` | `3.11.x` (optional but recommended, to match development) |

### 5.3 Memory requirement (read this before choosing a plan)

The agent memory uses `sentence-transformers` with the `all-MiniLM-L6-v2` model, and that library depends on **PyTorch**. Together they need roughly 1 GB or more of RAM once loaded.

- On a **512 MB** instance the service starts, and registration, login and the simulation all work. The first **boardroom consultation then fails with an out-of-memory error**, because the model is loaded lazily on the first request that needs an embedding.
- On a **2 GB** instance the full consultation workflow runs correctly. This is what the live deployment uses.
- Keep **one Uvicorn worker**. Every extra worker loads its own copy of the model and multiplies memory use.

Make sure `requirements.txt` includes `sentence-transformers`, or the backend will fail on import.

### 5.4 Optional: warm up the model at start-up

Because the model is loaded on first use, the first consultation after a restart is slow (the model has to be downloaded and loaded). To move that delay to start-up, load the model in the application's lifespan function in `app/main.py`:

```python
from app.memory.memory_manager import get_embedding_model

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting FounderVerse backend...")
    mongodb.connect()
    get_embedding_model()   # load the embedding model once, at start-up
    yield
    print("Shutting down FounderVerse backend...")
    mongodb.close()
```

This only makes sense on an instance with enough RAM (2 GB), and it makes start-up slower but every request fast.

### 5.5 Verify the backend

Open these in a browser:

- `https://<your-backend>.onrender.com/health` should return a healthy response.
- `https://<your-backend>.onrender.com/docs` should show the interactive API documentation.

---

## 6. Step 3: Frontend on Vercel

1. In Vercel, choose **Add New > Project** and import the same GitHub repository.
2. Use these settings:

| Setting | Value |
|---|---|
| **Root Directory** | `frontend` |
| **Framework Preset** | Vite |
| **Build Command** | `npm run build` |
| **Output Directory** | `dist` |

3. Add the environment variable that tells the frontend where the backend is. Use the variable name that `src/services/api.js` reads, for example:

| Variable | Value |
|---|---|
| `VITE_API_BASE_URL` | `https://founderverse-backend.onrender.com` (no trailing slash) |

> **Vite note:** variables prefixed with `VITE_` are baked into the JavaScript **at build time**. If you change this value, you must **redeploy** the frontend for it to take effect.

4. Deploy. Vercel gives you the frontend URL.

---

## 7. Step 4: Connect them (CORS)

Go back to the Render service and set `CORS_ORIGINS` to the exact Vercel URL (scheme and domain only, with no trailing slash and no path), then let Render redeploy. Without this, the browser blocks the frontend's requests to the backend and you will see CORS errors in the browser console.

If you later add a custom domain or use Vercel preview URLs, add those origins too, separated by commas.

---

## 8. Post-deployment checklist

Test the whole flow on the live site:

- [ ] Register a new account, then log out and log in again.
- [ ] Create a company.
- [ ] Open the dashboard and advance the simulation by a month.
- [ ] Ask a question in **Individual opinions** mode and confirm five agent cards appear.
- [ ] Ask a question in **Collaborative boardroom** mode and confirm discussion and synthesis appear.
- [ ] Record a Proceed or Hold Off decision, then open **History** and confirm it was saved.
- [ ] Check that the monthly usage counter goes down after each consultation.

---

## 9. Updating the deployment

Both platforms deploy automatically when you push to the connected branch.

| Change | What happens |
|---|---|
| Push backend code | Render rebuilds and restarts the service |
| Push frontend code | Vercel rebuilds and publishes |
| Change an environment variable on Render | Render restarts the service |
| Change a `VITE_` variable on Vercel | You must trigger a new Vercel deployment |

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Login and simulation work, but a boardroom question fails or the service restarts | Out of memory on a small instance (PyTorch plus the embedding model) | Use a 2 GB instance and a single worker. Check the memory graph under the service's **Metrics** tab. |
| Browser console shows a **CORS** error | `CORS_ORIGINS` is missing or does not exactly match the frontend URL | Set it to the exact Vercel origin with no trailing slash, then redeploy the backend |
| Frontend calls `localhost` or fails to reach the API | The API base URL variable is missing or was changed without a rebuild | Set it in Vercel and redeploy the frontend |
| `401` errors right after login | `JWT_SECRET_KEY` changed between deployments, or the token has expired | Log in again and keep the secret constant |
| `429` with `TRIAL_LIMIT_REACHED` | The user has used all 15 consultations this month | Expected behaviour. The counter resets at the start of the next UTC month. |
| Backend cannot connect to MongoDB | Atlas Network Access does not allow the service, or the password in the connection string is wrong or not URL-encoded | Allow the Render IPs (or `0.0.0.0/0`) in Atlas and re-check the connection string |
| First request after inactivity is very slow | The service restarted and the embedding model is loading (or a free instance is waking up) | Wait for it, or add the warm-up in section 5.4, and open the site a few minutes before a demo |
| An agent card says not to rely on that agent | The LLM returned invalid output twice, or the Gemini call failed | Try again. Check the Gemini API key, quota and model name in the Render logs. |
| `ModuleNotFoundError: sentence_transformers` | The package is missing from `requirements.txt` | Add `sentence-transformers` and redeploy |

Render's **Logs** tab shows the backend output, including which Gemini model was tried and any API errors.

---

## 11. Cost and usage

- **LLM usage is the main running cost.** Each consultation makes several Gemini calls: 5 for individual mode and 11 for collaborative or "both" mode, plus 1 classifier call when a decision is recorded.
- Each user is limited to **15 consultations per month**, so the worst case per user is 15 x (11 + 1) = 180 generations per month. This keeps API spend predictable.
- Hosting costs are the Render instance (the 2 GB size is the main hosting expense), plus Vercel and MongoDB Atlas, which have free tiers that are sufficient for this project. Check each provider's current pricing page.
- Billing in the Google AI console updates with a delay, so very recent usage may not be shown yet.

---

## 12. Security checklist

- [ ] No secrets in the repository. Everything sensitive is an environment variable.
- [ ] `JWT_SECRET_KEY` is long and random, and is not the development value.
- [ ] The Atlas database user has a strong, unique password.
- [ ] `CORS_ORIGINS` lists only your real frontend origin(s).
- [ ] `ENVIRONMENT` is set to `production`.
- [ ] If an API key or password is ever committed or shared by mistake, rotate it immediately.

---

## 13. Possible improvements

- Serve the same embedding model through an ONNX runtime (for example FastEmbed) to avoid PyTorch and run on a much smaller instance.
- Add rate limiting and monitoring (uptime checks and error alerts).
- Containerise the backend with Docker and add a CI/CD pipeline with automated tests before each deploy.
- Use a custom domain with HTTPS for both frontend and backend.