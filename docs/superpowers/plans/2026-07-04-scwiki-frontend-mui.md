# SC-Wiki React MUI Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 5-page React MUI frontend in `frontend_new/` matching future-plan HTML demos exactly.

**Architecture:** Vite 8 + React 19 + TypeScript 6 + MUI theme mapped from design.md + Recharts for charts. AppShell layout (TopAppBar + NavigationRail + content area). 5 routes with backend API integration.

**Tech Stack:** React 19.2, Vite 8, TypeScript 6, @mui/material, @mui/icons-material, @mui/x-data-grid, react-router-dom 7, recharts, react-markdown, katex

---

## File Structure Plan

```
frontend_new/
├── package.json                    # Dependencies
├── vite.config.ts                  # Proxy /api → 127.0.0.1:8000
├── tsconfig.json                   # ES2023, react-jsx
├── tsconfig.app.json
├── tsconfig.node.json
├── index.html                      # <div id="root" />
└── src/
    ├── main.tsx                    # Entry: ThemeProvider + BrowserRouter + App
    ├── App.tsx                     # Routes wrapper
    ├── theme.ts                    # MUI Theme = design.md mapping
    ├── data/
    │   └── elements.ts             # 118 elements from periodic_table.js
    ├── lib/
    │   ├── api.ts                  # Fetch wrapper (from frontend_test)
    │   └── useStreamingChat.ts     # SSE hook (from frontend_test)
    ├── components/
    │   ├── AppShell.tsx            # TopAppBar + NavRail + Outlet
    │   ├── MarkdownMessage.tsx     # KaTeX + GFM (from frontend_test)
    │   ├── EvidenceCard.tsx        # Review verdict card (from frontend_test)
    │   └── PeriodicTable.tsx       # 18-col CSS Grid
    ├── pages/
    │   ├── HomePage.tsx            # Periodic table + charts
    │   ├── SearchPage.tsx          # DataGrid + filters + detail drawer
    │   ├── RagPage.tsx             # Chat with MUI
    │   ├── TcPredictPage.tsx       # File upload + result
    │   └── ChartsPage.tsx          # Recharts scatter
    └── context/
        └── AuthContext.tsx         # Auth state (from frontend_test)
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `frontend_new/package.json`
- Create: `frontend_new/vite.config.ts`
- Create: `frontend_new/tsconfig.json`
- Create: `frontend_new/tsconfig.app.json`
- Create: `frontend_new/tsconfig.node.json`
- Create: `frontend_new/index.html`

- [ ] **Step 1: Write package.json**

```json
{
  "name": "sc-wiki-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@emotion/react": "^11.14.0",
    "@emotion/styled": "^11.14.0",
    "@mui/icons-material": "^7.3.5",
    "@mui/material": "^7.3.5",
    "@mui/x-data-grid": "^8.3.0",
    "katex": "^0.16.11",
    "react": "^19.2.6",
    "react-dom": "^19.2.6",
    "react-markdown": "^10.1.0",
    "react-router-dom": "^7.18.0",
    "recharts": "^2.15.2",
    "rehype-katex": "^7.0.1",
    "remark-gfm": "^4.0.1",
    "remark-math": "^6.0.0"
  },
  "devDependencies": {
    "@types/katex": "^0.16.8",
    "@types/react": "^19.2.14",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^6.0.1",
    "typescript": "~6.0.2",
    "vite": "^8.0.12"
  }
}
```

- [ ] **Step 2: Write vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 3: Write tsconfig.json**

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

- [ ] **Step 4: Write tsconfig.app.json**

```json
{
  "compilerOptions": {
    "target": "ES2023",
    "useDefineForClassFields": true,
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"]
}
```

- [ ] **Step 5: Write tsconfig.node.json**

```json
{
  "compilerOptions": {
    "target": "ES2023",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 6: Write index.html**

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SC-Wiki 超导文献数据库</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 7: Install dependencies**

Run: `cd /home/work/workshop/git/SC-Wiki/frontend_new && npm install`
Expected: node_modules created without errors.

---

### Task 2: MUI Theme — design.md Mapping

**Files:**
- Create: `frontend_new/src/theme.ts`

- [ ] **Step 1: Write theme.ts**

```typescript
import { createTheme } from '@mui/material/styles'

const theme = createTheme({
  palette: {
    primary: {
      main: '#4f46e5',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#0891b2',
      contrastText: '#ffffff',
    },
    error: {
      main: '#b3261e',
    },
    warning: {
      main: '#b45309',
    },
    success: {
      main: '#15803d',
    },
    background: {
      default: '#f8fafc',
      paper: '#ffffff',
    },
    text: {
      primary: '#1f2937',
      secondary: '#64748b',
    },
    divider: '#e2e8f0',
  },
  shape: {
    borderRadius: 8,
  },
  shadows: [
    'none',
    '0 1px 2px rgba(15,23,42,0.12), 0 1px 3px rgba(15,23,42,0.08)',
    '0 1px 2px rgba(15,23,42,0.12), 0 1px 3px rgba(15,23,42,0.08)',
    '0 2px 6px rgba(15,23,42,0.14), 0 4px 12px rgba(15,23,42,0.08)',
    '0 2px 6px rgba(15,23,42,0.14), 0 4px 12px rgba(15,23,42,0.08)',
    '0 4px 10px rgba(15,23,42,0.15), 0 6px 16px rgba(15,23,42,0.09)',
    '0 4px 10px rgba(15,23,42,0.15), 0 6px 16px rgba(15,23,42,0.09)',
    '0 5px 14px rgba(15,23,42,0.16), 0 8px 20px rgba(15,23,42,0.10)',
    '0 6px 16px rgba(15,23,42,0.16), 0 10px 24px rgba(15,23,42,0.10)',
    '0 6px 16px rgba(15,23,42,0.16), 0 10px 24px rgba(15,23,42,0.10)',
    '0 8px 20px rgba(15,23,42,0.17), 0 12px 28px rgba(15,23,42,0.11)',
    '0 8px 20px rgba(15,23,42,0.17), 0 12px 28px rgba(15,23,42,0.11)',
    '0 12px 28px rgba(15,23,42,0.18), 0 18px 40px rgba(15,23,42,0.12)',
    '0 12px 28px rgba(15,23,42,0.18), 0 18px 40px rgba(15,23,42,0.12)',
    '0 12px 28px rgba(15,23,42,0.18), 0 18px 40px rgba(15,23,42,0.12)',
    '0 14px 32px rgba(15,23,42,0.19), 0 20px 44px rgba(15,23,42,0.13)',
    '0 14px 32px rgba(15,23,42,0.19), 0 20px 44px rgba(15,23,42,0.13)',
    '0 14px 32px rgba(15,23,42,0.19), 0 20px 44px rgba(15,23,42,0.13)',
    '0 16px 36px rgba(15,23,42,0.20), 0 22px 48px rgba(15,23,42,0.14)',
    '0 16px 36px rgba(15,23,42,0.20), 0 22px 48px rgba(15,23,42,0.14)',
    '0 16px 36px rgba(15,23,42,0.20), 0 22px 48px rgba(15,23,42,0.14)',
    '0 18px 40px rgba(15,23,42,0.21), 0 24px 52px rgba(15,23,42,0.15)',
    '0 18px 40px rgba(15,23,42,0.21), 0 24px 52px rgba(15,23,42,0.15)',
    '0 18px 40px rgba(15,23,42,0.21), 0 24px 52px rgba(15,23,42,0.15)',
    '0 20px 44px rgba(15,23,42,0.22), 0 26px 56px rgba(15,23,42,0.16)',
  ],
  typography: {
    fontFamily: '"Roboto", "Inter", system-ui, -apple-system, sans-serif',
    h1: {
      fontSize: 'clamp(32px, 5vw, 52px)',
      fontWeight: 700,
      lineHeight: 1.05,
      letterSpacing: '-0.01em',
    },
    h2: { fontSize: 20, fontWeight: 600 },
    h3: { fontSize: 16, fontWeight: 600 },
    overline: {
      fontSize: 12,
      fontWeight: 700,
      letterSpacing: '0.08em',
      textTransform: 'uppercase' as const,
      color: '#4f46e5',
      lineHeight: 1.5,
    },
    body1: { fontSize: 14, lineHeight: 1.65 },
    body2: { fontSize: 13 },
    caption: { fontSize: 12, fontWeight: 600 },
    button: { textTransform: 'none' as const, fontWeight: 700 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          margin: 0,
          minHeight: '100vh',
          backgroundColor: '#f8fafc',
          color: '#1f2937',
          fontFamily: '"Roboto", "Inter", system-ui, -apple-system, sans-serif',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          minHeight: 40,
          padding: '0 20px',
          fontSize: 14,
          fontWeight: 700,
          textTransform: 'none' as const,
        },
        contained: {
          boxShadow: 'none',
          '&:hover': { boxShadow: 'none' },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          borderColor: '#e2e8f0',
          boxShadow: '0 1px 2px rgba(15,23,42,0.12), 0 1px 3px rgba(15,23,42,0.08)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          height: 32,
          fontSize: 12,
          fontWeight: 700,
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 2px rgba(15,23,42,0.12), 0 1px 3px rgba(15,23,42,0.08)',
        },
      },
    },
    MuiDataGrid: {
      styleOverrides: {
        root: {
          border: 'none',
          fontSize: 14,
        },
        columnHeader: {
          fontSize: 12,
          fontWeight: 800,
          color: '#64748b',
        },
        row: {
          '&.Mui-selected': {
            backgroundColor: '#e0e7ff !important',
          },
        },
        cell: {
          borderBottom: '1px solid #e2e8f0',
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 16,
        },
      },
    },
  },
})

export default theme
```

---

### Task 3: Entry Point + App Shell

**Files:**
- Create: `frontend_new/src/main.tsx`
- Create: `frontend_new/src/App.tsx`

- [ ] **Step 1: Write main.tsx**

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider, CssBaseline } from '@mui/material'
import theme from './theme'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>,
)
```

- [ ] **Step 2: Write App.tsx**

```typescript
import React from 'react'
import { Routes, Route } from 'react-router-dom'
import AppShell from './components/AppShell'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import RagPage from './pages/RagPage'
import TcPredictPage from './pages/TcPredictPage'
import ChartsPage from './pages/ChartsPage'

const App: React.FC = () => (
  <Routes>
    <Route element={<AppShell />}>
      <Route path="/" element={<HomePage />} />
      <Route path="/search" element={<SearchPage />} />
      <Route path="/rag" element={<RagPage />} />
      <Route path="/tc-predict" element={<TcPredictPage />} />
      <Route path="/charts" element={<ChartsPage />} />
    </Route>
  </Routes>
)

export default App
```

---

### Task 4: AppShell Layout (TopAppBar + NavigationRail)

**Files:**
- Create: `frontend_new/src/components/AppShell.tsx`

**Layout spec from material-demo.css:**
- Grid: 88px rail + 1fr content, 72px appbar
- AppBar: sticky, surface bg, border-bottom, elevation-1
- Rail: surface bg, border-right, 88px wide
- Rail items: 68×60px, border-radius 18px, muted text, active = primary-container bg

- [ ] **Step 1: Write AppShell.tsx**

```typescript
import React from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  Box, AppBar, Toolbar, Typography,
} from '@mui/material'

