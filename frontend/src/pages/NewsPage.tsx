import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Typography, Paper, Button, Chip, Tabs, Tab, Drawer } from '@mui/material'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { api } from '../lib/api'

const NEWS = [
  { date: '2024', title: 'LaBeH8 在 100 GPa 下 Tc 突破 170 K', summary: '吉林大学研究团队发现新型镧铍氢化物在高压下展现优异超导性能，为室温超导研究提供新方向。' },
  { date: '2023', title: 'LK-99 引发全球室温超导热潮', summary: '韩国团队声称合成常压室温超导体 LK-99，虽后续实验未能复现，但极大推动了公众对超导领域的关注。' },
  { date: '2019', title: 'LaH10 在 170 GPa 达到 250 K', summary: '德国马普所发现十氢化镧在高压下 Tc 接近室温，创造氢化物超导新纪录。' },
  { date: '2015', title: 'H3S 在 155 GPa 达到 203 K', summary: 'Drozdov 等人首次在硫化氢体系中突破 200 K，开创高压氢化物超导新纪元。' },
]

const NOBEL_MILESTONES = [
  { year: 1913, name: 'Heike Kamerlingh Onnes', feat: '液化氦气，发现汞在 4.2 K 的超导现象' },
  { year: 1972, name: 'Bardeen, Cooper, Schrieffer', feat: '提出 BCS 理论，解释常规超导微观机制' },
  { year: 1973, name: 'Esaki, Giaever, Josephson', feat: '发现隧穿效应，奠定超导电子学基础' },
  { year: 1987, name: 'Bednorz, M&uuml;ller', feat: '发现铜氧化物高温超导体，Tc 突破液氮温区' },
  { year: 2003, name: 'Abrikosov, Ginzburg, Leggett', feat: '超导涡旋态理论和超流理论' },
]

const NewsPage: React.FC = () => {
  const navigate = useNavigate()
  const [stats, setStats] = useState(0)
  const [tab, setTab] = useState(0)
  const [chartData, setChartData] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)

  useEffect(() => {
    api.get<any[]>('/api/papers/stats/chart-data').then((d) => setStats(d?.length || 0)).catch(() => {})
    api.get<any[]>('/api/papers/stats/tc-pressure').then(setChartData).catch(() => {})
  }, [])

  return (
    <Box>
      {/* Hero */}
      <Box sx={{ textAlign: 'center', pt: { xs: 4, md: 10 }, pb: { xs: 4, md: 8 } }}>
        <Typography variant="overline" sx={{ fontSize: 14, letterSpacing: '0.12em' }}>Jilin University · CALYPSO Group</Typography>
        <Typography variant="h1" sx={{ mt: 1 }}>
          超导文献数据库
        </Typography>
        <Typography variant="body1" sx={{ mt: 2, maxWidth: 560, mx: 'auto', color: 'text.secondary', fontSize: 16, lineHeight: 1.8 }}>
          围绕元素周期表构建的超导材料检索平台。覆盖常规超导体、铜基、铁基、高压氢化物等体系，支持文献检索、AI 问答和 Tc 预测。
        </Typography>
        <Box sx={{ mt: 4, display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Button variant="contained" size="large" onClick={() => navigate('/search')} sx={{ borderRadius: 999, px: 4, py: 1.5 }}>
            开始探索
          </Button>
          <Button variant="outlined" size="large" onClick={() => navigate('/rag')} sx={{ borderRadius: 999, px: 4, py: 1.5 }}>
            AI 文献助手
          </Button>
        </Box>
      </Box>

      {/* Feature cards */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' }, gap: 3, mb: 6 }}>
        {[
          { icon: '🔍', title: '元素检索', desc: '从周期表选元素，搜索相关超导记录，按 Tc、压强、空间群筛选。', path: '/search' },
          { icon: '💬', title: 'AI 问答', desc: '自然语言提问，AI 流式回答并标注引用来源。', path: '/rag' },
          { icon: '⚛️', title: 'Tc 预测', desc: '上传结构文件和态密度，估算超导临界温度。', path: '/tc-predict' },
        ].map(({ icon, title, desc, path }) => (
          <Paper key={title} sx={{ p: 3, borderRadius: 4, cursor: 'pointer', transition: 'transform .16s, box-shadow .16s', '&:hover': { transform: 'translateY(-2px)', boxShadow: 3 } }} onClick={() => navigate(path)}>
            <Typography sx={{ fontSize: 32, mb: 1 }}>{icon}</Typography>
            <Typography variant="h2" gutterBottom>{title}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>{desc}</Typography>
          </Paper>
        ))}
      </Box>

      {/* News Section */}
      <Typography variant="overline" sx={{ mb: 2, display: 'block' }}>超导快讯</Typography>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(2, minmax(0, 1fr))' }, gap: 3, mb: 6 }}>
        {NEWS.map((item) => (
          <Paper key={item.title} sx={{ p: 2.5, borderRadius: 4, borderLeft: '4px solid', borderColor: 'primary.main' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Chip label={item.date} size="small" color="primary" />
            </Box>
            <Typography variant="h3" gutterBottom>{item.title}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary', lineHeight: 1.7 }}>{item.summary}</Typography>
          </Paper>
        ))}
      </Box>

      {/* Nobel Milestones */}
      <Typography variant="overline" sx={{ mb: 2, display: 'block' }}>诺贝尔奖里程碑</Typography>
      <Paper sx={{ p: 3, borderRadius: 4, mb: 6 }}>
        <Box sx={{ display: 'grid', gap: 2 }}>
          {NOBEL_MILESTONES.map((item) => (
            <Box key={item.year} sx={{ display: 'flex', gap: 2, alignItems: 'baseline', pb: 2, borderBottom: '1px solid', borderColor: 'divider', '&:last-child': { borderBottom: 0, pb: 0 } }}>
              <Typography variant="h3" sx={{ color: 'primary.main', minWidth: 52 }}>{item.year}</Typography>
              <Box>
                <Typography fontWeight={700}>{item.name}</Typography>
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>{item.feat}</Typography>
              </Box>
            </Box>
          ))}
        </Box>
      </Paper>

      <Drawer anchor="right" open={!!selected} onClose={() => setSelected(null)} PaperProps={{ sx: { width: 360, p: 3 } }}>
        {selected && (
          <Box>
            <Typography variant="h3" gutterBottom>{selected.label || selected.formula}</Typography>
            <Typography variant="body2">Tc: {selected.y} K</Typography>
            <Typography variant="body2">压强: {selected.x} GPa</Typography>
            <Typography variant="body2">类型: {selected.type === 'experimental' ? '实验' : '理论'}</Typography>
            {selected.space_group && <Typography variant="body2">空间群: {selected.space_group}</Typography>}
            {selected.doi && <Typography variant="body2">DOI: {selected.doi}</Typography>}
          </Box>
        )}
      </Drawer>
    </Box>
  )
}

export default NewsPage
