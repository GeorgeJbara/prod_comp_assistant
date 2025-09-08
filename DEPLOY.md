# Deployment Instructions for Render

## Prerequisites
1. A GitHub account with your code repository
2. A Render account (sign up at https://render.com)
3. An OpenAI API key

## Step-by-Step Deployment

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit for Render deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 2. Deploy on Render

#### Option A: Using render.yaml (Recommended)
1. Go to https://dashboard.render.com/blueprints
2. Click "New Blueprint Instance"
3. Connect your GitHub repository
4. Render will detect the `render.yaml` file automatically
5. Review the configuration and click "Apply"

#### Option B: Manual Setup
1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub account and select your repository
4. Configure the service:
   - **Name**: airline-complaint-api
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api_enhanced:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free (or Starter for production)

### 3. Set Environment Variables
In the Render dashboard for your service:
1. Go to "Environment" tab
2. Add the following variables:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `OPENAI_MODEL`: gpt-4o-mini
   - `MODEL_TEMPERATURE`: 0
   - `DATABASE_URL`: (Will be auto-configured if using render.yaml)

### 4. Database Setup
If not using render.yaml:
1. Create a new PostgreSQL database in Render
2. Copy the Internal Database URL
3. Add it as `DATABASE_URL` environment variable to your web service

### 5. Deploy
- If using GitHub integration, pushes to main branch will auto-deploy
- Or manually deploy from Render dashboard

## Accessing Your Deployed API

Once deployed, your API will be available at:
- **Base URL**: `https://airline-complaint-api.onrender.com`
- **API Docs**: `https://airline-complaint-api.onrender.com/docs`
- **Graph Visualization**: `https://airline-complaint-api.onrender.com/api/v2/graph`

## Testing the Deployment

```bash
# Health check
curl https://airline-complaint-api.onrender.com/api/v2/health

# Process a complaint
curl -X POST https://airline-complaint-api.onrender.com/api/v2/complaint \
  -H "Content-Type: application/json" \
  -d '{"message": "Flight AA123 lost my luggage", "thread_id": "test001"}'
```

## Monitoring
- Check logs in Render dashboard → "Logs" tab
- Monitor metrics in "Metrics" tab
- Set up health check alerts in "Settings" → "Health & Alerts"

## Troubleshooting

### Common Issues:
1. **Port binding error**: Make sure you're using `$PORT` environment variable
2. **Database connection error**: Verify DATABASE_URL is correctly set
3. **OpenAI API error**: Check your API key is valid and has credits
4. **Module import errors**: Ensure all dependencies are in requirements.txt

### Free Tier Limitations:
- Service spins down after 15 minutes of inactivity
- First request after spin-down may take 30-60 seconds
- Limited to 512MB RAM and 0.1 CPU

## Production Recommendations
1. Upgrade to Starter or Standard instance for always-on service
2. Set up custom domain
3. Enable auto-deploy from GitHub
4. Configure health checks and alerts
5. Set up proper logging and monitoring