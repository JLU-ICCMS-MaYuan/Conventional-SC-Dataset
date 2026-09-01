import React, { useEffect, useId, useMemo, useRef, useState } from 'react'
import { Alert, Box, Button, Chip, CircularProgress, Divider, FormControl, InputLabel, MenuItem, Select, Stack, Typography } from '@mui/material'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import DownloadIcon from '@mui/icons-material/Download'
import BlockIcon from '@mui/icons-material/Block'
import RestoreIcon from '@mui/icons-material/Restore'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import StructureViewer3D from './StructureViewer3D'
import { StructureCandidate } from '../lib/paperProcessing'
import { useLanguage } from '../context/LanguageContext'

interface Props {
  candidates: StructureCandidate[]
  uploading: boolean
  onUpload: (file: File) => void
  onChange: (candidateId: string, changes: Partial<StructureCandidate>) => void
}

type CellKind = 'primitive' | 'conventional'
type StructureFormat = 'cif' | 'poscar'

const StructureCandidatePanel: React.FC<Props> = ({ candidates, uploading, onUpload, onChange }) => {
  const { t } = useLanguage()
  const preferredCandidate = useMemo(
    () => [...candidates].reverse().find(candidate => candidate.confirmation !== 'excluded') || candidates.at(-1),
    [candidates],
  )
  const [selectedCandidateId, setSelectedCandidateId] = useState(preferredCandidate?.candidate_id || '')
  const [cell, setCell] = useState<CellKind>('conventional')
  const [format, setFormat] = useState<StructureFormat>('cif')
  const cellLabelId = useId()
  const formatLabelId = useId()
  const previousCandidateCount = useRef(candidates.length)

  useEffect(() => {
    const candidateAdded = candidates.length > previousCandidateCount.current
    const selectionMissing = !candidates.some(candidate => candidate.candidate_id === selectedCandidateId)
    if (candidateAdded || selectionMissing) {
      setSelectedCandidateId(preferredCandidate?.candidate_id || '')
    }
    previousCandidateCount.current = candidates.length
  }, [candidates, preferredCandidate, selectedCandidateId])

  const candidate = candidates.find(item => item.candidate_id === selectedCandidateId) || preferredCandidate

  const download = (candidate: StructureCandidate, cell: CellKind, format: StructureFormat) => {
    const representation = candidate.representations?.[cell]?.[format]
    if (!representation?.text) return
    const blob = new Blob([representation.text], { type: format === 'cif' ? 'chemical/x-cif' : 'text/plain' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${candidate.candidate_id}-${cell}.${format === 'poscar' ? 'POSCAR' : 'cif'}`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const representation = candidate?.representations?.[cell]?.[format]
  const preview = representation?.text
    ? { text: representation.text, format: format === 'poscar' ? 'vasp' : 'cif' }
    : null
  const blocked = candidate?.status === 'blocked'
  const decided = candidate?.confirmation === 'confirmed' || candidate?.confirmation === 'excluded'
  const filename = candidate?.sources?.map(source => String(source.filename || '')).filter(Boolean).join(t('upload.listSeparator'))
  const statusLabel = blocked
    ? t('upload.structureStatusBlocked')
    : candidate?.confirmation === 'confirmed'
      ? t('upload.structureStatusConfirmed')
      : candidate?.confirmation === 'excluded'
        ? t('upload.structureStatusExcluded')
        : candidate?.status === 'valid'
          ? t('upload.structureStatusValid')
          : t('upload.structureStatusReview')
  const cellLabel = cell === 'conventional' ? t('upload.cell.conventional') : t('upload.cell.primitive')
  const formatLabel = format === 'cif' ? 'CIF' : 'POSCAR'

  return (
    <Box sx={{ mt: 2, p: { xs: 1.5, sm: 2 }, borderRadius: 1, bgcolor: 'action.hover' }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', sm: 'center' }} spacing={1}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="subtitle2" fontWeight={700}>{t('upload.structureAttachmentTitle')}</Typography>
          <Typography variant="caption" color="text.secondary">{t('upload.structureAttachmentHint')}</Typography>
        </Box>
        <Button component="label" size="small" variant="outlined" startIcon={uploading ? <CircularProgress size={16} /> : <UploadFileIcon />} disabled={uploading}>
          {uploading ? t('upload.validating') : t('upload.uploadStructure')}
          <input hidden type="file" accept=".cif,.poscar,.vasp,POSCAR,CONTCAR" onChange={event => {
            const selected = event.target.files?.[0]
            event.target.value = ''
            if (selected) onUpload(selected)
          }} />
        </Button>
      </Stack>

      {candidate && (
        <Box sx={{ mt: 1.5 }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={1}>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="subtitle2" fontWeight={700} sx={{ overflowWrap: 'anywhere' }}>{filename || candidate.candidate_id}</Typography>
              <Typography variant="caption" color="text.secondary">
                {t('upload.atomCount', { count: candidate.validation?.atom_count ?? t('common.notProvided') })} · {(candidate.validation?.elements || []).join(', ') || t('upload.elementsUnknown')}
              </Typography>
            </Box>
            <Chip size="small" label={statusLabel} color={blocked ? 'warning' : candidate.confirmation === 'confirmed' ? 'success' : 'default'} />
          </Stack>

          {candidates.length > 1 && (
            <Select fullWidth size="small" value={candidate.candidate_id} aria-label={t('upload.candidateSelectAria')} onChange={event => setSelectedCandidateId(String(event.target.value))} sx={{ mt: 1.5 }}>
              {candidates.map(item => (
                <MenuItem key={item.candidate_id} value={item.candidate_id}>
                  {item.sources?.map(source => String(source.filename || '')).filter(Boolean).join(t('upload.listSeparator')) || item.candidate_id}
                </MenuItem>
              ))}
            </Select>
          )}

          {blocked
            ? <Alert severity="error" sx={{ mt: 1.5 }}>{candidate.validation?.message || t('upload.blockedValidation')}</Alert>
            : preview
              ? (
                  <Box sx={{ mt: 1.5 }}>
                    <StructureViewer3D data={preview.text} format={preview.format} height={320} />
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.75 }}>
                      {t('upload.currentDisplay', { cell: cellLabel, format: formatLabel })}
                    </Typography>
                  </Box>
                )
              : <Alert severity="info" sx={{ mt: 1.5 }}>{t('upload.missingRepresentation', { cell: cellLabel, format: formatLabel })}</Alert>}

          {!blocked && (
            <>
              <Divider sx={{ my: 1.5 }} />
              <Box component="details">
                <Box component="summary" sx={{ cursor: 'pointer', fontWeight: 700, fontSize: '0.875rem' }}>{t('upload.crystalParamsTitle')}</Box>
                <Box sx={{ mt: 1, display: 'grid', gap: 0.75 }}>
                  <Typography variant="body2">{t('upload.elementLine', { elements: (candidate.validation?.elements || []).join(t('upload.listSeparator')) || t('common.notProvided') })}</Typography>
                  <Typography variant="body2">{t('upload.atomLine', { count: candidate.validation?.atom_count ?? t('common.notProvided') })}</Typography>
                  <Typography variant="body2">{t('upload.volumeLine', { volume: candidate.validation?.volume == null ? t('common.notProvided') : String(candidate.validation.volume) + ' Å³' })}</Typography>
                  <Typography variant="body2">{t('upload.cellParamsLine', { params: candidate.validation?.cell_parameters ? JSON.stringify(candidate.validation.cell_parameters) : t('common.notProvided') })}</Typography>
                </Box>
              </Box>
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.5 }}>
                <FormControl size="small">
                  <InputLabel id={cellLabelId}>{t('upload.cellRepresentation')}</InputLabel>
                  <Select labelId={cellLabelId} label={t('upload.cellRepresentation')} value={cell} onChange={event => setCell(event.target.value as CellKind)}>
                    <MenuItem value="conventional">{t('upload.cell.conventional')}</MenuItem>
                    <MenuItem value="primitive">{t('upload.cell.primitive')}</MenuItem>
                  </Select>
                </FormControl>
                <FormControl size="small">
                  <InputLabel id={formatLabelId}>{t('upload.structureFormat')}</InputLabel>
                  <Select labelId={formatLabelId} label={t('upload.structureFormat')} value={format} onChange={event => setFormat(event.target.value as StructureFormat)}>
                    <MenuItem value="cif">CIF</MenuItem>
                    <MenuItem value="poscar">POSCAR</MenuItem>
                  </Select>
                </FormControl>
                <Button startIcon={<DownloadIcon />} variant="outlined" disabled={!representation?.text} onClick={() => download(candidate, cell, format)}>{t('upload.downloadStructure')}</Button>
                {decided
                  ? (
                      <Button startIcon={<RestoreIcon />} color="inherit" onClick={() => onChange(candidate.candidate_id, { confirmation: 'unreviewed', status: 'valid' })}>
                        {t('upload.restoreToPending')}
                      </Button>
                    )
                  : (
                      <>
                        <Button startIcon={<CheckCircleOutlineIcon />} variant="contained" color="success" disabled={candidate.status !== 'valid'} onClick={() => onChange(candidate.candidate_id, { confirmation: 'confirmed', status: 'confirmed' })}>{t('upload.adoptStructure')}</Button>
                        <Button startIcon={<BlockIcon />} color="inherit" onClick={() => onChange(candidate.candidate_id, { confirmation: 'excluded', status: 'excluded' })}>{t('upload.excludeStructure')}</Button>
                      </>
                    )}
              </Stack>
            </>
          )}
        </Box>
      )}
    </Box>
  )
}

export default StructureCandidatePanel
