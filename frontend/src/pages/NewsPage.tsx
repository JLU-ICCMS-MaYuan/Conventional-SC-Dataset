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
      <Box sx={{ textAlign: 'center', pt: { xs: 4, md: 6 }, pb: { xs: 3, md: 4 } }}>
        <Typography variant="overline" sx={{ display: 'block', maxWidth: 900, mx: 'auto', fontSize: 13, lineHeight: 1.6 }}>
          {t('news.heroAffiliation')}
        </Typography>
        <Typography variant="h1" sx={{ mt: 1 }}>
          {t('news.heroTitle')}
        </Typography>
        <Typography variant="body1" sx={{ mt: 2, maxWidth: 560, mx: 'auto', color: 'text.secondary', fontSize: 16, lineHeight: 1.8 }}>
          {t('news.heroSubtitle')}
        </Typography>
        <Box sx={{ mt: 3 }}>
          <Button variant="contained" size="large" onClick={() => navigate('/search')} sx={{ borderRadius: 2, px: 4, py: 1.25 }}>
            {t('news.startExploring')}
          </Button>
        </Box>
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
