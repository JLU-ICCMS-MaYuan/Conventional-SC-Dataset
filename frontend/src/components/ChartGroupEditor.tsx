import React, { useState, useEffect } from 'react'
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Typography, Box,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  IconButton, Checkbox, FormControlLabel, Paper,
  Snackbar, Alert, CircularProgress, LinearProgress,
  FormControl, InputLabel, Select, MenuItem,
} from '@mui/material'
import { Delete, Add } from '@mui/icons-material'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'

// ── Types ──

interface LocalItem {
  id?: number
  sort_order: number
  source: 'kp' | 'custom'
  key_property_id: number | null
  material: string
  tc: number | null
  pressure: number | null
  type: string | null
  year: number | null
  custom_label?: string
  custom_tc?: number
  custom_pressure?: number
  custom_type?: string
  custom_article_type?: string
  custom_year?: number
}

interface LocalGroup {
  id?: number
  name: string
  description: string
  is_public: boolean
  items: LocalItem[]
}

interface Props {
  open: boolean
  groupId: number | null
  onClose: () => void
  onSaved: () => void
}

// ── Constants ──

const SC_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: 'hydride', label: '氢化物' },
  { value: 'cuprate', label: '铜基' },
  { value: 'iron_based', label: '铁基' },
  { value: 'nickel_based', label: '镍基' },
  { value: 'carbon', label: '碳基' },
  { value: 'organic', label: '有机' },
  { value: 'others', label: '其他' },
]

const SC_TYPE_LABEL_MAP: Record<string, string> = Object.fromEntries(
  SC_TYPE_OPTIONS.map(o => [o.value, o.label])
)

const emptyGroup: LocalGroup = { name: '', description: '', is_public: false, items: [] }

// ── Component ──

