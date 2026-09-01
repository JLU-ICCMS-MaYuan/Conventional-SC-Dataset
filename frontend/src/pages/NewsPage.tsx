import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Box, Typography, Paper, Button } from '@mui/material'
import NewsFeed, { ManualNews } from '../components/NewsFeed'
import { useLanguage } from '../context/LanguageContext'


const NewsPage: React.FC = () => {
  const navigate = useNavigate()
  const { t, dict } = useLanguage()

  return (
    <Box>
      {/* Hero */}
      <Box sx={{ textAlign: 'center', pt: { xs: 4, md: 10 }, pb: { xs: 4, md: 8 } }}>
        <Typography variant="overline" sx={{ fontSize: 14, letterSpacing: '0.12em' }}>Jilin University · CALYPSO Group</Typography>
        <Typography variant="h1" sx={{ mt: 1 }}>
          {t('news.heroTitle')}
        </Typography>
        <Typography variant="body1" sx={{ mt: 2, maxWidth: 560, mx: 'auto', color: 'text.secondary', fontSize: 16, lineHeight: 1.8 }}>
          {t('news.heroSubtitle')}
        </Typography>
        <Box sx={{ mt: 4, display: 'flex', gap: 2, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Button variant="contained" size="large" onClick={() => navigate('/search')} sx={{ borderRadius: 999, px: 4, py: 1.5 }}>
            {t('news.startExploring')}
          </Button>
          <Button variant="outlined" size="large" onClick={() => navigate('/rag')} sx={{ borderRadius: 999, px: 4, py: 1.5 }}>
            {t('news.aiAssistant')}
          </Button>
        </Box>
      </Box>

      {/* Feature cards */}
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' }, gap: 3, mb: 6 }}>
        {[
          { icon: '🔍', title: t('news.featureElementSearch'), desc: t('news.featureElementSearchDesc'), path: '/search' },
          { icon: '💬', title: t('news.featureAiQa'), desc: t('news.featureAiQaDesc'), path: '/rag' },
          { icon: '⚛️', title: t('news.featureTcPredict'), desc: t('news.featureTcPredictDesc'), path: '/tc-predict' },
        ].map(({ icon, title, desc, path }) => (
          <Paper key={title} sx={{ p: 3, borderRadius: 4, cursor: 'pointer', transition: 'transform .16s, box-shadow .16s', '&:hover': { transform: 'translateY(-2px)', boxShadow: 3 } }} onClick={() => navigate(path)}>
            <Typography sx={{ fontSize: 32, mb: 1 }}>{icon}</Typography>
            <Typography variant="h2" gutterBottom>{title}</Typography>
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>{desc}</Typography>
          </Paper>
        ))}
      </Box>

      {/* News Section */}
      <NewsFeed />
      <ManualNews />

      {/* Nobel Milestones */}
      <Typography variant="overline" sx={{ mb: 2, display: 'block' }}>{t('news.nobelMilestones')}</Typography>
      <Paper sx={{ p: 3, borderRadius: 4, mb: 6 }}>
        <Box sx={{ display: 'grid', gap: 2 }}>
          {dict.news.nobelMilestoneItems.map((item) => (
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

    </Box>
  )
}

export default NewsPage
