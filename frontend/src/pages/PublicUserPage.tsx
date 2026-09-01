import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Alert, Avatar, Box, Card, CardContent, Chip, CircularProgress, Stack, Typography } from '@mui/material'
import { Business, Fingerprint, Science } from '@mui/icons-material'
import { api } from '../lib/api'
import { useLanguage } from '../context/LanguageContext'

interface PublicProfile {
  username: string
  avatar_url?: string | null
  real_name?: string
  affiliation?: string | null
  orcid?: string | null
  research_interests?: string[]
  role_badge?: string
  is_banned?: boolean
}

const PublicUserPage: React.FC = () => {
  const { username = '' } = useParams()
  const { t } = useLanguage()
  const [profile, setProfile] = useState<PublicProfile | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const previousTitle = document.title
    let meta = document.querySelector<HTMLMetaElement>('meta[name="robots"]')
    const created = !meta
    if (!meta) { meta = document.createElement('meta'); meta.name = 'robots'; document.head.appendChild(meta) }
    const previous = meta.content
    meta.content = 'noindex,follow'
    document.title = `${username} · SC-Wiki`
    void api.get<PublicProfile>(`/api/users/${encodeURIComponent(username)}`).then(setProfile).catch(cause => setError(cause.message))
    return () => { document.title = previousTitle; if (created) meta?.remove(); else if (meta) meta.content = previous }
  }, [username])

  if (error) return <Alert severity="error" sx={{ maxWidth: 720, mx: 'auto', mt: 6 }}>{error}</Alert>
  if (!profile) return <Box sx={{ minHeight: '55vh', display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>

  return (
    <Box sx={{ maxWidth: 820, mx: 'auto', pt: 3 }}>
      {profile.is_banned && <Alert severity="warning" sx={{ mb: 2 }}>{t('account.bannedNotice')}</Alert>}
      <Card variant="outlined" sx={{ borderRadius: 4 }}>
        <CardContent sx={{ p: { xs: 3, md: 5 } }}>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={3} alignItems={{ sm: 'center' }}>
            <Avatar src={profile.avatar_url || undefined} sx={{ width: 112, height: 112, bgcolor: 'primary.main', fontSize: 40 }}>{profile.username[0].toUpperCase()}</Avatar>
            <Box>
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                <Typography variant="h3" fontWeight={800}>{profile.real_name || profile.username}</Typography>
                {profile.role_badge && <Chip color={profile.role_badge === '超级管理员' ? 'error' : 'primary'} label={profile.role_badge} />}
              </Stack>
              <Typography color="text.secondary" sx={{ mt: 0.5 }}>@{profile.username}</Typography>
            </Box>
          </Stack>
          <Stack spacing={2.5} sx={{ mt: 4 }}>
            {profile.affiliation && <Stack direction="row" spacing={1.5} alignItems="center"><Business color="action" /><Box><Typography variant="caption" color="text.secondary">{t('account.affiliation')}</Typography><Typography>{profile.affiliation}</Typography></Box></Stack>}
            {profile.orcid && <Stack direction="row" spacing={1.5} alignItems="center"><Fingerprint color="action" /><Box><Typography variant="caption" color="text.secondary">ORCID</Typography><Typography>{profile.orcid}</Typography></Box></Stack>}
            {profile.research_interests && profile.research_interests.length > 0 && <Stack direction="row" spacing={1.5} alignItems="start"><Science color="action" sx={{ mt: 0.5 }} /><Box><Typography variant="caption" color="text.secondary">{t('account.researchInterests')}</Typography><Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: 0.5 }}>{profile.research_interests.map(item => <Chip key={item} size="small" label={item} />)}</Stack></Box></Stack>}
            {!profile.affiliation && !profile.orcid && !profile.research_interests?.length && <Typography color="text.secondary">{t('account.emptyPublicProfile')}</Typography>}
          </Stack>
        </CardContent>
      </Card>
    </Box>
  )
}

export default PublicUserPage
