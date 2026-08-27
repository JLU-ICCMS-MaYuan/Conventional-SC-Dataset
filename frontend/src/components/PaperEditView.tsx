import React, { useState, useEffect } from 'react'
import {
  Box, Typography, Card, CardContent, Button,
  Chip, Alert,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
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
  // 只读展示状态：用于展示的本地状态，切换论文时重新填充
  const [editTitle, setEditTitle] = useState('')
  const [editDoi, setEditDoi] = useState('')
  const [editJournal, setEditJournal] = useState('')
  const [editYear, setEditYear] = useState<number | ''>('')
  const [editAuthors, setEditAuthors] = useState('')
  const [editAbstract, setEditAbstract] = useState('')
  const [editSummary, setEditSummary] = useState('')
  const [editKeyFinding, setEditKeyFinding] = useState('')
  const [editRationale, setEditRationale] = useState('')

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
    setEditKeyFinding(data.key_finding || '')
    setEditRationale(data.rationale || '')
  }, [paper])

  // 研究方法处理：转为可读列表
  const methodologyList: string[] = (() => {
    const raw = paper?.methodology
    if (!raw) return []
    if (Array.isArray(raw)) return raw
    return []
  })()

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

      <Box sx={{
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
                  <Box>
                    <Typography variant="caption" color="text.secondary">标题</Typography>
                    <Typography variant="body2">{editTitle || '-'}</Typography>
                  </Box>
                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">DOI</Typography>
                      <Typography variant="body2">{editDoi || '-'}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">年份</Typography>
                      <Typography variant="body2">{editYear || '-'}</Typography>
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">期刊</Typography>
                    <Typography variant="body2">{editJournal || '-'}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">作者</Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{editAuthors || '-'}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">摘要</Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{editAbstract || '-'}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">论文总结 (LLM)</Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{editSummary || '-'}</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip label={`审核状态: ${STATUS_LABELS[paper?.review_status] || paper?.review_status || '待审核'}`}
                      size="small" color={STATUS_COLORS[paper?.review_status] || 'default'} />
                    <Chip label="数据来源: Local" size="small" color="primary" />
                    {paper?.id && <Chip label={`ID: ${paper.id}`} size="small" variant="outlined" />}
                  </Box>
                </Box>
              </Box>
            </Box>

            {/* 材料状态 */}
            {(paper.material_states || []).length > 0 ? (
              <Box component="details" open sx={{
                border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 1.5, overflow: 'hidden',
              }}>
                <Box component="summary" sx={{ cursor: 'pointer', p: 2, fontSize: 18, fontWeight: 800 }}>
                  材料状态
                </Box>
                <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider', display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {(paper.material_states || []).map((state: any, index: number) => (
                    <Box key={state.id || index} sx={{
                      p: 2, borderRadius: 2, bgcolor: 'grey.50', border: '1px solid', borderColor: 'divider',
                    }}>
                      {/* 分类区 */}
                      <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1.5 }}>
                        {state.material || `材料状态 #${index + 1}`}
                      </Typography>

                      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 1.5, mb: 2 }}>
                        {state.material_family && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">材料家族</Typography>
                            <Typography variant="body2">{state.material_family.name}</Typography>
                          </Box>
                        )}
                        {state.element_count != null && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">不同元素种类数</Typography>
                            <Typography variant="body2">{state.element_count}</Typography>
                          </Box>
                        )}
                        {state.material_dimensionality && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">材料维度</Typography>
                            <Typography variant="body2">{state.material_dimensionality}</Typography>
                          </Box>
                        )}
                        {state.crystal_system && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">晶系</Typography>
                            <Typography variant="body2">{state.crystal_system}</Typography>
                          </Box>
                        )}
                        {state.reported_space_group_symbol && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">空间群符号</Typography>
                            <Typography variant="body2">{state.reported_space_group_symbol}</Typography>
                          </Box>
                        )}
                        {state.reported_space_group_number != null && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">空间群号</Typography>
                            <Typography variant="body2">{state.reported_space_group_number}</Typography>
                          </Box>
                        )}
                        {state.superconductor_kind && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">超导类型</Typography>
                            <Typography variant="body2">{state.superconductor_kind}</Typography>
                          </Box>
                        )}
                      </Box>

                      {/* 结构家族标签 */}
                      {(state.structure_families || []).length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" color="text.secondary">结构家族标签</Typography>
                          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                            {state.structure_families.map((family: any) => (
                              <Chip key={family.id || family.name} size="small" label={family.name} />
                            ))}
                          </Box>
                        </Box>
                      )}

                      {/* 压强区 */}
                      {(state.pressure_value_gpa != null || state.pressure_raw || state.pressure_min_gpa != null || state.pressure_max_gpa != null) && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" color="text.secondary">压强条件</Typography>
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mt: 0.5 }}>
                            {state.pressure_value_gpa != null && (
                              <Typography variant="body2">压强：{state.pressure_value_gpa} GPa</Typography>
                            )}
                            {state.pressure_raw && (
                              <Typography variant="body2" color="text.secondary">
                                原文：{state.pressure_raw}{state.pressure_unit_raw ? ` (${state.pressure_unit_raw})` : ''}
                              </Typography>
                            )}
                            {state.pressure_min_gpa != null && (
                              <Typography variant="body2">压强下限：{state.pressure_min_gpa} GPa</Typography>
                            )}
                            {state.pressure_max_gpa != null && (
                              <Typography variant="body2">压强上限：{state.pressure_max_gpa} GPa</Typography>
                            )}
                          </Box>
                        </Box>
                      )}

                      {/* Tc 结果区 */}
                      {(state.tc_results || []).length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" color="text.secondary">临界温度 Tc</Typography>
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 0.5 }}>
                            {state.tc_results.map((tcr: any, tcIdx: number) => (
                              <Box key={tcIdx} sx={{ p: 1, bgcolor: 'background.paper', borderRadius: 1 }}>
                                {tcr.result_kind && (
                                  <Typography variant="caption" color="primary">类型：{tcr.result_kind}</Typography>
                                )}
                                {tcr.tc_value_k != null && (
                                  <Typography variant="body2">Tc：{tcr.tc_value_k} K</Typography>
                                )}
                                {(tcr.tc_min_k != null || tcr.tc_max_k != null) && (
                                  <Typography variant="body2">
                                    Tc 区间：{tcr.tc_min_k ?? '-'} ~ {tcr.tc_max_k ?? '-'} K
                                  </Typography>
                                )}
                                {tcr.tc_method && (
                                  <Typography variant="body2">判定方法：{tcr.tc_method}</Typography>
                                )}
                                {tcr.tc_method_custom && (
                                  <Typography variant="body2">自定义方法：{tcr.tc_method_custom}</Typography>
                                )}
                                {tcr.value_raw && (
                                  <Typography variant="body2" color="text.secondary">
                                    原文：{tcr.value_raw}{tcr.unit_raw ? ` ${tcr.unit_raw}` : ''}
                                  </Typography>
                                )}
                              </Box>
                            ))}
                          </Box>
                        </Box>
                      )}

                      {/* 计算上下文（λ、ωlog、μ*） */}
                      {(state.calculation_contexts || []).length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" color="text.secondary">计算上下文</Typography>
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 0.5 }}>
                            {state.calculation_contexts.map((ctx: any, ctxIdx: number) => (
                              <Box key={ctxIdx} sx={{ p: 1, bgcolor: 'background.paper', borderRadius: 1 }}>
                                {ctx.lambda_ep != null && (
                                  <Typography variant="body2">电声耦合强度 λ：{ctx.lambda_ep}</Typography>
                                )}
                                {ctx.omega_log_k != null && (
                                  <Typography variant="body2">对数声子频率 ωlog：{ctx.omega_log_k} K</Typography>
                                )}
                                {ctx.mu_star != null && (
                                  <Typography variant="body2">库伦屏蔽常数 μ*：{ctx.mu_star}</Typography>
                                )}
                                {ctx.calculation_method && (
                                  <Typography variant="body2" color="text.secondary">计算方法：{ctx.calculation_method}</Typography>
                                )}
                                {ctx.lambda_ep == null && ctx.omega_log_k == null && ctx.mu_star == null && (
                                  <Typography variant="body2" color="text.disabled">（数值全为空）</Typography>
                                )}
                              </Box>
                            ))}
                          </Box>
                        </Box>
                      )}

                      {/* 普通物性 */}
                      {(state.key_properties || paper.key_properties?.filter((kp: any) => kp.material_state_id === state.id) || []).length > 0 && (
                        <Box>
                          <Typography variant="caption" color="text.secondary">其他物性</Typography>
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 0.5 }}>
                            {(state.key_properties || paper.key_properties?.filter((kp: any) => kp.material_state_id === state.id) || []).map((kp: any, kpIdx: number) => (
                              <Box key={kpIdx} sx={{ p: 1, bgcolor: 'background.paper', borderRadius: 1 }}>
                                <Typography variant="body2" fontWeight={600}>{kp.name || kp.name_raw || '未命名物性'}</Typography>
                                {kp.value_raw && (
                                  <Typography variant="body2">原始值：{kp.value_raw}</Typography>
                                )}
                                {kp.value_number != null && (
                                  <Typography variant="body2">解析值：{kp.value_number}</Typography>
                                )}
                                {kp.unit && (
                                  <Typography variant="body2">单位：{kp.unit}</Typography>
                                )}
                                {kp.condition_note && (
                                  <Typography variant="body2" color="text.secondary">条件说明：{kp.condition_note}</Typography>
                                )}
                              </Box>
                            ))}
                          </Box>
                        </Box>
                      )}
                    </Box>
                  ))}
                </Box>
              </Box>
            ) : (
              <Alert severity="info" sx={{ mb: 1.5 }}>该论文暂无材料状态数据</Alert>
            )}

            {/* 研究方法与发现 */}
            <Box component="details" sx={{
              border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 1.5, overflow: 'hidden',
            }}>
              <Box component="summary" sx={{ cursor: 'pointer', p: 2, fontSize: 18, fontWeight: 800 }}>
                研究方法与发现
              </Box>
              <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">研究方法</Typography>
                    {methodologyList.length > 0 ? (
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mt: 0.5 }}>
                        {methodologyList.map((method, idx) => (
                          <Typography key={idx} variant="body2">• {method}</Typography>
                        ))}
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">-</Typography>
                    )}
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">关键发现</Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{editKeyFinding || '-'}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">分类理由</Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{editRationale || '-'}</Typography>
                  </Box>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* Sidebar */}
        <Card sx={{ position: 'sticky', top: 20, boxShadow: 3 }}>
          <CardContent>
            <Typography variant="overline" color="text.secondary">化学式</Typography>
            <Typography variant="h5" fontWeight={700} sx={{ mb: 2, wordBreak: 'break-word' }}>
              {formula}
            </Typography>

            {(paper?.keywords_tags || []).length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">关键词</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                  {paper.keywords_tags.map((kw: string, idx: number) => (
                    <Chip key={idx} label={kw} size="small" />
                  ))}
                </Box>
              </Box>
            )}

            {structures.length > 0 ? (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {structures.map((s: any, i: number) => (
                  <Box key={i} sx={{ borderRadius: 2, overflow: 'hidden', border: '1px solid', borderColor: 'divider' }}>
                    <Box sx={{ p: 1.5, borderBottom: '1px solid', borderColor: 'divider', bgcolor: 'grey.50' }}>
                      <Typography variant="caption" color="text.secondary">结构 #{i + 1}</Typography>
                      <Typography variant="body2" fontWeight={700}>{s.material}</Typography>
                      {s.name_note && (
                        <Typography variant="caption" color="text.secondary">{s.name_note}</Typography>
                      )}
                      {s.pressure_gpa != null && (
                        <Chip label={`${s.pressure_gpa} GPa`} size="small" sx={{ ml: 1 }} />
                      )}
                    </Box>
                    <Box sx={{ height: 280, bgcolor: 'grey.100' }}>
                      <StructureViewer3D data={s.structure_text} format={s.structure_format} />
                    </Box>
                    <Box component="pre" sx={{
                      mt: 1, p: 1.5, borderRadius: 2, bgcolor: 'grey.50',
                      maxHeight: 200, overflow: 'auto', fontFamily: '"Roboto Mono",monospace', fontSize: 11,
                    }}>
                      {s.structure_text.slice(0, 1500)}
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
