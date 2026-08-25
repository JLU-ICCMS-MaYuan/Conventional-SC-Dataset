import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Dialog, DialogActions, DialogContent,
  DialogTitle, FormControl, InputLabel, MenuItem, Select, TextField, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import { api } from '../lib/api'
import {
  ClassificationCatalogs,
  ClassificationTerm,
  loadClassificationCatalogs,
  refreshClassificationCatalogs,
} from '../lib/classifications'

interface ClassificationProposal {
  id: number
  dimension: 'material_family' | 'structure_family'
  raw_name: string
  status: string
}

type ResolutionKind = 'mapped_existing' | 'alias_created' | 'formal_created' | 'rejected'
type CatalogDimension = 'material_family' | 'structure_family'

interface ManagedCatalogTerm extends ClassificationTerm {
  dimension: CatalogDimension
}

interface ClassificationAudit {
  id: number
  action: string
  dimension: string
  reason: string
  created_at: string
}

interface ClassificationGovernancePanelProps {
  isSuper: boolean
}

const ClassificationGovernancePanel: React.FC<ClassificationGovernancePanelProps> = ({ isSuper }) => {
  const [catalogs, setCatalogs] = useState<ClassificationCatalogs | null>(null)
  const [proposals, setProposals] = useState<ClassificationProposal[]>([])
  const [audits, setAudits] = useState<ClassificationAudit[]>([])
  const [error, setError] = useState('')
  const [dimension, setDimension] = useState<CatalogDimension>('material_family')
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [nameEn, setNameEn] = useState('')
  const [reason, setReason] = useState('')
  const [selectedProposal, setSelectedProposal] = useState<ClassificationProposal | null>(null)
  const [resolutionKind, setResolutionKind] = useState<ResolutionKind>('mapped_existing')
  const [targetId, setTargetId] = useState<number | ''>('')
  const [resolutionReason, setResolutionReason] = useState('')
  const [resolutionCode, setResolutionCode] = useState('')
  const [resolutionName, setResolutionName] = useState('')
  const [resolutionNameEn, setResolutionNameEn] = useState('')
  const [selectedTerm, setSelectedTerm] = useState<ManagedCatalogTerm | null>(null)
  const [termName, setTermName] = useState('')
  const [termNameEn, setTermNameEn] = useState('')
  const [termReason, setTermReason] = useState('')
  const [mergeTargetId, setMergeTargetId] = useState<number | ''>('')

  const load = useCallback(async () => {
    try {
      const [nextCatalogs, proposalResponse, auditResponse] = await Promise.all([
        loadClassificationCatalogs(),
        api.get<{ items: ClassificationProposal[] }>('/api/admin/classification-proposals'),
        isSuper
          ? api.get<{ items: ClassificationAudit[] }>('/api/superadmin/classification-audits')
          : Promise.resolve({ items: [] }),
      ])
      setCatalogs(nextCatalogs)
      setProposals((proposalResponse.items || []).filter(item => !['resolved', 'rejected'].includes(item.status)))
      setAudits(auditResponse.items || [])
      setError('')
    } catch (cause) {
      setError((cause as Error).message || '分类治理数据加载失败')
    }
  }, [isSuper])

  useEffect(() => { void load() }, [load])

  const createTerm = async () => {
    try {
      await api.post(`/api/superadmin/classification-catalogs/${dimension}`, {
        code, name, name_en: nameEn, reason,
      })
      const nextCatalogs = await refreshClassificationCatalogs()
      setCatalogs(nextCatalogs)
      setCode('')
      setName('')
      setNameEn('')
      setReason('')
      setError('')
    } catch (cause) {
      setError((cause as Error).message || '分类目录创建失败')
    }
  }

  const refreshCatalogs = async () => {
    const nextCatalogs = await refreshClassificationCatalogs()
    setCatalogs(nextCatalogs)
  }

  const openTerm = (term: ClassificationTerm, termDimension: CatalogDimension) => {
    setSelectedTerm({ ...term, dimension: termDimension })
    setTermName(term.name)
    setTermNameEn('')
    setTermReason('')
    setMergeTargetId('')
  }

  const closeTerm = () => {
    setMergeTargetId('')
    setSelectedTerm(null)
  }

  const updateTerm = async (changes: Record<string, unknown>) => {
    if (!selectedTerm) return
    try {
      await api.patch(`/api/superadmin/classification-catalogs/${selectedTerm.dimension}/${selectedTerm.id}`, {
        ...changes,
        reason: termReason,
      })
      await refreshCatalogs()
      closeTerm()
      setError('')
    } catch (cause) {
      setError((cause as Error).message || '分类目录修改失败')
    }
  }

  const mergeTerm = async () => {
    if (!selectedTerm || !mergeTargetId) return
    try {
      await api.post(`/api/superadmin/classification-catalogs/${selectedTerm.dimension}/${selectedTerm.id}/merge`, {
        target_id: mergeTargetId,
        reason: termReason,
      })
      await refreshCatalogs()
      closeTerm()
      setError('')
    } catch (cause) {
      setError((cause as Error).message || '分类目录合并失败')
    }
  }

  const openProposal = (proposal: ClassificationProposal) => {
    setSelectedProposal(proposal)
    setResolutionKind('mapped_existing')
    setTargetId('')
    setResolutionReason('')
    setResolutionCode('')
    setResolutionName(proposal.raw_name)
    setResolutionNameEn('')
  }

  const closeProposal = () => {
    setTargetId('')
    setSelectedProposal(null)
  }

  const resolveProposal = async () => {
    if (!selectedProposal) return
    try {
      if (isSuper) {
        await api.post(`/api/superadmin/classification-proposals/${selectedProposal.id}/resolve`, {
          resolution_kind: resolutionKind,
          target_id: targetId || 0,
          code: resolutionCode,
          name: resolutionName,
          name_en: resolutionNameEn,
          reason: resolutionReason,
        })
      } else if (resolutionKind === 'mapped_existing') {
        await api.post(`/api/admin/classification-proposals/${selectedProposal.id}/map`, {
          target_id: targetId,
          reason: resolutionReason,
        })
      } else {
        await api.post(`/api/admin/classification-proposals/${selectedProposal.id}/recommend`, {
          resolution_kind: resolutionKind,
          target_id: targetId || null,
          reason: resolutionReason,
        })
      }
      closeProposal()
      await load()
    } catch (cause) {
      setError((cause as Error).message || '分类建议处理失败')
    }
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {error && <Alert severity="error">{error}</Alert>}
      {isSuper && <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" fontWeight={700} gutterBottom>材料家族目录</Typography>
            {(catalogs?.material_families || []).map(item => (
              <Box key={item.id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
                <Typography variant="body2">
                  {item.name}{item.aliases.length ? `（别名：${item.aliases.join('、')}）` : ''}
                </Typography>
                <Button size="small" aria-label={`管理${item.name}`} onClick={() => openTerm(item, 'material_family')}>管理</Button>
              </Box>
            ))}
          </CardContent>
        </Card>
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" fontWeight={700} gutterBottom>结构家族目录</Typography>
            {(catalogs?.structure_families || []).map(item => (
              <Box key={item.id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 1 }}>
                <Typography variant="body2">
                  {item.name}{item.aliases.length ? `（别名：${item.aliases.join('、')}）` : ''}
                </Typography>
                <Button size="small" aria-label={`管理${item.name}`} onClick={() => openTerm(item, 'structure_family')}>管理</Button>
              </Box>
            ))}
          </CardContent>
        </Card>
      </Box>}

      {isSuper && <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '180px 1fr 1fr 1fr 2fr auto' }, gap: 1 }}>
        <FormControl size="small">
          <InputLabel>目录维度</InputLabel>
          <Select label="目录维度" value={dimension} onChange={event => setDimension(event.target.value as typeof dimension)}>
            <MenuItem value="material_family">材料家族</MenuItem>
            <MenuItem value="structure_family">结构家族</MenuItem>
          </Select>
        </FormControl>
        <TextField size="small" label="内部编码" value={code} onChange={event => setCode(event.target.value)} />
        <TextField size="small" label="规范中文名" value={name} onChange={event => setName(event.target.value)} />
        <TextField size="small" label="规范英文名" value={nameEn} onChange={event => setNameEn(event.target.value)} />
        <TextField size="small" label="创建原因" value={reason} onChange={event => setReason(event.target.value)} />
        <Button variant="contained" startIcon={<AddIcon />} disabled={!code || !name || !nameEn || !reason} onClick={() => void createTerm()}>
          新建
        </Button>
      </Box>}

      <Box>
        <Typography variant="subtitle1" fontWeight={700} gutterBottom>待处理建议</Typography>
        {proposals.map(proposal => {
          const terms = proposal.dimension === 'material_family'
            ? catalogs?.material_families || []
            : catalogs?.structure_families || []
          return (
            <Box key={proposal.id} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr auto' }, gap: 1, mb: 1, alignItems: 'center' }}>
              <Typography variant="body2">{proposal.raw_name}</Typography>
              <Button size="small" variant="outlined" onClick={() => openProposal(proposal)} disabled={terms.length === 0}>
                处理建议
              </Button>
            </Box>
          )
        })}
        {proposals.length === 0 && <Typography variant="body2" color="text.secondary">没有待处理建议</Typography>}
      </Box>

      <Dialog open={Boolean(selectedProposal)} onClose={closeProposal} fullWidth maxWidth="sm">
        <DialogTitle>处理分类建议</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '12px !important' }}>
          <Typography variant="body2">AI / 用户原始名称：{selectedProposal?.raw_name}</Typography>
          <FormControl size="small">
            <InputLabel id="classification-resolution-kind-label">处理方式</InputLabel>
            <Select labelId="classification-resolution-kind-label" label="处理方式" value={resolutionKind} onChange={event => { setResolutionKind(event.target.value as ResolutionKind); setTargetId('') }}>
              <MenuItem value="mapped_existing">映射到现有目录</MenuItem>
              <MenuItem value="alias_created">批准为现有项别名</MenuItem>
              <MenuItem value="formal_created">创建正式目录项</MenuItem>
              <MenuItem value="rejected">拒绝建议</MenuItem>
            </Select>
          </FormControl>
          {['mapped_existing', 'alias_created'].includes(resolutionKind) && (
            <FormControl size="small">
              <InputLabel id="classification-resolution-target-label">目标目录项</InputLabel>
              <Select labelId="classification-resolution-target-label" label="目标目录项" value={targetId} onChange={event => setTargetId(Number(event.target.value))}>
                {(selectedProposal?.dimension === 'material_family'
                  ? catalogs?.material_families || []
                  : catalogs?.structure_families || []).map(term => (
                  <MenuItem key={term.id} value={term.id}>{term.name}</MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          {isSuper && resolutionKind === 'formal_created' && (
            <>
              <TextField size="small" label="内部编码" value={resolutionCode} onChange={event => setResolutionCode(event.target.value)} />
              <TextField size="small" label="规范中文名" value={resolutionName} onChange={event => setResolutionName(event.target.value)} />
              <TextField size="small" label="规范英文名" value={resolutionNameEn} onChange={event => setResolutionNameEn(event.target.value)} />
            </>
          )}
          <TextField size="small" label="处理原因" multiline minRows={2} value={resolutionReason} onChange={event => setResolutionReason(event.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={closeProposal}>取消</Button>
          <Button
            variant="contained"
            disabled={
              !resolutionReason
              || (['mapped_existing', 'alias_created'].includes(resolutionKind) && !targetId)
              || (isSuper && resolutionKind === 'formal_created' && (!resolutionCode || !resolutionName || !resolutionNameEn))
            }
            onClick={() => void resolveProposal()}
          >
            确认处理
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(selectedTerm)} onClose={closeTerm} fullWidth maxWidth="sm">
        <DialogTitle>管理正式目录项</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '12px !important' }}>
          <Typography variant="body2">当前目录项：{selectedTerm?.name}</Typography>
          <TextField size="small" label="新的规范中文名" value={termName} onChange={event => setTermName(event.target.value)} />
          <TextField size="small" label="新的规范英文名" value={termNameEn} onChange={event => setTermNameEn(event.target.value)} />
          <FormControl size="small">
            <InputLabel id="classification-merge-target-label">合并到</InputLabel>
            <Select
              labelId="classification-merge-target-label"
              label="合并到"
              value={mergeTargetId}
              onChange={event => setMergeTargetId(Number(event.target.value))}
            >
              {(selectedTerm?.dimension === 'material_family'
                ? catalogs?.material_families || []
                : catalogs?.structure_families || [])
                .filter(item => item.id !== selectedTerm?.id)
                .map(item => <MenuItem key={item.id} value={item.id}>{item.name}</MenuItem>)}
            </Select>
          </FormControl>
          <TextField size="small" label="修改原因" multiline minRows={2} value={termReason} onChange={event => setTermReason(event.target.value)} />
        </DialogContent>
        <DialogActions sx={{ flexWrap: 'wrap' }}>
          <Button onClick={closeTerm}>取消</Button>
          <Button color="warning" disabled={!termReason} onClick={() => void updateTerm({ is_active: false })}>停用目录项</Button>
          <Button color="warning" disabled={!termReason || !mergeTargetId} onClick={() => void mergeTerm()}>合并目录项</Button>
          <Button
            variant="contained"
            disabled={!termName || !termNameEn || !termReason}
            onClick={() => void updateTerm({ name: termName, name_en: termNameEn })}
          >
            保存目录项
          </Button>
        </DialogActions>
      </Dialog>

      {isSuper && <Box>
        <Typography variant="subtitle1" fontWeight={700} gutterBottom>最近治理审计</Typography>
        {audits.slice(0, 20).map(audit => (
          <Typography key={audit.id} variant="body2" color="text.secondary">
            {audit.dimension} · {audit.action} · {audit.reason}
          </Typography>
        ))}
        {audits.length === 0 && <Typography variant="body2" color="text.secondary">暂无审计记录</Typography>}
      </Box>}
    </Box>
  )
}

export default ClassificationGovernancePanel
