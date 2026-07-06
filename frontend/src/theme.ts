import { createTheme } from '@mui/material/styles'
import type {} from '@mui/x-data-grid/themeAugmentation'

const theme = createTheme({
  palette: {
    primary: { main: '#4f46e5', contrastText: '#ffffff' },
    secondary: { main: '#0891b2', contrastText: '#ffffff' },
    error: { main: '#b3261e' },
    warning: { main: '#b45309' },
    success: { main: '#15803d' },
    background: { default: '#f8fafc', paper: '#ffffff' },
    text: { primary: '#1f2937', secondary: '#64748b' },
    divider: '#e2e8f0',
  },
  shape: { borderRadius: 8 },
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
    h1: { fontSize: 'clamp(32px, 5vw, 52px)', fontWeight: 700, lineHeight: 1.05, letterSpacing: '-0.01em' },
    h2: { fontSize: 20, fontWeight: 600 },
    h3: { fontSize: 16, fontWeight: 600 },
    overline: { fontSize: 12, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase' as const, color: '#4f46e5' },
    body1: { fontSize: 14, lineHeight: 1.65 },
    body2: { fontSize: 13 },
    caption: { fontSize: 12, fontWeight: 600 },
    button: { textTransform: 'none' as const, fontWeight: 700 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          margin: 0, minHeight: '100vh', backgroundColor: '#f8fafc', color: '#1f2937',
          fontFamily: '"Roboto", "Inter", system-ui, -apple-system, sans-serif',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 999, minHeight: 40, padding: '0 20px', fontSize: 14, fontWeight: 700, textTransform: 'none' as const },
        contained: { boxShadow: 'none', '&:hover': { boxShadow: 'none' } },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: { borderRadius: 16, borderColor: '#e2e8f0', boxShadow: '0 1px 2px rgba(15,23,42,0.12), 0 1px 3px rgba(15,23,42,0.08)' },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 999, height: 32, fontSize: 12, fontWeight: 700 },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: { boxShadow: '0 1px 2px rgba(15,23,42,0.12), 0 1px 3px rgba(15,23,42,0.08)' },
      },
    },
    MuiDataGrid: {
      styleOverrides: {
        root: { border: 'none', fontSize: 14 },
        columnHeader: { fontSize: 12, fontWeight: 800, color: '#64748b' },
        row: { '&.Mui-selected': { backgroundColor: '#e0e7ff !important' } },
        cell: { borderBottom: '1px solid #e2e8f0' },
      },
    },
    MuiDialog: {
      styleOverrides: { paper: { borderRadius: 16 } },
    },
  },
})

export default theme
