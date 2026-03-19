# Chrome Extension Local Testing Guide

## 🎯 Quick Setup (3 Steps)

### Step 1: Build the Extension
```bash
cd /Users/applefrontend
npm install
npm run build
```

### Step 2: Load in Chrome
1. Open Chrome
2. Go to: `chrome://extensions/`
3. Toggle **"Developer mode"** (top-right corner) to ON
4. Click **"Load unpacked"**
5. Navigate to and select: `/Users/applefrontend/dist`

### Step 3: Test It!
- Click the extension icon in your Chrome toolbar
- The VeriFact side panel should open
- Try verifying some text on any webpage!

---

## 🔄 Development Workflow

### Option 1: Manual Rebuild (Simple)
```bash
# Make your code changes, then:
npm run build

# Go to chrome://extensions/ and click the reload icon on your extension
```

### Option 2: Watch Mode (Recommended)
```bash
# Automatically rebuilds when files change
npm run build:watch

# After each rebuild, manually reload extension in Chrome:
# chrome://extensions/ → click reload icon
```

---

## 📝 Common Tasks

### Update Backend URL
```bash
# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env

# Rebuild
npm run build

# Reload extension in Chrome
```

### View Console Logs

**For Side Panel (UI):**
1. Open the side panel
2. Right-click anywhere in the panel
3. Click "Inspect"
4. Console tab shows React/UI logs

**For Background Script:**
1. Go to `chrome://extensions/`
2. Find your extension
3. Click "service worker" (under "Inspect views")
4. Console shows background script logs

### Debug Issues
```bash
# Check if files are built
ls -la dist/

# Should see:
# - index.html
# - main.js
# - background.js
# - assets/
```

---

## 🎨 Extension Features

### Side Panel
- Opens when you click the extension icon
- Displays verification results in real-time
- Shows progress steps and confidence scores

### Context Menu (Optional)
- Right-click selected text
- Choose "Verify with VeriFact"
- Results appear in side panel

### Permissions
- `sidePanel` - Display results panel
- `contextMenus` - Right-click verification
- `activeTab` - Read selected text
- `scripting` - Inject content scripts
- `geolocation` - Location-based context

---

## 🐛 Troubleshooting

### "Failed to load extension"
- ✅ Make sure you ran `npm run build`
- ✅ Select the `dist` folder, not the root folder
- ✅ Check for syntax errors in manifest.json

### "Service worker registration failed"
- ✅ Ensure `background.js` exists in `dist/`
- ✅ Check console for specific errors
- ✅ Rebuild: `npm run build`

### "Cannot connect to backend"
- ✅ Backend running? Check: `curl http://localhost:8000/health`
- ✅ CORS enabled? Check backend logs
- ✅ Check `.env` file has correct URL
- ✅ Rebuild after changing `.env`

### Changes not appearing
1. Save your files
2. Wait for build to complete (watch mode) or run `npm run build`
3. Go to `chrome://extensions/`
4. Click reload icon on your extension
5. Close and reopen the side panel
6. Hard refresh any test pages (Ctrl+Shift+R)

---

## 📚 Useful Chrome URLs

- `chrome://extensions/` - Manage extensions
- `chrome://inspect/#service-workers` - Debug service workers
- `chrome://webrtc-internals/` - WebSocket debugging

---

## 🚀 Publishing (Future)

When ready to publish to Chrome Web Store:

1. Update version in `manifest.json`
2. Build: `npm run build`
3. Zip the `dist` folder
4. Upload to [Chrome Web Store Developer Dashboard](https://chrome.google.com/webstore/devconsole/)

---

## 📖 Additional Resources

- [Chrome Extension Documentation](https://developer.chrome.com/docs/extensions/)
- [Manifest V3 Migration](https://developer.chrome.com/docs/extensions/mv3/intro/)
- [Side Panel API](https://developer.chrome.com/docs/extensions/reference/sidePanel/)

---

**Happy Testing!** 🎉

