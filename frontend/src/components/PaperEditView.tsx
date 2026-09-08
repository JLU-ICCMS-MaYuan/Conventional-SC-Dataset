import React, { useState, useEffect } from 'react'
import {
  Box, Typography, Card, CardContent, Button,
  Chip, Alert,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import DownloadIcon from '@mui/icons-material/Download'
import StructureViewer3D from './StructureViewer3D'
import { useLanguage } from '../context/LanguageContext'
import { familyName } from '../lib/classifications'
import { api } from '../lib/api'
import PropertyModuleEditor from './PropertyModuleEditor'
import { toTextList } from '../lib/paperTextLists'

interface PaperEditViewProps {
  // 论文数据与加载/错误分流由路由页面壳 PaperDetailPage 负责，本组件只负责展示。
  paper: any
  onBack: () => void
  onOpenMyPapers?: () => void
}

// 审核状态的颜色映射；标签文案按 value 查 dict.enums.reviewStatus。
const STATUS_COLORS: Record<string, 'warning' | 'success' | 'error' | 'info'> = {
  pending: 'warning', approved: 'success', rejected: 'error', needs_revision: 'info',
}

// 按当前语言解析审核状态标签；字典未收录的值回退原文（后端 value 是接口契约，不翻译）。
const reviewStatusLabel = (dict: any, value: string | null | undefined): string => {
  const table: Record<string, string> = dict?.enums?.reviewStatus || {}
  return (value && table[value]) || value || ''
}

const PaperEditView: React.FC<PaperEditViewProps> = ({ paper, onBack, onOpenMyPapers }) => {
  const { t, lang, dict } = useLanguage()

  // 只读展示状态：用于展示的本地状态，切换论文时重新填充
  const [editTitle, setEditTitle] = useState('')
  const [editDoi, setEditDoi] = useState('')
  const [editJournal, setEditJournal] = useState('')
  const [editYear, setEditYear] = useState<number | ''>('')
  const [editAuthors, setEditAuthors] = useState('')
  const [editAbstract, setEditAbstract] = useState('')
  const [editSummary, setEditSummary] = useState('')
  const [editKnowledgeGraphTitle, setEditKnowledgeGraphTitle] = useState('')
  const [editKeyFinding, setEditKeyFinding] = useState('')
  const [editResearchMotivation, setEditResearchMotivation] = useState('')
  const [exportError, setExportError] = useState('')

  const downloadMaterialState = async (state: any) => {
    try {
      setExportError('')
      const blob = await api.download(`/api/papers/${paper.id}/material-states/${encodeURIComponent(state.state_key)}/export`)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${state.material || 'material-state'}-revision-${paper.content_revision || paper.revision || 1}.json`
      link.click()
      URL.revokeObjectURL(url)
    } catch (reason) {
      setExportError(reason instanceof Error ? reason.message : '材料状态导出失败')
    }
  }

  // 化学式来自 MaterialState；Read switch 后不再依赖旧 key_properties。
  const formula = paper?.material_states?.[0]?.material || (paper?.materials?.[0]) || '-'

  // 论文数据由 props 传入；同步到本地展示状态，切换论文时重新填充
  useEffect(() => {
    const data = paper || {}
    setEditTitle(data.title || '')
    setEditDoi(data.doi || '')
    setEditJournal(data.journal || '')
    setEditYear(data.year || '')
    // authors 同为 JSON 文本列，直接展示会把 ["A","B"] 原样印到页面上；
    // 分隔符随界面语言：中文顿号、英文逗号。
    setEditAuthors(toTextList(data.authors).join(lang === 'zh' ? '、' : ', '))
    setEditAbstract(data.abstract || '')
    setEditSummary(data.summary || '')
    setEditKnowledgeGraphTitle(data.knowledge_graph_title || '')
    setEditKeyFinding(data.key_finding || '')
    setEditResearchMotivation(data.research_motivation || '')
  }, [paper, lang])

  // 研究方法与关键词处理：转为可读列表
  const methodologyList = toTextList(paper?.methodology)
  const keywordList = toTextList(paper?.keywords_tags)

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
            {t('paperDetail.backToUpload')}
          </Button>
          <Typography variant="overline" color="text.secondary">{t('paperDetail.readOnlyMode')}</Typography>
          <Typography variant="h4" fontWeight={800}>{t('paperDetail.paperDetailTitle')}</Typography>
        </Box>
        {/* 离开详情页后仍能经界面回到任意已提交论文，无需手工拼接网址 */}
        {onOpenMyPapers && (
          <Button size="small" variant="outlined" onClick={onOpenMyPapers}>{t('paperDetail.myPapers')}</Button>
        )}
      </Box>

      <Alert severity="info" sx={{ mb: 2 }}>{t('paperDetail.submittedNotice')}</Alert>

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
                {t('paperDetail.basicInfo')}
              </Box>
              <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldTitle')}</Typography>
                    <Typography variant="body2">{editTitle || '-'}</Typography>
                  </Box>
                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
                    <Box>
                      {/* DOI 为专有名词，两种语言下写法一致 */}
                      <Typography variant="caption" color="text.secondary">DOI</Typography>
                      <Typography variant="body2">{editDoi || '-'}</Typography>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldYear')}</Typography>
                      <Typography variant="body2">{editYear || '-'}</Typography>
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldJournal')}</Typography>
                    <Typography variant="body2">{editJournal || '-'}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldAuthors')}</Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{editAuthors || '-'}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldAbstract')}</Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{editAbstract || '-'}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldSummary')}</Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{editSummary || '-'}</Typography>
                  </Box>
                  {(paper.material_families || []).length > 0 && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldMaterialFamily')}</Typography>
                      <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mt: 0.5 }}>
                        {paper.material_families.map((family: any) => (
                          <Chip key={family.id ?? family.name} size="small" label={familyName(family, lang)} />
                        ))}
                      </Box>
                    </Box>
                  )}
                  {paper.superconductor_kind && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldSuperconductorKind')}</Typography>
                      <Typography variant="body2">{paper.superconductor_kind}</Typography>
                    </Box>
                  )}
                  {editKnowledgeGraphTitle && (
                    <Box>
                      <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldKgTitle')}</Typography>
                      <Typography variant="body2">{editKnowledgeGraphTitle}</Typography>
                    </Box>
                  )}
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip label={`${t('paperDetail.reviewStatus')}: ${reviewStatusLabel(dict, paper?.review_status) || reviewStatusLabel(dict, 'pending')}`}
                      size="small" color={STATUS_COLORS[paper?.review_status] || 'default'} />
                    <Chip label={`${t('paperDetail.dataSource')}: Local`} size="small" color="primary" />
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
                  {t('paperDetail.materialStates')}
                </Box>
                <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider', display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {(paper.material_states || []).map((state: any, index: number) => (
                    <Box key={state.id || index} sx={{
                      p: 2, borderRadius: 2, bgcolor: 'grey.50', border: '1px solid', borderColor: 'divider',
                    }}>
                      {/* 分类区 */}
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 1, mb: 1.5 }}>
                        <Typography variant="subtitle2" fontWeight={700}>
                          {state.material || t('paperDetail.materialStateFallback', { n: index + 1 })}
                        </Typography>
                        {state.state_key && <Button size="small" startIcon={<DownloadIcon />} onClick={() => void downloadMaterialState(state)}>导出材料状态</Button>}
                      </Box>
                      {exportError && <Alert severity="error" sx={{ mb: 1 }}>{exportError}</Alert>}

                      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 1.5, mb: 2 }}>
                        {state.element_count != null && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldElementCount')}</Typography>
                            <Typography variant="body2">{state.element_count}</Typography>
                          </Box>
                        )}
                        {state.material_dimensionality && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldDimensionality')}</Typography>
                            {/* 材料维度/晶系展示后端枚举 value（接口契约，不翻译） */}
                            <Typography variant="body2">{state.material_dimensionality}</Typography>
                          </Box>
                        )}
                        {state.crystal_system && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldCrystalSystem')}</Typography>
                            <Typography variant="body2">{state.crystal_system}</Typography>
                          </Box>
                        )}
                        {state.reported_space_group_symbol && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldSpaceGroupSymbol')}</Typography>
                            <Typography variant="body2">{state.reported_space_group_symbol}</Typography>
                          </Box>
                        )}
                        {state.reported_space_group_number != null && (
                          <Box>
                            <Typography variant="caption" color="text.secondary">{t('paperDetail.fieldSpaceGroupNumber')}</Typography>
                            <Typography variant="body2">{state.reported_space_group_number}</Typography>
                          </Box>
                        )}
                      </Box>

                      {/* 结构家族标签 */}
                      {(state.structure_families || []).length > 0 && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" color="text.secondary">{t('paperDetail.structureFamiliesLabel')}</Typography>
                          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                            {state.structure_families.map((family: any) => (
                              <Chip key={family.id || family.name} size="small" label={familyName(family, lang)} />
                            ))}
                          </Box>
                        </Box>
                      )}

                      {/* 压强区 */}
                      {(state.pressure_value_gpa != null || state.pressure_raw || state.pressure_min_gpa != null || state.pressure_max_gpa != null) && (
                        <Box sx={{ mb: 2 }}>
                          <Typography variant="caption" color="text.secondary">{t('paperDetail.pressureSection')}</Typography>
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mt: 0.5 }}>
                            {state.pressure_value_gpa != null && (
                              <Typography variant="body2">{t('paperDetail.pressureValue', { value: state.pressure_value_gpa })}</Typography>
                            )}
                            {state.pressure_raw && (
                              <Typography variant="body2" color="text.secondary">
                                {t('paperDetail.rawText', { value: `${state.pressure_raw}${state.pressure_unit_raw ? ` (${state.pressure_unit_raw})` : ''}` })}
                              </Typography>
                            )}
                            {state.pressure_min_gpa != null && (
                              <Typography variant="body2">{t('paperDetail.pressureMin', { value: state.pressure_min_gpa })}</Typography>
                            )}
                            {state.pressure_max_gpa != null && (
                              <Typography variant="body2">{t('paperDetail.pressureMax', { value: state.pressure_max_gpa })}</Typography>
                            )}
                          </Box>
                        </Box>
                      )}

                      <PropertyModuleEditor modules={state.property_modules || []} readOnly onChange={() => undefined} />
                    </Box>
                  ))}
                </Box>
              </Box>
            ) : (
              <Alert severity="info" sx={{ mb: 1.5 }}>{t('paperDetail.noMaterialStates')}</Alert>
            )}

            {/* 研究方法与发现 */}
            <Box component="details" sx={{
              border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 1.5, overflow: 'hidden',
            }}>
              <Box component="summary" sx={{ cursor: 'pointer', p: 2, fontSize: 18, fontWeight: 800 }}>
                {t('paperDetail.methodsFindings')}
              </Box>
              <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <Box>
                    <Typography variant="caption" color="text.secondary">{t('paperDetail.methodology')}</Typography>
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
                    <Typography variant="caption" color="text.secondary">{t('paperDetail.keyFinding')}</Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{editKeyFinding || '-'}</Typography>
                  </Box>
                  <Box>
                    <Typography variant="caption" color="text.secondary">{t('paperDetail.researchMotivation')}</Typography>
                    <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>{editResearchMotivation || '-'}</Typography>
                  </Box>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* Sidebar */}
        <Card sx={{ position: 'sticky', top: 20, boxShadow: 3 }}>
          <CardContent>
            <Typography variant="overline" color="text.secondary">{t('paperDetail.formulaLabel')}</Typography>
            <Typography variant="h5" fontWeight={700} sx={{ mb: 2, wordBreak: 'break-word' }}>
              {formula}
            </Typography>

            {keywordList.length > 0 && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="caption" color="text.secondary">{t('paperDetail.keywordsLabel')}</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                  {keywordList.map((kw, idx) => (
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
                      <Typography variant="caption" color="text.secondary">{t('paperDetail.structureIndex', { n: i + 1 })}</Typography>
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
                  {t('paperDetail.noStructure')}
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
