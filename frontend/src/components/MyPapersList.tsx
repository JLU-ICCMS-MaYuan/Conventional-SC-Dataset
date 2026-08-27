import React, { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Button, Chip, CircularProgress, Stack, Typography,
} from '@mui/material'
import { api } from '../lib/api'

interface MyPaper {
  id: number
  title: string | null
  doi: string | null
  journal: string | null
  year: number | null
  review_status: string | null
  created_at: string | null
}

const STATUS_LABELS: Record<string, string> = {
  pending: '待审核', approved: '审核完成', rejected: '已拒绝', needs_revision: '待审核（旧状态）',
}
const STATUS_COLORS: Record<string, 'warning' | 'success' | 'error' | 'info'> = {
  pending: 'warning', approved: 'success', rejected: 'error', needs_revision: 'info',
}

// 已提交论文永久保存在 MySQL，与上传页那份 24 小时后清理、受活动任务配额限制的
// 「上传解析记录」性质不同，因此单独放在用户中心，不混入上传工作区。
const MyPapersList: React.FC = () => {
  const navigate = useNavigate()
  const [items, setItems] = useState<MyPaper[] | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.get<{ items?: MyPaper[] }>('/api/papers/my-uploads')
      setItems(Array.isArray(data?.items) ? data.items : [])
    } catch (e: any) {
      setError(e?.message || '加载我的论文失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
        <CircularProgress size={28} />
      </Box>
    )
  }

  if (error) {
    return (
      <Box sx={{ py: 2 }}>
        <Typography color="error" variant="body2" gutterBottom>{error}</Typography>
        <Button size="small" onClick={() => void load()}>重试</Button>
      </Box>
    )
  }

  if (!items || items.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
        还没有提交过论文。上传并提交审核后，论文会出现在这里，可随时只读复查。
      </Typography>
    )
  }

  return (
    <Stack spacing={1} sx={{ mt: 1 }}>
      {items.map(paper => (
        <Box
          key={paper.id}
          role="button"
          tabIndex={0}
          onClick={() => navigate(`/papers/${paper.id}`)}
          onKeyDown={event => {
            if (event.key === 'Enter' || event.key === ' ') {
              event.preventDefault()
              navigate(`/papers/${paper.id}`)
            }
          }}
          sx={{
            p: 1.5, borderRadius: 2, border: '1px solid', borderColor: 'divider',
            cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' },
          }}
        >
          <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="body2" fontWeight={700} noWrap>
                {paper.title || `论文 #${paper.id}`}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {[paper.journal, paper.year, paper.doi].filter(Boolean).join(' · ') || '—'}
              </Typography>
            </Box>
            <Chip
              size="small"
              label={STATUS_LABELS[paper.review_status || ''] || paper.review_status || '待审核'}
              color={STATUS_COLORS[paper.review_status || ''] || 'default'}
            />
          </Stack>
        </Box>
      ))}
    </Stack>
  )
}

export default MyPapersList