interface NavItem {
  label: string
  icon: string
  path: string
}

const NAV_ITEMS: NavItem[] = [
  { label: '上传', icon: 'upload', path: '/' },
  { label: '审核', icon: 'verified', path: '/' },
  { label: '检索', icon: 'search', path: '/search' },
  { label: '图谱', icon: 'hub', path: '/' },
  { label: '问答', icon: 'chat', path: '/rag' },
  { label: '预测', icon: 'science', path: '/tc-predict' },
  { label: '社区', icon: 'groups', path: '/charts' },
]

const AppShell: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '88px 1fr', gridTemplateRows: '72px 1fr' }}>
      {/* Top App Bar */}
      <AppBar
        position="sticky"
        color="inherit"
        sx={{
          gridColumn: '1 / -1',
          zIndex: 10,
          minHeight: 72,
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
        }}
      >
        <Toolbar sx={{ minHeight: '72px !important', px: 3, justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box
              sx={{
                width: 40, height: 40, borderRadius: '12px',
                bgcolor: 'primary.main', color: 'primary.contrastText',
                display: 'grid', placeItems: 'center',
                boxShadow: 3, fontWeight: 700,
              }}
            >
              SC
            </Box>
            <Typography fontWeight={700}>SC-Wiki</Typography>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Navigation Rail */}
      <Box
        component="nav"
        sx={{
          bgcolor: 'background.paper',
          borderRight: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          flexDirection: 'column',
          gap: 1,
          p: '16px 10px',
        }}
      >
        {NAV_ITEMS.map((item) => {
          const isActive = item.path !== '/' && location.pathname.startsWith(item.path)
          return (
            <Box
              key={item.label}
              onClick={() => navigate(item.path)}
              sx={{
                width: 68, minHeight: 60, borderRadius: '18px',
                display: 'grid', placeItems: 'center', gap: 0.5,
                color: isActive ? '#312e81' : 'text.secondary',
                bgcolor: isActive ? '#e0e7ff' : 'transparent',
                fontSize: 11, fontWeight: 600,
                cursor: 'pointer', border: 0,
                transition: 'background 0.2s',
                '&:hover': { bgcolor: isActive ? '#e0e7ff' : 'action.hover' },
              }}
            >
              <Box component="span" sx={{ fontSize: 20 }}>
                {item.icon === 'upload' && '⬆'}
                {item.icon === 'verified' && '✓'}
                {item.icon === 'search' && '🔍'}
                {item.icon === 'hub' && '🔗'}
                {item.icon === 'chat' && '💬'}
                {item.icon === 'science' && '⚛'}
                {item.icon === 'groups' && '👥'}
              </Box>
              {item.label}
            </Box>
          )
        })}
      </Box>

      {/* Content Area */}
      <Box component="main" sx={{ p: 4, maxWidth: 1440, width: '100%', mx: 'auto' }}>
        <Outlet />
      </Box>
    </Box>
  )
}

