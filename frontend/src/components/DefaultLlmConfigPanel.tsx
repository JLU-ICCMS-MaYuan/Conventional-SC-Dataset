import React, { useEffect, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Dialog, DialogActions, DialogContent,
  DialogTitle, Stack, TextField, Typography,
} from '@mui/material'
import { Edit as EditIcon } from '@mui/icons-material'
import { useLanguage } from '../context/LanguageContext'
import { api } from '../lib/api'

interface DefaultLlmConfig {
  provider_name: string
  base_url: string
  model: string
  api_key_configured: boolean
  source: 'environment' | 'runtime'
}

const DefaultLlmConfigPanel: React.FC = () => {
  const { t } = useLanguage()
  const [config, setConfig] = useState<DefaultLlmConfig | null>(null)
  const [editing, setEditing] = useState(false)
  const [providerName, setProviderName] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  const applyConfig = (next: DefaultLlmConfig) => {
    setConfig(next)
    setProviderName(next.provider_name)
    setBaseUrl(next.base_url)
    setModel(next.model)
  }

  useEffect(() => {
    let active = true
    api.get<{ data: DefaultLlmConfig }>('/api/rag/llm/default-config')
      .then(result => {
        if (!active) return
        applyConfig(result.data)
      })
      .catch(() => { if (active) setMessage(t('admin.llmLoadFailed')) })
    return () => { active = false }
  }, [t])

  const openEditor = () => {
    setApiKey('')
    setMessage('')
    setEditing(true)
  }

  const save = async () => {
    setSaving(true)
    setMessage('')
    try {
      const result = await api.put<{ data: DefaultLlmConfig }>('/api/rag/llm/default-config', {
        provider_name: providerName, base_url: baseUrl, model, api_key: apiKey || undefined,
      })
      applyConfig(result.data)
      setApiKey('')
      setEditing(false)
    } catch (error: any) {
      setMessage(error.message || t('admin.llmSaveFailed'))
    } finally {
      setSaving(false)
    }
  }

  return <>
    <Card sx={{ borderLeft: '4px solid', borderColor: 'error.main' }}>
      <CardContent>
        <Typography variant="caption" color="text.secondary">{t('admin.llmDefaultTitle')}</Typography>
        <Typography variant="h6" fontWeight={700} noWrap title={config ? `${config.provider_name} · ${config.model}` : undefined}>
          {config ? `${config.provider_name} · ${config.model}` : '…'}
        </Typography>
        <Button size="small" startIcon={<EditIcon fontSize="small" />} onClick={openEditor} sx={{ mt: 1, px: 0, minWidth: 0 }}>
          {t('common.edit')}
        </Button>
      </CardContent>
    </Card>

    <Dialog open={editing} onClose={() => !saving && setEditing(false)} fullWidth maxWidth="sm">
      <DialogTitle>{t('admin.llmDefaultTitle')}</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>{t('admin.llmDefaultHint')}</Typography>
        <Stack spacing={1.5}>
          <TextField label={t('admin.llmProviderName')} value={providerName} onChange={event => setProviderName(event.target.value)} required fullWidth />
          <TextField label="Base URL" value={baseUrl} onChange={event => setBaseUrl(event.target.value)} required fullWidth />
          <TextField label={t('admin.llmModel')} value={model} onChange={event => setModel(event.target.value)} required fullWidth />
          <TextField
            label="API Key" value={apiKey} onChange={event => setApiKey(event.target.value)} type="password"
            placeholder={config?.api_key_configured ? t('admin.llmKeyKept') : ''} fullWidth
            helperText={t('admin.llmKeyHint')}
          />
          {config && <Typography variant="caption" color="text.secondary">
            {t('admin.llmSource', { source: config.source === 'runtime' ? t('admin.llmSourceRuntime') : t('admin.llmSourceEnvironment') })}
          </Typography>}
          {message && <Alert severity="error">{message}</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setEditing(false)} disabled={saving}>{t('common.cancel')}</Button>
        <Button variant="contained" onClick={() => void save()} disabled={saving}>{saving ? t('common.loading') : t('admin.llmSave')}</Button>
      </DialogActions>
    </Dialog>
  </>
}

export default DefaultLlmConfigPanel