const ChartGroupEditor: React.FC<Props> = ({ open, groupId, onClose, onSaved }) => {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin' || user?.role === 'superadmin'

  // ── Group state ──
  const [group, setGroup] = useState<LocalGroup>(emptyGroup)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  // ── Snackbar ──
  const [snackbar, setSnackbar] = useState<{ message: string; severity: 'success' | 'error' } | null>(null)

  // ── KP search ──
  const [kpSearch, setKpSearch] = useState('')
  const [kpLoading, setKpLoading] = useState(false)
  const [kpResults, setKpResults] = useState<any[]>([])

  // ── Custom point form ──
  const [customLabel, setCustomLabel] = useState('')
  const [customTc, setCustomTc] = useState('')
  const [customPressure, setCustomPressure] = useState('')
  const [customType, setCustomType] = useState('')
  const [customArticleType, setCustomArticleType] = useState('')
  const [customYear, setCustomYear] = useState('')

  // ── Import from group ──
  const [importGroupOpen, setImportGroupOpen] = useState(false)
  const [availableGroups, setAvailableGroups] = useState<any[]>([])

  const loadAvailableGroups = () => {
    api.get<any[]>('/api/chart-groups')
      .then(remote => {
        const local = JSON.parse(localStorage.getItem('scwiki_local_groups') || '[]')
        setAvailableGroups([...local, ...(Array.isArray(remote) ? remote : [])].filter((g: any) => g.id !== group.id))
      })
      .catch(() => {
        const local = JSON.parse(localStorage.getItem('scwiki_local_groups') || '[]')
        setAvailableGroups(local.filter((g: any) => g.id !== group.id))
      })
  }

  const importFromGroup = (src: any) => {
    const newItems = (src.items || []).map((it: any, i: number) => ({
      sort_order: group.items.length + i,
      source: (it.source || (it.key_property_id ? 'kp' : 'custom')) as 'kp' | 'custom',
      key_property_id: it.key_property_id ?? null,
      material: it.material ?? it.custom_label ?? '',
      tc: it.tc ?? it.custom_tc ?? null,
      pressure: it.pressure ?? it.custom_pressure ?? null,
      type: it.type ?? it.custom_type ?? null,
      year: it.year ?? it.custom_year ?? null,
      custom_label: it.custom_label,
      custom_tc: it.custom_tc,
      custom_pressure: it.custom_pressure,
      custom_type: it.custom_type,
      custom_article_type: it.custom_article_type,
      custom_year: it.custom_year,
    }))
    setGroup(prev => ({ ...prev, items: [...prev.items, ...newItems] }))
    setImportGroupOpen(false)
  }

  // ── Load existing group ──
  useEffect(() => {
    if (!open) return
    if (groupId) {
      setLoading(true);
      (user
        ? api.get<any>(`/api/chart-groups/${groupId}`)  // 已登录 → API
        : Promise.resolve(  // 未登录 → localStorage
            (JSON.parse(localStorage.getItem('scwiki_local_groups') || '[]') as any[])
              .find((g: any) => g.id === groupId) || null
          ).then(g => g ? { ...g, items: g.items || [] } : Promise.reject('not found'))
      ).then(d => {
        setGroup({
          id: d.id,
          name: d.name,
          description: d.description || '',
          is_public: d.is_public || false,
          items: (d.items || []).map((it: any) => ({
            id: it.id,
            sort_order: it.sort_order ?? 0,
            source: (it.source || (it.key_property_id ? 'kp' : 'custom')) as 'kp' | 'custom',
            key_property_id: it.key_property_id ?? null,
            material: it.material ?? it.custom_label ?? '',
            tc: it.tc ?? it.custom_tc ?? null,
            pressure: it.pressure ?? it.custom_pressure ?? null,
            type: it.type ?? it.custom_type ?? null,
            year: it.year ?? it.custom_year ?? null,
            custom_label: it.custom_label,
            custom_tc: it.custom_tc,
            custom_pressure: it.custom_pressure,
            custom_type: it.custom_type,
            custom_article_type: it.custom_article_type,
            custom_year: it.custom_year,
          })),
        })
      })
      .catch(() => setSnackbar({ message: '加载失败', severity: 'error' }))
      .finally(() => setLoading(false))
    } else {
      setGroup(emptyGroup)
    }
    // Reset sub-forms
    setKpSearch('')
    setKpResults([])
    setCustomLabel('')
    setCustomTc('')
    setCustomPressure('')
    setCustomType('')
    setCustomArticleType('')
    setCustomYear('')
  }, [open, groupId])

  // ── Search key_properties ──
  const handleSearchAndAdd = async () => {
    if (!kpSearch.trim()) return
    setKpLoading(true)
    try {
      const data = await api.get<any[]>(`/api/chart-groups/search?q=${encodeURIComponent(kpSearch)}`)
      setKpResults(data || [])
    } catch (e: any) {
      setSnackbar({ message: e.message || '搜索失败', severity: 'error' })
    } finally {
      setKpLoading(false)
    }
  }

  // ── Add KP result to group ──
  const addKpToGroup = (kp: any) => {
    // Prevent duplicate
    if (group.items.some(it => it.source === 'kp' && it.key_property_id === kp.id)) {
      setSnackbar({ message: '该数据点已在组合中', severity: 'error' })
      return
    }
    const newItem: LocalItem = {
      sort_order: group.items.length,
      source: 'kp',
      key_property_id: kp.id,
      material: kp.material,
      tc: kp.value_max ?? null,
      pressure: kp.pressure_gpa ?? null,
      type: kp.superconductor_type ?? null,
      year: null,
    }
    setGroup(prev => ({ ...prev, items: [...prev.items, newItem] }))
  }

  // ── Add custom point ──
  const addCustomPoint = () => {
    if (!customLabel.trim()) return
    const tcNum = customTc ? parseFloat(customTc) : undefined
    const pNum = customPressure ? parseFloat(customPressure) : undefined
    const yearNum = customYear ? parseInt(customYear) : undefined
    const newItem: LocalItem = {
      sort_order: group.items.length,
      source: 'custom',
      key_property_id: null,
      material: customLabel.trim(),
      tc: tcNum ?? null,
      pressure: pNum ?? null,
      type: customType || null,
      year: yearNum ?? null,
      custom_label: customLabel.trim(),
      custom_tc: tcNum,
      custom_pressure: pNum,
      custom_type: customType || undefined,
      custom_article_type: customArticleType || undefined,
      custom_year: yearNum,
    }
    setGroup(prev => ({ ...prev, items: [...prev.items, newItem] }))
    setCustomLabel('')
    setCustomTc('')
    setCustomPressure('')
    setCustomType('')
    setCustomArticleType('')
    setCustomYear('')
  }

  // ── Remove item ──
  const removeItem = (index: number) => {
    setGroup(prev => ({
      ...prev,
      items: prev.items.filter((_, i) => i !== index).map((it, i) => ({ ...it, sort_order: i })),
    }))
  }

  // ── Save ──
  const handleSave = async () => {
    if (!group.name.trim()) {
      setSnackbar({ message: '请输入组合名称', severity: 'error' })
      return
    }
    setSaving(true)
    try {
      const items = group.items.map(it => ({
        key_property_id: it.key_property_id,
        custom_label: it.custom_label,
        custom_tc: it.custom_tc,
        custom_pressure: it.custom_pressure,
        custom_type: it.custom_type,
        custom_article_type: it.custom_article_type,
        custom_year: it.custom_year,
      }))

      if (user) {
        // 已登录 → API
        const url = group.id ? `/api/chart-groups/${group.id}` : '/api/chart-groups'
        const body = { name: group.name.trim(), description: group.description.trim(), items }
        const result = group.id
          ? await api.put<any>(url, body)
          : await api.post<any>(url, body)
        if (isAdmin && result.id && group.is_public !== result.is_public) {
          await api.patch(`/api/chart-groups/${result.id}/public`, { is_public: group.is_public })
        }
      } else {
        // 未登录 → localStorage
        const stored = JSON.parse(localStorage.getItem('scwiki_local_groups') || '[]')
        if (group.id) {
          const idx = stored.findIndex((g: any) => g.id === group.id)
          if (idx >= 0) {
            stored[idx] = { ...stored[idx], name: group.name.trim(), description: group.description.trim(), items, updated_at: new Date().toISOString() }
          }
        } else {
          stored.push({
            id: Date.now(), name: group.name.trim(), description: group.description.trim(),
            is_preset: false, is_public: false, items, item_count: items.length,
            created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
          })
        }
        localStorage.setItem('scwiki_local_groups', JSON.stringify(stored))
      }

      onSaved()
      onClose()
    } catch (e: any) {
      setSnackbar({ message: e.message || '保存失败', severity: 'error' })
    } finally {
      setSaving(false)
    }
  }

  // ── Render helpers ──

  const formatValue = (v: number | null): string => {
    if (v == null) return '-'
    return Number.isInteger(v) ? String(v) : v.toFixed(2)
  }

  const typeLabel = (t: string | null): string => {
    if (!t) return '-'
    return SC_TYPE_LABEL_MAP[t] || t
  }

  // ═══════════════════════════════════════════════════════
  // Render
  // ═══════════════════════════════════════════════════════
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ fontWeight: 600, fontSize: '1.15rem' }}>
        {group.id ? '编辑组合' : '新建组合'}
      </DialogTitle>

      <DialogContent dividers>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
            {/* ── Basic info ── */}
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'flex-start' }}>
              <TextField
                label="名称"
                size="small"
                required
                value={group.name}
                onChange={e => setGroup(prev => ({ ...prev, name: e.target.value }))}
                sx={{ minWidth: 240, flex: 1 }}
              />
              <TextField
                label="描述"
                size="small"
                value={group.description}
                onChange={e => setGroup(prev => ({ ...prev, description: e.target.value }))}
                sx={{ minWidth: 240, flex: 2 }}
              />
            </Box>

            {isAdmin && (
              <FormControlLabel
                control={
                  <Checkbox
                    checked={group.is_public}
                    onChange={e => setGroup(prev => ({ ...prev, is_public: e.target.checked }))}
                    size="small"
                  />
                }
                label={<Typography variant="body2" color="text.secondary">公开（所有用户可见）</Typography>}
              />
            )}

            {/* ── Data point table ── */}
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                数据点 ({group.items.length})
              </Typography>
              {group.items.length === 0 ? (
                <Typography variant="body2" color="text.disabled" sx={{ py: 1 }}>
                  暂无数据点，请从下方添加
                </Typography>
              ) : (
                <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 280 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>材料</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Tc (K)</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>压力 (GPa)</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>类型</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>来源</TableCell>
                        <TableCell sx={{ fontWeight: 600, width: 48 }} />
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {group.items.map((it, idx) => (
                        <TableRow key={idx} hover>
                          <TableCell>{it.material}</TableCell>
                          <TableCell>{formatValue(it.tc)}</TableCell>
                          <TableCell>{formatValue(it.pressure)}</TableCell>
                          <TableCell>{typeLabel(it.type)}</TableCell>
                          <TableCell>
                            <Typography
                              variant="caption"
                              sx={{
                                bgcolor: it.source === 'kp' ? 'primary.50' : 'warning.50',
                                color: it.source === 'kp' ? 'primary.700' : 'warning.700',
                                px: 1, py: 0.25, borderRadius: 1,
                              }}
                            >
                              {it.source === 'kp' ? '数据库' : '自定义'}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <IconButton size="small" color="error" onClick={() => removeItem(idx)}>
                              <Delete fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>

            {/* ── Search from database ── */}
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                从数据库添加
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  size="small"
                  placeholder="搜索材料名称..."
                  value={kpSearch}
                  onChange={e => setKpSearch(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') handleSearchAndAdd() }}
                  sx={{ flex: 1 }}
                />
                <Button
                  variant="outlined"
                  size="small"
                  onClick={handleSearchAndAdd}
                  disabled={kpLoading || !kpSearch.trim()}
                >
                  {kpLoading ? <CircularProgress size={16} sx={{ mr: 0.5 }} /> : null}
                  搜索
                </Button>
              </Box>

              {kpLoading && <LinearProgress sx={{ mt: 1 }} />}

              {kpResults.length > 0 && (
                <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 0.5, maxHeight: 200, overflow: 'auto' }}>
                  {kpResults.map((kp, idx) => (
                    <Paper
                      key={idx}
                      variant="outlined"
                      sx={{
                        p: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' },
                      }}
                      onClick={() => addKpToGroup(kp)}
                    >
                      <Box>
                        <Typography variant="body2" fontWeight={600}>{kp.material}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          Tc: {formatValue(kp.value_max)}K · P: {formatValue(kp.pressure_gpa)}GPa
                          {kp.superconductor_type ? ` · ${typeLabel(kp.superconductor_type)}` : ''}
                        </Typography>
                      </Box>
                      <Add fontSize="small" color="action" />
                    </Paper>
                  ))}
                </Box>
              )}
            </Paper>

            {/* ── Add custom point ── */}
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                添加自定义点
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <TextField
                  label="材料名"
                  size="small"
                  value={customLabel}
                  onChange={e => setCustomLabel(e.target.value)}
                  sx={{ minWidth: 150, flex: 1 }}
                />
                <TextField
                  label="Tc (K)"
                  size="small"
                  type="number"
                  value={customTc}
                  onChange={e => setCustomTc(e.target.value)}
                  inputProps={{ step: 0.1 }}
                  sx={{ width: 120 }}
                />
                <TextField
                  label="压力 (GPa)"
                  size="small"
                  type="number"
                  value={customPressure}
                  onChange={e => setCustomPressure(e.target.value)}
                  inputProps={{ step: 0.1 }}
                  sx={{ width: 130 }}
                />
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>超导类型</InputLabel>
                  <Select value={customType} label="超导类型"
                    onChange={e => setCustomType(e.target.value)}>
                    <MenuItem value="">--</MenuItem>
                    {SC_TYPE_OPTIONS.map(opt => (
                      <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" sx={{ minWidth: 100 }}>
                  <InputLabel>实验/理论</InputLabel>
                  <Select value={customArticleType} label="实验/理论"
                    onChange={e => setCustomArticleType(e.target.value)}>
                    <MenuItem value="">--</MenuItem>
                    <MenuItem value="e">实验</MenuItem>
                    <MenuItem value="t">理论</MenuItem>
                  </Select>
                </FormControl>
                <TextField label="年份" size="small" type="number"
                  value={customYear} onChange={e => setCustomYear(e.target.value)}
                  inputProps={{ min: 1900, max: 2099 }}
                  sx={{ width: 100 }} />
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<Add />}
                  onClick={addCustomPoint}
                  disabled={!customLabel.trim()}
                  sx={{ height: 40 }}
                >
                  添加
                </Button>
              </Box>
            </Paper>

          {/* ── Import from group ── */}
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
              从组合导入
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button variant="outlined" size="small" startIcon={<Add />}
                onClick={() => { loadAvailableGroups(); setImportGroupOpen(!importGroupOpen); }}>
                选择组合
              </Button>
            </Box>
            {importGroupOpen && availableGroups.length > 0 && (
              <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 0.5, maxHeight: 200, overflow: 'auto' }}>
                {availableGroups.map((g: any) => (
                  <Paper key={g.id} variant="outlined" sx={{ p: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', '&:hover': { bgcolor: 'action.hover' } }}>
                    <Box>
                      <Typography variant="body2" fontWeight={600} noWrap>{g.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{g.item_count || (g.items?.length || 0)} 个数据点</Typography>
                    </Box>
                    <Button size="small" onClick={() => importFromGroup(g)}>导入</Button>
                  </Paper>
                ))}
              </Box>
            )}
            {importGroupOpen && availableGroups.length === 0 && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>没有可导入的组合</Typography>
            )}
          </Paper>
        </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 1.5 }}>
        <Button onClick={onClose} disabled={saving}>取消</Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={saving || loading}
          startIcon={saving ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          保存
        </Button>
      </DialogActions>

      {/* ── Snackbar ── */}
      <Snackbar
        open={!!snackbar}
        autoHideDuration={4000}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        {snackbar ? (
          <Alert
            severity={snackbar.severity}
            onClose={() => setSnackbar(null)}
            variant="filled"
            sx={{ width: '100%' }}
          >
            {snackbar.message}
          </Alert>
        ) : undefined}
      </Snackbar>
    </Dialog>
  )
}

export default ChartGroupEditor
