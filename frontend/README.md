# VeriFact Frontend - Chrome Extension

Real-time news claim verification Chrome extension for the VeriFact system.

## 🚀 Quick Start - Testing Locally

### 1. Build the Extension

```bash
# Install dependencies
npm install

# Build for production
npm run build
```

This creates a `dist` folder with the extension files.

### 2. Load in Chrome

1. Open Chrome and go to: `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **"Load unpacked"**
4. Select the `dist` folder from this directory
5. The extension is now loaded! 🎉

### 3. Use the Extension

- Click the extension icon to open the side panel
- Select text on any webpage
- Right-click and choose "Verify with VeriFact"
- The verification results will appear in the side panel

### 4. Development Mode (Auto-rebuild)

For rapid development with auto-rebuild on file changes:

```bash
# Terminal 1: Watch mode - rebuilds on file changes
npm run build:watch

# Terminal 2: After each rebuild, reload the extension in Chrome
# Go to chrome://extensions/ and click the reload icon
```

**Pro tip**: Use the extension reload shortcut:
- Press `Ctrl+R` (Windows/Linux) or `Cmd+R` (Mac) while focused on `chrome://extensions/`

---

## Backend Connection

The frontend connects to the backend API via WebSocket. By default, it connects to `http://localhost:8000`.

### Configuration

To configure a different backend URL, create a `.env` file in the frontend directory:

```bash
# .env
VITE_API_URL=http://localhost:8000
```

For production, set this to your deployed backend URL:

```bash
VITE_API_URL=https://api.yourdomain.com
```

The WebSocket endpoint will be automatically constructed as: `ws://<backend-url>/api/v1/ws/verify/{user_id}`

## 📦 Build Commands

```bash
# Development server (for testing as web app, not extension)
npm run dev

# Production build (for Chrome extension)
npm run build

# Watch mode (auto-rebuild on changes)
npm run build:watch

# Preview production build
npm run preview
```

## 🔧 Project Structure

```
frontend/
├── public/
│   ├── manifest.json       # Chrome extension manifest
│   └── vite.svg
├── src/
│   ├── background/         # Service worker for Chrome extension
│   ├── config/            # API configuration
│   ├── App.tsx            # Main React component (side panel UI)
│   └── main.tsx           # Entry point
├── dist/                  # Built extension (after npm run build)
└── package.json
```

## 🐛 Troubleshooting

### Extension not loading
- Make sure you built the project (`npm run build`)
- Check that you selected the `dist` folder, not the root folder
- Look for errors in the Chrome extension page

### Backend connection issues
- Ensure backend is running on `http://localhost:8000`
- Check the `.env` file for correct `VITE_API_URL`
- Rebuild after changing `.env`: `npm run build`

### Changes not reflecting
- After code changes, run `npm run build` again
- Click the reload icon on `chrome://extensions/` for your extension
- Hard refresh the page where you're testing (Ctrl+Shift+R)

---

## Development

```bash
npm install
npm run dev
```

## Building

```bash
npm run build
```

---

# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
