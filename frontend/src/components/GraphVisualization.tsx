import { useEffect, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Evidence } from '@/lib/api';

interface GraphVisualizationProps {
  evidence: Evidence[];
}

interface GraphNode {
  id: string;
  label: string;
  type: 'entity';
}

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  confidence: number;
}

function parseGraphPath(snippet: string): {
  nodes: GraphNode[];
  edges: GraphEdge[];
} {
  // Parse "Path: entity1 -> relation -> entity2 -> relation -> entity3... (Confidence: 0.85)"
  const pathMatch = snippet.match(/Path: (.+?)\.\.\. \(Confidence: ([\d.]+)\)/);
  if (!pathMatch) return { nodes: [], edges: [] };

  const pathStr = pathMatch[1];
  const confidence = parseFloat(pathMatch[2]);

  const parts = pathStr.split(' -> ').map((p) => p.trim());

  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];
  const nodeSet = new Set<string>();

  for (let i = 0; i < parts.length; i++) {
    if (i % 2 === 0) {
      // Entity
      const entity = parts[i];
      if (!nodeSet.has(entity)) {
        nodes.push({ id: entity, label: entity, type: 'entity' });
        nodeSet.add(entity);
      }

      // Create edge to next entity
      if (i + 2 < parts.length) {
        const relation = parts[i + 1];
        const target = parts[i + 2];
        edges.push({
          id: `${entity}-${relation}-${target}`,
          source: entity,
          target: target,
          label: relation,
          confidence: confidence,
        });
      }
    }
  }

  return { nodes, edges };
}

function mergeGraphData(evidence: Evidence[]): {
  nodes: GraphNode[];
  edges: GraphEdge[];
} {
  const allNodes = new Map<string, GraphNode>();
  const allEdges = new Map<string, GraphEdge>();

  evidence.forEach((ev) => {
    const { nodes, edges } = parseGraphPath(ev.snippet);

    nodes.forEach((node) => {
      if (!allNodes.has(node.id)) {
        allNodes.set(node.id, node);
      }
    });

    edges.forEach((edge) => {
      const edgeKey = `${edge.source}-${edge.target}`;
      if (
        !allEdges.has(edgeKey) ||
        allEdges.get(edgeKey)!.confidence < edge.confidence
      ) {
        allEdges.set(edgeKey, edge);
      }
    });
  });

  return {
    nodes: Array.from(allNodes.values()),
    edges: Array.from(allEdges.values()),
  };
}

export default function GraphVisualization({
  evidence,
}: GraphVisualizationProps) {
  const { nodes: graphNodes, edges: graphEdges } = useMemo(
    () => mergeGraphData(evidence),
    [evidence],
  );

  // Convert to ReactFlow format
  const initialNodes: Node[] = useMemo(() => {
    const centerX = 400;
    const centerY = 300;
    const radius = 200;

    return graphNodes.map((node, index) => {
      const angle = (index / graphNodes.length) * 2 * Math.PI;
      const x = centerX + radius * Math.cos(angle);
      const y = centerY + radius * Math.sin(angle);

      return {
        id: node.id,
        type: 'default',
        data: { label: node.label },
        position: { x, y },
        style: {
          background: '#3b82f6',
          color: 'white',
          border: '2px solid #1e40af',
          borderRadius: '8px',
          padding: '10px 20px',
          fontSize: '14px',
          fontWeight: 600,
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        },
      };
    });
  }, [graphNodes]);

  const initialEdges: Edge[] = useMemo(() => {
    return graphEdges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      label: edge.label,
      type: 'default',
      animated: true,
      style: {
        stroke: '#94a3b8',
        strokeWidth: 2,
      },
      labelStyle: {
        fill: '#64748b',
        fontSize: 12,
        fontWeight: 600,
      },
      labelBgStyle: {
        fill: '#f1f5f9',
      },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#94a3b8',
      },
    }));
  }, [graphEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  if (graphNodes.length === 0) {
    return (
      <div className='flex items-center justify-center h-96 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300'>
        <div className='text-center'>
          <div className='text-gray-400 mb-2'>
            <svg
              className='mx-auto h-12 w-12'
              fill='none'
              viewBox='0 0 24 24'
              stroke='currentColor'
            >
              <path
                strokeLinecap='round'
                strokeLinejoin='round'
                strokeWidth={2}
                d='M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7'
              />
            </svg>
          </div>
          <p className='text-gray-500 font-medium'>No graph data available</p>
          <p className='text-gray-400 text-sm mt-1'>
            Try asking a question that returns graph evidence
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className='h-96 bg-gray-50 rounded-lg border border-gray-200 overflow-hidden'>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        attributionPosition='bottom-left'
      >
        <Background color='#e2e8f0' gap={16} />
        <Controls />
        <MiniMap
          nodeColor='#3b82f6'
          maskColor='rgba(0, 0, 0, 0.1)'
          style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
          }}
        />
      </ReactFlow>
    </div>
  );
}
