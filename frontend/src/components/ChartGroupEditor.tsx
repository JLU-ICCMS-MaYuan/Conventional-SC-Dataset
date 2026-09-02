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
import { useLanguage } from '../context/LanguageContext'
import { ClassificationTerm, familyName, loadClassificationCatalogs } from '../lib/classifications'

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

const emptyGroup: LocalGroup = { name: '', description: '', is_public: false, items: [] }

// ── Component ──

const ChartGroupEditor: React.FC<Props> = ({ open, groupId, onClose, onSaved }) => {
  const { user } = useAuth()
  const { t, lang } = useLanguage()
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

  // ── 材料家族目录：分类选项随目录变化，含用户自建家族 ──
  const [families, setFamilies] = useState<ClassificationTerm[]>([])
  // 家族显示名按语言取：目录项双语（自建家族英文缺失时回退中文名）
  const familyNames = new Map(families.map(family => [family.id, familyName(family, lang)]))

  useEffect(() => {
    if (!open) return
    loadClassificationCatalogs()
      .then(catalogs => setFamilies(catalogs.material_families ?? []))
      .catch(() => setFamilies([]))
  }, [open])

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
      .catch(() => setSnackbar({ message: t('common.loadFailed'), severity: 'error' }))
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
      setSnackbar({ message: e.message || t('share.searchFailed'), severity: 'error' })
    } finally {
      setKpLoading(false)
    }
  }

  // ── Add KP result to group ──
  const addKpToGroup = (kp: any) => {
    // Prevent duplicate
    if (group.items.some(it => it.source === 'kp' && it.key_property_id === kp.id)) {
      setSnackbar({ message: t('share.duplicatePoint'), severity: 'error' })
      return
    }
    // 压强属于材料状态；Material family 已提升为论文级多选标签。
    const firstPaperFamily = kp.paper?.material_families?.[0]
    const newItem: LocalItem = {
      sort_order: group.items.length,
      source: 'kp',
      key_property_id: kp.id,
      material: kp.material,
      tc: kp.value_max ?? kp.value_number ?? null,
      pressure: kp.material_state?.pressure_value_gpa ?? null,
      type: firstPaperFamily?.id != null
        ? String(firstPaperFamily.id)
        : null,
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
      setSnackbar({ message: t('share.groupNameRequired'), severity: 'error' })
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
      setSnackbar({ message: e.message || t('common.saveFailed'), severity: 'error' })
    } finally {
      setSaving(false)
    }
  }

  // ── Render helpers ──

  const formatValue = (v: number | null): string => {
    if (v == null) return '-'
    return Number.isInteger(v) ? String(v) : v.toFixed(2)
  }

  // 组合点的分类值存材料家族 id（字符串形式，沿用 custom_type 列）。
  // 目录是动态的，标签必须查目录，不能硬编码。
  const typeLabel = (value: string | null): string => {
    if (!value) return '-'
    return familyNames.get(Number(value)) ?? value
  }

  // ═══════════════════════════════════════════════════════
  // Render
  // ═══════════════════════════════════════════════════════
  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle sx={{ fontWeight: 600, fontSize: '1.15rem' }}>
        {group.id ? t('share.editGroup') : t('share.newGroup')}
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
                label={t('share.groupName')}
                size="small"
                required
                value={group.name}
                onChange={e => setGroup(prev => ({ ...prev, name: e.target.value }))}
                sx={{ minWidth: 240, flex: 1 }}
              />
              <TextField
                label={t('share.groupDescription')}
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
                label={<Typography variant="body2" color="text.secondary">{t('share.publicVisible')}</Typography>}
              />
            )}

            {/* ── Data point table ── */}
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                {t('share.dataPointsHeading', { count: group.items.length })}
              </Typography>
              {group.items.length === 0 ? (
                <Typography variant="body2" color="text.disabled" sx={{ py: 1 }}>
                  {t('share.noDataPoints')}
                </Typography>
              ) : (
                <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 280 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ fontWeight: 600 }}>{t('share.colMaterial')}</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>Tc (K)</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>{t('share.pressureGpa')}</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>{t('share.materialFamily')}</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>{t('share.colSource')}</TableCell>
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
                              {it.source === 'kp' ? t('share.sourceDatabase') : t('share.sourceCustom')}
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
                {t('share.addFromDatabase')}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  size="small"
                  placeholder={t('share.searchMaterialPlaceholder')}
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
                  {t('common.search')}
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
                          Tc: {formatValue(kp.value_max ?? kp.value_number)}K · P: {formatValue(kp.material_state?.pressure_value_gpa)}GPa
                          {kp.paper?.material_families?.length
                            ? ` · ${kp.paper.material_families.map((item: any) => familyName(item, lang)).join(' / ')}`
                            : ''}
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
                {t('share.addCustomPointTitle')}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <TextField
                  label={t('share.materialNameLabel')}
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
                  label={t('share.pressureGpa')}
                  size="small"
                  type="number"
                  value={customPressure}
                  onChange={e => setCustomPressure(e.target.value)}
                  inputProps={{ step: 0.1 }}
                  sx={{ width: 130 }}
                />
                <FormControl size="small" sx={{ minWidth: 160 }}>
                  <InputLabel>{t('share.materialFamily')}</InputLabel>
                  <Select value={customType} label={t('share.materialFamily')}
                    onChange={e => setCustomType(e.target.value)}>
                    <MenuItem value="">--</MenuItem>
                    {families.map(family => (
                      <MenuItem key={family.id} value={String(family.id)}>{familyName(family, lang)}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <FormControl size="small" sx={{ minWidth: 100 }}>
                  <InputLabel>{t('share.experimentalTheoretical')}</InputLabel>
                  <Select value={customArticleType} label={t('share.experimentalTheoretical')}
                    onChange={e => setCustomArticleType(e.target.value)}>
                    <MenuItem value="">--</MenuItem>
                    <MenuItem value="e">{t('share.typeExperimental')}</MenuItem>
                    <MenuItem value="t">{t('share.typeTheoretical')}</MenuItem>
                  </Select>
                </FormControl>
                <TextField label={t('share.year')} size="small" type="number"
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
                  {t('common.add')}
                </Button>
              </Box>
            </Paper>

          {/* ── Import from group ── */}
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
              {t('share.importFromGroupTitle')}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button variant="outlined" size="small" startIcon={<Add />}
                onClick={() => { loadAvailableGroups(); setImportGroupOpen(!importGroupOpen); }}>
                {t('share.selectGroup')}
              </Button>
            </Box>
            {importGroupOpen && availableGroups.length > 0 && (
              <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 0.5, maxHeight: 200, overflow: 'auto' }}>
                {availableGroups.map((g: any) => (
                  <Paper key={g.id} variant="outlined" sx={{ p: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', '&:hover': { bgcolor: 'action.hover' } }}>
                    <Box>
                      <Typography variant="body2" fontWeight={600} noWrap>{g.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{t('share.dataPointsCount', { count: g.item_count || (g.items?.length || 0) })}</Typography>
                    </Box>
                    <Button size="small" onClick={() => importFromGroup(g)}>{t('share.importAction')}</Button>
                  </Paper>
                ))}
              </Box>
            )}
            {importGroupOpen && availableGroups.length === 0 && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>{t('share.noImportableGroups')}</Typography>
            )}
          </Paper>
        </Box>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 1.5 }}>
        <Button onClick={onClose} disabled={saving}>{t('common.cancel')}</Button>
        <Button
          variant="contained"
          onClick={handleSave}
          disabled={saving || loading}
          startIcon={saving ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          {t('common.save')}
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
