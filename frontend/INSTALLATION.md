# VeriFact Chrome Extension - Installation Guide

**Build Date:** February 15, 2026  
**Backend URL:** http://43.205.75.204:8000  
**Build Location:** `week-1/frontend/dist/`

---

## 🚀 Quick Install (Load Unpacked Extension)

### Step 1: Open Chrome Extensions Page

1. Open Google Chrome
2. Navigate to: `chrome://extensions/`
3. Enable **Developer mode** (toggle in top-right corner)

### Step 2: Load the Extension

1. Click **"Load unpacked"** button
2. Navigate to and select the folder:
   ```
   /Users/apple/Developer/KD/ai-league/week-1/frontend/dist
   ```
3. Click **"Select"**

✅ The extension is now installed!

---

## 📱 Using the Extension

### 1. Open the Side Panel

Click the VeriFact extension icon in your Chrome toolbar to open the side panel.

### 2. Verify Claims

**Method 1: Context Menu (Right-click)**
- Select any text on a webpage
- Right-click and choose **"Verify with VeriFact"**
- Results appear in the side panel

**Method 2: Manual Entry**
- Open the side panel
- Type or paste a claim
- Click verify

### 3. View Results

The extension will show:
- **Verdict:** TRUE, FALSE, MISLEADING, or NOT ENOUGH EVIDENCE
- **Confidence Score:** 0-100%
- **Reasoning Summary:** Why this verdict was reached
- **Quality Metrics:** Faithfulness, precision, correctness scores
- **Sources & Citations:** Supporting and contradicting evidence
- **Consensus Information:** Stance distribution across sources

---

## 🔧 Extension Configuration

### Backend Connection

The extension is pre-configured to connect to your deployed backend:
- **API URL:** http://43.205.75.204:8000
- **WebSocket:** ws://43.205.75.204:8000/api/v1/ws/verify/{user_id}

### Changing Backend URL

If you need to point to a different backend:

1. Edit the `.env` file:
   ```bash
   cd /Users/apple/Developer/KD/ai-league/week-1/frontend
   nano .env
   ```

2. Update the URL:
   ```bash
   VITE_API_URL=http://your-new-backend-url:8000
   ```

3. Rebuild:
   ```bash
   npm run build
   ```

4. Reload the extension:
   - Go to `chrome://extensions/`
   - Click the refresh icon on the VeriFact extension

---

## 🛠️ Development Mode

For rapid development with auto-rebuild:

### Terminal 1: Watch Mode
```bash
cd /Users/apple/Developer/KD/ai-league/week-1/frontend
npm run build:watch
```

### Terminal 2: After Each Rebuild
1. Go to `chrome://extensions/`
2. Click the reload icon (🔄) on the VeriFact extension
3. Refresh any open webpages using the extension

**Pro Tip:** Use `Cmd+R` (Mac) or `Ctrl+R` (Windows) while focused on `chrome://extensions/` to quickly reload.

---

## 📁 Build Structure

```
dist/
├── index.html              # Extension popup/panel HTML
├── main.js                 # Main application bundle (235 KB)
├── background.js           # Service worker for Chrome extension
├── manifest.json           # Chrome extension manifest
├── assets/
│   └── main-*.css         # Compiled styles (25 KB)
└── vite.svg               # App icon
```

---

## 🔍 Testing the Extension

### 1. Test Connection

Open the side panel and check the console:
```javascript
// Open Chrome DevTools for the extension
// Right-click extension popup → Inspect

// You should see:
// "Connected to backend: http://43.205.75.204:8000"
```

### 2. Test Verification

Try verifying a simple claim:
```
"The Earth orbits the Sun"
```

Expected result:
- Verdict: **TRUE**
- High confidence score (>90%)
- Multiple supporting sources
- Scientific citations

### 3. Check Backend Connection

```bash
# Test backend health
curl http://43.205.75.204:8000/health

# Expected response:
{
  "status": "healthy",
  "service": "verifact",
  "version": "1.0.0",
  "components": {
    "redis": "connected",
    "llm": "ready",
    "embeddings": "ready"
  }
}
```

---

## 🐛 Troubleshooting

### Issue: Extension doesn't load

**Solution:**
```bash
# Verify build files exist
ls -lh /Users/apple/Developer/KD/ai-league/week-1/frontend/dist/

# Should show:
# - manifest.json
# - index.html
# - main.js
# - background.js
```

### Issue: Can't connect to backend

**Symptoms:**
- Extension shows "Connection failed" or "Timeout"
- No results appear

**Solutions:**

