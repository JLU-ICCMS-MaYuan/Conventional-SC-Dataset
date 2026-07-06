import React from 'react'
import { Box, Typography } from '@mui/material'

const HomePage: React.FC = () => (
  <Box>
    <Typography variant="h1">SC-Wiki</Typography>
    <Typography variant="body1" sx={{ mt: 2, color: 'text.secondary' }}>超导文献数据库</Typography>
  </Box>
)

export default HomePage
