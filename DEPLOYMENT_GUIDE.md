# Kickbase Dashboard - Deployment Guide

## 🚀 Deploy to Streamlit Community Cloud (FREE)

### Prerequisites
- GitHub account
- Your dashboard code in a GitHub repository

---

## Step 1: Prepare Your Code

### 1.1 Update config import in app_unified.py

Change this line:
```python
from config import EMAIL, PASSWORD, ODDS_API_KEY
```

To:
```python
from config_deploy import EMAIL, PASSWORD, ODDS_API_KEY
```

### 1.2 Files to include in GitHub:
✅ Include:
- `app_unified.py`
- `config_deploy.py` (safe - uses secrets)
- `lineup_optimizer_advanced.py`
- `odds_fetcher.py`
- `odds_analyzer.py`
- `team_analytics.py`
- `defensive_analyzer.py`
- `fixture_analyzer.py`
- `fetch_all_players.py`
- `auth_manager.py`
- `team_name_mapper.py`
- `requirements.txt`
- `.gitignore`
- `README.md`

❌ DO NOT include:
- `config.py` (has your password!)
- `.streamlit/secrets.toml` (local secrets)
- `*.json` cache files
- `*.bat` files
- `__pycache__/`

---

## Step 2: Create GitHub Repository

### Option A: Using GitHub Desktop (Easiest)
1. Download GitHub Desktop: https://desktop.github.com/
2. Open GitHub Desktop
3. Click "File" → "Add Local Repository"
4. Select: `C:\Users\skinmatt\.aki\memories\kickbase_dashboard`
5. Click "Publish repository"
6. Name it: `kickbase-mls-dashboard`
7. **UNCHECK** "Keep this code private" (Streamlit Cloud requires public repos on free tier)
8. Click "Publish Repository"

### Option B: Using Git Command Line
```bash
cd C:\Users\skinmatt\.aki\memories\kickbase_dashboard

# Initialize git
git init

# Add files (respects .gitignore)
git add .

# Commit
git commit -m "Initial commit - Kickbase MLS Dashboard"

# Create repo on GitHub (you'll need to do this manually on github.com)
# Then link it:
git remote add origin https://github.com/YOUR_USERNAME/kickbase-mls-dashboard.git
git branch -M main
git push -u origin main
```

---

## Step 3: Deploy to Streamlit Cloud

### 3.1 Sign up for Streamlit Cloud
1. Go to: https://share.streamlit.io/
2. Click "Sign up with GitHub"
3. Authorize Streamlit to access your GitHub

### 3.2 Deploy Your App
1. Click "New app"
2. Select your repository: `kickbase-mls-dashboard`
3. Branch: `main`
4. Main file path: `app_unified.py`
5. Click "Advanced settings"

### 3.3 Add Secrets
In the "Secrets" section, paste this:

```toml
[kickbase]
email = "skinsstar06@gmail.com"
password = "Messi101996$"

[api]
odds_api_key = "914125dc93a75c3758a06bed9dba9db0"

[leagues]
default_league_id = "9830869"
red_bull_id = "9810244"
```

### 3.4 Deploy!
1. Click "Deploy!"
2. Wait 2-3 minutes for deployment
3. Your app will be live at: `https://YOUR_USERNAME-kickbase-mls-dashboard.streamlit.app`

---

## Step 4: Share with Friends

Send them the URL:
```
https://YOUR_USERNAME-kickbase-mls-dashboard.streamlit.app
```

That's it! They can access it from any device with a browser.

---

## 🔒 Security Notes

### Is it safe?
- ✅ Your password is stored securely in Streamlit secrets (encrypted)
- ✅ Secrets are NOT visible in your GitHub repo
- ✅ Only you can see/edit secrets in Streamlit Cloud dashboard
- ⚠️ The app itself is public (anyone with link can use it)

### Making it more private
If you want to restrict access, add this to the top of `app_unified.py`:

```python
import streamlit as st

# Simple password protection
def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "your_secret_password":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

if not check_password():
    st.stop()

# Rest of your app code...
```

---

## 🔄 Updating Your App

When you make changes:

1. **Edit locally** (on your computer)
2. **Test locally**: Run `streamlit run app_unified.py`
3. **Commit changes**:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push
   ```
4. **Streamlit Cloud auto-deploys** (takes ~1 minute)

---

## 📊 Monitoring

### View logs
1. Go to: https://share.streamlit.io/
2. Click on your app
3. Click "Manage app" → "Logs"

### Check usage
- Streamlit Cloud shows you how many people are using your app
- Free tier limits: 1GB RAM, 1 CPU core (should be fine for 3 friends)

---

## 🆘 Troubleshooting

### App won't start
- Check logs in Streamlit Cloud dashboard
- Common issues:
  - Missing dependencies in `requirements.txt`
  - Secrets not configured correctly
  - Import errors

### App is slow
- First load is always slower (cold start)
- Add caching to expensive operations:
  ```python
  @st.cache_data(ttl=3600)  # Cache for 1 hour
  def fetch_data():
      # Your data fetching code
      pass
  ```

### Secrets not working
- Make sure secrets are in TOML format (not JSON)
- Check for typos in secret keys
- Restart app after adding secrets

---

## 💰 Cost

**Streamlit Community Cloud**: FREE forever
- Unlimited public apps
- 1GB RAM per app
- 1 CPU core per app
- Perfect for hobby projects

**If you need more**:
- Streamlit Cloud Teams: $250/month (overkill for you)
- Alternative: Railway.app ($5/month), Render.com (free tier)

---

## 📞 Support

If you run into issues:
1. Check Streamlit docs: https://docs.streamlit.io/
2. Streamlit forum: https://discuss.streamlit.io/
3. Or ask me! 😊