1. **Check backend is running:**
   ```bash
   curl http://43.205.75.204:8000/health
   ```

2. **Check Chrome console for CORS errors:**
   - Right-click extension → Inspect
   - Look for CORS or network errors
   - Backend should allow `chrome-extension://*` origin

3. **Verify backend CORS settings:**
   ```bash
   ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204
   cd /app
   grep ALLOWED_ORIGINS .env
   
   # Should include: chrome-extension://*
   ```

### Issue: Extension UI appears broken

**Solutions:**

1. **Hard refresh the extension:**
   - Go to `chrome://extensions/`
   - Remove the extension
   - Re-add using "Load unpacked"

2. **Clear Chrome cache:**
   - Settings → Privacy → Clear browsing data
   - Select "Cached images and files"
   - Time range: "All time"

3. **Rebuild extension:**
   ```bash
   cd /Users/apple/Developer/KD/ai-league/week-1/frontend
   rm -rf dist node_modules
   npm install
   npm run build
   ```

### Issue: Changes not reflecting

After making code changes:

1. Rebuild:
   ```bash
   npm run build
   ```

2. Reload extension in Chrome:
   - `chrome://extensions/`
   - Click reload icon (🔄)

3. Hard refresh any open pages:
   - `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)

---

## 📦 Distribution Options

### Option 1: Local Development (Current)
✅ Already set up - extension loaded as unpacked

### Option 2: Chrome Web Store (Public Distribution)

Requirements:
- Google developer account ($5 one-time fee)
- Privacy policy
- Store listing images & description
- Chrome Web Store review process (3-5 days)

Steps:
1. Create a ZIP of the `dist/` folder
2. Upload to Chrome Web Store Developer Dashboard
3. Submit for review

### Option 3: Enterprise/Private Distribution

Package as `.crx` file:
```bash
cd /Users/apple/Developer/KD/ai-league/week-1/frontend
# Create private key
openssl genrsa -out private-key.pem 2048
# Package extension
google-chrome --pack-extension=dist --pack-extension-key=private-key.pem
```

Distribute the `.crx` file to users who can install manually.

---

## 🔄 Updating the Extension

### After Backend Changes

If backend API changes:

1. **Update types if needed:**
   ```bash
   cd /Users/apple/Developer/KD/ai-league/week-1/frontend
   # Edit src/types.ts to match new API response format
   ```

2. **Rebuild:**
   ```bash
   npm run build
   ```

3. **Reload in Chrome:**
   - `chrome://extensions/` → Reload icon

### After Code Changes

```bash
# Quick rebuild and reload
cd /Users/apple/Developer/KD/ai-league/week-1/frontend
npm run build && echo "✅ Build complete - Now reload in chrome://extensions/"
```

---

## 📊 Extension Metrics

| Metric | Value |
|--------|-------|
| **Bundle Size** | 235 KB (main.js) + 25 KB (CSS) |
| **Load Time** | < 1 second |
| **Memory Usage** | ~15-20 MB |
| **Manifest Version** | V3 (latest) |

---

## 🔒 Privacy & Permissions

### Required Permissions

The extension requests:

- **`activeTab`** - Access current tab when user invokes extension
- **`contextMenus`** - Add "Verify with VeriFact" to right-click menu
- **`sidePanel`** - Display results in Chrome side panel
- **`storage`** - Save user preferences locally

### Data Handling

- Claims are sent to backend for verification
- No data stored permanently on device
- WebSocket connections are temporary
- No tracking or analytics

---

## 📚 Additional Resources

- **Backend Deployment Info:** [`/Users/apple/Developer/KD/ai-league/week-1/DEPLOYMENT_INFO.md`](/Users/apple/Developer/KD/ai-league/week-1/DEPLOYMENT_INFO.md)
- **Frontend README:** [`/Users/apple/Developer/KD/ai-league/week-1/frontend/README.md`](/Users/apple/Developer/KD/ai-league/week-1/frontend/README.md)
- **Backend API Docs:** http://43.205.75.204:8000/docs

---

## 🆘 Support

### Check Extension Logs

```javascript
// Open Chrome DevTools for extension
// Method 1: Right-click extension icon → Inspect popup
// Method 2: chrome://extensions/ → VeriFact → Inspect views: service worker

// Console will show:
// - Connection status
// - WebSocket messages
// - API calls
// - Error messages
```

### Check Backend Logs

```bash
ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204
cd /app
sudo docker logs verifact-backend --tail 100 -f
```

---

**Last Updated:** February 15, 2026  
**Maintained By:** CodeSurgeons Team  
**Version:** 1.0.0
