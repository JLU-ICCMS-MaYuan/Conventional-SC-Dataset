import React, { useState, useEffect } from 'react'
import { Box, Typography, Card, CardContent, Chip, Button, LinearProgress } from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import { api } from '../lib/api'
import { useLanguage } from '../context/LanguageContext'
import StructureViewer3D from './StructureViewer3D'

/* ── HTSC-2025 专属 Layer 3：常压高温超导基准材料详情 ── */

interface Props {
  name: string        // 数据集内名称，如 M3XH8-NbAl3H8
  formula: string
  onBack: () => void
}

const HtscDetail: React.FC<Props> = ({ name, formula, onBack }) => {
  const { t, lang } = useLanguage()
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setData(null)
    setError('')
    api.get(`/api/htsc2025/detail/${encodeURIComponent(name)}`)
      .then((d: any) => setData(d))
      .catch((e: any) => setError(e.message || t('common.loadFailed')))
  }, [name])

  const className = (data?.name || name).split('-')[0]

  const downloadCif = () => {
    if (!data?.cif) return
    const blob = new Blob([data.cif], { type: 'chemical/x-cif' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${formula}.cif`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Box>
      <Box sx={{ display:'flex',alignItems:'center',justifyContent:'space-between',gap:2,mb:3 }}>
        <Box>
          <Button size="small" startIcon={<ArrowBackIcon/>} onClick={onBack} sx={{ mb:1 }}>{t('search.backResults')}</Button>
          <Typography variant="overline">Layer 3 · HTSC-2025 Material</Typography>
          <Typography variant="h1">{t('search.detailTitle', { formula })}</Typography>
          <Box sx={{ display:'flex',gap:1,mt:1 }}>
            <Chip label="HTSC-2025" size="small" />
            <Chip label={t('search.htsc.structureClass', { name: className })} size="small" variant="outlined" />
          </Box>
        </Box>
        <Button variant="contained" color="secondary" onClick={downloadCif} disabled={!data?.cif}>{t('search.htsc.downloadCif')}</Button>
      </Box>

      {error && <Typography color="error" sx={{ mb:2 }}>{error}</Typography>}
      {!data && !error && <LinearProgress sx={{ mb:2, borderRadius:999, height:4 }} />}

      <Box sx={{ display:'grid',gridTemplateColumns:'1fr 360px',gap:3,alignItems:'start','@media (max-width:1180px)':{gridTemplateColumns:'1fr'} }}>
        <Card sx={{ boxShadow: 3 }}>
          <CardContent>
            <Box component="details" open sx={{ border:'1px solid',borderColor:'divider',borderRadius:2,mb:1.5,overflow:'hidden' }}>
              <Box component="summary" sx={{ cursor:'pointer',p:2,fontSize:18,fontWeight:800 }}>{t('search.basicInfo')}</Box>
              <Box sx={{ px:2,pb:2,borderTop:'1px solid',borderColor:'divider' }}>
                <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1.5 }}>
                  <Box><Typography variant="caption">Formula</Typography><Typography fontWeight={600}>{formula}</Typography></Box>
                  <Box><Typography variant="caption">{t('search.htsc.datasetName')}</Typography><Typography fontWeight={600} sx={{ fontFamily:'"Roboto Mono",monospace' }}>{data?.name || name}</Typography></Box>
                  <Box><Typography variant="caption">{t('search.htsc.structureClassLabel')}</Typography><Typography fontWeight={600}>{className}</Typography></Box>
                  <Box><Typography variant="caption">{t('search.pressure')}</Typography><Typography fontWeight={600}>{t('search.htsc.ambientPressure')}</Typography></Box>
                  <Box>
                    <Typography variant="caption">{t('search.htsc.predictedTc')}</Typography>
                    <Typography fontWeight={800} color="primary.main" fontSize={20}>
                      {typeof data?.tc === 'number' ? `${data.tc.toFixed(1)} K` : '-'}
                    </Typography>
                  </Box>
                  <Box><Typography variant="caption">{t('search.htsc.source')}</Typography><Typography fontWeight={600}>{t('search.htsc.benchmarkDataset')}</Typography></Box>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* 结构预览 */}
        <Card sx={{ alignSelf:'start',position:'sticky',top:96,boxShadow:'0 6px 16px rgba(15,23,42,.16),0 10px 24px rgba(15,23,42,.10)' }}>
          <CardContent>
            <Typography variant="h2" gutterBottom>{t('search.structurePreview')}</Typography>
            {data?.cif ? (
              <Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb:1.5 }}>{t('search.structureHint')}</Typography>
                <StructureViewer3D data={data.cif} format="cif" height={340} />
                <Box component="details" sx={{ mt:1.5 }}>
                  <Box component="summary" sx={{ cursor:'pointer',fontSize:13,fontWeight:700,color:'text.secondary' }}>{t('search.viewCifText')}</Box>
                  <Box component="pre" sx={{ mt:1,p:2,borderRadius:2,bgcolor:'grey.50',maxHeight:240,overflow:'auto',fontFamily:'"Roboto Mono",monospace',fontSize:12 }}>
                    {data.cif}
                  </Box>
                </Box>
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">{data ? t('search.noStructureMaterial') : t('search.loading')}</Typography>
            )}
          </CardContent>
        </Card>
      </Box>
    </Box>
  )
}

export default HtscDetail
