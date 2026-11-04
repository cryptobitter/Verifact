# 🌐 VERIFACT: Multi-Cloud Deployment Architecture

This guide details the separation of concerns for deploying **VERIFACT** across three independent cloud tiers:

```mermaid
flowchart LR
    subgraph Frontend Tier
        FE["Vercel SPA<br/>(React 19 / Vite)<br/>https://verifact.vercel.app"]
    end

    subgraph Backend Tier
        BE["Render / Railway Web Service<br/>(FastAPI / Uvicorn)<br/>https://verifact-api.onrender.com"]
    end

    subgraph Data Tier
        DB[("Neon / Supabase<br/>PostgreSQL Serverless<br/>ep-*.neon.tech:5432")]
        ST["Supabase / S3 Storage<br/>(xray-images bucket)"]
    end

    FE -->|HTTPS REST API + Bearer JWT| BE
    BE -->|SQLAlchemy Connection Pool| DB
    BE -->|X-Ray & Heatmap Uploads| ST
```

---

## 1. 🗄️ Database Tier: Standalone PostgreSQL (Neon or Supabase)

### Option A: Neon Serverless Postgres (Recommended)
1. Go to [Neon.tech](https://neon.tech) and create a free project named `verifact`.
2. In the dashboard, copy your pooled connection string:
   ```text
   postgresql://neondb_owner:PASSWORD@ep-restless-rain-b7cz62ly-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require
   ```
3. Set that as `DATABASE_URL` in your backend environment. The backend auto-migrates all tables (`users`, `analyses`, `heatmap_url`, `displacement`, `signed_off`, `lateral_image_url`, `annotations`, `patient_id`, etc.) upon its first connection.

### Option B: Supabase Postgres & Storage
1. Go to [Supabase.com](https://supabase.com) and create a project named `verifact`.
2. Under **Project Settings > Database**, copy the **URI** connection string.
3. Under **Storage**, create a public bucket named `xray-images`.

---

## 2. ⚙️ Backend Tier: Web Service (Render or Railway)

### Deploying on Render:
1. Push your repository to GitHub under `verifact` (or `verifact-ortho-ai`).
2. In [Render Dashboard](https://dashboard.render.com), click **New + > Blueprint** and select your repo (Render detects `backend/render.yaml` automatically), OR click **New Web Service**:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Add the following **Environment Variables** in Render:
   - `DATABASE_URL`: Your pooled PostgreSQL connection string from Neon or Supabase
   - `SECRET_KEY`: High-entropy 64-char string (e.g. generated via `openssl rand -hex 32`)
   - `CORS_ORIGINS`: `["https://verifact.vercel.app","http://localhost:5173"]`
   - `GEMINI_API_KEY`: Your Google Gemini API Key
   - `GROQ_API_KEY`: Your Groq Cloud Vision API Key (Optional)
   - `OPENAI_API_KEY`: Your OpenAI API Key (Optional)
   - `GMAIL_ADDRESS`: Clinical dispatch Gmail address (Optional)
   - `GMAIL_APP_PASSWORD`: Gmail App Password (Optional)

---

## 3. 💻 Frontend Tier: Static Jamstack (Vercel)

### Deploying on Vercel:
1. In [Vercel Dashboard](https://vercel.com), click **Add New... > Project** and import your repository.
2. Configure project settings:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
3. Add Environment Variable:
   - `VITE_API_URL`: Your deployed backend URL (e.g. `https://verifact-api.onrender.com`)
4. Click **Deploy**. Vercel will build and assign your production domain.