export default AppShell
```

- [ ] **Step 2: Verify AppShell renders**

Run: `cd /home/work/workshop/git/SC-Wiki/frontend_new && npx vite --host 0.0.0.0 &`
Expected: App starts on port 5173. Quick browser check shows AppShell layout with TopAppBar + Rail.

---

### Task 5: Copy Reusable Files from frontend_test

**Files:**
- Create: `frontend_new/src/lib/api.ts` (copy from `frontend_old/frontend_test/src/lib/api.ts`)
- Create: `frontend_new/src/lib/useStreamingChat.ts` (copy from `frontend_old/frontend_test/src/hooks/useStreamingChat.ts`)
- Create: `frontend_new/src/components/MarkdownMessage.tsx` (copy from `frontend_old/frontend_test/src/components/MarkdownMessage.tsx`)
- Create: `frontend_new/src/components/EvidenceCard.tsx` (copy from `frontend_old/frontend_test/src/components/EvidenceCard.tsx`)
- Create: `frontend_new/src/context/AuthContext.tsx` (copy from `frontend_old/frontend_test/src/context/AuthContext.tsx`)

- [ ] **Step 1: Copy files**

Run:
```bash
cp /home/work/workshop/git/SC-Wiki/frontend_old/frontend_test/src/lib/api.ts /home/work/workshop/git/SC-Wiki/frontend_new/src/lib/api.ts
cp /home/work/workshop/git/SC-Wiki/frontend_old/frontend_test/src/hooks/useStreamingChat.ts /home/work/workshop/git/SC-Wiki/frontend_new/src/lib/useStreamingChat.ts
cp /home/work/workshop/git/SC-Wiki/frontend_old/frontend_test/src/components/MarkdownMessage.tsx /home/work/workshop/git/SC-Wiki/frontend_new/src/components/MarkdownMessage.tsx
cp /home/work/workshop/git/SC-Wiki/frontend_old/frontend_test/src/components/EvidenceCard.tsx /home/work/workshop/git/SC-Wiki/frontend_new/src/components/EvidenceCard.tsx
cp /home/work/workshop/git/SC-Wiki/frontend_old/frontend_test/src/context/AuthContext.tsx /home/work/workshop/git/SC-Wiki/frontend_new/src/context/AuthContext.tsx
```

- [ ] **Step 2: Fix import in useStreamingChat.ts**

The copied `useStreamingChat.ts` imports from `../lib/api`. Since it's now in `src/lib/`, change the import:

Read the file after copy, then edit:
```
- import { api } from '../lib/api'
+ import { api } from './api'
```

---

### Task 6: 118 Elements Data

**Files:**
- Create: `frontend_new/src/data/elements.ts`

- [ ] **Step 1: Write elements.ts**

Extract element data from `frontend_old/frontend/static/js/periodic_table.js` lines 1-118. The data format:

```typescript
export interface ElementData {
  symbol: string
  number: number
  row: number
  col: number
  category: 'alkali-metal' | 'alkaline-earth' | 'transition-metal' | 'post-transition'
    | 'metalloid' | 'nonmetal' | 'halogen' | 'noble-gas' | 'lanthanide' | 'actinide'
  exist: 'natural' | 'synthetic'
  radioactive?: boolean
}

export const CATEGORY_COLORS: Record<ElementData['category'], string> = {
  'alkali-metal': '#f4bcc2',
  'alkaline-earth': '#e3bd91',
  'transition-metal': '#edcda9',
  'post-transition': '#ededab',
  'metalloid': '#9cd5a8',
  'nonmetal': '#a3d7dc',
  'halogen': '#b7a0db',
  'noble-gas': '#cfb5d6',
  'lanthanide': '#cea1ce',
  'actinide': '#c782ab',
}

