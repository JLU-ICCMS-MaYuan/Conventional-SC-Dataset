import React, { useEffect, useMemo, useState } from 'react'
import {
  Alert, Box, Button, Dialog, DialogActions, DialogContent, DialogTitle,
  IconButton, InputAdornment, MenuItem, Select, Stack, TextField, Tooltip, Typography,
} from '@mui/material'
import {
  SmartToy as SmartToyIcon, Visibility as VisibilityIcon, VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material'
import { useLanguage } from '../context/LanguageContext'
import {
  clearLlmConfig, maskApiKey, PROVIDER_PRESETS, readStoredLlmConfig,
  saveLlmConfig, validateLlmBaseUrl,
} from '../lib/llmProvider'
import { api } from '../lib/api'

const DEFAULT_ID = 'server-default'

interface CurrentLlm {
  provider: string
  provider_name: string
  model: string
  source: 'browser' | 'server'
}

const LlmProviderSwitcher: React.FC = () => {
  const { lang } = useLanguage()
  const [open, setOpen] = useState(false)
  const [saved, setSaved] = useState(readStoredLlmConfig)
  const [provider, setProvider] = useState(saved?.provider || DEFAULT_ID)
  const [baseUrl, setBaseUrl] = useState(saved?.baseUrl || '')
  const [model, setModel] = useState(saved?.model || '')
  const [apiKey, setApiKey] = useState(saved?.apiKey || '')
  const [showApiKey, setShowApiKey] = useState(false)
  const [error, setError] = useState('')
  const [connection, setConnection] = useState('')
  const [testing, setTesting] = useState(false)
  const [serverDefault, setServerDefault] = useState<CurrentLlm | null>(null)

  const { t } = useLanguage()
  const current = useMemo(
    () => {
      if (saved) {
        const label = PROVIDER_PRESETS.find(item => item.id === saved.provider)?.label || saved.provider
        return `${label} · ${saved.model}`
      }
      return serverDefault?.model
        ? `${serverDefault.provider_name} · ${serverDefault.model}`
        : t('nav.llmDefault')
    },
    [saved, serverDefault, t],
  )
  const selected = PROVIDER_PRESETS.find(item => item.id === provider) || PROVIDER_PRESETS[0]
  const isDefault = provider === DEFAULT_ID

  useEffect(() => {
    if (saved) return
    let active = true
    api.get<{ data: CurrentLlm }>('/api/rag/llm/current')
      .then(result => { if (active) setServerDefault(result.data) })
      .catch(() => { if (active) setServerDefault(null) })
    return () => { active = false }
  }, [saved])

  const openPanel = () => {
    const config = readStoredLlmConfig()
    setSaved(config)
    setProvider(config?.provider || DEFAULT_ID)
    setBaseUrl(config?.baseUrl || '')
    setModel(config?.model || '')
    setApiKey(config?.apiKey || '')
    setShowApiKey(false)
    setError('')
    setConnection('')
    setOpen(true)
  }

  const selectProvider = (id: string) => {
    const preset = PROVIDER_PRESETS.find(item => item.id === id) || PROVIDER_PRESETS[0]
    setProvider(id)
    if (id === DEFAULT_ID) {
      setBaseUrl(''); setModel(''); setApiKey('')
    } else if (id !== saved?.provider) {
      setBaseUrl(''); setModel(''); setApiKey('')
    }
    setError(''); setConnection('')
    if (preset.id === 'custom') { setBaseUrl(''); setModel('') }
  }

  const save = () => {
    if (isDefault) {
      clearLlmConfig(); setSaved(null); setOpen(false); return
    }
    const finalBaseUrl = baseUrl.trim() || selected.baseUrl
    const finalModel = model.trim() || selected.model
    const urlError = validateLlmBaseUrl(finalBaseUrl)
    if (urlError) { setError(urlError); return }
    if (!finalModel || !apiKey.trim()) { setError(t('nav.llmKeyRequired')); return }
    const next = { provider, baseUrl: finalBaseUrl, model: finalModel, apiKey: apiKey.trim() }
    saveLlmConfig(next); setSaved(next); setOpen(false)
  }

  const testConnection = async () => {
    if (isDefault) { setConnection(t('nav.llmDefaultActive')); return }
    const finalBaseUrl = baseUrl.trim() || selected.baseUrl
    const urlError = validateLlmBaseUrl(finalBaseUrl)
    if (urlError || !model.trim() || !apiKey.trim()) { setError(urlError || t('nav.llmKeyRequired')); return }
    const prior = readStoredLlmConfig()
    saveLlmConfig({ provider, baseUrl: finalBaseUrl, model: model.trim(), apiKey: apiKey.trim() })
    setTesting(true); setError(''); setConnection('')
    try {
      const result = await api.post<{ data: { latency_ms: number } }>('/api/rag/llm/test-connection')
      setConnection(t('nav.llmConnected', { latency: result.data.latency_ms }))
    } catch (err: any) {
      setError(err.message || t('nav.llmConnectionFailed'))
      if (prior) saveLlmConfig(prior); else clearLlmConfig()
    } finally { setTesting(false) }
  }

  return <>
    <Button size="small" startIcon={<SmartToyIcon fontSize="small" />} onClick={openPanel} aria-label={t('nav.llmConfigure')} sx={{ textTransform: 'none', minWidth: 0 }}>
      {current}
    </Button>
    <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
      <DialogTitle>{t('nav.llmTitle')}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Select value={provider} onChange={event => selectProvider(event.target.value)} fullWidth aria-label={lang === 'en' ? 'AI provider' : 'AI 供应商'}>
            {PROVIDER_PRESETS.map(item => <MenuItem key={item.id} value={item.id}>{item.id === 'server-default' ? t('nav.llmServerDefault') : item.label}</MenuItem>)}
          </Select>
          {isDefault && serverDefault?.model && <Typography variant="body2" color="text.secondary">
            {t('nav.llmCurrentServer', { provider: serverDefault.provider_name, model: serverDefault.model })}
          </Typography>}
          {!isDefault && <>
            <TextField label="Base URL" value={baseUrl} onChange={event => setBaseUrl(event.target.value)} placeholder={selected.baseUrl || 'https://your-gateway.example.com/v1'} fullWidth />
            <TextField label={t('nav.llmModel')} value={model} onChange={event => setModel(event.target.value)} placeholder={selected.model || 'model-name'} fullWidth />
            <TextField
              label="API Key" value={apiKey} onChange={event => setApiKey(event.target.value)}
              type={showApiKey ? 'text' : 'password'} fullWidth
              slotProps={{ input: { endAdornment: <InputAdornment position="end">
                <Tooltip title={showApiKey ? t('nav.llmHideKey') : t('nav.llmShowKey')}>
                  <IconButton aria-label={showApiKey ? t('nav.llmHideKey') : t('nav.llmShowKey')} edge="end" onClick={() => setShowApiKey(value => !value)}>
                    {showApiKey ? <VisibilityOffIcon /> : <VisibilityIcon />}
                  </IconButton>
                </Tooltip>
              </InputAdornment> }}}
            />
            {apiKey && <Typography variant="caption" color="text.secondary">{t('nav.llmStoredKey', { key: maskApiKey(apiKey) })}</Typography>}
            <Typography variant="caption" color="text.secondary">{t('nav.llmKeyStorage')}</Typography>
            <Box>{error && <Alert severity="error">{error}</Alert>}{connection && <Alert severity="success">{connection}</Alert>}</Box>
          </>}
        </Stack>
      </DialogContent>
      <DialogActions>
        {!isDefault && <Button color="error" onClick={() => { clearLlmConfig(); setSaved(null); setProvider(DEFAULT_ID); setBaseUrl(''); setModel(''); setApiKey(''); setConnection(''); setError('') }}>{t('nav.llmClear')}</Button>}
        {!isDefault && <Button onClick={testConnection} disabled={testing}>{testing ? t('nav.llmTesting') : t('nav.llmTest')}</Button>}
        <Button onClick={() => setOpen(false)}>{t('nav.llmCancel')}</Button>
        <Button variant="contained" onClick={save}>{t('nav.llmSave')}</Button>
      </DialogActions>
    </Dialog>
  </>
}

export default LlmProviderSwitcher
