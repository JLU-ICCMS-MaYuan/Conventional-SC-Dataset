import React, { useMemo, useState } from 'react'
import { Alert, Box, Button, Card, CardContent, Chip, Divider, MenuItem, Select, Stack, Typography } from '@mui/material'
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline'
import DownloadIcon from '@mui/icons-material/Download'
import BlockIcon from '@mui/icons-material/Block'
import StructureViewer3D from './StructureViewer3D'
import { DraftMaterialState, StructureCandidate } from '../lib/paperProcessing'

interface Props {
  candidates: StructureCandidate[]
  materialStates: DraftMaterialState[]
  sx?: any
  onChange: (candidateId: string, changes: Partial<StructureCandidate>) => void
}

type CellKind = 'primitive' | 'conventional'
type StructureFormat = 'cif' | 'poscar'

const StructureCandidatePanel: React.FC<Props> = ({ candidates, materialStates, sx, onChange }) => {
  const [cellByCandidate, setCellByCandidate] = useState<Record<string, CellKind>>({})
  const [formatByCandidate, setFormatByCandidate] = useState<Record<string, StructureFormat>>({})

  const validCount = useMemo(() => candidates.filter(item => item.status === 'valid' || item.status === 'confirmed').length, [candidates])
  if (!candidates.length) return <Box component="aside" aria-label="晶体结构" sx={{ mt: 0, ...sx }}><Typography variant="h6" fontWeight={700} sx={{ mb: 1 }}>晶体结构</Typography><Alert severity="info"><Typography variant="body2" fontWeight={700}>尚未发现可预览结构</Typography><Typography variant="caption" color="text.secondary">仅有空间群符号或群号、没有完整晶格和原子坐标时，不生成三维结构。可上传 CIF 或 POSCAR 结构附件。</Typography></Alert></Box>

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

  return (
    <Box sx={sx}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="h6" fontWeight={700}>晶体结构</Typography>
        <Chip size="small" label={`${validCount}/${candidates.length} 项可确认`} color={validCount ? 'success' : 'default'} />
      </Stack>
      <Alert severity="info" sx={{ mb: 1.5 }}>候选只会在你明确确认且论文提交成功后写入正式结构模型。</Alert>
      <Stack spacing={1.5}>
        {candidates.map(candidate => {
          const cell = cellByCandidate[candidate.candidate_id] || 'conventional'
          const format = formatByCandidate[candidate.candidate_id] || 'cif'
          const representation = candidate.representations?.[cell]?.[format]
          const preview = candidate.representations?.conventional?.cif?.text || candidate.representations?.conventional?.poscar?.text
          const blocked = candidate.status === 'blocked'
          const assignedState = candidate.material_state_ref || ''
          return (
            <Card key={candidate.candidate_id} variant="outlined">
              <CardContent>
                <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" spacing={1}>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="subtitle2" fontWeight={700} sx={{ overflowWrap: 'anywhere' }}>
                      {candidate.sources?.map(source => String(source.filename || '')).filter(Boolean).join('、') || candidate.candidate_id}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {candidate.source_kind === 'attachment' ? '原生附件' : candidate.source_kind || '结构来源'} · {candidate.validation?.atom_count ?? '未提供'} 个原子 · {(candidate.validation?.elements || []).join(', ') || '元素未知'}
                    </Typography>
                  </Box>
                  <Chip size="small" label={blocked ? '需要人工处理' : candidate.confirmation === 'confirmed' ? '已确认' : candidate.confirmation === 'excluded' ? '已排除' : candidate.status === 'valid' ? '可确认' : '待核对'} color={blocked ? 'warning' : candidate.confirmation === 'confirmed' ? 'success' : 'default'} />
                </Stack>
                {blocked ? (
                  <Alert severity="error" sx={{ mt: 1.5 }}>{candidate.validation?.message || '结构无法通过确定性校验'}</Alert>
                ) : (
                  <>
                    {preview ? <Box sx={{ mt: 1.5 }}><StructureViewer3D data={preview} format="cif" height={280} /></Box> : <Alert severity="info" sx={{ mt: 1.5 }}>结构文本缺失，暂不生成三维预览。</Alert>}
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
                    <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1.5 }}>
                      <Select
                        size="small"
                        value={assignedState}
                        displayEmpty
                        aria-label="关联材料状态"
                        onChange={event => onChange(candidate.candidate_id, { material_state_ref: event.target.value || null })}
                        renderValue={value => value
                          ? (() => {
                            const index = Number(String(value).match(/\[(\d+)\]/)?.[1] || -1)
                            const state = materialStates[index]
                            return state?.material ? `材料状态 #${index + 1} · ${state.material}` : `材料状态 #${index + 1}`
                          })()
                          : '选择材料状态'}
                        sx={{ minWidth: { sm: 190 } }}
                      >
                        <MenuItem value=""><em>选择材料状态</em></MenuItem>
                        {materialStates.map((state, index) => (
                          <MenuItem key={index} value={`material_states[${index}]`}>
                            材料状态 #{index + 1}{state.material ? ` · ${state.material}` : ''}
                          </MenuItem>
                        ))}
                      </Select>
                      <Select size="small" value={cell} aria-label="晶胞表示" onChange={event => setCellByCandidate(current => ({ ...current, [candidate.candidate_id]: event.target.value as CellKind }))}>
                        <MenuItem value="conventional">惯用胞</MenuItem>
                        <MenuItem value="primitive">原胞</MenuItem>
                      </Select>
                      <Select size="small" value={format} aria-label="结构导出格式" onChange={event => setFormatByCandidate(current => ({ ...current, [candidate.candidate_id]: event.target.value as StructureFormat }))}>
                        <MenuItem value="cif">CIF</MenuItem>
                        <MenuItem value="poscar">POSCAR</MenuItem>
                      </Select>
                      <Button startIcon={<DownloadIcon />} variant="outlined" disabled={!representation?.text} onClick={() => download(candidate, cell, format)}>下载结构</Button>
                      <Button startIcon={<CheckCircleOutlineIcon />} variant="contained" color="success" disabled={blocked || candidate.status !== 'valid' || !assignedState} onClick={() => onChange(candidate.candidate_id, { confirmation: 'confirmed', status: 'confirmed' })}>确认</Button>
                      <Button startIcon={<BlockIcon />} color="inherit" disabled={blocked || candidate.confirmation === 'excluded'} onClick={() => onChange(candidate.candidate_id, { confirmation: 'excluded', status: 'excluded' })}>排除</Button>
                    </Stack>
                  </>
                )}
              </CardContent>
            </Card>
          )
        })}
      </Stack>
    </Box>
  )
}

export default StructureCandidatePanel