export const ELEMENTS: ElementData[] = [
  { symbol: 'H',  number: 1,   row: 1, col: 1,  category: 'nonmetal',         exist: 'natural' },
  { symbol: 'He', number: 2,   row: 1, col: 18, category: 'noble-gas',         exist: 'natural' },
  { symbol: 'Li', number: 3,   row: 2, col: 1,  category: 'alkali-metal',      exist: 'natural' },
  { symbol: 'Be', number: 4,   row: 2, col: 2,  category: 'alkaline-earth',    exist: 'natural' },
  { symbol: 'B',  number: 5,   row: 2, col: 13, category: 'metalloid',         exist: 'natural' },
  { symbol: 'C',  number: 6,   row: 2, col: 14, category: 'nonmetal',          exist: 'natural' },
  { symbol: 'N',  number: 7,   row: 2, col: 15, category: 'nonmetal',          exist: 'natural' },
  { symbol: 'O',  number: 8,   row: 2, col: 16, category: 'nonmetal',          exist: 'natural' },
  { symbol: 'F',  number: 9,   row: 2, col: 17, category: 'halogen',           exist: 'natural' },
  { symbol: 'Ne', number: 10,  row: 2, col: 18, category: 'noble-gas',         exist: 'natural' },
  { symbol: 'Na', number: 11,  row: 3, col: 1,  category: 'alkali-metal',      exist: 'natural' },
  { symbol: 'Mg', number: 12,  row: 3, col: 2,  category: 'alkaline-earth',    exist: 'natural' },
  { symbol: 'Al', number: 13,  row: 3, col: 13, category: 'post-transition',   exist: 'natural' },
  { symbol: 'Si', number: 14,  row: 3, col: 14, category: 'metalloid',         exist: 'natural' },
  { symbol: 'P',  number: 15,  row: 3, col: 15, category: 'nonmetal',          exist: 'natural' },
  { symbol: 'S',  number: 16,  row: 3, col: 16, category: 'nonmetal',          exist: 'natural' },
  { symbol: 'Cl', number: 17,  row: 3, col: 17, category: 'halogen',           exist: 'natural' },
  { symbol: 'Ar', number: 18,  row: 3, col: 18, category: 'noble-gas',         exist: 'natural' },
  { symbol: 'K',  number: 19,  row: 4, col: 1,  category: 'alkali-metal',      exist: 'natural' },
  { symbol: 'Ca', number: 20,  row: 4, col: 2,  category: 'alkaline-earth',    exist: 'natural' },
  { symbol: 'Sc', number: 21,  row: 4, col: 3,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Ti', number: 22,  row: 4, col: 4,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'V',  number: 23,  row: 4, col: 5,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Cr', number: 24,  row: 4, col: 6,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Mn', number: 25,  row: 4, col: 7,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Fe', number: 26,  row: 4, col: 8,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Co', number: 27,  row: 4, col: 9,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Ni', number: 28,  row: 4, col: 10, category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Cu', number: 29,  row: 4, col: 11, category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Zn', number: 30,  row: 4, col: 12, category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Ga', number: 31,  row: 4, col: 13, category: 'post-transition',   exist: 'natural' },
  { symbol: 'Ge', number: 32,  row: 4, col: 14, category: 'metalloid',         exist: 'natural' },
  { symbol: 'As', number: 33,  row: 4, col: 15, category: 'metalloid',         exist: 'natural' },
  { symbol: 'Se', number: 34,  row: 4, col: 16, category: 'nonmetal',          exist: 'natural' },
  { symbol: 'Br', number: 35,  row: 4, col: 17, category: 'halogen',           exist: 'natural' },
  { symbol: 'Kr', number: 36,  row: 4, col: 18, category: 'noble-gas',         exist: 'natural' },
  { symbol: 'Rb', number: 37,  row: 5, col: 1,  category: 'alkali-metal',      exist: 'natural' },
  { symbol: 'Sr', number: 38,  row: 5, col: 2,  category: 'alkaline-earth',    exist: 'natural' },
  { symbol: 'Y',  number: 39,  row: 5, col: 3,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Zr', number: 40,  row: 5, col: 4,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Nb', number: 41,  row: 5, col: 5,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Mo', number: 42,  row: 5, col: 6,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Tc', number: 43,  row: 5, col: 7,  category: 'transition-metal',  exist: 'synthetic' },
  { symbol: 'Ru', number: 44,  row: 5, col: 8,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Rh', number: 45,  row: 5, col: 9,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Pd', number: 46,  row: 5, col: 10, category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Ag', number: 47,  row: 5, col: 11, category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Cd', number: 48,  row: 5, col: 12, category: 'transition-metal',  exist: 'natural' },
  { symbol: 'In', number: 49,  row: 5, col: 13, category: 'post-transition',   exist: 'natural' },
  { symbol: 'Sn', number: 50,  row: 5, col: 14, category: 'post-transition',   exist: 'natural' },
  { symbol: 'Sb', number: 51,  row: 5, col: 15, category: 'metalloid',         exist: 'natural' },
  { symbol: 'Te', number: 52,  row: 5, col: 16, category: 'metalloid',         exist: 'natural' },
  { symbol: 'I',  number: 53,  row: 5, col: 17, category: 'halogen',           exist: 'natural' },
  { symbol: 'Xe', number: 54,  row: 5, col: 18, category: 'noble-gas',         exist: 'natural' },
  { symbol: 'Cs', number: 55,  row: 6, col: 1,  category: 'alkali-metal',      exist: 'natural' },
  { symbol: 'Ba', number: 56,  row: 6, col: 2,  category: 'alkaline-earth',    exist: 'natural' },
  { symbol: 'La', number: 57,  row: 6, col: 3,  category: 'lanthanide',        exist: 'natural', radioactive: true },
  { symbol: 'Hf', number: 72,  row: 6, col: 4,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Ta', number: 73,  row: 6, col: 5,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'W',  number: 74,  row: 6, col: 6,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Re', number: 75,  row: 6, col: 7,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Os', number: 76,  row: 6, col: 8,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Ir', number: 77,  row: 6, col: 9,  category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Pt', number: 78,  row: 6, col: 10, category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Au', number: 79,  row: 6, col: 11, category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Hg', number: 80,  row: 6, col: 12, category: 'transition-metal',  exist: 'natural' },
  { symbol: 'Tl', number: 81,  row: 6, col: 13, category: 'post-transition',   exist: 'natural' },
  { symbol: 'Pb', number: 82,  row: 6, col: 14, category: 'post-transition',   exist: 'natural' },
  { symbol: 'Bi', number: 83,  row: 6, col: 15, category: 'post-transition',   exist: 'natural' },
  { symbol: 'Po', number: 84,  row: 6, col: 16, category: 'metalloid',         exist: 'natural', radioactive: true },
  { symbol: 'At', number: 85,  row: 6, col: 17, category: 'halogen',           exist: 'natural', radioactive: true },
  { symbol: 'Rn', number: 86,  row: 6, col: 18, category: 'noble-gas',         exist: 'natural', radioactive: true },
  { symbol: 'Fr', number: 87,  row: 7, col: 1,  category: 'alkali-metal',      exist: 'natural', radioactive: true },
  { symbol: 'Ra', number: 88,  row: 7, col: 2,  category: 'alkaline-earth',    exist: 'natural', radioactive: true },
  { symbol: 'Ac', number: 89,  row: 7, col: 3,  category: 'actinide',          exist: 'natural', radioactive: true },
  { symbol: 'Rf', number: 104, row: 7, col: 4,  category: 'transition-metal',  exist: 'synthetic', radioactive: true },
  { symbol: 'Db', number: 105, row: 7, col: 5,  category: 'transition-metal',  exist: 'synthetic', radioactive: true },
  { symbol: 'Sg', number: 106, row: 7, col: 6,  category: 'transition-metal',  exist: 'synthetic', radioactive: true },
  { symbol: 'Bh', number: 107, row: 7, col: 7,  category: 'transition-metal',  exist: 'synthetic', radioactive: true },
  { symbol: 'Hs', number: 108, row: 7, col: 8,  category: 'transition-metal',  exist: 'synthetic', radioactive: true },
  { symbol: 'Mt', number: 109, row: 7, col: 9,  category: 'transition-metal',  exist: 'synthetic', radioactive: true },
  { symbol: 'Ds', number: 110, row: 7, col: 10, category: 'transition-metal',  exist: 'synthetic', radioactive: true },
  { symbol: 'Rg', number: 111, row: 7, col: 11, category: 'transition-metal',  exist: 'synthetic', radioactive: true },
  { symbol: 'Cn', number: 112, row: 7, col: 12, category: 'transition-metal',  exist: 'synthetic', radioactive: true },
  { symbol: 'Nh', number: 113, row: 7, col: 13, category: 'post-transition',   exist: 'synthetic', radioactive: true },
  { symbol: 'Fl', number: 114, row: 7, col: 14, category: 'post-transition',   exist: 'synthetic', radioactive: true },
  { symbol: 'Mc', number: 115, row: 7, col: 15, category: 'post-transition',   exist: 'synthetic', radioactive: true },
  { symbol: 'Lv', number: 116, row: 7, col: 16, category: 'post-transition',   exist: 'synthetic', radioactive: true },
  { symbol: 'Ts', number: 117, row: 7, col: 17, category: 'halogen',           exist: 'synthetic', radioactive: true },
  { symbol: 'Og', number: 118, row: 7, col: 18, category: 'noble-gas',         exist: 'synthetic', radioactive: true },
]
```

---

### Task 7: PeriodicTable Component

**Files:**
- Create: `frontend_new/src/components/PeriodicTable.tsx`

- [ ] **Step 1: Write PeriodicTable.tsx**

```typescript
import React from 'react'
import { Box, Typography } from '@mui/material'
import { ELEMENTS, CATEGORY_COLORS, ElementData } from '../data/elements'

interface PeriodicTableProps {
  selected: Set<string>
  onToggle: (symbol: string) => void
  disabledElements?: Set<string>
}

const PeriodicTable: React.FC<PeriodicTableProps> = ({ selected, onToggle, disabledElements }) => {
  // Build a lookup map: row-col → element
  const grid = new Map<string, ElementData>()
  ELEMENTS.forEach((el) => {
    grid.set(`${el.row}-${el.col}`, el)
  })

  // 7 rows × 18 cols
  const rows = [1, 2, 3, 4, 5, 6, 7]
  const cols = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: 'repeat(18, 60px)',
        gap: '3px',
        justifyContent: 'center',
        '@media (max-width: 1160px)': { gridTemplateColumns: 'repeat(18, 50px)' },
        '@media (max-width: 768px)': { gridTemplateColumns: 'repeat(18, 40px)' },
      }}
    >
      {rows.map((row) =>
        cols.map((col) => {
          const el = grid.get(`${row}-${col}`)
          if (!el) {
            return <Box key={`${row}-${col}`} sx={{ width: 60, height: 60, '@media (max-width: 1160px)': { width: 50, height: 50 }, '@media (max-width: 768px)': { width: 40, height: 40 } }} />
          }

          const isSelected = selected.has(el.symbol)
          const isDisabled = disabledElements?.has(el.symbol) || false
          const bgColor = CATEGORY_COLORS[el.category]

          return (
            <Box
              key={el.symbol}
              onClick={() => !isDisabled && onToggle(el.symbol)}
              sx={{
                width: 60, height: 60,
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                border: isSelected ? '2px solid #7b7b7b' : '1px solid #ccc',
                borderRadius: '4px',
                bgcolor: bgColor,
                cursor: isDisabled ? 'not-allowed' : 'pointer',
                opacity: isDisabled ? 0.6 : 1,
                userSelect: 'none',
                transition: 'all 0.2s ease',
                position: 'relative',
                boxShadow: isSelected ? 'inset 0 0 0 100px rgba(255,255,255,0.3)' : 'none',
                '&:hover': !isDisabled ? {
                  boxShadow: '0 4px 8px rgba(0,0,0,0.2)',
                  transform: 'scale(1.05)',
                  zIndex: 10,
                } : {},
                '@media (max-width: 1160px)': { width: 50, height: 50 },
                '@media (max-width: 768px)': { width: 40, height: 40 },
              }}
            >
              <Typography sx={{ fontSize: 8, color: '#666', lineHeight: 1 }}>{el.number}</Typography>
              <Typography sx={{ fontSize: 20, fontWeight: 'bold', lineHeight: 1.2, '@media (max-width: 1160px)': { fontSize: 16 }, '@media (max-width: 768px)': { fontSize: 14 } }}>
                {el.symbol}
              </Typography>
              <Typography sx={{ fontSize: 9, color: '#666', lineHeight: 1, '@media (max-width: 768px)': { display: 'none' } }}>
                {el.symbol}
              </Typography>
            </Box>
          )
        })
      )}
    </Box>
  )
}

export default PeriodicTable
```

---

### Task 8: HomePage

**Files:**
- Create: `frontend_new/src/pages/HomePage.tsx`

**Design reference:** elements.html periodic table layout + chart sections

- [ ] **Step 1: Write HomePage.tsx**

```typescript
import React, { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Typography, Card, CardContent, Button, Chip, ToggleButtonGroup, ToggleButton,
  Alert,
} from '@mui/material'
import PeriodicTable from '../components/PeriodicTable'

const SEARCH_MODES = [
  { value: 'combination', label: '选择元素的组合' },
  { value: 'only', label: '仅包含选择元素' },
  { value: 'contains', label: '包含所选元素' },
]

