import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Typography, Paper, Button, Chip, Tabs, Tab, Drawer } from '@mui/material'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { api } from '../lib/api'


const NOBEL_MILESTONES = [
  {
    year: 1913,
    name: 'Heike Kamerlingh Onnes',
    title: '液氦制备与超导电性的发现',
    feat: '1908年首次液化氦气（沸点4.2K），1911年发现汞在4.2K时电阻突然降至零——人类第一次观测到超导现象。这不仅证明了极低温下物质的新物态，更开启了长达百年的超导研究序幕。Onnes 当时在笔记中写下「Mercury practically zero」，这一时刻被铭刻在物理学的历史上。',
  },
  {
    year: 1972,
    name: 'John Bardeen, Leon Cooper, John Schrieffer',
    title: 'BCS 超导微观理论',
    feat: '1957年三人提出以姓氏命名的 BCS 理论，首次从量子力学微观机制完整解释了超导电性：电子通过晶格振动（声子）交换形成库珀对（Cooper Pair），在无电阻的宏观量子态中运动。Bardeen 因此成为历史上唯一两次获得诺贝尔物理学奖的人（第一次是1956年发明晶体管）。BCS 理论至今仍是凝聚态物理最重要的理论基石之一。',
  },
  {
    year: 1973,
    name: '江崎玲於奈, Ivar Giaever, Brian Josephson',
    title: '半导体与超导体中的隧穿效应',
    feat: '江崎玲於奈于1957年发现半导体中的电子隧穿效应（Esaki Diode），Giaever 于1960年实验验证了超导体中的单电子隧穿，而当时年仅22岁的研究生 Josephson 则从理论上预言了超导隧道结中库珀对的隧穿效应——即著名的约瑟夫森效应（Josephson Effect）。这一预言后来被精确验证（误差<10⁻¹²），成为超导电子学、SQUID 磁强计和电压标准的物理基础。',
  },
  {
    year: 1987,
    name: 'Georg Bednorz, Alex Müller',
    title: '铜氧化物高温超导体的突破',
    feat: '1986年，IBM 苏黎世实验室的 Bednorz 和 Müller 在镧钡铜氧（LaBaCuO）陶瓷材料中发现35K的超导电性，打破了此前 Nb₃Ge 保持13年的23K记录。更重要的是，这种氧化物陶瓷是传统 BCS 理论无法解释的新型超导体。这一发现引发了全球「超导淘金热」，随后朱经武、赵忠贤等人迅速将 Tc 推至液氮温区（77K）以上，使超导应用成本骤降，彻底改变了超导技术的产业化前景。',
  },
  {
    year: 2003,
    name: 'Alexei Abrikosov, Vitaly Ginzburg, Anthony Leggett',
    title: '第二类超导体与超流理论',
    feat: 'Ginzburg 和 Landau 于1950年提出超导相变的唯象理论（GL 理论），成功描述了超导态的宏观波函数行为。Abrikosov 在1957年基于 GL 理论预言了第二类超导体中的磁通涡旋晶格——即著名的 Abrikosov 涡旋，直接解释了实用超导磁体（如 MRI、粒子加速器磁铁）在高场下的工作机制。Leggett 则因超流³He 的理论工作分享了该奖项。这三位科学家的贡献共同奠定了现代超导应用的理论基础。',
  },
]

const NewsPage: React.FC = () => {
  const navigate = useNavigate()
  const [stats, setStats] = useState(0)
  const [tab, setTab] = useState(0)
  const [chartData, setChartData] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [news, setNews] = useState<any[]>([])

  useEffect(() => {
    api.get<any[]>('/api/papers/stats/chart-data').then((d) => setStats(d?.length || 0)).catch(() => {})
    api.get<any[]>('/api/papers/stats/tc-pressure').then(setChartData).catch(() => {})
    api.get<any[]>('/api/news').then(setNews).catch(() => {})
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
        {news.map((item) => (
          <Paper key={item.id}
            onClick={() => item.link && window.open(item.link, '_blank')}
            sx={{ p: 2.5, borderRadius: 4, borderLeft: '4px solid', borderColor: 'primary.main',
              cursor: item.link ? 'pointer' : 'default',
              transition: 'box-shadow 0.15s',
              '&:hover': item.link ? { boxShadow: '0 4px 16px rgba(79,70,229,.14)' } : {},
            }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
              <Chip label={item.event_date} size="small" color="primary" />
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
            <Box key={item.year} sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', pb: 3, borderBottom: '1px solid', borderColor: 'divider', '&:last-child': { borderBottom: 0, pb: 0 } }}>
              <Typography variant="h3" sx={{ color: 'primary.main', minWidth: 56, fontWeight: 800 }}>{item.year}</Typography>
              <Box sx={{ flex: 1 }}>
                <Typography fontWeight={700} fontSize={16}>{item.name}</Typography>
                <Typography variant="subtitle2" color="primary.main" sx={{ mb: 0.5 }}>{item.title}</Typography>
                <Typography variant="body2" sx={{ color: 'text.secondary', lineHeight: 1.8 }}>{item.feat}</Typography>
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
