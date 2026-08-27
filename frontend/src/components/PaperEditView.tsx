import React, { useState, useEffect } from 'react'
import {
  Box, Typography, Card, CardContent, Button, TextField,
  Chip, Alert,
  IconButton, Tooltip,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import StructureViewer3D from './StructureViewer3D'

interface PaperEditViewProps {
  // 论文数据与加载/错误分流由路由页面壳 PaperDetailPage 负责，本组件只负责展示。
  paper: any
  onBack: () => void
  onOpenMyPapers?: () => void
}

const STATUS_LABELS: Record<string, string> = {
  pending: '待审核', approved: '审核完成', rejected: '已拒绝', needs_revision: '待审核（旧状态）',
}
const STATUS_COLORS: Record<string, 'warning' | 'success' | 'error' | 'info'> = {
  pending: 'warning', approved: 'success', rejected: 'error', needs_revision: 'info',
}

const PaperEditView: React.FC<PaperEditViewProps> = ({ paper, onBack, onOpenMyPapers }) => {
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

  // Chem formula (read-only, derived from key_properties)
  const formula = paper?.key_properties?.[0]?.material || (paper?.materials?.[0]) || '-'

  // 论文数据由 props 传入；同步到本地展示状态，切换论文时重新填充
  useEffect(() => {
    const data = paper || {}
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
  }, [paper])

  // 物性的条件取自所属材料状态：压强与温度不在物性表上。
  const kpCondition = (kp: any) => {
    const state = (paper?.material_states || []).find((ms: any) => ms.id === kp.material_state_id)
    return {
      pressure: state?.pressure_raw
        ?? (state?.pressure_value_gpa != null ? `${state.pressure_value_gpa} GPa` : '-'),
      temperature: state?.temperature_raw
        ?? (state?.temperature_value_k != null ? `${state.temperature_value_k} K` : '-'),
    }
  }

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
      is_primary: false, article_type: '',
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

  // 结构数据来自 structure_models（挂在材料状态下），物性表没有结构文本列。
  const structures = (paper?.material_states || []).flatMap((state: any) =>
    (state.structures || [])
      .filter((item: any) => item.structure_text)
      .map((item: any) => ({
        structure_text: item.structure_text,
        structure_format: item.structure_format || 'cif',
        material: state.material,
        name_note: item.space_group_symbol,
        pressure_gpa: state.pressure_value_gpa,
      }))
  )

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, mb: 3 }}>
        <Box>
          <Button size="small" startIcon={<ArrowBackIcon />} onClick={onBack} sx={{ mb: 1 }}>
            返回上传列表
          </Button>
          <Typography variant="overline" color="text.secondary">只读模式</Typography>
          <Typography variant="h4" fontWeight={800}>论文详情</Typography>
        </Box>
        {/* 离开详情页后仍能经界面回到任意已提交论文，无需手工拼接网址 */}
        {onOpenMyPapers && (
          <Button size="small" variant="outlined" onClick={onOpenMyPapers}>我的论文</Button>
        )}
      </Box>

      <Alert severity="info" sx={{ mb: 2 }}>论文已提交审核。普通用户不能在这里直接修改正式记录。</Alert>

      <Box component="fieldset" disabled sx={{
        border: 0, p: 0, m: 0, minWidth: 0,
        display: 'grid', gridTemplateColumns: '1fr 360px', gap: 3, alignItems: 'start',
        '@media (max-width:1180px)': { gridTemplateColumns: '1fr' },
      }}>
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

            {(paper.material_states || []).length > 0 && (
              <Box component="details" open sx={{
                border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 1.5, overflow: 'hidden',
              }}>
                <Box component="summary" sx={{ cursor: 'pointer', p: 2, fontSize: 18, fontWeight: 800 }}>
                  材料状态分类
                </Box>
                <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider', display: 'flex', flexDirection: 'column', gap: 1 }}>
                  {(paper.material_states || []).map((state: any, index: number) => (
                    <Box key={state.id || index} sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
                      <Typography variant="body2" fontWeight={700}>{state.material || `材料状态 #${index + 1}`}</Typography>
                      <Chip size="small" label={state.material_family?.name || '材料家族待确认'} color={state.material_family ? 'primary' : 'warning'} />
                      <Chip size="small" variant="outlined" label={`不同元素种类数: ${state.element_count ?? '未知'}`} />
                      {(state.structure_families || []).map((family: any) => (
                        <Chip key={family.id || family.name} size="small" variant="outlined" label={`${family.name}${family.is_primary ? '（主）' : ''}`} />
                      ))}
                    </Box>
                  ))}
                </Box>
              </Box>
            )}

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
                          bgcolor: 'grey.50',
                          border: '1px solid', borderColor: 'divider',
                          opacity: kp._deleted ? 0.35 : 1,
                        }}>
                          {/* Row 1: 核心字段。主次标记在条件化模型中已无对应列，不再展示 */}
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Chip size="small" label={`#${index + 1}`} variant="outlined" />
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
                            {/* 物性名来自规范定义或原文名，不再是固定候选枚举 */}
                            <TextField label="物性名" size="small"
                              value={kp.name || kp.name_raw || ''}
                              onChange={e => setF('name_raw', e.target.value)} />
                          </Box>

                          {/* Row 3: 数值范围 */}
                          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, mb: 1 }}>
                            <TextField label="最小值" size="small" type="number"
                              value={kp.value_min ?? ''}
                              onChange={e => setF('value_min', e.target.value ? Number(e.target.value) : null)} />
                            <TextField label="最大值" size="small" type="number"
                              value={kp.value_max ?? ''}
                              onChange={e => setF('value_max', e.target.value ? Number(e.target.value) : null)} />
                            <TextField label="单位" size="small"
                              value={kp.unit || ''} onChange={e => setF('unit', e.target.value)} />
                          </Box>

                          {/* Row 4: 条件。压强与温度属材料状态，此处按所属状态只读展示 */}
                          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, mb: 1 }}>
                            <TextField label="压强（来自材料状态）" size="small"
                              value={kpCondition(kp).pressure} InputProps={{ readOnly: true }} />
                            <TextField label="温度（来自材料状态）" size="small"
                              value={kpCondition(kp).temperature} InputProps={{ readOnly: true }} />
                          </Box>

                          {/* Row 5: 备注 */}
                          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                            <TextField label="数值（解析值）" size="small"
                              value={kp.value_number ?? ''} InputProps={{ readOnly: true }} />
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

    </Box>
  )
}

export default PaperEditView
