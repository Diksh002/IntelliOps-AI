# Deployment Guide - DigitalOcean App Platform

## Prerequisites
- GitHub repository pushed to: `MBilalKhanAI/DataScout-backend`
- DigitalOcean account
- API Keys: OpenAI, Pinecone

---

## Step 1: Push Code to GitHub

```bash
cd backend
git init
git add .
git commit -m "Initial commit: Production-ready backend"
git branch -M main
git remote add origin https://github.com/MBilalKhanAI/DataScout-backend.git
git push -u origin main
```

---

## Step 2: Create App on DigitalOcean

### Option A: Using the Web UI (Easiest)

1. Go to https://cloud.digitalocean.com/apps/new
2. **Connect Repository:**
   - Select "GitHub"
   - Choose repository: `MBilalKhanAI/DataScout-backend`
   - Branch: `main`

3. **Configure Service:**
   - Type: Web Service
   - HTTP Port: `8000`
   - Run Command: `uvicorn main:app --host 0.0.0.0 --port 8000`

4. **Set Environment Variables:**
   ```
   OPENAI_API_KEY = your-openai-api-key (encrypted)
   PINECONE_API_KEY = your-pinecone-api-key (encrypted)
   PINECONE_INDEX_NAME = datascout
   PINECONE_HOST = your-pinecone-host-url (encrypted)
   ```

5. **Select Plan:**
   - Basic ($5/month) - Recommended
   - Or Professional for production

6. **Deploy!**
   - Click "Create Resources"
   - Wait 5-10 minutes for deployment

### Option B: Using the CLI

```bash
# Install doctl
# Windows: choco install doctl
# Mac: brew install doctl

# Authenticate
doctl auth init

# Create app from spec
doctl apps create --spec .do/app.yaml

# Update environment variables
doctl apps update <app-id> --env OPENAI_API_KEY=your-key
```

---

## Step 3: Verify Deployment

Once deployed, you'll get a URL like:
```
https://datascout-backend-xxxxx.ondigitalocean.app
```

**Test endpoints:**
```bash
# Health check
curl https://your-app-url.ondigitalocean.app/

# API docs
https://your-app-url.ondigitalocean.app/docs
```

---

## Step 4: Update Frontend

Update frontend `.env.local`:
```env
NEXT_PUBLIC_API_URL=https://your-app-url.ondigitalocean.app
```

---

## Deployment Settings

### Build Settings
- **Build Command:** (auto-detected from Dockerfile)
- **Run Command:** `uvicorn main:app --host 0.0.0.0 --port 8000`
- **HTTP Port:** 8000

### Instance Size
- **Development:** Basic ($5/mo) - 512MB RAM, 1 vCPU
- **Production:** Professional ($12/mo) - 1GB RAM, 1 vCPU

### Auto-Deploy
- ✅ Enable "Autodeploy" to deploy on every git push

---

## Environment Variables (Required)

| Variable | Type | Example |
|----------|------|---------|
| `OPENAI_API_KEY` | Secret | sk-proj-... |
| `PINECONE_API_KEY` | Secret | pcsk_... |
| `PINECONE_INDEX_NAME` | Plain | datascout |
| `PINECONE_HOST` | Secret | https://datascout-xxxxx... |

---

## Troubleshooting

### Database Issues
The SQLite database is created on first deployment. If you need to reset:
1. Add build command: `python init_db.py`
2. Redeploy

### Port Issues
Make sure HTTP Port is set to `8000` in settings.

### Environment Variables Not Loading
1. Check they're marked as "Encrypted" for secrets
2. Verify spelling matches exactly what's in `.env.example`

---

## Monitoring

**View Logs:**
- Go to DigitalOcean dashboard
- Click on your app
- Navigate to "Runtime Logs"

**Metrics:**
- CPU and Memory usage visible in dashboard
- Set up alerts for high usage

---

## Cost Estimate

- **Basic Plan:** $5/month
- **Custom Domain:** Free
- **SSL Certificate:** Free (automatic)

**Total:** ~$5/month

---

## Next Steps

1. Deploy backend ✅
2. Get deployment URL
3. Deploy frontend to Vercel
4. Update frontend env with backend URL
5. Test full integration

---

**Your backend is now production-ready!** 🚀
