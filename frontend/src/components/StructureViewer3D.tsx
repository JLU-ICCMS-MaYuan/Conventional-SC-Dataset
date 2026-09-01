import React, { useEffect, useRef, useState } from 'react'
import { Box, Typography } from '@mui/material'
import { useLanguage } from '../context/LanguageContext'

/* ── 3D 晶体结构查看器（3Dmol.js，动态加载避免主包膨胀）── */

interface Props {
  data: string          // 结构文本（CIF / POSCAR …）
  format?: string       // 3Dmol 格式名：cif、vasp 等，默认 cif
  height?: number
}

interface LegendItem { el: string; color: string }

const StructureViewer3D: React.FC<Props> = ({ data, format = 'cif', height = 320 }) => {
  const { t } = useLanguage()
  const ref = useRef<HTMLDivElement>(null)
  const [error, setError] = useState('')
  const [legend, setLegend] = useState<LegendItem[]>([])

  useEffect(() => {
    let viewer: any
    let resizeObserver: ResizeObserver | undefined
    let cancelled = false
    if (!data || !ref.current) return
    setError('')
    setLegend([])
    import('3dmol').then(($3Dmol: any) => {
      if (cancelled || !ref.current) return
      ref.current.innerHTML = ''
      // orthographic: 正交投影，无近大远小透视变形
      viewer = $3Dmol.createViewer(ref.current, { backgroundColor: '#f8fafc', orthographic: true })
      const model = viewer.addModel(data, format)
      // 球棍模型（Jmol 元素配色）+ 晶胞线框
      viewer.setStyle({}, { sphere: { scale: 0.32, colorscheme: 'Jmol' }, stick: { radius: 0.12, colorscheme: 'Jmol' } })
      viewer.addUnitCell(model, { box: { color: '#94a3b8' } })
      viewer.zoomTo()
      viewer.render()
      if (typeof ResizeObserver !== 'undefined') {
        resizeObserver = new ResizeObserver(() => {
          viewer.resize()
          viewer.render()
        })
        resizeObserver.observe(ref.current)
      }
      // 从模型提取元素集合，与 Jmol 配色对应生成图例
      const jmol = $3Dmol.elementColors?.Jmol || {}
      const els: string[] = Array.from(new Set(model.selectedAtoms({}).map((a: any) => a.elem)))
      setLegend(els.map(el => ({
        el,
        color: '#' + Number(jmol[el] ?? 0x909090).toString(16).padStart(6, '0'),
      })))
    }).catch((e: any) => {
      if (!cancelled) setError(e?.message || t('paperDetail.renderFailed'))
    })
    return () => {
      cancelled = true
      resizeObserver?.disconnect()
      if (viewer) { try { viewer.clear() } catch { /* viewer 已销毁 */ } }
    }
  }, [data, format, t])

  if (error) {
    return <Typography variant="body2" color="error">{t('paperDetail.renderFailedDetail', { error })}</Typography>
  }
  return (
    <Box sx={{ minWidth: 0 }}>
      <Box ref={ref} sx={{
        position:'relative', width:'100%', minWidth:0, height,
        borderRadius:2, overflow:'hidden', border:'1px solid', borderColor:'divider',
        // 3Dmol 内部 canvas 为绝对定位，需要相对定位容器
        '& canvas': { borderRadius: 2 },
      }} />
      {legend.length > 0 && (
        <Box sx={{ display:'flex',flexWrap:'wrap',gap:1.5,mt:1.5,alignItems:'center' }}>
          {legend.map(({ el, color }) => (
            <Box key={el} sx={{ display:'inline-flex',alignItems:'center',gap:0.6 }}>
              <Box sx={{ width:14,height:14,borderRadius:'50%',bgcolor:color,border:'1px solid rgba(15,23,42,.25)' }} />
              <Typography variant="body2" fontWeight={700}>{el}</Typography>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  )
}

export default StructureViewer3D
