/**
 * components/SpanTree.jsx — Renders the span tree as an interactive graph.
 *
 * Uses @xyflow/react (React Flow) to render nodes and edges.
 * Converts the nested span tree from the API into a flat list of
 * nodes + edges that React Flow understands.
 *
 * Layout: simple top-down tree with manual x/y positioning.
 * Each level of the tree is a new row; siblings are spread horizontally.
 */

import { useCallback, useMemo } from 'react'
import { ReactFlow, Background, Controls, MiniMap, useNodesState, useEdgesState } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import SpanNode from './SpanNode'

const NODE_WIDTH  = 220
const NODE_HEIGHT = 100
const H_GAP = 40
const V_GAP = 80

const nodeTypes = { spanNode: SpanNode }

/** Recursively flatten the nested span tree into nodes + edges */
function flattenTree(spans, parentId = null, depth = 0, siblings = { count: 0 }) {
  const nodes = []
  const edges = []

  spans.forEach((span, i) => {
    const x = siblings.count * (NODE_WIDTH + H_GAP)
    const y = depth * (NODE_HEIGHT + V_GAP)
    siblings.count++

    nodes.push({
      id: span.span_id,
      type: 'spanNode',
      position: { x, y },
      data: { ...span },
    })

    if (parentId) {
      edges.push({
        id: `${parentId}->${span.span_id}`,
        source: parentId,
        target: span.span_id,
        animated: false,
      })
    }

    if (span.children?.length) {
      const { nodes: cn, edges: ce } = flattenTree(span.children, span.span_id, depth + 1, siblings)
      nodes.push(...cn)
      edges.push(...ce)
    }
  })

  return { nodes, edges }
}

export default function SpanTree({ spans, onNodeClick }) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => flattenTree(spans),
    [spans]
  )

  const [nodes, , onNodesChange] = useNodesState(initialNodes)
  const [edges, , onEdgesChange] = useEdgesState(initialEdges)

  const handleNodeClick = useCallback((_, node) => {
    onNodeClick?.(node.data)
  }, [onNodeClick])

  return (
    <div style={{ height: 500, background: '#0a0e1a', borderRadius: 12, border: '1px solid #2a3a55' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.3}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#2a3a55" gap={24} size={1} />
        <Controls style={{ background: '#1a2235', border: '1px solid #2a3a55' }} />
        <MiniMap
          nodeColor={(n) => {
            const colors = { orchestrator: '#3b82f6', researcher: '#8b5cf6', writer: '#10b981', critic: '#f59e0b' }
            return colors[n.data?.agent_name] || '#6b7280'
          }}
          style={{ background: '#1a2235', border: '1px solid #2a3a55' }}
        />
      </ReactFlow>
    </div>
  )
}