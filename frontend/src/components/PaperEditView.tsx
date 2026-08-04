import React, { useState, useEffect, useCallback } from 'react'
import {
  Box, Typography, Card, CardContent, Button, TextField,
  Chip, Snackbar, Alert, CircularProgress,
  Dialog, DialogTitle, DialogContent, DialogActions,
  FormControl, InputLabel, Select, MenuItem,
  IconButton, Tooltip, Checkbox, FormControlLabel,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import SaveIcon from '@mui/icons-material/Save'
import SendIcon from '@mui/icons-material/Send'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import { api } from '../lib/api'
import StructureViewer3D from './StructureViewer3D'

interface PaperEditViewProps {
  paperId: number
  onBack: () => void
  onDeleted?: () => void
}

const STATUS_LABELS: Record<string, string> = {
  pending: '待审核', approved: '审核完成', rejected: '已拒绝', needs_revision: '需修改',
}
const STATUS_COLORS: Record<string, 'warning' | 'success' | 'error' | 'info'> = {
  pending: 'warning', approved: 'success', rejected: 'error', needs_revision: 'info',
}

const PROP_NAME_OPTIONS = [
  { value: 'critical_temperature', label: '超导临界温度 (Tc)' },
  { value: 'electron_phonon_coupling', label: '电声耦合常数 (λ)' },
  { value: 'omega_log', label: '对数平均声子频率 (ω_log)' },
  { value: 'superconducting_gap', label: '超导能隙' },
  { value: 'upper_critical_field', label: '上临界磁场 (Hc2)' },
  { value: 'critical_current_density', label: '临界电流密度' },
  { value: 'coulomb_pseudopotential', label: '库仑赝势 (μ*)' },
  { value: 'dos_fermi', label: '费米面态密度 N(Ef)' },
  { value: 'debye_temperature', label: '德拜温度' },
  { value: 'metallization_pressure', label: '金属化压力' },
  { value: 'synthesis_pressure', label: '合成压力' },
  { value: 'stability_pressure', label: '稳定压力' },
  { value: 'transition_pressure', label: '相变压力' },
  { value: 'lattice_parameter', label: '晶格常数' },
  { value: 'formation_enthalpy', label: '形成焓' },
  { value: 'band_gap', label: '带隙' },
  { value: 'diffusivity', label: '扩散系数' },
  { value: 'hydrogen_storage_capacity', label: '储氢容量' },
]

const PaperEditView: React.FC<PaperEditViewProps> = ({ paperId, onBack, onDeleted }) => {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [snackbar, setSnackbar] = useState('')
  const [error, setError] = useState('')
  const [paper, setPaper] = useState<any>(null)

  // Editable fields
  const [editTitle, setEditTitle] = useState('')
  const [editDoi, setEditDoi] = useState('')
  const [editJournal, setEditJournal] = useState('')
  const [editYear, setEditYear] = useState<number | ''>('')
  const [editAuthors, setEditAuthors] = useState('')
  const [editAbstract, setEditAbstract] = useState('')
  const [editSummary, setEditSummary] = useState('')
  const [editMethodology, setEditMethodology] = useState('')
  const [editKeyFinding, setEditKeyFinding] = useState('')
  const [editRationale, setEditRationale] = useState('')

  // Editable key_properties
  const [editKps, setEditKps] = useState<any[]>([])

  // Review dialog
  const [reviewDlg, setReviewDlg] = useState(false)
  const [reviewStatus, setReviewStatus] = useState('pending')
  const [reviewComment, setReviewComment] = useState('')

  // Delete dialog
  const [deleteDlg, setDeleteDlg] = useState(false)

  // Chem formula (read-only, derived from key_properties)
  const formula = paper?.key_properties?.[0]?.material || (paper?.materials?.[0]) || '-'

  const loadPaper = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      // Use Python backend endpoint (public, no admin required)
      const data = await api.get<any>(`/api/papers/${paperId}`)
      setPaper(data)
      setEditTitle(data.title || '')
      setEditDoi(data.doi || '')
      setEditJournal(data.journal || '')
      setEditYear(data.year || '')
      setEditAuthors(typeof data.authors === 'string' ? data.authors : JSON.stringify(data.authors || []))
      setEditAbstract(data.abstract || '')
      setEditSummary(data.summary || '')
      setEditMethodology(typeof data.methodology === 'string' ? data.methodology : JSON.stringify(data.methodology || []))
      setEditKeyFinding(data.key_finding || '')
      setEditRationale(data.rationale || '')
      // 深拷贝 key_properties 用于本地编辑
      setEditKps((data.key_properties || []).map((kp: any) => ({ ...kp })))
    } catch (e: any) {
      setError(e.message || '加载论文失败')
    } finally {
      setLoading(false)
    }
  }, [paperId])

  useEffect(() => { loadPaper() }, [loadPaper])

  /* ── KP helpers ──────────────────────────── */
  const updateKp = (index: number, field: string, value: any) => {
    setEditKps(prev => prev.map((kp, i) => i === index ? { ...kp, [field]: value } : kp))
  }

  const addKp = () => {
    setEditKps(prev => [...prev, {
      _new: true,
      material: '', name: 'critical_temperature', name_raw: '', name_note: '',
      value_min: null, value_max: null, value_raw: '', unit: 'K',
      pressure_gpa: null, temperature_k: null, condition_note: '',
      is_primary: false, superconductor_type: '', article_type: '',
      structure_text: '', structure_format: 'cif',
    }])
  }

  const deleteKp = (index: number) => {
    setEditKps(prev => {
      const kp = prev[index]
      if (kp.id) {
        // 已有 ID 的标记为删除（后端根据 _deleted 处理）
        return prev.map((k, i) => i === index ? { ...k, _deleted: true } : k)
      }
      // 新建的未保存 KP 直接从列表移除
      return prev.filter((_, i) => i !== index)
    })
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      // 清理 kps 数据：移除临时字段 _new、只发送有意义的字段
      const kpsPayload = editKps.map(({ _new, _deleted, label, ...kp }: any) => {
        const clean: any = {}
        if (kp.id) clean.id = kp.id
        if (_deleted) { clean._deleted = true; return clean }
        const fields = ['material', 'name', 'name_raw', 'name_note',
          'value_min', 'value_max', 'value_raw', 'unit',
          'pressure_gpa', 'temperature_k', 'is_primary',
          'superconductor_type', 'article_type', 'condition_note',
          'structure_text', 'structure_format']
        for (const f of fields) {
          if (kp[f] !== undefined && kp[f] !== '') clean[f] = kp[f]
        }
        return clean
      })

      const payload: Record<string, any> = {
        title: editTitle || null,
        doi: editDoi || null,
        journal: editJournal || null,
        year: editYear ? Number(editYear) : null,
        authors: editAuthors || null,
        abstract: editAbstract || null,
        summary: editSummary || null,
        methodology: editMethodology || null,
        key_finding: editKeyFinding || null,
        rationale: editRationale || null,
        key_properties: kpsPayload,
      }
      await api.put(`/api/admin/papers/${paperId}`, payload)
      setSnackbar('保存成功')
      loadPaper() // Refresh
    } catch (e: any) {
      setSnackbar(`保存失败: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }

  const handleSubmitReview = async () => {
    try {
      await api.post(`/api/admin/papers/${paperId}/review`, {
        status: 'pending',
        comment: reviewComment || undefined,
      })
      setSnackbar('已提交审核')
      setReviewDlg(false)
      loadPaper()
    } catch (e: any) {
      setSnackbar(`提交失败: ${e.message}`)
    }
  }

  const handleDelete = async () => {
    try {
      await api.del(`/api/admin/papers/${paperId}`)
      setSnackbar('已删除')
      onDeleted?.()
    } catch (e: any) {
      setSnackbar(`删除失败: ${e.message}`)
    }
  }

  // Structure data from key_properties
  const structures = (paper?.key_properties || [])
    .filter((kp: any) => kp.structure_text)
    .map((kp: any) => ({
      structure_text: kp.structure_text,
      structure_format: kp.structure_format || 'cif',
      material: kp.material,
      name_note: kp.name_note,
      pressure_gpa: kp.pressure_gpa,
    }))

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Box sx={{ textAlign: 'center', py: 8 }}>
        <Typography color="error" gutterBottom>{error}</Typography>
        <Button onClick={onBack} startIcon={<ArrowBackIcon />}>返回</Button>
      </Box>
    )
  }

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mb: 3 }}>
        <Box>
          <Button size="small" startIcon={<ArrowBackIcon />} onClick={onBack} sx={{ mb: 1 }}>
            返回上传列表
          </Button>
          <Typography variant="overline" color="text.secondary">编辑模式</Typography>
          <Typography variant="h4" fontWeight={800}>论文详情</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" color="error" startIcon={<DeleteIcon />}
            onClick={() => setDeleteDlg(true)}>删除</Button>
          <Button variant="contained" startIcon={saving ? <CircularProgress size={18} /> : <SaveIcon />}
            onClick={handleSave} disabled={saving}>保存修改</Button>
          <Button variant="contained" color="secondary" startIcon={<SendIcon />}
            onClick={() => setReviewDlg(true)}>提交审核</Button>
        </Box>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 3, alignItems: 'start',
        '@media (max-width:1180px)': { gridTemplateColumns: '1fr' } }}>
        {/* Main content */}
        <Card sx={{ boxShadow: 3 }}>
          <CardContent>
            {/* 基础信息 */}
            <Box component="details" open sx={{
              border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 1.5, overflow: 'hidden',
            }}>
              <Box component="summary" sx={{ cursor: 'pointer', p: 2, fontSize: 18, fontWeight: 800 }}>
                基础信息
              </Box>
              <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <TextField label="标题" size="small" fullWidth multiline rows={2}
                    value={editTitle} onChange={e => setEditTitle(e.target.value)} />
                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
                    <TextField label="DOI" size="small" value={editDoi}
                      onChange={e => setEditDoi(e.target.value)} />
                    <TextField label="年份" size="small" type="number" value={editYear}
                      onChange={e => setEditYear(e.target.value ? Number(e.target.value) : '')} />
                  </Box>
                  <TextField label="期刊" size="small" fullWidth value={editJournal}
                    onChange={e => setEditJournal(e.target.value)} />
                  <TextField label="作者" size="small" fullWidth multiline rows={2}
                    helperText="JSON 数组格式"
                    value={editAuthors}
                    onChange={e => setEditAuthors(e.target.value)} />
                  <TextField label="摘要" size="small" fullWidth multiline rows={3}
                    value={editAbstract} onChange={e => setEditAbstract(e.target.value)} />
                  <TextField label="论文总结 (LLM)" size="small" fullWidth multiline rows={3}
                    value={editSummary} onChange={e => setEditSummary(e.target.value)} />
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip label={`审核状态: ${STATUS_LABELS[paper?.review_status] || paper?.review_status || '待审核'}`}
                      size="small" color={STATUS_COLORS[paper?.review_status] || 'default'} />
                    <Chip label="数据来源: Local" size="small" color="primary" />
                    {paper?.id && <Chip label={`ID: ${paper.id}`} size="small" variant="outlined" />}
                  </Box>
                </Box>
              </Box>
            </Box>

            {/* 关键物性 */}
            <Box component="details" open sx={{
              border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 1.5, overflow: 'hidden',
            }}>
              <Box component="summary" sx={{ cursor: 'pointer', p: 2, fontSize: 18, fontWeight: 800 }}>
                关键物性
                <Chip size="small" label={editKps.filter(k => !k._deleted).length} sx={{ ml: 1, fontWeight: 700 }} />
              </Box>
              <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                {editKps.length === 0 ? (
                  <Box sx={{ textAlign: 'center', py: 3 }}>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                      暂无物性数据
                    </Typography>
                    <Button size="small" variant="outlined" startIcon={<AddIcon />} onClick={addKp}>
                      添加物性
                    </Button>
                  </Box>
                ) : (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 1 }}>
                    {editKps.map((kp: any, index: number) => {
                      if (kp._deleted) return null
                      const setF = (f: string, v: any) => updateKp(index, f, v)

                      return (
                        <Box key={kp.id || `new-${index}`} sx={{
                          p: 1.5, borderRadius: 2,
                          bgcolor: kp.is_primary ? '#eef2ff' : 'grey.50',
                          border: '1px solid', borderColor: kp.is_primary ? '#818cf8' : 'divider',
                          opacity: kp._deleted ? 0.35 : 1,
                        }}>
                          {/* Row 1: 核心字段 */}
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Chip size="small" label={`#${index + 1}`} variant="outlined" />
                            <FormControlLabel
                              control={<Checkbox checked={!!kp.is_primary} size="small"
                                onChange={e => setF('is_primary', e.target.checked)} />}
                              label="主要"
                              sx={{ m: 0, '& .MuiTypography-root': { fontSize: 12 } }}
                            />
                            <Box sx={{ flex: 1 }} />
                            <Tooltip title="删除此物性">
                              <IconButton size="small" color="error" onClick={() => deleteKp(index)}>
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>

                          {/* Row 2: 材料 + 物性名 */}
                          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, mb: 1 }}>
                            <TextField label="材料 (material)" size="small"
                              value={kp.material || ''} onChange={e => setF('material', e.target.value)} />
                            <FormControl size="small">
                              <InputLabel>物性名</InputLabel>
                              <Select
                                value={kp.name || ''}
                                label="物性名"
                                onChange={e => setF('name', e.target.value)}>
                                {PROP_NAME_OPTIONS.map(o => (
                                  <MenuItem key={o.value} value={o.value}>{o.label}</MenuItem>
                                ))}
                              </Select>
                            </FormControl>
                          </Box>

                          {/* Row 3: 数值范围 */}
                          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 1, mb: 1 }}>
                            <TextField label="最小值" size="small" type="number"
                              value={kp.value_min ?? ''}
                              onChange={e => setF('value_min', e.target.value ? Number(e.target.value) : null)} />
                            <TextField label="最大值" size="small" type="number"
                              value={kp.value_max ?? ''}
                              onChange={e => setF('value_max', e.target.value ? Number(e.target.value) : null)} />
                            <TextField label="单位" size="small"
                              value={kp.unit || ''} onChange={e => setF('unit', e.target.value)} />
                          </Box>

                          {/* Row 4: 条件 + 分类 */}
                          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 1, mb: 1 }}>
                            <TextField label="压强 (GPa)" size="small" type="number"
                              value={kp.pressure_gpa ?? ''}
                              onChange={e => setF('pressure_gpa', e.target.value ? Number(e.target.value) : null)} />
                            <TextField label="温度 (K)" size="small" type="number"
                              value={kp.temperature_k ?? ''}
                              onChange={e => setF('temperature_k', e.target.value ? Number(e.target.value) : null)} />
                            <FormControl size="small">
                              <InputLabel>超导类型</InputLabel>
                              <Select value={kp.superconductor_type || ''} label="超导类型"
                                onChange={e => setF('superconductor_type', e.target.value)}>
                                <MenuItem value="">-</MenuItem>
                                <MenuItem value="hydride">hydride · 氢化物</MenuItem>
                                <MenuItem value="cuprate">cuprate · 铜基</MenuItem>
                                <MenuItem value="iron_based">iron_based · 铁基</MenuItem>
                                <MenuItem value="nickel_based">nickel_based · 镍基</MenuItem>
                                <MenuItem value="carbon">carbon · 碳基</MenuItem>
                                <MenuItem value="organic">organic · 有机</MenuItem>
                                <MenuItem value="others">others · 其他</MenuItem>
                              </Select>
                            </FormControl>
                          </Box>

                          {/* Row 5: 备注 */}
                          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                            <TextField label="物性备注 (name_note)" size="small"
                              value={kp.name_note || ''} onChange={e => setF('name_note', e.target.value)} />
                            <TextField label="条件备注 (condition_note)" size="small"
                              value={kp.condition_note || ''} onChange={e => setF('condition_note', e.target.value)} />
                          </Box>
                        </Box>
                      )
                    })}

                    {/* Add button */}
                    <Button variant="outlined" startIcon={<AddIcon />} onClick={addKp}
                      sx={{ alignSelf: 'center', borderRadius: '999px' }}>
                      添加物性
                    </Button>
                  </Box>
                )}
              </Box>
            </Box>

            {/* 研究方法与发现 */}
            <Box component="details" sx={{
              border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 1.5, overflow: 'hidden',
            }}>
              <Box component="summary" sx={{ cursor: 'pointer', p: 2, fontSize: 18, fontWeight: 800 }}>
                研究方法与发现
              </Box>
              <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 1 }}>
                  <TextField label="研究方法 (methodology)" size="small" fullWidth multiline rows={3}
                    helperText="JSON 数组格式"
                    value={editMethodology}
                    onChange={e => setEditMethodology(e.target.value)} />
                  <TextField label="核心发现 (key_finding)" size="small" fullWidth multiline rows={3}
                    value={editKeyFinding}
                    onChange={e => setEditKeyFinding(e.target.value)} />
                  <TextField label="研究理由 (rationale)" size="small" fullWidth multiline rows={2}
                    value={editRationale}
                    onChange={e => setEditRationale(e.target.value)} />
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* Structure preview sidebar */}
        <Card sx={{
          alignSelf: 'start', position: 'sticky', top: 96,
          boxShadow: '0 6px 16px rgba(15,23,42,.16),0 10px 24px rgba(15,23,42,.10)',
        }}>
          <CardContent>
            <Typography variant="h2" gutterBottom>结构预览</Typography>
            {structures.length > 0 ? (
              <Box>
                {structures.map((s: any, i: number) => (
                  <Box key={i} sx={{ mb: i < structures.length - 1 ? 2.5 : 0 }}>
                    {s.name_note && (
                      <Typography variant="body2" fontWeight={700} sx={{ mb: 0.5 }}>
                        {s.material} · {s.name_note}{s.pressure_gpa != null ? ` @ ${s.pressure_gpa} GPa` : ''}
                      </Typography>
                    )}
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      格式 {s.structure_format || 'cif'} · 拖拽旋转 · 滚轮缩放
                    </Typography>
                    <StructureViewer3D
                      data={s.structure_text}
                      format={s.structure_format === 'poscar' || s.structure_format === 'vasp' ? 'vasp' : 'cif'}
                      height={240}
                    />
                    <Box component="details" sx={{ mt: 1 }}>
                      <Box component="summary" sx={{ cursor: 'pointer', fontSize: 12, fontWeight: 700, color: 'text.secondary' }}>
                        查看结构文本
                      </Box>
                      <Box component="pre" sx={{
                        mt: 1, p: 1.5, borderRadius: 2, bgcolor: 'grey.50',
                        maxHeight: 200, overflow: 'auto', fontFamily: '"Roboto Mono",monospace', fontSize: 11,
                      }}>
                        {s.structure_text.slice(0, 1500)}
                      </Box>
                    </Box>
                  </Box>
                ))}
              </Box>
            ) : (
              <Box sx={{
                minHeight: 240, borderRadius: 2, border: '1px solid', borderColor: 'divider',
                background: `radial-gradient(circle at 22% 28%, #4f46e5 0 9px, transparent 10px),
                  radial-gradient(circle at 66% 34%, #0891b2 0 9px, transparent 10px),
                  radial-gradient(circle at 42% 70%, #4f46e5 0 9px, transparent 10px),
                  linear-gradient(145deg, #fff, #f1f5f9)`,
                position: 'relative', overflow: 'hidden',
                '&::before,&::after': {
                  content: '""', position: 'absolute', left: '25%', right: '25%',
                  top: '34%', height: 2, bgcolor: '#cbd5e1', transform: 'rotate(18deg)',
                },
                '&::after': { top: '58%', transform: 'rotate(-25deg)' },
              }}>
                <Typography variant="body2" sx={{ position: 'absolute', bottom: 12, left: 12, color: 'text.secondary' }}>
                  该记录暂无结构数据
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      </Box>

      {/* Review Dialog */}
      <Dialog open={reviewDlg} onClose={() => setReviewDlg(false)} maxWidth="sm" fullWidth>
        <DialogTitle>提交审核</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            将论文提交给管理员审核。审核通过后将对外可见。
          </Typography>
          <TextField label="审核备注（可选）" size="small" fullWidth multiline rows={3}
            value={reviewComment} onChange={e => setReviewComment(e.target.value)}
            placeholder="可填写需要管理员注意的事项" />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReviewDlg(false)}>取消</Button>
          <Button variant="contained" onClick={handleSubmitReview}>确认提交</Button>
        </DialogActions>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={deleteDlg} onClose={() => setDeleteDlg(false)} maxWidth="xs" fullWidth>
        <DialogTitle>确认删除</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            删除后将无法恢复，包括所有关联的物性数据。确认删除？
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDlg(false)}>取消</Button>
          <Button variant="contained" color="error" onClick={handleDelete}>确认删除</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={!!snackbar} autoHideDuration={3000} onClose={() => setSnackbar('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity="info" variant="filled" onClose={() => setSnackbar('')}>{snackbar}</Alert>
      </Snackbar>
    </Box>
  )
}

export default PaperEditView
