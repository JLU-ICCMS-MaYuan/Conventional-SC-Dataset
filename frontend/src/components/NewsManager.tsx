import React, { useState, useEffect, useCallback } from 'react'
import {
  Box, Typography, Button, TextField, IconButton, Tooltip, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Dialog, DialogTitle, DialogContent, DialogActions,
  Snackbar, Alert,
} from '@mui/material'
import { Edit as EditIcon, Delete as DeleteIcon, Add as AddIcon } from '@mui/icons-material'
import { api } from '../lib/api'

interface NewsItem {
  id: number
  event_date: string
  title: string
  summary: string
  link: string
}

const emptyItem = { event_date: '', title: '', summary: '', link: '' }

const NewsManager: React.FC = () => {
  const [items, setItems] = useState<NewsItem[]>([])
  const [dialog, setDialog] = useState(false)
  const [editing, setEditing] = useState<NewsItem | null>(null)
  const [form, setForm] = useState(emptyItem)
  const [snackbar, setSnackbar] = useState('')

  const load = useCallback(() => {
    api.get<NewsItem[]>('/api/news').then(setItems).catch(() => {})
  }, [])

  useEffect(() => { load() }, [load])

  const openCreate = () => { setEditing(null); setForm(emptyItem); setDialog(true) }
  const openEdit = (item: NewsItem) => { setEditing(item); setForm(item); setDialog(true) }

  const save = async () => {
    try {
      if (editing?.id) {
        await api.put(`/api/admin/news/${editing.id}`, form)
      } else {
        await api.post('/api/admin/news', form)
      }
      setSnackbar('已保存'); setDialog(false); load()
    } catch (e: any) { setSnackbar(`失败: ${e.message}`) }
  }

  const remove = async (id: number) => {
    if (!window.confirm('确认删除？')) return
    try {
      await api.del(`/api/admin/news/${id}`)
      setSnackbar('已删除'); load()
    } catch (e: any) { setSnackbar(`失败: ${e.message}`) }
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'center' }}>
        <Typography variant="h6" fontWeight={600} sx={{ flex: 1 }}>快讯管理</Typography>
        <Button variant="contained" size="small" startIcon={<AddIcon />} onClick={openCreate}>添加快讯</Button>
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell sx={{ width: 80 }}>日期</TableCell>
              <TableCell>标题</TableCell>
              <TableCell sx={{ width: 100 }}>链接</TableCell>
              <TableCell sx={{ width: 100 }} align="right">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((item) => (
              <TableRow key={item.id} hover>
                <TableCell><Chip label={item.event_date} size="small" /></TableCell>
                <TableCell>
                  <Typography variant="body2" fontWeight={600}>{item.title}</Typography>
                  <Typography variant="caption" color="text.secondary">{item.summary?.slice(0, 60)}...</Typography>
                </TableCell>
                <TableCell>
                  {item.link ? <Chip label="有" size="small" variant="outlined" /> : <Typography variant="caption" color="text.disabled">-</Typography>}
                </TableCell>
                <TableCell align="right">
                  <Tooltip title="编辑"><IconButton size="small" onClick={() => openEdit(item)}><EditIcon fontSize="small" /></IconButton></Tooltip>
                  <Tooltip title="删除"><IconButton size="small" color="error" onClick={() => remove(item.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialog} onClose={() => setDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing?.id ? '编辑快讯' : '添加快讯'}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 1 }}>
          <TextField label="日期" size="small" value={form.event_date} onChange={e => setForm({ ...form, event_date: e.target.value })} placeholder="2024" />
          <TextField label="标题" size="small" fullWidth value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
          <TextField label="简介" size="small" fullWidth multiline rows={3} value={form.summary} onChange={e => setForm({ ...form, summary: e.target.value })} />
          <TextField label="超链接" size="small" fullWidth value={form.link} onChange={e => setForm({ ...form, link: e.target.value })} placeholder="https://..." />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialog(false)}>取消</Button>
          <Button variant="contained" onClick={save}>保存</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={!!snackbar} autoHideDuration={3000} onClose={() => setSnackbar('')} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity="info" variant="filled" onClose={() => setSnackbar('')}>{snackbar}</Alert>
      </Snackbar>
    </Box>
  )
}

export default NewsManager
