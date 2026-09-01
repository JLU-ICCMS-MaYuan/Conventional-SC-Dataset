import React, { useState, useRef } from 'react'
import { Box, Typography, Button, Chip, Paper, CircularProgress, LinearProgress } from '@mui/material'
import CloudUploadIcon from '@mui/icons-material/CloudUpload'
import { api } from '../lib/api'
import { useLanguage } from '../context/LanguageContext'

const TcPredictPage: React.FC = () => {
  const { t } = useLanguage()
  const [contcarFile, setContcarFile] = useState<File | null>(null)
  const [pdosFiles, setPdosFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')
  const contcarRef = useRef<HTMLInputElement>(null)
  const pdosRef = useRef<HTMLInputElement>(null)

  const handleSubmit = async () => {
    if (!contcarFile || pdosFiles.length === 0) return
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const form = new FormData()
      form.append('contcar', contcarFile)
      pdosFiles.forEach((f) => form.append('pdos_files', f))
      const data = await api.post<any>('/api/tc-predict/', form)
      setResult(data)
    } catch (err: any) {
      setError(err.message || t('tcPredict.failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 3, alignItems: 'end', mb: 3 }}>
        <Box>
          <Typography variant="overline">Tc Estimation</Typography>
          <Typography variant="h1">{t('tcPredict.title')}</Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            {t('tcPredict.disclaimer')}
          </Typography>
        </Box>
      </Box>

      {/* Two-column layout */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.6fr) minmax(320px, 0.9fr)', gap: 3 }}>
        {/* Left: Input + Config */}
        <Box sx={{ display: 'grid', gap: 3 }}>
          {/* Input files card */}
          <Paper sx={{ p: 2.5, borderRadius: 4 }}>
            <Typography variant="h2" gutterBottom>{t('tcPredict.inputFiles')}</Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              {/* CONTCAR */}
              <Box
                component="label"
                sx={{
                  p: 2, bgcolor: 'grey.50', borderRadius: 2, textAlign: 'center', cursor: 'pointer',
                  border: '2px dashed', borderColor: contcarFile ? 'success.main' : 'divider',
                  '&:hover': { borderColor: 'primary.main' }, display: 'block',
                }}
              >
                <CloudUploadIcon sx={{ fontSize: 32, color: 'text.secondary', mb: 1 }} />
                <Typography variant="h3">CONTCAR</Typography>
                <Chip label={contcarFile ? t('tcPredict.uploaded') : t('tcPredict.clickUpload')} size="small" color={contcarFile ? 'success' : 'default'} sx={{ mt: 1 }} />
                <input type="file" hidden onChange={(e) => setContcarFile(e.target.files?.[0] || null)} />
              </Box>
              {/* PDOS */}
              <Box
                component="label"
                sx={{
                  p: 2, bgcolor: 'grey.50', borderRadius: 2, textAlign: 'center', cursor: 'pointer',
                  border: '2px dashed', borderColor: pdosFiles.length > 0 ? 'success.main' : 'divider',
                  '&:hover': { borderColor: 'primary.main' }, display: 'block',
                }}
              >
                <CloudUploadIcon sx={{ fontSize: 32, color: 'text.secondary', mb: 1 }} />
                <Typography variant="h3">PDOS_H.dat</Typography>
                <Chip label={pdosFiles.length > 0 ? t('tcPredict.uploadedCount', { count: pdosFiles.length }) : t('tcPredict.clickUpload')} size="small" color={pdosFiles.length > 0 ? 'success' : 'default'} sx={{ mt: 1 }} />
                <input type="file" multiple hidden onChange={(e) => setPdosFiles([...(e.target.files || [])])} />
              </Box>
            </Box>
          </Paper>

        </Box>

        {/* Right: Result card */}
        <Paper sx={{
          p: 2.5, borderRadius: 4, alignSelf: 'start', position: 'sticky', top: 96,
          boxShadow: '0 6px 16px rgba(15,23,42,.16), 0 10px 24px rgba(15,23,42,.10)',
        }}>
          <Typography variant="h2" gutterBottom>{t('tcPredict.result')}</Typography>

          {loading && <LinearProgress sx={{ mb: 2, borderRadius: 999 }} />}

          {error && (
            <Paper sx={{ p: 2, bgcolor: '#fff0f0', borderRadius: 2, mb: 2 }}>
              <Typography variant="body2" color="error">{error}</Typography>
            </Paper>
          )}

          {result ? (
            <Box>
              <Typography sx={{ fontSize: 52, color: 'primary.main', fontWeight: 800 }}>
                {result.predicted_tc} K
              </Typography>
              <Box sx={{ mt: 2, display: 'grid', gap: 1 }}>
                <Typography variant="body2">f₂ = {result.f2_value}</Typography>
                <Typography variant="body2">{t('tcPredict.dosRatio', { value: result.dos_h_ratio })}</Typography>
                <Typography variant="body2">{t('tcPredict.bondMean', { value: result.bonds_mean })}</Typography>
                <Typography variant="body2">{t('tcPredict.bondVariance', { value: result.bonds_var })}</Typography>
              </Box>
              <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                <Chip label="PREDICTED ONLY" color="warning" size="small" />
              </Box>
            </Box>
          ) : (
            <Paper sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                {t('tcPredict.emptyHint')}
              </Typography>
            </Paper>
          )}

          <Button
            variant="contained"
            fullWidth
            onClick={handleSubmit}
            disabled={!contcarFile || pdosFiles.length === 0 || loading}
            sx={{ mt: 2.5, borderRadius: 999 }}
          >
            {loading ? t('tcPredict.predicting') : t('tcPredict.run')}
          </Button>
        </Paper>
      </Box>
    </Box>
  )
}

export default TcPredictPage
