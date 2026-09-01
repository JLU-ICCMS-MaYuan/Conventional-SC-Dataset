import React, { useEffect, useRef, useState, useCallback } from 'react'
import {
  Box, Typography, Paper, Chip, IconButton, Stack, CircularProgress,
  Divider, Link,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import OpenInNewIcon from '@mui/icons-material/OpenInNew'
import { DataSet } from 'vis-data'
import { Network } from 'vis-network'
import 'vis-network/styles/vis-network.css'
import { api } from '../lib/api'
import { useLanguage } from '../context/LanguageContext'

const TYPE_COLORS: Record<string, string> = {
  first_discovery: '#e53935',
  experimental_validation: '#43a047',
  theoretical_basis: '#1e88e5',
  correction_or_dispute: '#fb8c00',
  development_extension: '#8e24aa',
  material_system_extension: '#00acc1',
  same_research_direction: '#546e7a',
  supporting_evidence: '#78909c',
}

const RELATION_TYPES = Object.keys(TYPE_COLORS)

const KnowledgeGraphPage: React.FC = () => {
  const { t } = useLanguage()
  const relationLabel = useCallback((type: string) => t(`kg.relation.${type}`), [t])
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const nodesDs = useRef<DataSet<any>>(new DataSet([]))
  const edgesDs = useRef<DataSet<any>>(new DataSet([]))
  const expandedRef = useRef(false)  // 展开后锁定，空白点击不恢复

  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState<any>(null)
  const [selectedEdge, setSelectedEdge] = useState<any>(null)
  const [activeTypes, setActiveTypes] = useState<Set<string>>(new Set())
  const [paperDetail, setPaperDetail] = useState<any>(null)
  const [totalEdges, setTotalEdges] = useState(0)

  // BFS 找所有可达节点
  const getReachable = (startId: string): Set<string> => {
    const adj = new Map<string, Set<string>>()
    edgesDs.current.forEach((e: any) => {
      if (!adj.has(e.from)) adj.set(e.from, new Set())
      if (!adj.has(e.to)) adj.set(e.to, new Set())
      adj.get(e.from)!.add(e.to)
      adj.get(e.to)!.add(e.from)
    })
    const visited = new Set<string>()
    const queue = [startId]
    visited.add(startId)
    while (queue.length) {
      const cur = queue.shift()!
      for (const nb of adj.get(cur) || []) {
        if (!visited.has(nb)) { visited.add(nb); queue.push(nb) }
      }
    }
    return visited
  }

  const filterReachable = (centerId: string) => {
    const reachable = getReachable(centerId)
    nodesDs.current.forEach((n: any) => {
      nodesDs.current.update({ id: n.id, hidden: !reachable.has(n.id), opacity: 1.0 })
    })
  }

  const initNetwork = useCallback(() => {
    if (!containerRef.current) return
    const net = new Network(containerRef.current, { nodes: nodesDs.current, edges: edgesDs.current }, {
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: { gravitationalConstant: -35, centralGravity: 0.008, springLength: 160, springConstant: 0.06 },
        stabilization: { iterations: 150 },
      },
      edges: {
        arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        smooth: { enabled: true, type: 'continuous', roundness: 0.5 },
        font: { size: 9, color: '#666', strokeWidth: 2, align: 'top' as const },
      },
      nodes: {
        shape: 'dot',
        size: 14,
        font: { size: 11, color: '#222', strokeWidth: 2 },
        borderWidth: 2,
        shadow: { enabled: true, size: 6 },
      },
      interaction: { hover: true, tooltipDelay: 150, zoomView: true, dragView: true },
    })
    networkRef.current = net

    // 选中节点：1-hop 邻居透明，其他节点透明
    const highlightNeighbors = (nodeId: string) => {
      const direct = new Set<string>([nodeId])
      edgesDs.current.forEach((e: any) => {
        if (e.from === nodeId) direct.add(e.to)
        if (e.to === nodeId) direct.add(e.from)
      })
      nodesDs.current.forEach((n: any) => {
        nodesDs.current.update({ id: n.id, opacity: direct.has(n.id) ? 1.0 : 0.12 })
      })
    }
    const unhighlightAll = () => {
      if (expandedRef.current) return  // 展开后锁定，不可恢复
      nodesDs.current.forEach((n: any) => {
        nodesDs.current.update({ id: n.id, opacity: 1.0, hidden: false })
      })
    }

    net.on('click', (p: any) => {
      if (p.nodes.length) {
        const n = nodesDs.current.get(p.nodes[0]) as any
        setSelectedNode({ id: p.nodes[0], ...n })
        setSelectedEdge(null)
        highlightNeighbors(p.nodes[0])
        if (n.paper_id) {
          api.get<any>(`/api/papers/${n.paper_id}`).then(d => setPaperDetail(d)).catch(() => setPaperDetail(null))
        } else {
          setPaperDetail(null)
        }
      } else if (p.edges.length) {
        const e = edgesDs.current.get(p.edges[0]) as any
        setSelectedEdge(e)
        setSelectedNode(null)
        setPaperDetail(null)
      } else {
        setSelectedNode(null); setSelectedEdge(null); setPaperDetail(null)
        unhighlightAll()
      }
    })
    return net
  }, [])

  useEffect(() => {
    const net = initNetwork()
    return () => { net?.destroy() }
  }, [initNetwork])

  const rebuildGraph = useCallback((nodesArr: any[], edgesArr: any[]) => {
    nodesDs.current.clear(); edgesDs.current.clear()
    nodesDs.current.add(nodesArr)
    edgesDs.current.add(edgesArr)
  }, [])

  const loadOverview = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.get<any>('/api/knowledge-graph/overview?limit=30')
      setTotalEdges(data.total_edges || 0)
      const types = new Set<string>()
      const nodeItems = data.nodes.map((n: any) => {
        const hasPid = n.id.startsWith('paper_')
        return {
          id: n.id, label: (n.label || n.id).substring(0, 35),
          title: `<b>${n.label}</b>`,
          color: hasPid ? { background: '#1e88e5', border: '#1565c0', highlight: { background: '#42a5f5' } }
            : { background: '#90a4ae', border: '#607d8b' },
          size: hasPid ? 16 : 9,
          font: { size: hasPid ? 12 : 10 },
          paper_id: n.paper_id, match_method: n.match_method,
        }
      })
      const edgeItems = data.edges.map((e: any) => {
        types.add(e.type)
        return {
          id: `${e.source}_${e.target}_${e.type}`,
          from: e.source, to: e.target,
          label: relationLabel(e.type),
          title: `<b>${relationLabel(e.type)}</b><br>importance: ${e.importance?.toFixed(3)}`,
          color: { color: TYPE_COLORS[e.type] || '#999', opacity: 0.7 },
          width: Math.max(1.2, (e.importance || 0.5) * 3),
          type: e.type, importance: e.importance, evidence: e.evidence,
        }
      })
      rebuildGraph(nodeItems, edgeItems)
      setActiveTypes(types)
    } catch (e) { console.error(e) }
    setLoading(false)
  }, [rebuildGraph, relationLabel])

  useEffect(() => { loadOverview() }, [loadOverview])

  const expandNode = useCallback(async (nodeId: string) => {
    try {
      const data = await api.get<any>(`/api/knowledge-graph/papers/${encodeURIComponent(nodeId)}/neighbors?limit=10`)
      const existingIds = new Set(nodesDs.current.getIds())
      // 获取中心节点位置，新节点放在附近（避免 (0,0) 导致边不可见）
      const positions = networkRef.current?.getPositions([nodeId])
      const cx = positions?.[nodeId]?.x ?? 0
      const cy = positions?.[nodeId]?.y ?? 0
      for (const n of data.new_nodes || []) {
        if (!existingIds.has(n.id)) {
          const hasPid = n.id.startsWith('paper_')
          nodesDs.current.add({
            id: n.id, label: (n.label || n.id).substring(0, 35),
            title: `<b>${n.label}</b>`,
            color: hasPid ? { background: '#43a047', border: '#2e7d32', highlight: { background: '#66bb6a' } }
              : { background: '#90a4ae', border: '#607d8b' },
            size: hasPid ? 14 : 8,
            font: { size: hasPid ? 11 : 9 },
            x: cx + (Math.random() - 0.5) * 300,
            y: cy + (Math.random() - 0.5) * 300,
            paper_id: n.paper_id,
          })
        }
      }
      for (const e of data.new_edges || []) {
        const eid = `${e.source}_${e.target}_${e.type}`
        const existingEdge = edgesDs.current.get(eid)
        if (!existingEdge) {
          edgesDs.current.add({
            id: eid, from: e.source, to: e.target,
            label: relationLabel(e.type),
            color: { color: TYPE_COLORS[e.type] || '#999', opacity: 0.7 },
            width: Math.max(1.2, (e.importance || 0.5) * 3),
            type: e.type, importance: e.importance, evidence: e.evidence,
          })
        }
      }
      // highlight center + BFS: 可达节点显示，其余消失，锁定不可恢复
      nodesDs.current.update({ id: nodeId, borderWidth: 3, color: { background: '#ff9800', border: '#e65100' } })
      expandedRef.current = true
      filterReachable(nodeId)
    } catch (e) { console.error(e) }
  }, [relationLabel])

  const toggleType = (t: string) => {
    const next = new Set(activeTypes)
    next.has(t) ? next.delete(t) : next.add(t)
    setActiveTypes(next)
    edgesDs.current.forEach((e: any) => {
      edgesDs.current.update({ id: e.id, hidden: !next.has(e.type) })
    })
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)', px: 3, py: 2, gap: 2 }}>
      {/* Header */}
      <Box>
        <Typography variant="overline" color="text.secondary">Knowledge Graph</Typography>
        <Typography variant="h5" fontWeight={700}>{t('kg.title')}</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {t('kg.description')}
          {totalEdges > 0 && t('kg.relationCount', { count: totalEdges })}
        </Typography>
      </Box>

      {/* Main: Graph + Side Sheet */}
      <Box sx={{ flex: 1, display: 'flex', gap: 2, minHeight: 0 }}>
        {/* Graph Card */}
        <Paper elevation={1} sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, position: 'relative' }}>
          {/* Filter bar */}
          <Box sx={{ p: 1.5, pb: 0 }}>
            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
              {RELATION_TYPES.map(key => (
                <Chip key={key} label={relationLabel(key)} size="small"
                  variant={activeTypes.has(key) ? 'filled' : 'outlined'}
                  sx={{
                    bgcolor: activeTypes.has(key) ? TYPE_COLORS[key] : undefined,
                    color: activeTypes.has(key) ? '#fff' : undefined,
                    mb: 0.5,
                  }}
                  onClick={() => toggleType(key)}
                />
              ))}
            </Stack>
          </Box>
          {loading && (
            <CircularProgress size={20} sx={{ position: 'absolute', top: 60, left: '50%', zIndex: 10 }} />
          )}
          <Box ref={containerRef} sx={{ flex: 1, minHeight: 300 }} />
        </Paper>

        {/* Side Sheet */}
        <Paper elevation={3} sx={{ width: 340, p: 2.5, overflow: 'auto', flexShrink: 0 }}>
          {!selectedNode && !selectedEdge && (
            <>
              <Typography variant="subtitle1" fontWeight={600}>{t('kg.selectHint')}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {t('kg.selectDescription')}
              </Typography>
            </>
          )}

          {selectedNode && (
            <>
              <Typography variant="overline" color="text.secondary">{t('kg.selectedPaper')}</Typography>
              <Typography variant="subtitle2" fontWeight={600} sx={{ mt: 0.5 }}>
                {selectedNode.label}
              </Typography>
              {selectedNode.paper_id && (
                <Chip label={`paper_${selectedNode.paper_id}`} size="small" sx={{ mt: 1 }} />
              )}

              {/* Paper detail from API */}
              {paperDetail && (
                <Stack spacing={0.5} sx={{ mt: 1.5 }}>
                  {paperDetail.year && <Typography variant="caption">{t('kg.year', { value: paperDetail.year })}</Typography>}
                  {paperDetail.journal && <Typography variant="caption">{t('kg.journal', { value: paperDetail.journal })}</Typography>}
                  {paperDetail.doi && (
                    <Link href={`https://doi.org/${paperDetail.doi}`} target="_blank" variant="caption"
                      sx={{ display: 'flex', alignItems: 'center', gap: 0.3 }}>
                      DOI: {paperDetail.doi} <OpenInNewIcon sx={{ fontSize: 12 }} />
                    </Link>
                  )}
                  {paperDetail.authors && (
                    <Typography variant="caption">
                      {t('kg.authors', { value: Array.isArray(paperDetail.authors) ? paperDetail.authors.slice(0, 3).join(', ') : paperDetail.authors })}
                    </Typography>
                  )}
                </Stack>
              )}

              <Divider sx={{ my: 1.5 }} />
              <Typography variant="caption" fontWeight={600}>{t('kg.actions')}</Typography>
              <Box sx={{ mt: 0.5 }}>
                <Chip icon={<ExpandMoreIcon />} label={t('kg.expand')} color="primary" size="small"
                  onClick={() => expandNode(selectedNode.id)} />
              </Box>
            </>
          )}

          {selectedEdge && (
            <>
              <Typography variant="overline" color="text.secondary">{t('kg.relationDetail')}</Typography>
              <Chip label={relationLabel(selectedEdge.type)} size="small"
                sx={{ mt: 1, bgcolor: TYPE_COLORS[selectedEdge.type] || '#999', color: '#fff' }} />
              <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                importance: {selectedEdge.importance?.toFixed(3)}
              </Typography>
              <Typography variant="caption" display="block">
                {selectedEdge.from} → {selectedEdge.to}
              </Typography>

              {selectedEdge.evidence && (
                <Paper variant="outlined" sx={{ mt: 2, p: 1.5, bgcolor: '#fafafa' }}>
                  <Typography variant="caption" color="text.secondary" fontWeight={600}>{t('kg.evidence')}</Typography>
                  <Typography variant="body2" sx={{ mt: 0.5, fontSize: 12 }}>
                    {selectedEdge.evidence}
                  </Typography>
                </Paper>
              )}
            </>
          )}
        </Paper>
      </Box>
    </Box>
  )
}

export default KnowledgeGraphPage
