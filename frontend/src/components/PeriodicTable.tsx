import React from 'react'
import { Box, Typography } from '@mui/material'
import { ELEMENTS, CATEGORY_COLORS, ElementData } from '../lib/periodicElements'

interface PeriodicTableProps {
  selected: Set<string>
  onToggle: (symbol: string) => void
  disabledElements?: Set<string>
}

const PeriodicTable: React.FC<PeriodicTableProps> = ({ selected, onToggle, disabledElements }) => {
  const grid = new Map<string, ElementData>()
  ELEMENTS.forEach((el) => { grid.set(`${el.row}-${el.col}`, el) })

  const rows = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
  const cols = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]

  // 主表中镧系/锕系的占位块（实体元素在第 9/10 行副表）
  const PLACEHOLDERS: Record<string, { range: string; label: string; category: 'lanthanide' | 'actinide' }> = {
    '6-3': { range: '57-71', label: 'La-Lu', category: 'lanthanide' },
    '7-3': { range: '89-103', label: 'Ac-Lr', category: 'actinide' },
  }

  return (
    <Box sx={{
      display: 'grid', gridTemplateColumns: 'repeat(18, 60px)', gap: '3px', justifyContent: 'center',
      '@media (max-width:1160px)': { gridTemplateColumns: 'repeat(18, 50px)' },
      '@media (max-width:768px)': { gridTemplateColumns: 'repeat(18, 40px)' },
    }}>
      {rows.map((row) =>
        cols.map((col) => {
          const el = grid.get(`${row}-${col}`)
          if (!el) {
            const ph = PLACEHOLDERS[`${row}-${col}`]
            if (ph) {
              return (
                <Box key={`${row}-${col}`} sx={{
                  width:60, height:60, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center',
                  border:'1px dashed #999', borderRadius:'4px', bgcolor:CATEGORY_COLORS[ph.category], opacity:0.75, userSelect:'none',
                  '@media (max-width:1160px)':{ width:50, height:50 }, '@media (max-width:768px)':{ width:40, height:40 },
                }}>
                  <Typography sx={{ fontSize:8, color:'#666', lineHeight:1 }}>{ph.range}</Typography>
                  <Typography sx={{ fontSize:12, fontWeight:'bold', lineHeight:1.3, '@media (max-width:768px)':{ fontSize:10 } }}>
                    {ph.label}
                  </Typography>
                </Box>
              )
            }
            return <Box key={`${row}-${col}`} sx={{ width: 60, height: 60, '@media (max-width:1160px)':{ width:50,height:50 }, '@media (max-width:768px)':{ width:40,height:40 } }} />
          }

          const isSelected = selected.has(el.symbol)
          const isDisabled = disabledElements?.has(el.symbol) || false
          const bgColor = CATEGORY_COLORS[el.category]

          return (
            <Box key={el.symbol} onClick={() => !isDisabled && onToggle(el.symbol)} sx={{
              width:60, height:60, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center',
              border: isSelected ? '2px solid #7b7b7b' : '1px solid #ccc', borderRadius:'4px', bgcolor:bgColor,
              cursor: isDisabled ? 'not-allowed' : 'pointer', opacity: isDisabled ? 0.6 : 1, userSelect:'none',
              transition: 'all 0.2s ease', position:'relative',
              boxShadow: isSelected ? 'inset 0 0 0 100px rgba(255,255,255,0.3)' : 'none',
              '&:hover': !isDisabled ? { boxShadow:'0 4px 8px rgba(0,0,0,0.2)', transform:'scale(1.05)', zIndex:10 } : {},
              '@media (max-width:1160px)':{ width:50, height:50 }, '@media (max-width:768px)':{ width:40, height:40 },
            }}>
              <Typography sx={{ fontSize:8, color:'#666', lineHeight:1 }}>{el.number}</Typography>
              <Typography sx={{ fontSize:20, fontWeight:'bold', lineHeight:1.2, '@media (max-width:1160px)':{ fontSize:16 }, '@media (max-width:768px)':{ fontSize:14 } }}>
                {el.symbol}
              </Typography>
              <Typography sx={{ fontSize:9, color:'#666', lineHeight:1, '@media (max-width:768px)':{ display:'none' } }}>
                {el.symbol}
              </Typography>
            </Box>
          )
        })
      )}
    </Box>
  )
}

export default PeriodicTable
