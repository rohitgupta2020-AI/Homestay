# Streamlit Cloud Deployment Guide

## Quick Start

### Step 1: Push to GitHub

1. Initialize git (if not already done):
```bash
git init
```

2. Add all files:
```bash
git add .
```

3. Commit:
```bash
git commit -m "Ready for Streamlit Cloud deployment"
```

4. Create a new repository on GitHub (if you haven't already)

5. Add remote and push:
```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Streamlit Cloud

1. **Go to Streamlit Cloud:**
   - Visit: https://share.streamlit.io
   - Sign in with your GitHub account

2. **Create New App:**
   - Click "New app" button
   - Select your GitHub repository
   - Select the branch (usually `main`)
   - Set Main file path: `app.py`
   - Click "Deploy"

### Step 3: Configure Secrets

1. **In Streamlit Cloud Dashboard:**
   - Go to your app's settings
   - Click on "Secrets" in the sidebar
   - Add the following configuration:

```toml
[api]
auth_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiaXNzIjoiaHVtYW5pdGljcy5jb20iLCJleHAiOjE3NzkxNjk3NDgsImlhdCI6MTc2MzYxNzc0M30.ZsDuDiwJ9ovnjUoHMlaf8KI0XtHl0lFdcHPjJO0HPNs"
```

2. **Save the secrets** - Your app will automatically redeploy

### Step 4: Access Your Public App

Your app will be available at:
```
https://YOUR-APP-NAME.streamlit.app
```

## File Structure Required

Your repository should have:
- ✅ `app.py` (main application file)
- ✅ `requirements.txt` (Python dependencies)
- ✅ `.gitignore` (excludes secrets)
- ✅ `.streamlit/secrets.toml.template` (template, not the actual secrets)

## Troubleshooting

### App won't deploy?
- Check that `requirements.txt` exists and has all dependencies
- Verify `app.py` is in the root directory
- Check the deployment logs in Streamlit Cloud dashboard

### "Token not found" error?
- Make sure you've added secrets in Streamlit Cloud dashboard
- Verify the secret key matches: `[api]["auth_token"]`

### App is slow?
- The app caches data for 5 minutes
- Check API response times
- Consider increasing cache TTL if needed

## Security Notes

- ✅ Never commit `.streamlit/secrets.toml` to GitHub
- ✅ Always use Streamlit Cloud's secrets management
- ✅ Your secrets are encrypted and secure on Streamlit Cloud

