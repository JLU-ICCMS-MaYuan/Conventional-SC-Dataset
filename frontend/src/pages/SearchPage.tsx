import React, { useState, useMemo, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Box, Typography, Card, CardContent, Chip, Button, IconButton,
  Snackbar, Alert, LinearProgress,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import PeriodicTable from '../components/PeriodicTable'
import { ELEMENTS } from '../lib/periodicElements'
import { api } from '../lib/api'

/* ── mock data matching 03 demo records exactly ── */
interface SuperconductorRecord {
  sourceSystem: string; sourceRecordId: string; formula: string; year: number
  type: string; pressureValue: number; pressure: string; tcValue: number; tc: string
  tcField: string; source: string; status: string; doi: string; journal: string
  title: string; spaceGroupNumber: number; spaceGroup: string; showInChart: boolean
  lambda: string; omegaLog: string; nef: string; method: string; software: string; note: string
  record_id?: number; paper_id?: number
}

const MOCK_RECORDS: SuperconductorRecord[] = [
  { sourceSystem:'local',sourceRecordId:'123',formula:'LaH10',year:2019,type:'Hydride',pressureValue:200,pressure:'200 GPa',tcValue:250,tc:'250 K',tcField:'experimental_tc',source:'Local',status:'Approved',doi:'10.1038/s41586-demo',journal:'Nature',title:'High-pressure superconductivity in lanthanum hydride',spaceGroupNumber:225,spaceGroup:'Fm-3m',showInChart:true,lambda:'3.41',omegaLog:'1120 K',nef:'0.48',method:'DFT + EPC',software:'Quantum ESPRESSO',note:'Mock record for future-plan demo.' },
  { sourceSystem:'local',sourceRecordId:'124',formula:'H3S',year:2015,type:'Hydride',pressureValue:155,pressure:'155 GPa',tcValue:203,tc:'203 K',tcField:'experimental_tc',source:'Local',status:'Approved',doi:'10.1038/s41586-demo2',journal:'Nature',title:'Conventional superconductivity at 203 kelvin',spaceGroupNumber:229,spaceGroup:'Im-3m',showInChart:true,lambda:'2.19',omegaLog:'1010 K',nef:'0.36',method:'Experiment + DFT',software:'VASP',note:'Classic sulfur hydride benchmark.' },
  { sourceSystem:'htsc2025',sourceRecordId:'456',formula:'YH9',year:2024,type:'Hydride',pressureValue:180,pressure:'180 GPa',tcValue:185,tc:'185 K',tcField:'allen_dynes_tc',source:'HTSC-2025',status:'External',doi:'-',journal:'External dataset',title:'Predicted high-Tc yttrium hydride',spaceGroupNumber:194,spaceGroup:'P63/mmc',showInChart:false,lambda:'1.87',omegaLog:'930 K',nef:'0.31',method:'Screening',software:'Dataset',note:'External source, not locally reviewed.' },
  { sourceSystem:'alexandria',sourceRecordId:'mp-demo',formula:'MgB2',year:2001,type:'Conventional',pressureValue:0,pressure:'0 GPa',tcValue:39,tc:'39 K',tcField:'experimental_tc',source:'Alexandria',status:'External',doi:'-',journal:'External dataset',title:'Magnesium diboride benchmark',spaceGroupNumber:191,spaceGroup:'P6/mmm',showInChart:true,lambda:'0.73',omegaLog:'620 K',nef:'0.21',method:'Dataset',software:'Alexandria',note:'External mock benchmark.' },
]

/* ── 类型映射（与旧前端 scTypeMap 一致）── */
const SC_TYPE_MAP: {[k:string]:string} = {
  h:'高压氢化物', c:'碳基', cb:'铜基', ot:'其他超导',
  cuprate:'铜基', iron_based:'铁基', nickel_based:'镍基',
  hydride:'高压氢化物', carbon:'碳基', organic:'有机', others:'其他超导',
}
const REVIEW_MAP: {[k:string]:string} = {
  pending:'Pending', approved:'Approved', reviewed:'Approved', rejected:'Rejected',
}

/* ── helpers ── */
const CAT_COLORS: globalThis.Record<string,string> = {
  'alkali-metal':'#f4bcc2','alkaline-earth':'#e3bd91','transition-metal':'#edcda9',
  'post-transition':'#ededab','metalloid':'#9cd5a8','nonmetal':'#a3d7dc',
  'halogen':'#b7a0db','noble-gas':'#cfb5d6','lanthanide':'#cea1ce','actinide':'#c782ab',
}

/* ── main component ── */
const SearchPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  // 从 URL 参数读取初始值
  const initElements = (searchParams.get('elements') || 'La,H').split(',').filter(Boolean)
  const initMode = searchParams.get('mode') || 'elements_combination_search'
  const [stage, setStage] = useState<'explore'|'results'|'detail'>(
    searchParams.get('elements') ? 'results' : 'explore'
  )
  const [selected, setSelected] = useState<Set<string>>(new Set(initElements))
  const [mode, setMode] = useState(initMode)
  const [formula, setFormula] = useState(initElements.join(''))
  const [source, setSource] = useState('Local')
  const [selectedRecord, setSelectedRecord] = useState<SuperconductorRecord>(MOCK_RECORDS[0])
  const [detailOpen, setDetailOpen] = useState(false)
  const [snackbar, setSnackbar] = useState('')
  const [loading, setLoading] = useState(false)
  const [paperDetail, setPaperDetail] = useState<any>(null)
  const [structureData, setStructureData] = useState<any>(null)
  const [apiError, setApiError] = useState('')
  const [apiRecords, setApiRecords] = useState<SuperconductorRecord[]>([])

  const [filters, setFilters] = useState({
    formula:'', tcMin:0, tcMax:9999, pMin:0, pMax:9999,
    yMin:1900, yMax:2030, type:'All', spaceMin:0, spaceMax:230,
    review:'All', chartOnly:false,
  })

  useEffect(() => {
    if (stage !== 'results') return
    setLoading(true)
    setApiError('')
    const elementList = [...selected].sort()
    const modeKey = mode === 'elements_exact_search' ? 'only'
      : mode === 'elements_contained_search' ? 'contains' : 'combination'

    let url: string, body: any
    // 所有筛选参数传给后端
    const backendFilters: any = { limit: 50, offset: 0 }
    if (filters.formula) backendFilters.keyword = filters.formula
    backendFilters.tc_min = filters.tcMin
    backendFilters.tc_max = filters.tcMax
    backendFilters.pressure_min = filters.pMin
    backendFilters.pressure_max = filters.pMax
    backendFilters.year_min = filters.yMin
    backendFilters.year_max = filters.yMax
    if (filters.type !== 'All') backendFilters.superconductor_type = filters.type.toLowerCase()
    backendFilters.space_group_min = filters.spaceMin
    backendFilters.space_group_max = filters.spaceMax
    if (filters.review !== 'All') backendFilters.review_status = filters.review.toLowerCase()
    if (filters.chartOnly) backendFilters.chart_only = true
    if (source === 'Alexandria') {
      url = '/api/alexandria/search'
      body = { elements: elementList, mode: modeKey, ...backendFilters }
    } else if (source === 'HTSC-2025') {
      url = '/api/htsc2025/search'
      body = { elements: elementList, mode: modeKey, ...backendFilters }
    } else if (source === 'All') {
      url = '/api/papers/search/all'
      body = { elements: elementList, mode: modeKey, ...backendFilters }
    } else {
      url = '/api/papers/search/records'
      body = { elements: elementList, mode, ...backendFilters }
    }

    console.log('fetching:', url, body)
    api.post(url, body)
    .then((res: any) => {
      const items = (res.items || []).filter((r: any) => r._type !== 'section')
      const rows: SuperconductorRecord[] = []
      const searchElements = elementList.map((s: string) => s.toLowerCase())
      const addRow = (rec: any, paper: any, src: string) => {
        // 后端扁平记录：year/formula/type/pressure/tc/space_group/source/status/doi
        const isFlat = rec.year !== undefined && rec.type !== undefined
        rows.push({
          sourceSystem: src === 'Local' ? 'local' : src === 'Alexandria' ? 'alexandria' : 'htsc2025',
          sourceRecordId: String(rec.record_id || rec.id || rec.mat_id || ''),
          record_id: rec.record_id,
          paper_id: rec.paper_id,
          formula: isFlat ? rec.formula : (rec.formula || rec.chemical_formula || paper?.chemical_formula || '-'),
          year: isFlat ? rec.year : (rec.year || paper?.year || 1900),
          type: isFlat ? rec.type : (SC_TYPE_MAP[paper?.superconductor_types?.[0] || rec.type || ''] || 'Unknown'),
          pressureValue: isFlat ? parseFloat(rec.pressure) || 0 : (Number(rec.pressure_gpa ?? rec.pressure) || 0),
          pressure: isFlat ? rec.pressure : ((rec.pressure_gpa ?? rec.pressure) != null ? `${rec.pressure_gpa ?? rec.pressure} GPa` : '-'),
          tcValue: isFlat ? parseFloat(rec.tc) || 0 : (rec.tc_max ?? rec.tc_allen_dynes ?? rec.tc ?? 0),
          tc: isFlat ? rec.tc : ((rec.tc_max ?? rec.tc_allen_dynes ?? rec.tc) != null ? `${Number(rec.tc_max ?? rec.tc_allen_dynes ?? rec.tc).toFixed(1)} K` : '-'),
          tcField: 'tc_max',
          source: isFlat ? rec.source : src,
          status: isFlat ? rec.status : (src !== 'Local' ? 'External' : (REVIEW_MAP[paper?.review_status] || 'Pending')),
          doi: isFlat ? rec.doi : (rec.doi || paper?.doi || '-'),
          journal: isFlat ? '-' : (rec.journal || paper?.journal || '-'),
          title: isFlat ? '-' : (rec.title || paper?.title || '-'),
          spaceGroupNumber: rec.space_group_number ?? rec.spg ?? 0,
          spaceGroup: isFlat ? rec.space_group : (rec.space_group_symbol || (rec.spg ? `#${rec.spg}` : '-')),
          showInChart: rec.show_in_chart !== false,
          lambda: '-', omegaLog: '-', nef: '-', method: '-', software: '-', note: '-',
        })
      }

      if (source === 'Alexandria') {
        items.forEach((item: any) => {
          if ((item.tc_max ?? item.tc_allen_dynes) == null) return
          addRow(item, null, 'Alexandria')
        })
      } else if (source === 'HTSC-2025') {
        items.forEach((item: any) => {
          if (item.tc == null) return
          const f = (item.formula || '').toLowerCase()
          if (!searchElements.every((el: string) => f.includes(el))) return
          addRow(item, null, 'HTSC-2025')
        })
      } else if (source === 'All') {
        // 混合来源：按 _source 区分
        items.forEach((item: any) => {
          const src = item._source === 'alexandria' ? 'Alexandria' : item._source === 'htsc2025' ? 'HTSC-2025' : 'Local'
          const recs = Array.isArray(item.records) ? item.records : [item]
          recs.forEach((rec: any) => addRow(rec, item, src))
        })
      } else {
        // Local：后端已返回扁平记录
        items.forEach((item: any) => addRow(item, null, 'Local'))
      }
      setApiRecords(rows)
    }).catch((err: any) => {
      setApiError(err.message || '检索失败')
    }).finally(() => setLoading(false))
  }, [stage, mode, source, [...selected].join(',')])

  const toast = (msg: string) => setSnackbar(msg)

  // Stage 3: fetch paper detail + structure
  useEffect(() => {
    if (stage !== 'detail' || !selectedRecord.record_id) return
    setPaperDetail(null)
    setStructureData(null)
    api.get(`/api/papers/${selectedRecord.paper_id || selectedRecord.record_id}`)
      .then((data: any) => setPaperDetail(data))
      .catch(() => setPaperDetail(null))
    // 获取结构数据
    api.get(`/api/structures/by-record/${selectedRecord.record_id}`)
      .then((data: any) => setStructureData(data))
      .catch(() => setStructureData(null))
  }, [stage, selectedRecord.record_id])

  const formulaQuery = formula.trim()

  /* ── Stage 1: Explore ── */
  if (stage === 'explore') {
    return (
      <Box>
        <Box sx={{ display:'flex',alignItems:'center',justifyContent:'space-between',gap:2,mb:3 }}>
          <Box>
            <Typography variant="overline">Layer 1 · SC Explore</Typography>
            <Typography variant="h1">用元素或 Formula 进入超导体系检索</Typography>
            <Typography variant="body2" sx={{ mt:1 }}>化学式检索是轻量入口，周期表用于元素组合选择；元素符号始终保持英文。</Typography>
          </Box>
        </Box>

        {/* Formula search card */}
        <Card sx={{ mb:3 }}>
          <CardContent>
            <Typography variant="h2" gutterBottom>化学式检索</Typography>
            <Box sx={{ display:'grid',gridTemplateColumns:'minmax(0,1fr) auto',gap:1.5,alignItems:'end' }}>
              <Box sx={{ minHeight:56,border:'1px solid',borderColor:'divider',borderRadius:1,p:'8px 12px',display:'grid',alignContent:'center',bgcolor:'background.paper' }}>
                <Box component="label" sx={{ color:'text.secondary',fontSize:12,fontWeight:700 }}>Formula</Box>
                <Box component="input" value={formula} onChange={e=>setFormula(e.target.value)}
                  sx={{ border:'none',outline:'none',fontSize:15,fontWeight:600,mt:0.5,width:'100%',bg:'transparent',fontFamily:'inherit' }} />
              </Box>
              <Button variant="contained" onClick={()=>{setStage('results');toast('已按 Formula 刷新结果')}} disabled={!formulaQuery}>搜索</Button>
            </Box>
          </CardContent>
        </Card>

        {/* Periodic table card */}
        <Card sx={{ boxShadow: 3 }}>
          <CardContent>
            <Box sx={{ display:'flex',alignItems:'center',justifyContent:'space-between',gap:2,mb:2 }}>
              <Box>
                <Typography variant="h2">元素周期表检索</Typography>
                <Box sx={{ display:'flex',alignItems:'center',gap:1.5,mt:1.5 }}>
                  <Typography variant="body2">已选元素</Typography>
                  <Chip label={selected.size ? [...selected].sort().join(', ') : '未选择'} color={selected.size ? 'primary' : 'default'} />
                </Box>
              </Box>
              <Box sx={{ display:'flex',alignItems:'center',gap:1 }}>
                {/* Mode segments */}
                <Box sx={{ display:'inline-flex',gap:0.5,bgcolor:'#e8e8ed',borderRadius:'20px',p:0.5 }}>
                  {[
                    {v:'elements_combination_search',l:'选择元素的组合'},
                    {v:'elements_exact_search',l:'仅包含选择元素'},
                    {v:'elements_contained_search',l:'包含所选元素'},
                  ].map(m=>(
                    <Button key={m.v} size="small"
                      sx={{ borderRadius:'16px',px:3.5,py:1,fontSize:'0.9rem',color:mode===m.v?'#fff':'text.primary',bg:mode===m.v?'primary.main':'transparent',minWidth:0,textTransform:'none','&:hover':{bg:mode===m.v?'primary.main':'action.hover'} }}
                      onClick={()=>setMode(m.v)}>{m.l}</Button>
                  ))}
                </Box>
                <Button variant="contained" disabled={selected.size===0 && !formulaQuery}
                  onClick={()=>{setStage('results');toast('已按当前元素组合刷新结果表格')}}>进入页面</Button>
                <Button variant="outlined" onClick={()=>setSelected(new Set())}>清除选择</Button>
              </Box>
            </Box>
            <Box sx={{ overflowX:'auto',py:2 }}>
              <PeriodicTable selected={selected} onToggle={s=>setSelected(prev=>{const n=new Set(prev);n.has(s)?n.delete(s):n.add(s);return n})} />
            </Box>
          </CardContent>
        </Card>
        <Snackbar open={!!snackbar} autoHideDuration={2200} onClose={()=>setSnackbar('')}><Alert severity="success" variant="filled">{snackbar}</Alert></Snackbar>
      </Box>
    )
  }

  /* ── Stage 2: Results ── */
  if (stage === 'results') {
    return (
      <Box>
        <Box sx={{ display:'flex',alignItems:'center',justifyContent:'space-between',gap:2,mb:3 }}>
          <Box>
            <Button size="small" startIcon={<ArrowBackIcon/>} onClick={()=>setStage('explore')} sx={{ mb:1 }}>返回元素搜索</Button>
            <Typography variant="overline">Layer 2 · Data Table</Typography>
            <Typography variant="h1">{selected.size ? [...selected].sort().join('-') : formulaQuery} 体系结果</Typography>
            <Typography variant="body2" sx={{ mt:1 }}>主视图恢复为固定 9 列 Data Table，点击表格行更新右侧 Side Sheet。</Typography>
          </Box>
        </Box>

        {/* Three-column layout */}
        <Box sx={{ display:'grid',gridTemplateColumns:detailOpen?'280px 1fr 360px':'280px 1fr',gap:3,alignItems:'start',minWidth:0,overflow:'hidden',
          '@media (max-width:1180px)':{gridTemplateColumns:'1fr'} }}>
          {/* Filter sidebar — matches demo .filter-stack exactly */}
          <Box component="aside" sx={{ minWidth:0, maxWidth:'100%', overflow:'hidden', p:2.5, bgcolor:'background.paper', borderRadius:4, border:'1px solid', borderColor:'divider', boxShadow:1 }}>
            <Typography variant="h2" gutterBottom>筛选</Typography>
            <Box sx={{ display:'grid',gap:1.5 }}>
              {/* 数据来源 */}
              <Box>
                <Box component="label" sx={{ color:'text.secondary',fontSize:12,fontWeight:700 }}>数据来源</Box>
                <Box sx={{ display:'flex',gap:1,mt:1,flexWrap:'wrap' }}>
                  {['Local','Alexandria','HTSC-2025','All'].map(s=>(
                    <Box key={s} component="button" onClick={()=>setSource(s)}
                      sx={{ minHeight:32,px:1.5,borderRadius:'999px',display:'inline-flex',alignItems:'center',gap:0.75,border:'1px solid',borderColor:source===s?'primary.main':'divider',bgcolor:source===s?'#e0e7ff':'grey.50',color:source===s?'#312e81':'text.primary',fontSize:12,fontWeight:700,cursor:'pointer' }}>
                      {s==='All'?'全部来源':s==='HTSC-2025'?'HTSC-2025':s}
                    </Box>
                  ))}
                </Box>
              </Box>
              {/* Formula */}
              <Box sx={{ minHeight:56,border:'1px solid',borderColor:'divider',borderRadius:1,px:1.5,py:1,display:'grid',bgcolor:'background.paper' }}>
                <Box component="label" sx={{ color:'text.secondary',fontSize:12,fontWeight:700 }}>Formula</Box>
                <Box component="input" value={filters.formula} onChange={e=>setFilters({...filters,formula:e.target.value})}
                  sx={{ border:'none',outline:'none',fontSize:15,fontWeight:600,mt:0.5,width:'100%',bg:'transparent',fontFamily:'inherit',color:'text.primary' }} />
              </Box>
              {/* Tc */}
              <Box>
                <Box component="label" sx={{ color:'text.secondary',fontSize:12,fontWeight:700 }}>代表 Tc / K</Box>
                <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1,mt:0.5 }}>
                  <Box component="input" type="number" value={filters.tcMin} onChange={e=>setFilters({...filters,tcMin:+e.target.value})}
                    sx={{ minHeight:44,border:'1px solid',borderColor:'divider',borderRadius:1,px:1.5,fontSize:14,fontWeight:650,width:'100%',bg:'background.paper',color:'text.primary' }} />
                  <Box component="input" type="number" value={filters.tcMax} onChange={e=>setFilters({...filters,tcMax:+e.target.value})}
                    sx={{ minHeight:44,border:'1px solid',borderColor:'divider',borderRadius:1,px:1.5,fontSize:14,fontWeight:650,width:'100%',bg:'background.paper',color:'text.primary' }} />
                </Box>
              </Box>
              {/* Pressure */}
              <Box>
                <Box component="label" sx={{ color:'text.secondary',fontSize:12,fontWeight:700 }}>压强 / GPa</Box>
                <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1,mt:0.5 }}>
                  <Box component="input" type="number" value={filters.pMin} onChange={e=>setFilters({...filters,pMin:+e.target.value})}
                    sx={{ minHeight:44,border:'1px solid',borderColor:'divider',borderRadius:1,px:1.5,fontSize:14,fontWeight:650,width:'100%',bg:'background.paper',color:'text.primary' }} />
                  <Box component="input" type="number" value={filters.pMax} onChange={e=>setFilters({...filters,pMax:+e.target.value})}
                    sx={{ minHeight:44,border:'1px solid',borderColor:'divider',borderRadius:1,px:1.5,fontSize:14,fontWeight:650,width:'100%',bg:'background.paper',color:'text.primary' }} />
                </Box>
              </Box>
              {/* Year */}
              <Box>
                <Box component="label" sx={{ color:'text.secondary',fontSize:12,fontWeight:700 }}>年份</Box>
                <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1,mt:0.5 }}>
                  <Box component="input" type="number" value={filters.yMin} onChange={e=>setFilters({...filters,yMin:+e.target.value})}
                    sx={{ minHeight:44,border:'1px solid',borderColor:'divider',borderRadius:1,px:1.5,fontSize:14,fontWeight:650,width:'100%',bg:'background.paper',color:'text.primary' }} />
                  <Box component="input" type="number" value={filters.yMax} onChange={e=>setFilters({...filters,yMax:+e.target.value})}
                    sx={{ minHeight:44,border:'1px solid',borderColor:'divider',borderRadius:1,px:1.5,fontSize:14,fontWeight:650,width:'100%',bg:'background.paper',color:'text.primary' }} />
                </Box>
              </Box>
              {/* Type */}
              <Box sx={{ minHeight:56,border:'1px solid',borderColor:'divider',borderRadius:1,px:1.5,py:1,display:'grid',bgcolor:'background.paper' }}>
                <Box component="label" sx={{ color:'text.secondary',fontSize:12,fontWeight:700 }}>超导类型</Box>
                <Box component="select" value={filters.type} onChange={e=>setFilters({...filters,type:e.target.value})}
                  sx={{ width:'100%',minHeight:44,border:'none',bg:'transparent',fontSize:14,fontWeight:650,mt:0.5,fontFamily:'inherit',color:'text.primary' }}>
                  {['All','Hydride','Cuprate','Iron-based','Conventional'].map(o=><option key={o}>{o}</option>)}
                </Box>
              </Box>
              {/* Space group */}
              <Box>
                <Box component="label" sx={{ color:'text.secondary',fontSize:12,fontWeight:700 }}>空间群编号范围</Box>
                <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1,mt:0.5 }}>
                  <Box component="select" value={filters.spaceMin} onChange={e=>setFilters({...filters,spaceMin:+e.target.value})}
                    sx={{ minHeight:44,border:'1px solid',borderColor:'divider',borderRadius:1,px:1.5,fontSize:14,fontWeight:650,bg:'background.paper',color:'text.primary' }}>
                    {[1,14,62,166,194,225].map(v=><option key={v} value={v}>{v}</option>)}
                  </Box>
                  <Box component="select" value={filters.spaceMax} onChange={e=>setFilters({...filters,spaceMax:+e.target.value})}
                    sx={{ minHeight:44,border:'1px solid',borderColor:'divider',borderRadius:1,px:1.5,fontSize:14,fontWeight:650,bg:'background.paper',color:'text.primary' }}>
                    {[14,62,166,194,225,230].map(v=><option key={v} value={v}>{v}</option>)}
                  </Box>
                </Box>
              </Box>
              {/* Review */}
              <Box sx={{ minHeight:56,border:'1px solid',borderColor:'divider',borderRadius:1,px:1.5,py:1,display:'grid',bgcolor:'background.paper' }}>
                <Box component="label" sx={{ color:'text.secondary',fontSize:12,fontWeight:700 }}>审核状态</Box>
                <Box component="select" value={filters.review} onChange={e=>setFilters({...filters,review:e.target.value})}
                  sx={{ width:'100%',minHeight:44,border:'none',bg:'transparent',fontSize:14,fontWeight:650,mt:0.5,fontFamily:'inherit',color:'text.primary' }}>
                  {['All','Approved','Pending','Rejected','External'].map(o=><option key={o}>{o}</option>)}
                </Box>
              </Box>
              {/* Chart toggle */}
              <Box component="button" onClick={()=>setFilters({...filters,chartOnly:!filters.chartOnly})}
                sx={{ minHeight:32,px:1.5,borderRadius:'999px',display:'inline-flex',alignItems:'center',gap:0.75,border:'1px solid',borderColor:filters.chartOnly?'primary.main':'divider',bgcolor:filters.chartOnly?'#e0e7ff':'grey.50',color:filters.chartOnly?'#312e81':'text.primary',fontSize:12,fontWeight:700,cursor:'pointer',justifySelf:'start' }}>
                进入默认图表
              </Box>
              <Box component="button" onClick={()=>setFilters({formula:'',tcMin:0,tcMax:9999,pMin:0,pMax:9999,yMin:1900,yMax:2030,type:'All',spaceMin:0,spaceMax:230,review:'All',chartOnly:false})}
                sx={{ minHeight:40,px:2.5,borderRadius:'999px',display:'inline-flex',alignItems:'center',justifyContent:'center',gap:1,border:'1px solid',borderColor:'divider',bgcolor:'transparent',color:'primary.main',fontSize:14,fontWeight:700,cursor:'pointer' }}>
                重置筛选
              </Box>
            </Box>
          </Box>

          {/* Data table */}
          <Card>
            <CardContent>
              <Typography variant="h2" gutterBottom>结果表格</Typography>
              {loading && <LinearProgress sx={{ mb: 2, borderRadius: 999, height: 4 }} />}
              {apiError && (
                <Box sx={{ display:'flex',alignItems:'center',justifyContent:'space-between',gap:1.5,mb:1.5,p:1.5,border:'1px solid',borderColor:'divider',borderRadius:2,bgcolor:'grey.50' }}>
                  <Typography variant="body2" color="error">{apiError}</Typography>
                  <Button size="small" variant="text" onClick={() => { setApiError(''); setStage('results') }}>重试</Button>
                </Box>
              )}
              <Box sx={{ overflowX:'auto',border:'1px solid',borderColor:'divider',borderRadius:2,bgcolor:'background.paper' }}>
                <Box component="table" sx={{ width:'100%',minWidth:980,borderCollapse:'separate',borderSpacing:0,fontSize:14 }}>
                  <Box component="thead">
                    <Box component="tr">
                      {['年份','体系名称','超导类型','压强','代表 Tc','空间群','数据来源','审核状态','DOI'].map(h=>(
                        <Box key={h} component="th" sx={{ p:'14px 12px',borderBottom:'1px solid',borderColor:'divider',color:'text.secondary',fontSize:12,fontWeight:800,letterSpacing:'.02em',textTransform:'uppercase',textAlign:'left',whiteSpace:'nowrap',bgcolor:'grey.50',position:'sticky',top:0,zIndex:1 }}>{h}</Box>
                      ))}
                    </Box>
                  </Box>
                  <Box component="tbody">
                    {apiRecords.map((r,i)=>(
                      <Box key={i} component="tr"
                        onClick={()=>{setSelectedRecord(r);setDetailOpen(true);toast('详情面板已更新')}}
                        sx={{
                          cursor:'pointer',transition:'background .16s ease',
                          '&:hover':{bgcolor:'grey.50'},
                          bgcolor:detailOpen&&selectedRecord===r?'#e0e7ff':'transparent',
                          boxShadow:detailOpen&&selectedRecord===r?'inset 4px 0 0 #4f46e5':'none',
                        }}>
                        <Box component="td" sx={{ p:'14px 12px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap' }}>{r.year}</Box>
                        <Box component="td" sx={{ p:'14px 12px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap' }}>{r.formula}</Box>
                        <Box component="td" sx={{ p:'14px 12px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap' }}>{r.type}</Box>
                        <Box component="td" sx={{ p:'14px 12px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap' }}>{r.pressure}</Box>
                        <Box component="td" sx={{ p:'14px 12px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap',color:'primary.main',fontWeight:800 }}>{r.tc}</Box>
                        <Box component="td" sx={{ p:'14px 12px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap' }}>{r.spaceGroup}</Box>
                        <Box component="td" sx={{ p:'14px 12px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap' }}><Chip label={r.source} size="small" color={r.source==='Local'?'primary':r.source==='Alexandria'?'secondary':'default'} /></Box>
                        <Box component="td" sx={{ p:'14px 12px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap' }}><Chip label={r.status} size="small" color={r.status==='Approved'?'success':r.status==='Pending'?'warning':'default'} /></Box>
                        <Box component="td" sx={{ p:'14px 12px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap' }}>{r.doi}</Box>
                      </Box>
                    ))}
                    {apiRecords.length===0&&(
                      <Box component="tr"><Box component="td" colSpan={9} sx={{ p:4,textAlign:'center',color:'text.secondary' }}>
                        <Typography variant="h3">没有匹配记录</Typography>
                        <Typography variant="body2">可以重置筛选，或扩大 Tc、压强、年份、空间群范围。</Typography>
                        <Button variant="contained" sx={{ mt:2 }} onClick={()=>setFilters({...filters,tcMin:0,tcMax:999,pMin:0,pMax:999,yMin:1900,yMax:2030,type:'All',spaceMin:1,spaceMax:230,review:'All'})}>重置筛选</Button>
                      </Box></Box>
                    )}
                  </Box>
                </Box>
              </Box>
            </CardContent>
          </Card>

          {/* Detail preview side sheet */}
          {detailOpen && (
            <Card sx={{ alignSelf:'start',position:'sticky',top:96,boxShadow:'0 6px 16px rgba(15,23,42,.16),0 10px 24px rgba(15,23,42,.10)' }}>
              <CardContent>
                <Box sx={{ display:'flex',justifyContent:'space-between',alignItems:'center',mb:2 }}>
                  <Typography variant="h2">记录详情</Typography>
                  <IconButton size="small" onClick={()=>setDetailOpen(false)}>✕</IconButton>
                </Box>
                <Typography sx={{ fontFamily:'"Roboto Mono",monospace',mb:2 }}>{selectedRecord.formula} · {selectedRecord.pressure} · representative_tc = {selectedRecord.tcField}</Typography>
                <Box sx={{ display:'flex',gap:1,mb:2 }}><Chip label={selectedRecord.status} size="small" color={selectedRecord.status==='Approved'?'success':'warning'} /><Chip label={selectedRecord.source} size="small" color="primary" /></Box>
                <Button variant="contained" fullWidth onClick={()=>{setStage('detail');toast('已进入研究记录详情')}}>查看完整详情</Button>
              </CardContent>
            </Card>
          )}
        </Box>
        <Snackbar open={!!snackbar} autoHideDuration={2200} onClose={()=>setSnackbar('')}><Alert severity="success" variant="filled">{snackbar}</Alert></Snackbar>
      </Box>
    )
  }

  /* ── Stage 3: Detail ── */
  const r = selectedRecord
  return (
    <Box>
      <Box sx={{ display:'flex',alignItems:'center',justifyContent:'space-between',gap:2,mb:3 }}>
        <Box>
          <Button size="small" startIcon={<ArrowBackIcon/>} onClick={()=>setStage('results')} sx={{ mb:1 }}>返回结果表格</Button>
          <Typography variant="overline">Layer 3 · Research Record</Typography>
          <Typography variant="h1">{r.formula} 详情</Typography>
        </Box>
        <Box sx={{ display:'flex',gap:1 }}>
          <Button variant="contained" color="secondary" onClick={()=>toast('已生成 JSON')}>下载 JSON</Button>
          <Button variant="outlined" onClick={()=>toast('已生成 RIS')}>导出 RIS</Button>
          <Button variant="outlined" onClick={()=>{navigator.clipboard.writeText(r.doi);toast('DOI 已复制')}}>复制 DOI</Button>
        </Box>
      </Box>

      <Box sx={{ display:'grid',gridTemplateColumns:'1fr 360px',gap:3,alignItems:'start','@media (max-width:1180px)':{gridTemplateColumns:'1fr'} }}>
        {/* Detail main — accordion sections matching demo */}
        <Card sx={{ boxShadow: 3 }}>
          <CardContent>
            {/* 基础信息 */}
            <Box component="details" open sx={{ border:'1px solid',borderColor:'divider',borderRadius:2,mb:1.5,overflow:'hidden' }}>
              <Box component="summary" sx={{ cursor:'pointer',p:2,fontSize:18,fontWeight:800 }}>基础信息</Box>
              <Box sx={{ px:2,pb:2,borderTop:'1px solid',borderColor:'divider' }}>
                <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1.5 }}>
                  <Box><Typography variant="caption">Formula</Typography><Typography fontWeight={600}>{r.formula}</Typography></Box>
                  <Box><Typography variant="caption">年份</Typography><Typography fontWeight={600}>{r.year}</Typography></Box>
                  <Box><Typography variant="caption">DOI</Typography><Typography fontWeight={600}>{r.doi}</Typography></Box>
                  <Box><Typography variant="caption">期刊</Typography><Typography fontWeight={600}>{paperDetail?.journal || r.journal}</Typography></Box>
                  <Box sx={{ gridColumn:'1/-1' }}><Typography variant="caption">论文标题</Typography><Typography fontWeight={600}>{paperDetail?.title || r.title}</Typography></Box>
                  <Box><Typography variant="caption">审核状态</Typography><Chip label={r.status} size="small" color={r.status==='Approved'?'success':'warning'} /></Box>
                  <Box><Typography variant="caption">数据来源</Typography><Chip label={r.source} size="small" color="primary" /></Box>
                </Box>
              </Box>
            </Box>
            {/* 超导参数 */}
            <Box component="details" sx={{ border:'1px solid',borderColor:'divider',borderRadius:2,mb:1.5,overflow:'hidden' }}>
              <Box component="summary" sx={{ cursor:'pointer',p:2,fontSize:18,fontWeight:800 }}>超导参数</Box>
              <Box sx={{ px:2,pb:2,borderTop:'1px solid',borderColor:'divider' }}>
                <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1.5 }}>
                  <Box><Typography variant="caption">代表 Tc</Typography><Typography fontWeight={800} color="primary.main" fontSize={20}>{r.tc} ({r.tcField})</Typography></Box>
                  <Box><Typography variant="caption">压强</Typography><Typography fontWeight={600}>{r.pressure}</Typography></Box>
                  <Box><Typography variant="caption">λ</Typography><Typography fontWeight={600}>{paperDetail?.records?.[0]?.lambda_value ?? r.lambda}</Typography></Box>
                  <Box><Typography variant="caption">ω_log</Typography><Typography fontWeight={600}>{paperDetail?.records?.[0]?.omega_log != null ? `${paperDetail.records[0].omega_log} K` : r.omegaLog}</Typography></Box>
                  <Box><Typography variant="caption">N(Ef)</Typography><Typography fontWeight={600}>{paperDetail?.records?.[0]?.n_ef_total ?? r.nef}</Typography></Box>
                </Box>
              </Box>
            </Box>
            {/* 结构信息 */}
            <Box component="details" sx={{ border:'1px solid',borderColor:'divider',borderRadius:2,mb:1.5,overflow:'hidden' }}>
              <Box component="summary" sx={{ cursor:'pointer',p:2,fontSize:18,fontWeight:800 }}>结构信息</Box>
              <Box sx={{ px:2,pb:2,borderTop:'1px solid',borderColor:'divider' }}>
                <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1.5 }}>
                  <Box><Typography variant="caption">空间群</Typography><Typography fontWeight={600}>{r.spaceGroup}{paperDetail?.records?.[0]?.space_group_number ? ` (#${paperDetail.records[0].space_group_number})` : ''}</Typography></Box>
                  <Box><Typography variant="caption">压强</Typography><Typography fontWeight={600}>{r.pressure}</Typography></Box>
                </Box>
              </Box>
            </Box>
            {/* 计算与备注 */}
            <Box component="details" sx={{ border:'1px solid',borderColor:'divider',borderRadius:2,mb:1.5,overflow:'hidden' }}>
              <Box component="summary" sx={{ cursor:'pointer',p:2,fontSize:18,fontWeight:800 }}>计算与备注</Box>
              <Box sx={{ px:2,pb:2,borderTop:'1px solid',borderColor:'divider' }}>
                <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1.5 }}>
                  <Box><Typography variant="caption">方法</Typography><Typography fontWeight={600}>{paperDetail?.records?.[0]?.method || r.method}</Typography></Box>
                  <Box><Typography variant="caption">软件</Typography><Typography fontWeight={600}>{paperDetail?.records?.[0]?.calculation_code || r.software}</Typography></Box>
                  <Box sx={{ gridColumn:'1/-1' }}><Typography variant="caption">备注</Typography><Typography fontWeight={600}>{paperDetail?.records?.[0]?.note || r.note}</Typography></Box>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* Structure preview */}
        <Card sx={{ alignSelf:'start',position:'sticky',top:96,boxShadow:'0 6px 16px rgba(15,23,42,.16),0 10px 24px rgba(15,23,42,.10)' }}>
          <CardContent>
            <Typography variant="h2" gutterBottom>结构预览</Typography>
            {structureData ? (
              <Box>
                <Box sx={{ display:'grid',gap:1 }}>
                  <Typography variant="body2">格式: {structureData.structure_format || '-'}</Typography>
                  <Typography variant="body2">空间群: {structureData.space_group_symbol || '-'} (#{structureData.space_group_number || '-'})</Typography>
                  <Typography variant="body2">原子数: {structureData.atom_count || '-'}</Typography>
                  {structureData.cell_parameters && (
                    <Typography variant="body2">晶胞参数: {JSON.stringify(structureData.cell_parameters)}</Typography>
                  )}
                  {structureData.volume != null && (
                    <Typography variant="body2">体积: {structureData.volume}</Typography>
                  )}
                </Box>
                {structureData.structure_text && (
                  <Box component="pre" sx={{ mt:2,p:2,borderRadius:2,bgcolor:'grey.50',maxHeight:240,overflow:'auto',fontFamily:'"Roboto Mono",monospace',fontSize:12 }}>
                    {structureData.structure_text.slice(0, 2000)}
                  </Box>
                )}
              </Box>
            ) : (
              <Box sx={{ minHeight:240,borderRadius:2,border:'1px solid',borderColor:'divider',
                background:`radial-gradient(circle at 22% 28%, #4f46e5 0 9px, transparent 10px), radial-gradient(circle at 66% 34%, #0891b2 0 9px, transparent 10px), radial-gradient(circle at 42% 70%, #4f46e5 0 9px, transparent 10px), linear-gradient(145deg, #fff, #f1f5f9)`,
                position:'relative',overflow:'hidden',
                '&::before,&::after':{content:'""',position:'absolute',left:'25%',right:'25%',top:'34%',height:2,bg:'#cbd5e1',transform:'rotate(18deg)'},
                '&::after':{top:'58%',transform:'rotate(-25deg)'},
              }}>
                <Typography variant="body2" sx={{ position:'absolute',bottom:12,left:12,color:'text.secondary' }}>
                  该记录暂无结构数据
                </Typography>
              </Box>
            )}
          </CardContent>
        </Card>
      </Box>
      <Snackbar open={!!snackbar} autoHideDuration={2200} onClose={()=>setSnackbar('')}><Alert severity="success" variant="filled">{snackbar}</Alert></Snackbar>
    </Box>
  )
}

export default SearchPage
