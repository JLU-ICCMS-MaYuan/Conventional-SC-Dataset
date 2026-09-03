import React, { useEffect, useState } from 'react'
import { Alert, Box, Button, Stack, TextField, Typography } from '@mui/material'
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
  const [providerName, setProviderName] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [model, setModel] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [message, setMessage] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let active = true
    api.get<{ data: DefaultLlmConfig }>('/api/rag/llm/default-config')
      .then(result => {
        if (!active) return
        setConfig(result.data)
        setProviderName(result.data.provider_name)
        setBaseUrl(result.data.base_url)
        setModel(result.data.model)
      })
      .catch(() => { if (active) setMessage(t('admin.llmLoadFailed')) })
    return () => { active = false }
  }, [t])

  const save = async () => {
    setSaving(true)
    setMessage('')
    try {
      const result = await api.put<{ data: DefaultLlmConfig }>('/api/rag/llm/default-config', {
        provider_name: providerName, base_url: baseUrl, model, api_key: apiKey || undefined,
      })
      setConfig(result.data)
      setProviderName(result.data.provider_name)
      setBaseUrl(result.data.base_url)
      setModel(result.data.model)
      setApiKey('')
      setMessage(t('admin.llmSaved'))
    } catch (error: any) {
      setMessage(error.message || t('admin.llmSaveFailed'))
    } finally {
      setSaving(false)
    }
  }

  return <Box sx={{ borderTop: '1px solid', borderColor: 'divider', pt: 3, mb: 3 }}>
    <Typography variant="h6" fontWeight={700}>{t('admin.llmDefaultTitle')}</Typography>
    <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, mb: 2 }}>
      {t('admin.llmDefaultHint')}
    </Typography>
    <Stack spacing={1.5} sx={{ maxWidth: 640 }}>
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
      {message && <Alert severity={message === t('admin.llmSaved') ? 'success' : 'error'}>{message}</Alert>}
      <Box><Button variant="contained" onClick={() => void save()} disabled={saving}>{saving ? t('common.loading') : t('admin.llmSave')}</Button></Box>
    </Stack>
  </Box>
}

export default DefaultLlmConfigPanel
