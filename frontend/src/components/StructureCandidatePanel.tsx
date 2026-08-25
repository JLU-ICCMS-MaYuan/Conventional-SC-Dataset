import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Alert, Box, Button, Chip, CircularProgress, Divider, MenuItem, Select, Stack, Typography } from '@mui/material'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import DownloadIcon from '@mui/icons-material/Download'
import BlockIcon from '@mui/icons-material/Block'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import StructureViewer3D from './StructureViewer3D'
import { StructureCandidate } from '../lib/paperProcessing'

interface Props {
  candidates: StructureCandidate[]
  uploading: boolean
  onUpload: (file: File) => void
  onChange: (candidateId: string, changes: Partial<StructureCandidate>) => void
}

type CellKind = 'primitive' | 'conventional'
type StructureFormat = 'cif' | 'poscar'

const StructureCandidatePanel: React.FC<Props> = ({ candidates, uploading, onUpload, onChange }) => {
  const preferredCandidate = useMemo(
    () => [...candidates].reverse().find(candidate => candidate.confirmation !== 'excluded') || candidates.at(-1),
    [candidates],
  )
  const [selectedCandidateId, setSelectedCandidateId] = useState(preferredCandidate?.candidate_id || '')
  const [cell, setCell] = useState<CellKind>('conventional')
  const [format, setFormat] = useState<StructureFormat>('cif')
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
  const preview = candidate?.representations?.conventional?.cif?.text
    ? { text: candidate.representations.conventional.cif.text, format: 'cif' }
    : candidate?.representations?.conventional?.poscar?.text
      ? { text: candidate.representations.conventional.poscar.text, format: 'vasp' }
      : null
  const blocked = candidate?.status === 'blocked'
  const filename = candidate?.sources?.map(source => String(source.filename || '')).filter(Boolean).join('、')
  const statusLabel = blocked
    ? '需要人工处理'
    : candidate?.confirmation === 'confirmed'
      ? '已确认'
      : candidate?.confirmation === 'excluded'
        ? '已排除'
        : candidate?.status === 'valid'
          ? '可确认'
          : '待核对'

  return (
    <Box sx={{ mt: 2, p: { xs: 1.5, sm: 2 }, borderRadius: 1, bgcolor: 'action.hover' }}>
      <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', sm: 'center' }} spacing={1}>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="subtitle2" fontWeight={700}>结构附件</Typography>
          <Typography variant="caption" color="text.secondary">上传后自动校验，并在当前材料状态下预览</Typography>
        </Box>
        <Button component="label" size="small" variant="outlined" startIcon={uploading ? <CircularProgress size={16} /> : <UploadFileIcon />} disabled={uploading}>
          {uploading ? '校验中' : '上传 CIF / POSCAR / VASP'}
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
                {candidate.validation?.atom_count ?? '未提供'} 个原子 · {(candidate.validation?.elements || []).join(', ') || '元素未知'}
              </Typography>
            </Box>
            <Chip size="small" label={statusLabel} color={blocked ? 'warning' : candidate.confirmation === 'confirmed' ? 'success' : 'default'} />
          </Stack>

          {candidates.length > 1 && (
            <Select fullWidth size="small" value={candidate.candidate_id} aria-label="结构候选" onChange={event => setSelectedCandidateId(String(event.target.value))} sx={{ mt: 1.5 }}>
              {candidates.map(item => (
                <MenuItem key={item.candidate_id} value={item.candidate_id}>
                  {item.sources?.map(source => String(source.filename || '')).filter(Boolean).join('、') || item.candidate_id}
                </MenuItem>
              ))}
            </Select>
          )}

          {blocked
            ? <Alert severity="error" sx={{ mt: 1.5 }}>{candidate.validation?.message || '结构无法通过确定性校验'}</Alert>
            : preview
              ? <Box sx={{ mt: 1.5 }}><StructureViewer3D data={preview.text} format={preview.format} height={320} /></Box>
              : <Alert severity="info" sx={{ mt: 1.5 }}>结构文本缺失，暂不生成三维预览。</Alert>}

          {!blocked && (
            <>
              <Divider sx={{ my: 1.5 }} />
              <Box component="details">
                <Box component="summary" sx={{ cursor: 'pointer', fontWeight: 700, fontSize: '0.875rem' }}>晶体结构参数</Box>
                <Box sx={{ mt: 1, display: 'grid', gap: 0.75 }}>
                  <Typography variant="body2">元素：{(candidate.validation?.elements || []).join('、') || '未提供'}</Typography>
                  <Typography variant="body2">原子数：{candidate.validation?.atom_count ?? '未提供'}</Typography>
                  <Typography variant="body2">晶胞体积：{candidate.validation?.volume == null ? '未提供' : String(candidate.validation.volume) + ' Å³'}</Typography>
                  <Typography variant="body2">晶胞参数：{candidate.validation?.cell_parameters ? JSON.stringify(candidate.validation.cell_parameters) : '未提供'}</Typography>
                </Box>
              </Box>
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 1.5 }}>
                <Select size="small" value={cell} aria-label="晶胞表示" onChange={event => setCell(event.target.value as CellKind)}>
                  <MenuItem value="conventional">惯用胞</MenuItem>
                  <MenuItem value="primitive">原胞</MenuItem>
                </Select>
                <Select size="small" value={format} aria-label="结构导出格式" onChange={event => setFormat(event.target.value as StructureFormat)}>
                  <MenuItem value="cif">CIF</MenuItem>
                  <MenuItem value="poscar">POSCAR</MenuItem>
                </Select>
                <Button startIcon={<DownloadIcon />} variant="outlined" disabled={!representation?.text} onClick={() => download(candidate, cell, format)}>下载结构</Button>
                <Button startIcon={<CheckCircleOutlineIcon />} variant="contained" color="success" disabled={candidate.status !== 'valid'} onClick={() => onChange(candidate.candidate_id, { confirmation: 'confirmed', status: 'confirmed' })}>确认</Button>
                <Button startIcon={<BlockIcon />} color="inherit" disabled={candidate.confirmation === 'excluded'} onClick={() => onChange(candidate.candidate_id, { confirmation: 'excluded', status: 'excluded' })}>排除</Button>
              </Stack>
            </>
          )}
        </Box>
      )}
    </Box>
  )
}

export default StructureCandidatePanel
