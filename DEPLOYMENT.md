# 🚀 Deploying Surf Heat Judge Pro to Render (Free)

## What you'll get:
- Live URL accessible from anywhere
- HTTPS (secure connection)
- Installable as PWA on your phone
- Free tier (perfect for personal use)

## Step-by-Step Deployment:

### 1. Prepare Your Files
Create a project folder with these files:
```
surf-judge/
├── surf_judge_pro.py
├── requirements.txt
├── templates/
│   └── index.html (rename index_dark.html to this)
└── static/
    ├── manifest.json
    └── service-worker.js
```

### 2. Create a GitHub Repository (Optional but recommended)
- Go to github.com
- Create new repository "surf-heat-judge"
- Upload your files
- Or use Render's direct upload

### 3. Deploy on Render
1. Go to https://render.com
2. Sign up (free account)
3. Click "New +" → "Web Service"
4. Connect your GitHub repo OR use "Deploy from Git URL"
5. Configure:
   - **Name**: surf-heat-judge
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn surf_judge_pro:app`
   - **Instance Type**: Free

6. Add to requirements.txt:
```
Flask==3.0.0
reportlab==4.0.7
gunicorn==21.2.0
```

7. Click "Create Web Service"
8. Wait 5-10 minutes for deployment
9. You'll get a URL like: `https://surf-heat-judge.onrender.com`

### 4. Install on Your Phone
1. Open the URL on your phone
2. Chrome: Menu → "Install app" or "Add to Home Screen"
3. Safari: Share button → "Add to Home Screen"
4. Now you have an app icon on your phone!

### 5. Use Offline (after first load)
- The PWA will cache the interface
- Open the app even without internet
- Judging works completely offline
- Data saved locally in browser

## Alternative: Railway (Also Free)
Similar process:
1. railway.app
2. "New Project" → "Deploy from GitHub"
3. Same configuration
4. Get URL and install

## Alternative: PythonAnywhere (Free)
1. pythonanywhere.com
2. Upload files
3. Configure web app
4. Get URL

---

## Pro Tips:
- **Custom Domain**: Buy a domain and point it to your Render URL
- **Password Protection**: Add basic auth if you want privacy
- **Multiple Heats**: Data resets between sessions (by design)

Need help deploying? Let me know! 🤙
