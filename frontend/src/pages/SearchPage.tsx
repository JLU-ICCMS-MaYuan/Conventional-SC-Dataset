import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Box, Typography, Card, CardContent, Chip, Button,
  Snackbar, Alert, LinearProgress, Select, MenuItem,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import PeriodicTable from '../components/PeriodicTable'
import AlexandriaDetail from '../components/AlexandriaDetail'
import HtscDetail from '../components/HtscDetail'
import StructureViewer3D from '../components/StructureViewer3D'
import { ELEMENTS } from '../lib/periodicElements'
import { api } from '../lib/api'
import { collectPropertyRows, collectStructures, viewerFormat } from '../lib/paperDetailView'

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

/* ── 类型映射（规范全称 → 中文，与 backend/sc_types.py 保持一致）── */
const SC_TYPE_MAP: {[k:string]:string} = {
  hydride:'高压氢化物', cuprate:'铜氧化物', iron_based:'铁基',
  nickel_based:'镍基', carbon:'碳基', organic:'有机', others:'其他超导',
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

/* ── Layer 2 筛选侧栏 ── */
const FILTER_DEFAULTS = {
  formula:'', tcMin:0, tcMax:9999, pMin:0, pMax:9999,
  yMin:1900, yMax:2030, type:'All', spaceMin:0, spaceMax:230,
  review:'All', chartOnly:false,
}
// 各数据源后端实际支持的筛选组（与检索请求的参数裁剪保持一致；v2 本地库暂无空间群数据）
const SOURCE_FILTER_SUPPORT: {[k:string]:Set<string>} = {
  'Local': new Set(['formula','tc','pressure','year','type','review','chart']),
  'Alexandria': new Set(['tc','pressure','space']),
  'HTSC-2025': new Set(['tc','pressure']),
  'All': new Set<string>(),
}
// 联排输入壳：聚焦时主色描边 + 浅靛光环
const shellSx = {
  display:'flex',alignItems:'center',minWidth:0,border:'1px solid',borderColor:'divider',borderRadius:2,
  bgcolor:'background.paper',overflow:'hidden',transition:'border-color .15s ease, box-shadow .15s ease',
  '&:focus-within':{ borderColor:'primary.main',boxShadow:'0 0 0 3px rgba(79,70,229,.12)' },
}
const bareInputSx = {
  flex:1,width:'100%',minWidth:0,minHeight:40,border:'none',outline:'none',px:1.25,fontSize:14,fontWeight:650,
  bgcolor:'transparent',color:'text.primary',fontFamily:'inherit',textAlign:'center' as const,
  '&:disabled':{ cursor:'not-allowed',color:'text.disabled' },
}
// MUI Select：嵌入联排壳的无下划线样式
const selectSx = {
  flex:1,minWidth:0,fontSize:14,fontWeight:650,color:'text.primary',
  '& .MuiSelect-select':{ py:1.1,px:1.5,minHeight:'unset !important',display:'flex',alignItems:'center' },
  '&.Mui-disabled':{ cursor:'not-allowed' },
}
// 下拉弹层：圆角卡片 + 浅靛选中态，与主题一致
const selectMenuProps = {
  PaperProps: {
    sx: {
      mt:0.5, borderRadius:2, border:'1px solid', borderColor:'divider',
      boxShadow:'0 8px 24px rgba(15,23,42,.14)',
      '& .MuiMenuItem-root':{ fontSize:14, fontWeight:600, borderRadius:1.5, mx:0.5, my:0.25, minHeight:36 },
      '& .MuiMenuItem-root.Mui-selected':{ bgcolor:'#e0e7ff', color:'#312e81' },
      '& .MuiMenuItem-root.Mui-selected:hover':{ bgcolor:'#e0e7ff' },
    },
  },
}

/* 组标题：该组筛选生效时左侧亮起靛蓝短竖条 */
const FilterGroupLabel: React.FC<{ text:string; unit?:string; active?:boolean; disabled?:boolean }> =
  ({ text, unit, active, disabled }) => (
  <Box sx={{ display:'flex',alignItems:'center',justifyContent:'space-between',mb:0.75 }}>
    <Box sx={{ display:'flex',alignItems:'center',gap:0.75 }}>
      {active && <Box sx={{ width:3,height:12,borderRadius:2,bgcolor:'primary.main' }} />}
      <Typography sx={{ fontSize:11,fontWeight:800,letterSpacing:'.08em',textTransform:'uppercase',
        color: active ? 'primary.main' : disabled ? 'text.disabled' : 'text.secondary' }}>{text}</Typography>
    </Box>
    {unit && <Typography sx={{ fontSize:11,fontWeight:700,color:'text.disabled' }}>{unit}</Typography>}
  </Box>
)

/* min – max 联排范围输入 */
const RangeField: React.FC<{
  label:string; unit?:string; active?:boolean; disabled?:boolean
  lo:number; hi:number; onLo:(v:number)=>void; onHi:(v:number)=>void
}> = ({ label, unit, active, disabled, lo, hi, onLo, onHi }) => (
  <Box title={disabled ? '当前数据源不支持该筛选' : undefined} sx={{ opacity: disabled ? 0.45 : 1 }}>
    <FilterGroupLabel text={label} unit={unit} active={active} disabled={disabled} />
    <Box sx={shellSx}>
      <Box component="input" type="number" disabled={disabled} value={lo}
        onChange={(e:any)=>onLo(+e.target.value)} sx={bareInputSx} />
      <Typography sx={{ color:'text.disabled',px:0.25,userSelect:'none' }}>–</Typography>
      <Box component="input" type="number" disabled={disabled} value={hi}
        onChange={(e:any)=>onHi(+e.target.value)} sx={bareInputSx} />
    </Box>
  </Box>
)

/* ── main component ── */
const SearchPage: React.FC = () => {
  const [searchParams] = useSearchParams()
  // 从 URL 参数读取初始值
  // 无 elements 参数时不预选任何元素：默认选中某个体系会把检索静默限定在该体系，
  // 用户未必察觉自己并非在做全库检索。
  const initElements = (searchParams.get('elements') || '').split(',').filter(Boolean)
  const initMode = searchParams.get('mode') || 'elements_combination_search'
  const initPaperId = searchParams.get('paper_id')
  const [stage, setStage] = useState<'explore'|'results'|'detail'>(
    initPaperId ? 'detail' : (searchParams.get('elements') ? 'results' : 'explore')
  )
  const [selected, setSelected] = useState<Set<string>>(new Set(initElements))
  const [mode, setMode] = useState(initMode)
  const [formula, setFormula] = useState(initElements.join(''))
  const [source, setSource] = useState('Local')
  const [selectedRecord, setSelectedRecord] = useState<SuperconductorRecord>(MOCK_RECORDS[0])
  const [snackbar, setSnackbar] = useState('')
  const [loading, setLoading] = useState(false)
  const [paperDetail, setPaperDetail] = useState<any>(null)
  const [structureData, setStructureData] = useState<any>(null)
  const [structureMsg, setStructureMsg] = useState('该记录暂无结构数据')
  const [apiError, setApiError] = useState('')
  const [apiRecords, setApiRecords] = useState<SuperconductorRecord[]>([])
  const [page, setPage] = useState(0)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [retryTick, setRetryTick] = useState(0)
  const PAGE_SIZE = 50

  const [filters, setFilters] = useState({ ...FILTER_DEFAULTS })

  const formulaQuery = formula.trim()
  const elementsKey = [...selected].sort().join(',')
  const filtersKey = JSON.stringify(filters)

  // 直接从图表跳转——加载论文详情
  useEffect(() => {
    if (!initPaperId) return
    const pid = parseInt(initPaperId)
    api.get<any>(`/api/papers/${pid}`).then(data => {
      const r: SuperconductorRecord = {
        sourceSystem: 'local', sourceRecordId: String(pid),
        formula: data.key_properties?.[0]?.material || data.chemical_formula || '-',
        year: data.year || 0, type: data.superconductor_types?.[0] || '',
        pressureValue: 0, pressure: '-', tcValue: 0, tc: '-', tcField: '',
        source: 'Local', status: data.review_status || 'Pending',
        doi: data.doi || '', journal: data.journal || '',
        title: data.title || '', spaceGroupNumber: 0, spaceGroup: '-',
        showInChart: false, lambda: '', omegaLog: '', nef: '',
        method: '', software: '', note: '',
        paper_id: pid,
      }
      setSelectedRecord(r)
      setStage('detail')
    }).catch(() => {})
  }, [initPaperId])

  useEffect(() => {
    if (stage !== 'results') return
    const elementList = [...selected].sort()
    // 未选元素时走化学式检索（仅 Local 支持）
    const isFormulaSearch = elementList.length === 0 && !!formulaQuery
    if (elementList.length === 0 && !isFormulaSearch) return
    if (isFormulaSearch && source !== 'Local') {
      setApiRecords([]); setTotal(0); setTotalPages(0);
      setApiError('化学式检索仅支持 Local 数据源，请选择元素或切回 Local')
      return
    }

    // 防抖：筛选输入连续变化时只发最后一次请求
    const timer = setTimeout(() => {
      setLoading(true)
      setApiError('')
      const modeKey = mode === 'elements_exact_search' ? 'only'
        : mode === 'elements_contained_search' ? 'contains' : 'combination'

      // 仅传用户实际收紧过的筛选，避免默认区间误伤缺失字段的记录
      const backendFilters: any = {}
      if (filters.formula) backendFilters.keyword = filters.formula
      if (filters.tcMin > 0) backendFilters.tc_min = filters.tcMin
      if (filters.tcMax < 9999) backendFilters.tc_max = filters.tcMax
      if (filters.pMin > 0) backendFilters.pressure_min = filters.pMin
      if (filters.pMax < 9999) backendFilters.pressure_max = filters.pMax
      if (filters.yMin > 1900) backendFilters.year_min = filters.yMin
      if (filters.yMax < 2030) backendFilters.year_max = filters.yMax
      if (filters.type !== 'All') backendFilters.superconductor_type = filters.type
      if (filters.spaceMin > 0) backendFilters.space_group_min = filters.spaceMin
      if (filters.spaceMax < 230) backendFilters.space_group_max = filters.spaceMax
      if (filters.review !== 'All') backendFilters.review_status = filters.review.toLowerCase()
      if (filters.chartOnly) backendFilters.chart_only = true
      // 各来源只发送其后端支持的筛选字段
      const pick = (keys: string[]) =>
        Object.fromEntries(keys.filter(k => backendFilters[k] !== undefined).map(k => [k, backendFilters[k]]))
      const paging = { limit: PAGE_SIZE, offset: page * PAGE_SIZE }

      let url: string, body: any
      if (source === 'Alexandria') {
        url = '/api/alexandria/search'
        body = { elements: elementList, mode: modeKey, require_tc: true,
          ...pick(['tc_min','tc_max','pressure_min','pressure_max','space_group_min','space_group_max']), ...paging }
      } else if (source === 'HTSC-2025') {
        url = '/api/htsc2025/search'
        body = { elements: elementList, mode: modeKey,
          ...pick(['tc_min','tc_max','pressure_min','pressure_max']), ...paging }
      } else if (source === 'All') {
        url = '/api/papers/search/all'
        body = { elements: elementList, mode, ...paging }
      } else {
        url = '/api/papers/search/records'
        body = isFormulaSearch
          ? { elements: [], mode: 'formula_search', formula: formulaQuery, ...backendFilters, ...paging }
          : { elements: elementList, mode, ...backendFilters, ...paging }
      }

      console.log('fetching:', url, body)
      api.post(url, body)
      .then((res: any) => {
        const items = (res.items || []).filter((r: any) => r._type !== 'section')
        const rows: SuperconductorRecord[] = []
        const addRow = (rec: any, paper: any, src: string) => {
          // 后端扁平记录：year/formula/type/pressure/tc/space_group/source/status/doi
          const isFlat = rec.year !== undefined && rec.type !== undefined
          rows.push({
            sourceSystem: src === 'Local' ? 'local' : src === 'Alexandria' ? 'alexandria' : 'htsc2025',
            // 标识优先级：本地记录 id → Alexandria mat_id → HTSC name → 数字主键兜底
            sourceRecordId: String(rec.record_id || rec.mat_id || rec.name || rec.id || ''),
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
            addRow(item, null, 'HTSC-2025')
          })
        } else if (source === 'All') {
          // 混合来源：按 _source 区分
          items.forEach((item: any) => {
            const src = item._source === 'alexandria' ? 'Alexandria' : item._source === 'htsc2025' ? 'HTSC-2025' : 'Local'
            if (src === 'Local' && Array.isArray(item.key_properties)) {
              // Local 论文条目：key_properties 中的临界温度物性展开为行
              item.key_properties
                .filter((kp: any) => kp.name === 'critical_temperature' && kp.value_max != null)
                .forEach((kp: any) => addRow({
                  record_id: kp.id, paper_id: item.id, year: item.year || 0,
                  formula: kp.material || '-',
                  type: SC_TYPE_MAP[kp.superconductor_type] || 'Unknown',
                  pressure: kp.pressure_gpa != null ? `${kp.pressure_gpa} GPa` : '-',
                  tc: kp.value_min !== kp.value_max ? `${kp.value_min}–${kp.value_max} K` : `${Number(kp.value_max).toFixed(1)} K`,
                  space_group: '-', source: 'Local',
                  status: REVIEW_MAP[item.review_status] || 'Pending',
                  doi: item.doi || '-',
                }, item, src))
            } else {
              addRow(item, item, src)
            }
          })
        } else {
          // Local：后端已返回扁平记录
          items.forEach((item: any) => addRow(item, null, 'Local'))
        }
        setApiRecords(rows)

        // 后端真分页：total/total_pages 来自服务端
        const totalCount = res.total ?? rows.length
        setTotal(totalCount)
        setTotalPages(source === 'All' ? (res.total_pages ?? (rows.length ? 1 : 0)) : Math.ceil(totalCount / PAGE_SIZE))
      }).catch((err: any) => {
        setApiError(err.message || '检索失败')
      }).finally(() => setLoading(false))
    }, 300)
    return () => clearTimeout(timer)
  }, [stage, mode, source, elementsKey, filtersKey, formulaQuery, page, retryTick])

  const toast = (msg: string) => setSnackbar(msg)

  // Stage 3: fetch paper detail + 从 material_states[].structures[] 取结构
  useEffect(() => {
    if (stage !== 'detail' || !selectedRecord.paper_id) return
    setPaperDetail(null)
    setStructureData(null)
    setStructureMsg('该记录暂无结构数据')
    api.get(`/api/papers/${selectedRecord.paper_id}`)
      .then((data: any) => {
        setPaperDetail(data)
        const structures = collectStructures(data)
        setStructureData(structures.length > 0 ? structures : null)
      })
      .catch(() => setPaperDetail(null))
  }, [stage, selectedRecord.paper_id])

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
                  sx={{ border:'none',outline:'none',fontSize:15,fontWeight:600,mt:0.5,width:'100%',bgcolor:'transparent',fontFamily:'inherit' }} />
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
                      sx={{ borderRadius:'16px',px:3.5,py:1,fontSize:'0.9rem',color:mode===m.v?'#fff':'text.primary',bgcolor:mode===m.v?'primary.main':'transparent',minWidth:0,textTransform:'none','&:hover':{bgcolor:mode===m.v?'primary.main':'action.hover'} }}
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
    // 各筛选组是否已被收紧（用于生效指示与计数）
    const groupActive = {
      formula: !!filters.formula,
      tc: filters.tcMin > 0 || filters.tcMax < 9999,
      pressure: filters.pMin > 0 || filters.pMax < 9999,
      year: filters.yMin > 1900 || filters.yMax < 2030,
      type: filters.type !== 'All',
      space: filters.spaceMin > 0 || filters.spaceMax < 230,
      review: filters.review !== 'All',
      chart: filters.chartOnly,
    }
    const activeCount = Object.values(groupActive).filter(Boolean).length
    const supported = SOURCE_FILTER_SUPPORT[source] ?? SOURCE_FILTER_SUPPORT['Local']
    return (
      <Box>
        <Box sx={{ display:'flex',alignItems:'center',justifyContent:'space-between',gap:2,mb:3 }}>
          <Box>
            <Button size="small" startIcon={<ArrowBackIcon/>} onClick={()=>setStage('explore')} sx={{ mb:1 }}>返回元素搜索</Button>
            <Typography variant="overline">Layer 2 · Data Table</Typography>
            <Typography variant="h1">{selected.size ? [...selected].sort().join('-') : formulaQuery} 体系结果</Typography>
            <Typography variant="body2" sx={{ mt:1 }}>点击表格行展开详情，再次点击收起。</Typography>
          </Box>
        </Box>

        {/* Three-column layout */}
        <Box sx={{ display:'grid',gridTemplateColumns:'280px 1fr',gap:3,alignItems:'start',minWidth:0,overflow:'hidden',
          '@media (max-width:1180px)':{gridTemplateColumns:'1fr'} }}>
          {/* Filter sidebar */}
          <Box component="aside" sx={{ minWidth:0, maxWidth:'100%', overflow:'hidden', p:2.5, bgcolor:'background.paper', borderRadius:4, border:'1px solid', borderColor:'divider', boxShadow:1 }}>
            {/* 标题行：生效计数 + 按需出现的重置 */}
            <Box sx={{ display:'flex',alignItems:'center',justifyContent:'space-between',mb:2 }}>
              <Box sx={{ display:'flex',alignItems:'center',gap:1 }}>
                <Typography variant="h2">筛选</Typography>
                {activeCount > 0 && (
                  <Box sx={{ minWidth:20,height:20,px:0.5,borderRadius:'999px',bgcolor:'primary.main',color:'#fff',fontSize:12,fontWeight:800,display:'inline-flex',alignItems:'center',justifyContent:'center' }}>
                    {activeCount}
                  </Box>
                )}
              </Box>
              {activeCount > 0 && (
                <Box component="button" onClick={()=>setFilters({ ...FILTER_DEFAULTS })}
                  sx={{ border:'none',bgcolor:'transparent',color:'primary.main',fontSize:13,fontWeight:700,cursor:'pointer',p:0,'&:hover':{textDecoration:'underline'} }}>
                  重置
                </Box>
              )}
            </Box>
            {/* minmax(0,1fr)：切断 number input 内在宽度对单列 grid 的撑破 */}
            <Box sx={{ display:'grid',gridTemplateColumns:'minmax(0,1fr)',gap:2 }}>
              {/* 数据来源 */}
              <Box>
                <FilterGroupLabel text="数据来源" />
                <Box sx={{ display:'flex',gap:1,mt:0.5,flexWrap:'wrap' }}>
                  {['Local','Alexandria','HTSC-2025','All'].map(s=>(
                    <Box key={s} component="button" onClick={()=>setSource(s)}
                      sx={{ minHeight:32,px:1.5,borderRadius:'999px',display:'inline-flex',alignItems:'center',gap:0.75,border:'1px solid',borderColor:source===s?'primary.main':'divider',bgcolor:source===s?'#e0e7ff':'grey.50',color:source===s?'#312e81':'text.primary',fontSize:12,fontWeight:700,cursor:'pointer',transition:'all .15s ease','&:hover':{borderColor:'primary.main'} }}>
                      {s==='All'?'全部来源':s}
                    </Box>
                  ))}
                </Box>
                {source === 'All' && (
                  <Typography sx={{ fontSize:11,color:'text.disabled',mt:0.75 }}>全部来源模式仅按元素检索，下方筛选不参与</Typography>
                )}
              </Box>
              <Box sx={{ height:'1px',bgcolor:'divider' }} />
              {/* Formula 关键词 */}
              <Box title={supported.has('formula') ? undefined : '当前数据源不支持该筛选'} sx={{ opacity: supported.has('formula') ? 1 : 0.45 }}>
                <FilterGroupLabel text="Formula 关键词" active={groupActive.formula} disabled={!supported.has('formula')} />
                <Box sx={shellSx}>
                  <Box component="input" placeholder="如 LaH10" disabled={!supported.has('formula')}
                    value={filters.formula} onChange={e=>setFilters({...filters,formula:e.target.value})}
                    sx={{ ...bareInputSx, textAlign:'left', px:1.5 }} />
                </Box>
              </Box>
              {/* 数值范围 */}
              <RangeField label="代表 Tc" unit="K" active={groupActive.tc} disabled={!supported.has('tc')}
                lo={filters.tcMin} hi={filters.tcMax}
                onLo={v=>setFilters({...filters,tcMin:v})} onHi={v=>setFilters({...filters,tcMax:v})} />
              <RangeField label="压强" unit="GPa" active={groupActive.pressure} disabled={!supported.has('pressure')}
                lo={filters.pMin} hi={filters.pMax}
                onLo={v=>setFilters({...filters,pMin:v})} onHi={v=>setFilters({...filters,pMax:v})} />
              <RangeField label="年份" active={groupActive.year} disabled={!supported.has('year')}
                lo={filters.yMin} hi={filters.yMax}
                onLo={v=>setFilters({...filters,yMin:v})} onHi={v=>setFilters({...filters,yMax:v})} />
              {/* 空间群编号范围 */}
              <Box title={supported.has('space') ? undefined : '当前数据源不支持该筛选'} sx={{ opacity: supported.has('space') ? 1 : 0.45 }}>
                <FilterGroupLabel text="空间群编号" unit="#1–230" active={groupActive.space} disabled={!supported.has('space')} />
                <Box sx={shellSx}>
                  <Select variant="standard" disableUnderline disabled={!supported.has('space')} MenuProps={selectMenuProps}
                    value={filters.spaceMin} onChange={e=>setFilters({...filters,spaceMin:+e.target.value})} sx={selectSx}>
                    {[0,1,14,62,166,194,225].map(v=><MenuItem key={v} value={v}>{v === 0 ? '不限' : v}</MenuItem>)}
                  </Select>
                  <Typography sx={{ color:'text.disabled',px:0.25,userSelect:'none' }}>–</Typography>
                  <Select variant="standard" disableUnderline disabled={!supported.has('space')} MenuProps={selectMenuProps}
                    value={filters.spaceMax} onChange={e=>setFilters({...filters,spaceMax:+e.target.value})} sx={selectSx}>
                    {[14,62,166,194,225,230].map(v=><MenuItem key={v} value={v}>{v === 230 ? '不限' : v}</MenuItem>)}
                  </Select>
                </Box>
              </Box>
              <Box sx={{ height:'1px',bgcolor:'divider' }} />
              {/* 超导类型 */}
              <Box title={supported.has('type') ? undefined : '当前数据源不支持该筛选'} sx={{ opacity: supported.has('type') ? 1 : 0.45 }}>
                <FilterGroupLabel text="超导类型" active={groupActive.type} disabled={!supported.has('type')} />
                <Box sx={shellSx}>
                  <Select variant="standard" disableUnderline disabled={!supported.has('type')} MenuProps={selectMenuProps}
                    value={filters.type} onChange={e=>setFilters({...filters,type:e.target.value})} sx={selectSx}>
                    {/* 规范全称，与 backend/sc_types.py 一致 */}
                    {[
                      {v:'All',l:'全部类型'},{v:'hydride',l:'高压氢化物'},{v:'cuprate',l:'铜氧化物'},
                      {v:'iron_based',l:'铁基'},{v:'nickel_based',l:'镍基'},{v:'carbon',l:'碳基'},
                      {v:'organic',l:'有机'},{v:'others',l:'其他超导'},
                    ].map(o=><MenuItem key={o.v} value={o.v}>{o.l}</MenuItem>)}
                  </Select>
                </Box>
              </Box>
              {/* 审核状态 */}
              <Box title={supported.has('review') ? undefined : '当前数据源不支持该筛选'} sx={{ opacity: supported.has('review') ? 1 : 0.45 }}>
                <FilterGroupLabel text="审核状态" active={groupActive.review} disabled={!supported.has('review')} />
                <Box sx={shellSx}>
                  <Select variant="standard" disableUnderline disabled={!supported.has('review')} MenuProps={selectMenuProps}
                    value={filters.review} onChange={e=>setFilters({...filters,review:e.target.value})} sx={selectSx}>
                    {[
                      {v:'All',l:'全部状态'},{v:'Approved',l:'已通过 Approved'},{v:'Pending',l:'待审核 Pending'},
                      {v:'Rejected',l:'已驳回 Rejected'},{v:'External',l:'外部数据 External'},
                    ].map(o=><MenuItem key={o.v} value={o.v}>{o.l}</MenuItem>)}
                  </Select>
                </Box>
              </Box>
              {/* 图表记录开关 */}
              <Box component="button" disabled={!supported.has('chart')}
                title={supported.has('chart') ? undefined : '当前数据源不支持该筛选'}
                onClick={()=>setFilters({...filters,chartOnly:!filters.chartOnly})}
                sx={{ minHeight:32,px:1.5,borderRadius:'999px',display:'inline-flex',alignItems:'center',gap:0.75,border:'1px solid',borderColor:filters.chartOnly?'primary.main':'divider',bgcolor:filters.chartOnly?'#e0e7ff':'grey.50',color:filters.chartOnly?'#312e81':'text.primary',fontSize:12,fontWeight:700,cursor:'pointer',justifySelf:'start',opacity:supported.has('chart')?1:0.45,transition:'all .15s ease' }}>
                <Box sx={{ width:8,height:8,borderRadius:'50%',bgcolor:filters.chartOnly?'primary.main':'text.disabled' }} />
                仅看图表记录
              </Box>
            </Box>
          </Box>

          {/* Data table */}
          <Card sx={{ position:'relative' }}>
            <CardContent>
              <Typography variant="h2" gutterBottom>结果表格</Typography>
              {loading && <LinearProgress sx={{ mb: 2, borderRadius: 999, height: 4 }} />}
              {apiError && (
                <Box sx={{ display:'flex',alignItems:'center',justifyContent:'space-between',gap:1.5,mb:1.5,p:1.5,border:'1px solid',borderColor:'divider',borderRadius:2,bgcolor:'grey.50' }}>
                  <Typography variant="body2" color="error">{apiError}</Typography>
                  <Button size="small" variant="text" onClick={() => setRetryTick(t => t + 1)}>重试</Button>
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
                        onClick={()=>{setSelectedRecord(r);setStage('detail')}}
                        sx={{ cursor:'pointer','&:hover':{bgcolor:'grey.50'} }}>
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
                        <Button variant="contained" sx={{ mt:2 }} onClick={()=>setFilters({ ...FILTER_DEFAULTS })}>重置筛选</Button>
                      </Box></Box>
                    )}
                  </Box>
                </Box>
              </Box>
              {totalPages > 1 && (
                <Box sx={{ display:'flex',alignItems:'center',justifyContent:'center',gap:2,mt:2 }}>
                  <Button size="small" variant="outlined" disabled={page===0} onClick={()=>setPage(p=>p-1)}>上一页</Button>
                  <Typography variant="body2" color="text.secondary">
                    第 {page+1}/{totalPages} 页，共 {total} 条
                  </Typography>
                  <Button size="small" variant="outlined" disabled={page+1>=totalPages} onClick={()=>setPage(p=>p+1)}>下一页</Button>
                </Box>
              )}
            </CardContent>
          </Card>

          {/* Detail preview side sheet */}
        </Box>
        <Snackbar open={!!snackbar} autoHideDuration={2200} onClose={()=>setSnackbar('')}><Alert severity="success" variant="filled">{snackbar}</Alert></Snackbar>
      </Box>
    )
  }

  /* ── Stage 3: Detail（按数据源分派不同 Layer 3）── */
  if (selectedRecord.sourceSystem === 'alexandria') {
    return <AlexandriaDetail matId={selectedRecord.sourceRecordId} formula={selectedRecord.formula} onBack={()=>setStage('results')} />
  }
  if (selectedRecord.sourceSystem === 'htsc2025') {
    return <HtscDetail name={selectedRecord.sourceRecordId} formula={selectedRecord.formula} onBack={()=>setStage('results')} />
  }
  const r = selectedRecord
  // Tc 与计算参数不在 key_properties 里，须跨三张来源表汇总（见 lib/paperDetailView）
  const propertyRows = collectPropertyRows(paperDetail)
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
                  {/* summary 常含分条结构的真实换行，pre-wrap 须保留；否则多条记录会被挤成一段 */}
                  {paperDetail?.summary && (
                    <Box sx={{ gridColumn:'1/-1' }}><Typography variant="caption">论文总结</Typography><Typography variant="body2" sx={{ lineHeight:1.8,whiteSpace:'pre-wrap' }}>{paperDetail.summary}</Typography></Box>
                  )}
                  <Box><Typography variant="caption">审核状态</Typography><Chip label={r.status} size="small" color={r.status==='Approved'?'success':'warning'} /></Box>
                  <Box><Typography variant="caption">数据来源</Typography><Chip label={r.source} size="small" color="primary" /></Box>
                </Box>
              </Box>
            </Box>
            {/* 关键物性：Tc（tc_results）+ 计算参数（calculation_contexts）+ 普通物性（key_properties）*/}
            <Box component="details" open sx={{ border:'1px solid',borderColor:'divider',borderRadius:2,mb:1.5,overflow:'hidden' }}>
              <Box component="summary" sx={{ cursor:'pointer',p:2,fontSize:18,fontWeight:800 }}>关键物性</Box>
              <Box sx={{ px:2,pb:2,borderTop:'1px solid',borderColor:'divider',overflowX:'auto' }}>
                {propertyRows.length > 0 ? (
                  <Box component="table" sx={{ width:'100%',borderCollapse:'collapse',fontSize:13,mt:1 }}>
                    <Box component="thead">
                      <Box component="tr">
                        {['材料','物性','数值','条件','备注'].map(h=>(
                          <Box key={h} component="th" sx={{ p:'6px 10px',borderBottom:'2px solid',borderColor:'divider',textAlign:'left',color:'text.secondary',fontSize:12,whiteSpace:'nowrap' }}>{h}</Box>
                        ))}
                      </Box>
                    </Box>
                    <Box component="tbody">
                      {propertyRows.map(row => (
                        <Box component="tr" key={row.key}>
                          <Box component="td" sx={{ p:'6px 10px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap',fontWeight:600 }}>{row.material}</Box>
                          <Box component="td" sx={{ p:'6px 10px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap' }}>{row.label}</Box>
                          <Box component="td" sx={{ p:'6px 10px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap',fontWeight:700,color:'primary.main' }}>{row.value}</Box>
                          <Box component="td" sx={{ p:'6px 10px',borderBottom:'1px solid',borderColor:'divider',whiteSpace:'nowrap',color:'text.secondary' }}>{row.condition}</Box>
                          <Box component="td" sx={{ p:'6px 10px',borderBottom:'1px solid',borderColor:'divider',color:'text.secondary',minWidth:180 }}>{row.note}</Box>
                        </Box>
                      ))}
                    </Box>
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary" sx={{ mt:1 }}>{paperDetail ? '该论文暂无结构化物性数据' : '加载中…'}</Typography>
                )}
              </Box>
            </Box>
            {/* 研究方法与发现（clean_results 结构化成果）*/}
            <Box component="details" sx={{ border:'1px solid',borderColor:'divider',borderRadius:2,mb:1.5,overflow:'hidden' }}>
              <Box component="summary" sx={{ cursor:'pointer',p:2,fontSize:18,fontWeight:800 }}>研究方法与发现</Box>
              <Box sx={{ px:2,pb:2,borderTop:'1px solid',borderColor:'divider' }}>
                <Box sx={{ display:'grid',gap:1.5,mt:1 }}>
                  <Box>
                    <Typography variant="caption">研究方法</Typography>
                    <Box sx={{ display:'flex',gap:0.75,flexWrap:'wrap',mt:0.5 }}>
                      {(() => { try { const m = JSON.parse(paperDetail?.methodology || '[]'); return Array.isArray(m) && m.length ? m.map((x: string) => <Chip key={x} label={x} size="small" variant="outlined" />) : <Typography fontWeight={600}>-</Typography> } catch { return <Typography fontWeight={600}>{paperDetail?.methodology || '-'}</Typography> } })()}
                    </Box>
                  </Box>
                  <Box>
                    <Typography variant="caption">核心发现</Typography>
                    <Typography fontWeight={600} sx={{ lineHeight:1.8 }}>
                      {(() => { try { return JSON.parse(paperDetail?.key_finding || '""') || '-' } catch { return paperDetail?.key_finding || '-' } })()}
                    </Typography>
                  </Box>
                </Box>
              </Box>
            </Box>
          </CardContent>
        </Card>

        {/* Structure preview */}
        <Card sx={{ alignSelf:'start',position:'sticky',top:96,boxShadow:'0 6px 16px rgba(15,23,42,.16),0 10px 24px rgba(15,23,42,.10)' }}>
          <CardContent>
            <Typography variant="h2" gutterBottom>结构预览</Typography>
            {structureData && Array.isArray(structureData) && structureData.length > 0 ? (
              <Box>
                {structureData.map((s: any, i: number) => (
                  <Box key={i} sx={{ mb: i < structureData.length - 1 ? 2.5 : 0 }}>
                    {s.name_note && (
                      <Typography variant="body2" fontWeight={700} sx={{ mb:0.5 }}>
                        {s.material} · {s.name_note}{s.pressure_gpa != null ? ` @ ${s.pressure_gpa} GPa` : ''}
                      </Typography>
                    )}
                    <Typography variant="body2" color="text.secondary" sx={{ mb:1 }}>
                      格式 {s.structure_format || 'cif'} · 拖拽旋转 · 滚轮缩放
                    </Typography>
                    <StructureViewer3D
                      data={s.structure_text}
                      format={viewerFormat(s.structure_format)}
                      height={240}
                    />
                    <Box component="details" sx={{ mt:1 }}>
                      <Box component="summary" sx={{ cursor:'pointer',fontSize:12,fontWeight:700,color:'text.secondary' }}>查看结构文本</Box>
                      <Box component="pre" sx={{ mt:1,p:1.5,borderRadius:2,bgcolor:'grey.50',maxHeight:200,overflow:'auto',fontFamily:'"Roboto Mono",monospace',fontSize:11 }}>
                        {s.structure_text.slice(0, 1500)}
                      </Box>
                    </Box>
                  </Box>
                ))}
              </Box>
            ) : (
              <Box sx={{ minHeight:240,borderRadius:2,border:'1px solid',borderColor:'divider',
                background:`radial-gradient(circle at 22% 28%, #4f46e5 0 9px, transparent 10px), radial-gradient(circle at 66% 34%, #0891b2 0 9px, transparent 10px), radial-gradient(circle at 42% 70%, #4f46e5 0 9px, transparent 10px), linear-gradient(145deg, #fff, #f1f5f9)`,
                position:'relative',overflow:'hidden',
                '&::before,&::after':{content:'""',position:'absolute',left:'25%',right:'25%',top:'34%',height:2,bgcolor:'#cbd5e1',transform:'rotate(18deg)'},
                '&::after':{top:'58%',transform:'rotate(-25deg)'},
              }}>
                <Typography variant="body2" sx={{ position:'absolute',bottom:12,left:12,color:'text.secondary' }}>
                  {structureMsg}
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
