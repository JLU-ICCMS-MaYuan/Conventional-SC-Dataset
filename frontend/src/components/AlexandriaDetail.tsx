import React, { useState, useEffect } from 'react'
import { Box, Typography, Card, CardContent, Chip, Button, LinearProgress } from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import { api } from '../lib/api'
import StructureViewer3D from './StructureViewer3D'

/* ── Alexandria 专属 Layer 3：电声耦合材料详情 ── */

interface Props {
  matId: string
  formula: string
  onBack: () => void
}

const Field = ({ label, value }: { label: string; value: React.ReactNode }) => (
  <Box>
    <Typography variant="caption">{label}</Typography>
    <Typography fontWeight={600}>{value ?? '-'}</Typography>
  </Box>
)

const num = (v: any, digits = 3) => (typeof v === 'number' ? v.toFixed(digits) : '-')

const AlexandriaDetail: React.FC<Props> = ({ matId, formula, onBack }) => {
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setData(null)
    setError('')
    api.get(`/api/alexandria/material/${matId}`)
      .then((d: any) => setData(d))
      .catch((e: any) => setError(e.message || '加载失败'))
  }, [matId])

  const tc = data?.tc || {}
  const st = data?.structure || {}
  const stress = data?.stress
  const pressure = Array.isArray(stress) && stress.length >= 3
    ? `${(-(stress[0] + stress[1] + stress[2]) / 3 * 0.1).toFixed(2)} GPa` : '-'
  const mustr: number[] = tc.mustr || []
  const tcMcM: number[] = tc.TcMcMillan || []
  const tcAD: number[] = tc.TcAllenDynes || []
  // 代表 Tc 取 μ* = 0.10
  const idx10 = mustr.findIndex(m => Math.abs(m - 0.1) < 1e-6)
  const tcRep = idx10 >= 0 ? (tcAD[idx10] ?? tcMcM[idx10]) : undefined

  return (
    <Box>
      <Box sx={{ display:'flex',alignItems:'center',justifyContent:'space-between',gap:2,mb:3 }}>
        <Box>
          <Button size="small" startIcon={<ArrowBackIcon/>} onClick={onBack} sx={{ mb:1 }}>返回结果表格</Button>
          <Typography variant="overline">Layer 3 · Alexandria Material</Typography>
          <Typography variant="h1">{formula} 详情</Typography>
          <Box sx={{ display:'flex',gap:1,mt:1 }}>
            <Chip label="Alexandria" size="small" color="secondary" />
            <Chip label={matId} size="small" variant="outlined" sx={{ fontFamily:'"Roboto Mono",monospace' }} />
          </Box>
        </Box>
        <Box sx={{ display:'flex',gap:1 }}>
          <Button variant="contained" color="secondary" component="a" href={`/api/alexandria/material/${matId}/cif`} download>下载 CIF</Button>
          <Button variant="outlined" component="a" href={`/api/alexandria/material/${matId}/download`}>下载完整数据</Button>
        </Box>
      </Box>

      {error && <Typography color="error" sx={{ mb:2 }}>{error}</Typography>}
      {!data && !error && <LinearProgress sx={{ mb:2, borderRadius:999, height:4 }} />}

      <Box sx={{ display:'grid',gridTemplateColumns:'1fr 360px',gap:3,alignItems:'start','@media (max-width:1180px)':{gridTemplateColumns:'1fr'} }}>
        <Card sx={{ boxShadow: 3 }}>
          <CardContent>
            {/* 基础信息 */}
            <Box component="details" open sx={{ border:'1px solid',borderColor:'divider',borderRadius:2,mb:1.5,overflow:'hidden' }}>
              <Box component="summary" sx={{ cursor:'pointer',p:2,fontSize:18,fontWeight:800 }}>基础信息</Box>
              <Box sx={{ px:2,pb:2,borderTop:'1px solid',borderColor:'divider' }}>
                <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1.5 }}>
                  <Field label="Formula" value={data?.formula || formula} />
                  <Field label="材料 ID" value={data?.mat_id || matId} />
                  <Field label="元素" value={(data?.elements || []).join(', ') || '-'} />
                  <Field label="原胞原子数" value={data?.nsites} />
                  <Field label="空间群" value={st.spg_symbol ? `${st.spg_symbol} (#${st.spg_number})` : '-'} />
                  <Field label="动力学稳定" value={data ? (data.imag ? '否（存在虚声子）' : '是（无虚声子）') : '-'} />
                </Box>
              </Box>
            </Box>
            {/* 电声耦合参数 */}
            <Box component="details" open sx={{ border:'1px solid',borderColor:'divider',borderRadius:2,mb:1.5,overflow:'hidden' }}>
              <Box component="summary" sx={{ cursor:'pointer',p:2,fontSize:18,fontWeight:800 }}>电声耦合参数</Box>
              <Box sx={{ px:2,pb:2,borderTop:'1px solid',borderColor:'divider' }}>
                <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1.5 }}>
                  <Box>
                    <Typography variant="caption">代表 Tc（Allen-Dynes，μ*=0.10）</Typography>
                    <Typography fontWeight={800} color="primary.main" fontSize={20}>
                      {typeof tcRep === 'number' ? `${tcRep.toFixed(1)} K` : '-'}
                    </Typography>
                  </Box>
                  <Field label="λ（电声耦合常数）" value={num(tc.lambda)} />
                  <Field label="ω_log" value={typeof tc['wlog[K]'] === 'number' ? `${tc['wlog[K]'].toFixed(1)} K` : '-'} />
                  <Field label="ω₂" value={typeof tc['w2av[K]'] === 'number' ? `${tc['w2av[K]'].toFixed(1)} K` : '-'} />
                  <Field label="∫α²F" value={num(tc.integral_a2F, 2)} />
                  <Field label="费米能级" value={typeof data?.fermi_level === 'number' ? `${data.fermi_level} eV` : '-'} />
                  <Field label="压强（应力换算）" value={pressure} />
                </Box>
              </Box>
            </Box>
            {/* Tc–μ* 表格 */}
            {mustr.length > 0 && (
              <Box component="details" sx={{ border:'1px solid',borderColor:'divider',borderRadius:2,mb:1.5,overflow:'hidden' }}>
                <Box component="summary" sx={{ cursor:'pointer',p:2,fontSize:18,fontWeight:800 }}>Tc – μ* 关系表</Box>
                <Box sx={{ px:2,pb:2,borderTop:'1px solid',borderColor:'divider',overflowX:'auto' }}>
                  <Box component="table" sx={{ width:'100%',borderCollapse:'collapse',fontSize:13,mt:1 }}>
                    <Box component="thead">
                      <Box component="tr">
                        {['μ*','Tc McMillan / K','Tc Allen-Dynes / K'].map(h=>(
                          <Box key={h} component="th" sx={{ p:'6px 10px',borderBottom:'2px solid',borderColor:'divider',textAlign:'left',color:'text.secondary',fontSize:12 }}>{h}</Box>
                        ))}
                      </Box>
                    </Box>
                    <Box component="tbody">
                      {mustr.map((mu, i) => (
                        <Box component="tr" key={i} sx={{ bgcolor: i === idx10 ? '#e0e7ff' : 'transparent' }}>
                          <Box component="td" sx={{ p:'5px 10px',borderBottom:'1px solid',borderColor:'divider' }}>{mu.toFixed(2)}</Box>
                          <Box component="td" sx={{ p:'5px 10px',borderBottom:'1px solid',borderColor:'divider' }}>{num(tcMcM[i], 2)}</Box>
                          <Box component="td" sx={{ p:'5px 10px',borderBottom:'1px solid',borderColor:'divider' }}>{num(tcAD[i], 2)}</Box>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                </Box>
              </Box>
            )}
            {/* 计算设置 */}
            <Box component="details" sx={{ border:'1px solid',borderColor:'divider',borderRadius:2,mb:1.5,overflow:'hidden' }}>
              <Box component="summary" sx={{ cursor:'pointer',p:2,fontSize:18,fontWeight:800 }}>计算设置</Box>
              <Box sx={{ px:2,pb:2,borderTop:'1px solid',borderColor:'divider' }}>
                <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1.5 }}>
                  <Field label="动能截断" value={typeof data?.kinetic_cutoff === 'number' ? `${data.kinetic_cutoff} Ry` : '-'} />
                  <Field label="总能量" value={typeof data?.energy_total === 'number' ? `${data.energy_total.toFixed(4)} Ry` : '-'} />
                  <Field label="粗 k 点数" value={data?.kpoints_coarse ?? '-'} />
                  <Field label="细 k 点数" value={data?.kpoints_fine ?? '-'} />
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* 结构预览 */}
        <Card sx={{ alignSelf:'start',position:'sticky',top:96,boxShadow:'0 6px 16px rgba(15,23,42,.16),0 10px 24px rgba(15,23,42,.10)' }}>
          <CardContent>
            <Typography variant="h2" gutterBottom>结构预览</Typography>
            {st.cif ? (
              <Box>
                <Box sx={{ display:'grid',gap:1,mb:1.5 }}>
                  <Typography variant="body2">空间群: {st.spg_symbol || '-'} (#{st.spg_number || '-'})</Typography>
                  <Typography variant="body2" color="text.secondary">拖拽旋转 · 滚轮缩放</Typography>
                </Box>
                <StructureViewer3D data={st.cif} format="cif" height={320} />
                <Box component="details" sx={{ mt:1.5 }}>
                  <Box component="summary" sx={{ cursor:'pointer',fontSize:13,fontWeight:700,color:'text.secondary' }}>查看 CIF 文本</Box>
                  <Box component="pre" sx={{ mt:1,p:2,borderRadius:2,bgcolor:'grey.50',maxHeight:240,overflow:'auto',fontFamily:'"Roboto Mono",monospace',fontSize:12 }}>
                    {st.cif}
                  </Box>
                </Box>
              </Box>
            ) : (
              <Typography variant="body2" color="text.secondary">{data ? '该材料无结构数据' : '加载中…'}</Typography>
            )}
          </CardContent>
        </Card>
      </Box>
    </Box>
  )
}

export default AlexandriaDetail
