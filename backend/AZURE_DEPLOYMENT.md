# Azure Deployment Guide

## Quick Deploy to Azure (Easiest Method)

### Step 1: Create Azure Web App

1. Go to Azure Portal: https://portal.azure.com
2. Click **"Create a resource"**
3. Search for **"Web App"** and click Create

**Configuration:**
- **Name:** `datascout-backend` (must be unique globally)
- **Publish:** Code
- **Runtime stack:** Python 3.11
- **Operating System:** Linux
- **Region:** Choose closest (e.g., East US)
- **Pricing Plan:** Free F1 (sufficient for portfolio)

4. Click **Review + Create** → **Create**

### Step 2: Configure Web App

After creation:

1. Go to your Web App resource
2. Click **Configuration** (left sidebar)
3. Click **Application settings** → **New application setting**

Add these environment variables:

```
OPENAI_API_KEY = sk-proj-your-key
PINECONE_API_KEY = pcsk_your-key
PINECONE_INDEX_NAME = datascout
PINECONE_HOST = https://your-pinecone-host
LANGCHAIN_TRACING_V2 = false
SCM_DO_BUILD_DURING_DEPLOYMENT = true
```

4. Click **Save**
5. Go to **General settings** tab
6. Set **Startup Command:**
```
python -m gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Step 3: Deploy from GitHub

**Option A: Deployment Center (Easiest)**

1. In your Web App, click **Deployment Center**
2. **Source:** GitHub
3. Authorize GitHub
4. **Organization:** MBilalKhanAI
5. **Repository:** DataScout-backend
6. **Branch:** main
7. Click **Save**

Azure will automatically deploy!

**Option B: GitHub Actions (Automated)**

1. In Azure Web App, go to **Deployment Center**
2. Download **Publish Profile**
3. Go to GitHub: `MBilalKhanAI/DataScout-backend`
4. **Settings** → **Secrets and variables** → **Actions**
5. Click **New repository secret**
   - Name: `AZURE_WEBAPP_PUBLISH_PROFILE`
   - Value: (paste the publish profile content)
6. Push the `.github/workflows/azure-deploy.yml` file
7. Done! Auto-deploys on every push

---

## Update requirements.txt

Add `gunicorn` for Azure:

```txt
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
langchain>=0.1.0
langchain-openai>=0.0.2
langchain-pinecone>=0.0.1
pinecone-client>=3.0.0
python-dotenv>=1.0.0
pypdf>=3.17.0
tiktoken>=0.5.0
gunicorn>=21.2.0
```

---

## Verify Deployment

Your app will be at:
```
https://datascout-backend.azurewebsites.net
```

Test:
```bash
curl https://datascout-backend.azurewebsites.net/
```

API Docs:
```
https://datascout-backend.azurewebsites.net/docs
```

---

## Costs

**Free Tier (F1):** $0/month
- 1 GB RAM
- 1 GB storage
- 60 CPU minutes/day
- Perfect for portfolio!

**If you need more:**
- Basic B1: ~$13/month (covered by $100 student credits)

---

## Troubleshooting

**Deployment fails:**
1. Check logs in **Deployment Center** → **Logs**
2. Verify startup command is correct
3. Check environment variables are set

**App not starting:**
1. Go to **Log stream** to see real-time logs
2. Verify `gunicorn` is in requirements.txt
3. Check `init_db.py` runs successfully

---

**Ready to deploy!** Choose Option A (Deployment Center) for quickest setup.