const HomePage: React.FC = () => {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [mode, setMode] = useState('combination')

  const toggleElement = (symbol: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(symbol)) next.delete(symbol)
      else next.add(symbol)
      return next
    })
  }

  const clearSelection = () => setSelected(new Set())

  const handleEnter = () => {
    if (selected.size === 0) return
    const elements = [...selected].sort().join(',')
    const modeMap: Record<string, string> = {
      combination: 'elements_combination_search',
      only: 'elements_exact_search',
      contains: 'elements_contained_search',
    }
    navigate(`/search?elements=${elements}&mode=${modeMap[mode]}`)
  }

  const disabledElements = useMemo(() => new Set(['Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac', 'Rf', 'Db', 'Sg', 'Bh', 'Hs', 'Mt', 'Ds', 'Rg', 'Cn', 'Nh', 'Fl', 'Mc', 'Lv', 'Ts', 'Og']), [])

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 3, alignItems: 'end', mb: 3 }}>
        <Box>
          <Typography variant="overline">Periodic Table Explorer</Typography>
          <Typography variant="h1">超导文献数据库</Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            基于元素周期表的超导材料文献检索系统
          </Typography>
        </Box>
      </Box>

      {/* Selection Panel */}
      <Card sx={{ maxWidth: '80%', mx: 'auto', mb: 4 }}>
        <CardContent>
          <Typography variant="h3" gutterBottom>
            已选元素：{selected.size > 0 ? [...selected].join(', ') : '未选择'}
          </Typography>
          <Typography variant="body2" sx={{ mb: 2 }}>
            点击元素进行选择，选中后再次点击可取消。选择完成后点击下方按钮或按Enter键进入页面。
          </Typography>

          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
            {/* Mode Selector — Apple-style tabs via ToggleButtonGroup */}
            <ToggleButtonGroup
              value={mode}
              exclusive
              onChange={(_, v) => v && setMode(v)}
              size="small"
              sx={{
                bgcolor: '#e8e8ed', borderRadius: '20px', p: 0.5,
                '& .MuiToggleButton-root': {
                  border: 'none', borderRadius: '16px', px: 3.5, py: 1,
                  fontSize: '0.9rem', color: 'text.primary',
                  '&.Mui-selected': { bgcolor: 'primary.main', color: '#fff', '&:hover': { bgcolor: 'primary.main' } },
                },
              }}
            >
              {SEARCH_MODES.map((m) => (
                <ToggleButton key={m.value} value={m.value}>{m.label}</ToggleButton>
              ))}
            </ToggleButtonGroup>

            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button variant="contained" disabled={selected.size === 0} onClick={handleEnter}>
                进入页面
              </Button>
              <Button variant="outlined" onClick={clearSelection}>
                清除选择
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Periodic Table */}
      <Box sx={{ overflowX: 'auto', py: 2 }}>
        <PeriodicTable selected={selected} onToggle={toggleElement} disabledElements={disabledElements} />
      </Box>

      {/* Info Card */}
      <Card sx={{ mt: 4 }}>
        <CardContent>
          <Typography variant="h3">使用说明</Typography>
          <ul>
            <li>选择一个或多个元素，系统将显示含有这些元素的超导体文献</li>
            <li>选择多个元素时，显示<strong>同时包含所有选中元素</strong>的化合物文献</li>
            <li>如果元素组合暂无文献，系统会提示您重新选择</li>
            <li>支持键盘Enter键快捷跳转</li>
          </ul>
        </CardContent>
      </Card>
    </Box>
  )
}

export default HomePage
```

---

### Task 9: SearchPage (DataGrid + Filters + Detail Drawer)

**Files:**
- Create: `frontend_new/src/pages/SearchPage.tsx`

- [ ] **Step 1: Write SearchPage.tsx**

```typescript
import React, { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Box, Typography, Card, CardContent, Button, Chip, TextField, ToggleButtonGroup, ToggleButton,
  Drawer, IconButton, CircularProgress, LinearProgress, Snackbar, Alert,
} from '@mui/material'
import { DataGrid, GridColDef, GridRowParams } from '@mui/x-data-grid'
import CloseIcon from '@mui/icons-material/Close'
import { api } from '../lib/api'

const SOURCES = [
  { value: 'local', label: '本地数据库' },
  { value: 'alexandria', label: 'Alexandria' },
  { value: 'htsc2025', label: 'HTSC-2025' },
  { value: 'all', label: '全部来源' },
]

const COLUMNS: GridColDef[] = [
  { field: 'year', headerName: '年份', width: 70 },
  { field: 'formula', headerName: 'Formula', width: 120, renderCell: (p) => p.value || p.row.chemical_formula || '-' },
  { field: 'superconductor_type', headerName: '类型', width: 100 },
  { field: 'pressure_gpa', headerName: '压强', width: 100, renderCell: (p) => p.value != null ? `${p.value} GPa` : '-' },
  { field: 'representative_tc', headerName: 'Tc', width: 100, renderCell: (p) => p.value != null ? `${p.value} K` : '-' },
  { field: 'space_group', headerName: '空间群', width: 100 },
  { field: '_source', headerName: '来源', width: 90, renderCell: (p) => <Chip label={p.value === 'local' ? 'Local' : p.value === 'alexandria' ? 'Alex' : 'HTSC'} size="small" color={p.value === 'local' ? 'primary' : p.value === 'alexandria' ? 'secondary' : 'default'} variant="tonal" /> },
  { field: 'review_status', headerName: '审核', width: 90, renderCell: (p) => <Chip label={p.value || '-'} size="small" color={p.value === 'approved' ? 'success' : 'warning'} variant="tonal" /> },
  { field: 'doi', headerName: 'DOI', width: 150 },
]

const SearchPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  const elementsParam = searchParams.get('elements') || ''
  const modeParam = searchParams.get('mode') || 'elements_combination_search'
  const selectedElements = elementsParam ? elementsParam.split(',') : []

  const [source, setSource] = useState('local')
  const [keyword, setKeyword] = useState('')
  const [rows, setRows] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(30)
  const [selectedRow, setSelectedRow] = useState<any>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [snackbar, setSnackbar] = useState('')

  const doSearch = useCallback(async () => {
    if (selectedElements.length === 0) return
    setLoading(true)
    try {
      interface SearchResult { items: any[]; total: number; ok?: boolean }
      let data: SearchResult
      if (source === 'all') {
        const res = await api.post<SearchResult>('/api/papers/search/all', {
          elements: selectedElements,
          mode: modeParam === 'elements_combination_search' ? 'combination' : modeParam === 'elements_exact_search' ? 'only' : 'contains',
          keyword: keyword || undefined,
          limit: pageSize,
          offset: page * pageSize,
        })
        data = res
      } else if (source === 'local') {
        const res = await api.post<SearchResult>('/api/papers/search-by-mode', {
          elements: selectedElements,
          mode: modeParam,
          keyword: keyword || undefined,
          limit: pageSize,
          offset: page * pageSize,
        })
        data = res
      } else {
        setRows([])
        setTotal(0)
        setLoading(false)
        return
      }
      setRows(data.items || [])
      setTotal(data.total || 0)
    } catch (err: any) {
      setSnackbar(err.message || '搜索失败')
    } finally {
      setLoading(false)
    }
  }, [selectedElements.join(','), modeParam, source, keyword, page, pageSize])

  useEffect(() => { doSearch() }, [doSearch])

  const handleRowClick = (params: GridRowParams) => {
    setSelectedRow(params.row)
    setDrawerOpen(true)
  }

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 3, alignItems: 'end', mb: 3 }}>
        <Box>
          <Typography variant="overline">Database Discovery</Typography>
          <Typography variant="h1">比较超导记录并查看完整科研细节</Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            默认展示本地数据库，支持元素组合、Formula、Tc、压强、年份、空间群和 DOI 筛选。
          </Typography>
        </Box>
      </Box>

      {/* Search Context */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
        {selectedElements.map((el) => (
          <Chip key={el} label={el} color="primary" variant="tonal" />
        ))}
        <Chip label={modeParam === 'elements_exact_search' ? '仅包含' : modeParam === 'elements_contained_search' ? '包含所选' : '元素组合'} variant="outlined" />
      </Box>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          {/* Source Selector */}
          <ToggleButtonGroup value={source} exclusive onChange={(_, v) => v && setSource(v)} size="small" sx={{ mb: 2 }}>
            {SOURCES.map((s) => (
              <ToggleButton key={s.value} value={s.value}>{s.label}</ToggleButton>
            ))}
          </ToggleButtonGroup>

          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2 }}>
            <TextField label="Formula" size="small" value={keyword} onChange={(e) => setKeyword(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && doSearch()} />
            <TextField label="Tc 最小值 (K)" size="small" type="number" />
            <TextField label="压强范围 (GPa)" size="small" />
          </Box>
        </CardContent>
      </Card>

      {/* Results: Two-column layout */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1.6fr 0.9fr', gap: 3 }}>
        {/* Data Table */}
        <Card>
          <CardContent sx={{ p: '0 !important' }}>
            {loading && <LinearProgress />}
            <DataGrid
              rows={rows.map((r, i) => ({ id: r.id || i, ...r }))}
              columns={COLUMNS}
              rowCount={total}
              paginationModel={{ page, pageSize }}
              onPaginationModelChange={(m) => { setPage(m.page); setPageSize(m.pageSize) }}
              pageSizeOptions={[30, 50, 100]}
              paginationMode="server"
              onRowClick={handleRowClick}
              loading={loading}
              autoHeight
              sx={{ border: 'none' }}
            />
          </CardContent>
        </Card>

        {/* Detail Side Sheet */}
        <Drawer anchor="right" open={drawerOpen} onClose={() => setDrawerOpen(false)} PaperProps={{ sx: { width: 420, p: 3 } }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h3">记录详情</Typography>
            <IconButton onClick={() => setDrawerOpen(false)}><CloseIcon /></IconButton>
          </Box>
          {selectedRow && (
            <Box>
              <Typography variant="h2">{selectedRow.formula || selectedRow.chemical_formula || '-'}</Typography>
              <Box sx={{ display: 'flex', gap: 1, my: 2 }}>
                <Chip label={selectedRow.review_status || 'pending'} color={selectedRow.review_status === 'approved' ? 'success' : 'warning'} variant="tonal" />
                <Chip label={selectedRow._source || 'local'} color="primary" variant="tonal" />
              </Box>
              <Typography variant="body2" sx={{ mb: 1 }}>DOI: {selectedRow.doi || '-'}</Typography>
              <Typography variant="body2" sx={{ mb: 1 }}>压强: {selectedRow.pressure_gpa != null ? `${selectedRow.pressure_gpa} GPa` : '-'}</Typography>
              <Typography variant="body2" sx={{ mb: 1 }}>Tc: {selectedRow.experimental_tc || selectedRow.allen_dynes_tc || selectedRow.mcmillan_tc || '-'} K</Typography>
              <Typography variant="body2">来源: {selectedRow._source || 'local'}</Typography>
            </Box>
          )}
        </Drawer>
      </Box>

      <Snackbar open={!!snackbar} autoHideDuration={4000} onClose={() => setSnackbar('')}>
        <Alert severity="error">{snackbar}</Alert>
      </Snackbar>
    </Box>
  )
}

export default SearchPage
```

---

### Task 10: RagPage (MUI Rewrite)

**Files:**
- Create: `frontend_new/src/pages/RagPage.tsx`

**Strategy:** Keep the core logic from frontend_test's RagPage.tsx but replace Bootstrap/inline styles with MUI components.

- [ ] **Step 1: Write RagPage.tsx (MUI version)**

```typescript
import React, { useState, useRef, useEffect, useMemo } from 'react'
import {
  Box, Typography, Button, IconButton, Chip, List, ListItemButton, ListItemText,
  TextField, Paper, CircularProgress, Divider,
} from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import { useStreamingChat } from '../lib/useStreamingChat'
import MarkdownMessage from '../components/MarkdownMessage'
import EvidenceCard from '../components/EvidenceCard'

function citationOrder(content: string): string[] {
  const ids: string[] = []
  for (const m of content.matchAll(/\[PID_(\d+)\]/g)) {
    if (!ids.includes(m[1])) ids.push(m[1])
  }
  return ids
}

const SUGGESTIONS = ['LaH10 的 Tc 是多少?', '超导温度高于 200K 的有哪些?', '笼状氢化物是什么?']

const RagPage: React.FC = () => {
  const {
    convs, activeId, messages, loading, papers, top10, streamRef: _streamRef,
    ideas, reviews, statusLog, savedPapers,
    newConversation, switchConversation, deleteConversation, send,
  } = useStreamingChat()

  const [input, setInput] = useState('')
  const [exploreMode, setExploreMode] = useState(false)
  const [sourceOpen, setSourceOpen] = useState(true)
  const [isStreaming, setIsStreaming] = useState(false)
  const chatBoxRef = useRef<HTMLDivElement>(null)
  const streamDivRef = useRef<HTMLDivElement>(null)

  useEffect(() => { chatBoxRef.current?.scrollTo(0, chatBoxRef.current.scrollHeight) }, [messages, loading, ideas])

  useEffect(() => {
    if (!loading) { setIsStreaming(false); return }
    const check = setInterval(() => {
      if (streamDivRef.current?.textContent) setIsStreaming(true)
    }, 100)
    return () => clearInterval(check)
  }, [loading])

  const handleSend = () => { const q = input; setInput(''); send(q, exploreMode) }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const citedOrder = useMemo(() => {
    const last = [...messages].reverse().find((m) => m.role === 'assistant')
    return last ? citationOrder(last.content) : []
  }, [messages])

  const paperSeqMap = useMemo(() => {
    const map: Record<string, number> = {}
    savedPapers.forEach((p, i) => { map[p.pid] = i + 1 })
    return map
  }, [savedPapers])

  return (
    <Box sx={{ height: 'calc(100vh - 72px - 64px)', display: 'flex', ml: -4, mr: -4, mt: -4 }}>
      {/* Left: Conversation List */}
      <Box sx={{ width: 230, flexShrink: 0, bgcolor: 'background.paper', borderRight: 1, borderColor: 'divider', display: 'flex', flexDirection: 'column', p: 1.5 }}>
        <Button fullWidth variant="outlined" onClick={newConversation} sx={{ mb: 1.5 }}>+ 新对话</Button>
        <List dense sx={{ flex: 1, overflow: 'auto' }}>
          {convs.map((c) => (
            <ListItemButton key={c.id} selected={c.id === activeId} onClick={() => switchConversation(c.id)} sx={{ borderRadius: 2, mb: 0.5 }}>
              <ListItemText primary={c.title} secondary={new Date(c.createdAt).toLocaleDateString()} primaryTypographyProps={{ fontSize: 13, noWrap: true }} secondaryTypographyProps={{ fontSize: 11 }} />
              <IconButton size="small" onClick={(e) => { e.stopPropagation(); deleteConversation(c.id) }} sx={{ color: '#ccc', '&:hover': { color: '#e55' } }}>✕</IconButton>
            </ListItemButton>
          ))}
        </List>
      </Box>

      {/* Center: Chat */}
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, bgcolor: '#fafafa' }}>
        <Box ref={chatBoxRef} sx={{ flex: 1, overflow: 'auto', p: '20px 0' }}>
          <Box sx={{ maxWidth: 720, mx: 'auto' }}>
            {messages.length === 0 && (
              <Box sx={{ textAlign: 'center', pt: '20vh' }}>
                <Typography variant="h1" sx={{ fontSize: 28, mb: 1 }}>氢化物超导文献助手</Typography>
                <Typography variant="body2" sx={{ mb: 3 }}>基于超导论文数据库，问任何关于氢化物超导的问题</Typography>
                {SUGGESTIONS.map((s) => (
                  <Chip key={s} label={s} onClick={() => { setInput(s); send(s, exploreMode) }} sx={{ m: 0.5 }} />
                ))}
              </Box>
            )}

            {messages.map((msg, i) => {
              const isUser = msg.role === 'user'
              const isAssistant = msg.role === 'assistant'
              const emptyAssistant = isAssistant && !msg.content && loading
              const beforeAssistant = isUser && messages[i + 1]?.role === 'assistant'

              return (
                <React.Fragment key={i}>
                  {isUser && (
                    <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
                      <Paper sx={{ maxWidth: '70%', p: '10px 16px', borderRadius: '18px', bgcolor: 'primary.main', color: 'primary.contrastText', fontSize: 14, lineHeight: 1.7 }}>
                        {msg.content}
                      </Paper>
                    </Box>
                  )}

                  {beforeAssistant && statusLog.length > 0 && (
                    <Box sx={{ mb: 1.5 }}>
                      {statusLog.map((s, j) => (
                        <Typography key={j} variant="body2" sx={{ color: '#888', fontWeight: 500, lineHeight: 1.8 }}>{s}</Typography>
                      ))}
                    </Box>
                  )}

                  {isAssistant && msg.content && (
                    <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
                      <Paper sx={{ maxWidth: '85%', p: '12px 18px', borderRadius: '18px', bgcolor: 'background.paper', border: 1, borderColor: 'divider' }}>
                        <MarkdownMessage content={msg.content} papers={papers} paperSeqMap={paperSeqMap} />
                      </Paper>
                    </Box>
                  )}

                  {emptyAssistant && (
                    <>
                      {isStreaming && (
                        <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2 }}>
                          <Paper ref={streamDivRef} sx={{ maxWidth: '85%', p: '12px 18px', borderRadius: '18px', bgcolor: 'background.paper', border: 1, borderColor: 'divider' }} />
                        </Box>
                      )}
                      {!isStreaming && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, p: '4px 0 12px' }}>
                          {[0, 0.2, 0.4].map((delay) => (
                            <Box key={delay} sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#999', animation: 'blink 1.2s infinite', animationDelay: `${delay}s`, '@keyframes blink': { '0%,60%,100%': { opacity: 0.3, transform: 'scale(0.8)' }, '30%': { opacity: 1, transform: 'scale(1)' } } }} />
                          ))}
                          <Typography variant="body2" sx={{ ml: 0.5 }}>思考中...</Typography>
                        </Box>
                      )}
                    </>
                  )}
                </React.Fragment>
              )
            })}

            {ideas.length > 0 && (
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', mb: 2, maxWidth: '85%' }}>
                {ideas.map((idea, i) => (
                  <EvidenceCard key={i} idea={idea} review={reviews[i]} paperSeqMap={paperSeqMap} />
                ))}
              </Box>
            )}
          </Box>
        </Box>

        {/* Input Bar */}
        <Box sx={{ p: '12px 20px 20px', bgcolor: '#fafafa' }}>
          <Box sx={{ maxWidth: 720, mx: 'auto', display: 'flex', alignItems: 'center', bgcolor: 'background.paper', borderRadius: '24px', border: 1, borderColor: 'divider', p: '4px 4px 4px 16px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}>
            <TextField
              fullWidth
              variant="standard"
              InputProps={{ disableUnderline: true }}
              placeholder={exploreMode ? "说说你的想法，AI 帮你探索研究方向..." : "问一个超导问题..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
              sx={{ flex: 1 }}
            />
            <Button
              size="small"
              variant={exploreMode ? 'contained' : 'outlined'}
              onClick={() => setExploreMode(!exploreMode)}
              sx={{ borderRadius: '18px', mr: 0.75, flexShrink: 0, whiteSpace: 'nowrap' }}
            >
              🔬 探索模式
            </Button>
            <IconButton
              onClick={handleSend}
              disabled={!input.trim() || loading}
              sx={{ width: 34, height: 34, bgcolor: 'primary.main', color: 'primary.contrastText', '&:hover': { bgcolor: 'primary.dark' }, '&.Mui-disabled': { opacity: 0.3 } }}
            >
              <SendIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Box>
        </Box>
      </Box>

      {/* Right: Sources Panel */}
      {sourceOpen && (
        <Box sx={{ width: 300, flexShrink: 0, bgcolor: 'background.paper', borderLeft: 1, borderColor: 'divider', display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: 1.5, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="caption">文献来源</Typography>
            <IconButton size="small" onClick={() => setSourceOpen(false)}>✕</IconButton>
          </Box>
          <Box sx={{ flex: 1, overflow: 'auto', p: 1.5 }}>
            {savedPapers.length > 0 ? savedPapers.map(({ pid, info: p }, i) => (
              <Box key={pid} sx={{ py: 1, borderBottom: 1, borderColor: 'divider' }}>
                <Typography variant="body2" fontWeight={600}>
                  <Chip label={`[${i + 1}]`} size="small" color="primary" variant="tonal" sx={{ mr: 0.75 }} />
                  {p.title || `Paper #${pid}`}
                </Typography>
                {p.journal && <Typography variant="caption" sx={{ ml: 3 }}>{p.journal}{p.year ? ` (${p.year})` : ''}</Typography>}
              </Box>
            )) : (
              <Typography variant="body2" sx={{ color: '#999' }}>探索模式下筛选的文献将显示在此处</Typography>
            )}
          </Box>
        </Box>
      )}
    </Box>
  )
}

export default RagPage
```

---

### Task 11: TcPredictPage

**Files:**
- Create: `frontend_new/src/pages/TcPredictPage.tsx`

- [ ] **Step 1: Write TcPredictPage.tsx**

```typescript
import React, { useState, useRef } from 'react'
import {
  Box, Typography, Card, CardContent, Button, CircularProgress, Alert,
} from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import { api } from '../lib/api'

const TcPredictPage: React.FC = () => {
  const [contcar, setContcar] = useState<File | null>(null)
  const [pdosFiles, setPdosFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')
  const contcarRef = useRef<HTMLInputElement>(null)
  const pdosRef = useRef<HTMLInputElement>(null)

  const handleSubmit = async () => {
    if (!contcar || pdosFiles.length === 0) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const form = new FormData()
      form.append('contcar', contcar)
      pdosFiles.forEach((f) => form.append('pdos_files', f))
      const data = await api.post<any>('/api/tc-predict/', form)
      setResult(data)
    } catch (err: any) {
      setError(err.message || '预测失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      <Box sx={{ mb: 3 }}>
        <Typography variant="overline">AI-Assisted Tc Estimation</Typography>
        <Typography variant="h1">超导临界温度预测</Typography>
        <Typography variant="body2" sx={{ mt: 1 }}>
          上传 CONTCAR 结构文件和 PDOS 态密度数据，系统将计算预测 Tc 值
        </Typography>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h3" gutterBottom>输入文件</Typography>

          {/* CONTCAR */}
          <Box
            onClick={() => contcarRef.current?.click()}
            sx={{
              border: '2px dashed', borderColor: 'divider', borderRadius: 3, p: 3, mb: 2,
              textAlign: 'center', cursor: 'pointer', bgcolor: 'grey.50',
              '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' },
            }}
          >
            <CloudUploadIcon sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
            <Typography variant="body2">{contcar ? contcar.name : '点击上传 CONTCAR 文件'}</Typography>
            <input ref={contcarRef} type="file" hidden onChange={(e) => setContcar(e.target.files?.[0] || null)} />
          </Box>

          {/* PDOS */}
          <Box
            onClick={() => pdosRef.current?.click()}
            sx={{
              border: '2px dashed', borderColor: 'divider', borderRadius: 3, p: 3, mb: 2,
              textAlign: 'center', cursor: 'pointer', bgcolor: 'grey.50',
              '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' },
            }}
          >
            <CloudUploadIcon sx={{ fontSize: 40, color: 'text.secondary', mb: 1 }} />
            <Typography variant="body2">
              {pdosFiles.length > 0 ? pdosFiles.map((f) => f.name).join(', ') : '点击上传 PDOS 文件（需包含 PDOS_H.dat）'}
            </Typography>
            <input ref={pdosRef} type="file" multiple hidden onChange={(e) => setPdosFiles([...(e.target.files || [])])} />
          </Box>

          <Button
            variant="contained"
            fullWidth
            onClick={handleSubmit}
            disabled={!contcar || pdosFiles.length === 0 || loading}
            startIcon={loading ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {loading ? '预测中...' : '开始预测'}
          </Button>
        </CardContent>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 3 }}>{error}</Alert>}

      {result && (
        <Card>
          <CardContent>
            <Typography variant="h3" gutterBottom>预测结果</Typography>
            <Typography variant="h1" sx={{ color: 'primary.main' }}>{result.predicted_tc} K</Typography>
            <Box sx={{ mt: 2, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
              <Typography variant="body2">f2 值: {result.f2_value}</Typography>
              <Typography variant="body2">H 态密度占比: {result.dos_h_ratio}</Typography>
              <Typography variant="body2">H-H 键长均值: {result.bonds_mean}</Typography>
              <Typography variant="body2">H-H 键长方差: {result.bonds_var}</Typography>
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  )
}

export default TcPredictPage
```

---

### Task 12: ChartsPage

**Files:**
- Create: `frontend_new/src/pages/ChartsPage.tsx`

- [ ] **Step 1: Write ChartsPage.tsx**

```typescript
import React, { useState, useEffect } from 'react'
import {
  Box, Typography, Card, CardContent, Tabs, Tab, IconButton, Drawer, Chip,
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'
import RestartAltIcon from '@mui/icons-material/RestartAlt'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Line } from 'recharts'
import { api } from '../lib/api'

interface ChartPoint {
  x: number; y: number; type: string; label: string; year?: number;
  formula?: string; space_group?: string; doi?: string; sc_type?: string;
}

const SC_TYPES: Record<string, string> = {
  cuprate: '#ff6384', iron_based: '#4bc0c0', nickel_based: '#4bef3a',
  hydride: '#9966ff', carbon: '#36a2eb', organic: '#ffce56', others: '#cc4646',
}

const ChartsPage: React.FC = () => {
  const [tab, setTab] = useState(0)
  const [data, setData] = useState<ChartPoint[]>([])
  const [selectedPoint, setSelectedPoint] = useState<ChartPoint | null>(null)

  useEffect(() => {
    const endpoint = tab === 0 ? '/api/papers/stats/tc-pressure' : '/api/papers/stats/tc-year'
    api.get<ChartPoint[]>(endpoint).then(setData).catch(() => {})
  }, [tab])

  const expData = data.filter((d) => d.type === 'experimental')
  const theoData = data.filter((d) => d.type === 'theoretical')

  // s-factor curves for Tc-pressure chart
  const sCurves = Array.from({ length: 10 }, (_, i) => {
    const s = i + 1
    const points = []
    for (let p = 0; p <= 300; p += 10) {
      points.push({ x: p, y: s * Math.sqrt(1521 + p * p) })
    }
    return { s, points }
  })

  return (
    <Box sx={{ ml: -4, mr: -4, mt: -4 }}>
      <Card sx={{ borderRadius: 0, mb: 3 }}>
        <CardContent>
          <Typography variant="overline">Research Community Charts</Typography>
          <Typography variant="h1">超导热点图表</Typography>
        </CardContent>
      </Card>

      <Box sx={{ px: 4 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
          <Tab label="Tc vs Pressure" />
          <Tab label="Tc vs Year" />
        </Tabs>

        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h3">{tab === 0 ? 'Tc-Pressure 分布' : 'Tc-Year 演变'}</Typography>
              <Box>
                <IconButton size="small"><DownloadIcon /></IconButton>
                <IconButton size="small"><RestartAltIcon /></IconButton>
              </Box>
            </Box>

            <ResponsiveContainer width="100%" height={400}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  dataKey="x"
                  name={tab === 0 ? 'Pressure' : 'Year'}
                  label={{ value: tab === 0 ? 'Pressure (GPa)' : 'Year', position: 'bottom' }}
                  domain={tab === 0 ? [0, 300] : [1900, 2040]}
                />
                <YAxis type="number" dataKey="y" name="Tc" label={{ value: 'Tc (K)', angle: -90, position: 'insideLeft' }} domain={[0, 350]} />
                <Tooltip cursor={{ strokeDasharray: '3 3' }} formatter={(value: number, name: string) => [`${value} ${name === 'y' ? 'K' : name === 'x' && tab === 0 ? 'GPa' : ''}`, name === 'y' ? 'Tc' : name === 'x' && tab === 0 ? 'Pressure' : 'Year']} />
                <Legend />

                {/* s-factor curves (Tc-pressure only) */}
                {tab === 0 && sCurves.map(({ s, points }) => (
                  <Line key={`s${s}`} data={points} dataKey="y" stroke="rgba(0,0,0,0.08)" strokeDasharray="5 5" dot={false} legendType="none" />
                ))}

                <Scatter name="实验" data={expData} fill="#8884d8" shape="square" onClick={(p: any) => setSelectedPoint(p)} />
                <Scatter name="理论" data={theoData} fill="#82ca9d" shape="triangle" onClick={(p: any) => setSelectedPoint(p)} />

                {/* Superconductor type legend (dummy) */}
                {Object.entries(SC_TYPES).map(([type, color]) => (
                  <Scatter key={type} name={type} data={[]} fill={color} legendType="rect" />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Box>

      {/* Point Detail Drawer */}
      <Drawer anchor="right" open={!!selectedPoint} onClose={() => setSelectedPoint(null)} PaperProps={{ sx: { width: 360, p: 3 } }}>
        {selectedPoint && (
          <>
            <Typography variant="h3" gutterBottom>{selectedPoint.label || selectedPoint.formula}</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Typography variant="body2">Tc: {selectedPoint.y} K</Typography>
              <Typography variant="body2">{tab === 0 ? `压强: ${selectedPoint.x} GPa` : `年份: ${selectedPoint.x}`}</Typography>
              <Typography variant="body2">类型: {selectedPoint.type}</Typography>
              <Typography variant="body2">空间群: {selectedPoint.space_group || '-'}</Typography>
              {selectedPoint.doi && <Typography variant="body2">DOI: {selectedPoint.doi}</Typography>}
            </Box>
          </>
        )}
      </Drawer>
    </Box>
  )
}

export default ChartsPage
```

---

### Task 13: Verify Complete App

- [ ] **Step 1: Start dev server**

Run: `cd /home/work/workshop/git/SC-Wiki/frontend_new && npx vite`

- [ ] **Step 2: Test all routes**

| Route | Expected |
|------|------|
| `http://localhost:5173/` | Periodic table + element selection + mode toggle |
| `http://localhost:5173/search?elements=La,H&mode=elements_combination_search` | Search results table + filters + detail drawer |
| `http://localhost:5173/rag` | Chat interface with conversation list + source panel |
| `http://localhost:5173/tc-predict` | File upload cards + predict button |
| `http://localhost:5173/charts` | Recharts scatter with tab switching |

- [ ] **Step 3: Visual comparison with HTML demos**

Open browser side-by-side:
- `future-plan/03-data-search-and-database-discovery/index.html` vs `/search`
- `future-plan/05-rag-question-answering/index.html` vs `/rag`
- `future-plan/06-ai-assisted-tc-estimation/index.html` vs `/tc-predict`
- `future-plan/07-researcher-community-forum/index.html` vs `/charts`

Check: card border-radius (16px), button pill shape, chip pill shape, table row styling, side sheet width, typography hierarchy.
