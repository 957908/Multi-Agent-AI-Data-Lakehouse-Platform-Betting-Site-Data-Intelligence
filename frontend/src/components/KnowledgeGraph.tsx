import React, { useState, useMemo } from 'react';
import { Network, Database, ShieldAlert, Cpu, Layers } from 'lucide-react';
import { Transaction } from '../services/api';

interface KnowledgeGraphProps {
  transactions: Transaction[];
}

interface GraphNode {
  id: string;
  label: string;
  type: 'platform' | 'method' | 'account';
  val: number; // weight/volume
  extra?: any;
}

interface GraphLink {
  source: string;
  target: string;
}

export default function KnowledgeGraph({ transactions }: KnowledgeGraphProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // 1. Process real database transactions to extract unique entities and relationships
  const graphData = useMemo(() => {
    const nodesMap = new Map<string, GraphNode>();
    const links: GraphLink[] = [];
    
    // Track volumes and counts dynamically
    const platformStats: Record<string, { vol: number; count: number; methods: Set<string> }> = {};
    const methodStats: Record<string, { vol: number; count: number; accounts: Set<string> }> = {};
    const accountStats: Record<string, { vol: number; count: number; platforms: Set<string>; isAnomalous: boolean }> = {};

    transactions.forEach(t => {
      const plat = t.platform_name || "Unknown Platform";
      const meth = t.method_name || t.type || "UPI";
      // Construct a realistic account identifier from transaction references
      const acct = t.user_id && t.user_id.length > 5 ? t.user_id : `ACC_${t.ref_number.slice(-4)}`;

      // Initialize stats
      if (!platformStats[plat]) platformStats[plat] = { vol: 0, count: 0, methods: new Set() };
      if (!methodStats[meth]) methodStats[meth] = { vol: 0, count: 0, accounts: new Set() };
      if (!accountStats[acct]) accountStats[acct] = { vol: 0, count: 0, platforms: new Set(), isAnomalous: false };

      // Update volumes
      platformStats[plat].vol += t.amount;
      platformStats[plat].count += 1;
      platformStats[plat].methods.add(meth);

      methodStats[meth].vol += t.amount;
      methodStats[meth].count += 1;
      methodStats[meth].accounts.add(acct);

      accountStats[acct].vol += t.amount;
      accountStats[acct].count += 1;
      accountStats[acct].platforms.add(plat);
      if (t.is_anomalous) {
        accountStats[acct].isAnomalous = true;
      }

      // Add links
      links.push({ source: plat, target: meth });
      links.push({ source: meth, target: acct });
    });

    // Create unique platform nodes
    Object.entries(platformStats).forEach(([plat, stats]) => {
      nodesMap.set(plat, {
        id: plat,
        label: plat,
        type: 'platform',
        val: stats.vol,
        extra: { count: stats.count, connections: Array.from(stats.methods) }
      });
    });

    // Create unique payment method nodes
    Object.entries(methodStats).forEach(([meth, stats]) => {
      nodesMap.set(meth, {
        id: meth,
        label: meth,
        type: 'method',
        val: stats.vol,
        extra: { count: stats.count, connections: Array.from(stats.accounts) }
      });
    });

    // Create unique account nodes
    Object.entries(accountStats).forEach(([acct, stats]) => {
      nodesMap.set(acct, {
        id: acct,
        label: acct.startsWith("USR_") ? `UPI: ${acct.slice(4)}@pay` : `Bank: ${acct}`,
        type: 'account',
        val: stats.vol,
        extra: { count: stats.count, connections: Array.from(stats.platforms), isAnomalous: stats.isAnomalous }
      });
    });

    // Deduplicate links
    const uniqueLinks: GraphLink[] = [];
    const linkKeys = new Set<string>();
    links.forEach(l => {
      const key = `${l.source}->${l.target}`;
      if (!linkKeys.has(key)) {
        linkKeys.add(key);
        uniqueLinks.push(l);
      }
    });

    return {
      nodes: Array.from(nodesMap.values()),
      links: uniqueLinks
    };
  }, [transactions]);

  // Determine positions for a layered flow diagram
  // Columns: Left (Platforms), Middle (Methods), Right (Accounts)
  const layoutNodes = useMemo(() => {
    const platforms = graphData.nodes.filter(n => n.type === 'platform');
    const methods = graphData.nodes.filter(n => n.type === 'method').slice(0, 8); // cap to keep clean
    const accounts = graphData.nodes.filter(n => n.type === 'account').slice(0, 10); // cap to keep clean

    const width = 700;
    const height = 400;

    const positioned: (GraphNode & { x: number; y: number })[] = [];

    platforms.forEach((node, i) => {
      positioned.push({
        ...node,
        x: 60,
        y: height * ((i + 1.2) / (platforms.length + 1.5))
      });
    });

    methods.forEach((node, i) => {
      positioned.push({
        ...node,
        x: width / 2,
        y: height * ((i + 0.8) / (methods.length + 0.8))
      });
    });

    accounts.forEach((node, i) => {
      positioned.push({
        ...node,
        x: width - 80,
        y: height * ((i + 0.6) / (accounts.length + 0.5))
      });
    });

    return positioned;
  }, [graphData]);

  // Map positioned nodes by ID for link path coordinates
  const nodesLookup = useMemo(() => {
    const lookup: Record<string, { x: number; y: number; type: string; id: string }> = {};
    layoutNodes.forEach(n => {
      lookup[n.id] = { x: n.x, y: n.y, type: n.type, id: n.id };
    });
    return lookup;
  }, [layoutNodes]);

  // Filter links where both source and target nodes are actively layout-positioned
  const layoutLinks = useMemo(() => {
    return graphData.links.filter(l => nodesLookup[l.source] && nodesLookup[l.target]);
  }, [graphData, nodesLookup]);

  // Determine if a node/link is highlighted during hovers
  const isNodeHighlighted = (nodeId: string) => {
    if (!hoveredNode) return true;
    if (hoveredNode === nodeId) return true;
    
    // Highlight if connected
    return graphData.links.some(l => 
      (l.source === hoveredNode && l.target === nodeId) || 
      (l.target === hoveredNode && l.source === nodeId)
    );
  };

  const isLinkHighlighted = (link: GraphLink) => {
    if (!hoveredNode) return true;
    return link.source === hoveredNode || link.target === hoveredNode;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* LEFT 3 COLUMNS: The Graph visual canvas */}
      <div className="lg:col-span-3 glass-panel p-6 rounded-2xl border border-white/5 bg-slate-900/30 flex flex-col h-[520px]">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-red-600/10 rounded-xl border border-red-500/20 text-red-500">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold font-outfit text-white">Payment Channel Relational Graph</h3>
              <p className="text-xs text-slate-400">Tracing deposit wallets and bank accounts shared across platform bounds</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-[10px] text-slate-400 font-mono">
            <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-cyan-400" /> Platform</div>
            <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-purple-400" /> Channel</div>
            <div className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400" /> Account</div>
          </div>
        </div>

        {/* SVG Drawing Area */}
        <div className="flex-1 bg-black/40 border border-white/5 rounded-2xl relative overflow-hidden flex items-center justify-center p-4">
          <svg className="w-full h-full max-w-[700px] max-h-[400px]" viewBox="0 0 700 400">
            {/* Draw Links/Edges */}
            <g>
              {layoutLinks.map((link, idx) => {
                const s = nodesLookup[link.source];
                const t = nodesLookup[link.target];
                const active = isLinkHighlighted(link);
                
                // Draw curve connection path
                const dx = t.x - s.x;
                const dy = t.y - s.y;
                const pathStr = `M ${s.x} ${s.y} C ${s.x + dx/2} ${s.y}, ${s.x + dx/2} ${t.y}, ${t.x} ${t.y}`;
                
                return (
                  <path
                    key={idx}
                    d={pathStr}
                    fill="none"
                    stroke={active ? 'url(#activeGrad)' : 'rgba(255, 255, 255, 0.05)'}
                    strokeWidth={active ? 1.5 : 1}
                    className="transition-all duration-300"
                  />
                );
              })}
            </g>

            {/* SVG Gradients definitions */}
            <defs>
              <linearGradient id="activeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#22d3ee" stopOpacity="0.4" />
                <stop offset="50%" stopColor="#a855f7" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#34d399" stopOpacity="0.4" />
              </linearGradient>
            </defs>

            {/* Draw Nodes */}
            <g>
              {layoutNodes.map((node) => {
                const isHovered = hoveredNode === node.id;
                const active = isNodeHighlighted(node.id);
                
                let ringColor = 'border-slate-800';
                let dotColor = 'bg-slate-400';
                if (node.type === 'platform') {
                  ringColor = isHovered ? 'stroke-cyan-400 shadow-[0_0_15px_#22d3ee]' : 'stroke-cyan-500/30';
                  dotColor = '#06b6d4';
                } else if (node.type === 'method') {
                  ringColor = isHovered ? 'stroke-purple-400 shadow-[0_0_15px_#a855f7]' : 'stroke-purple-500/30';
                  dotColor = '#a855f7';
                } else if (node.type === 'account') {
                  if (node.extra?.isAnomalous) {
                    ringColor = isHovered ? 'stroke-red-400' : 'stroke-red-500/40';
                    dotColor = '#f43f5e';
                  } else {
                    ringColor = isHovered ? 'stroke-emerald-400 shadow-[0_0_15px_#34d399]' : 'stroke-emerald-500/30';
                    dotColor = '#10b981';
                  }
                }

                return (
                  <g
                    key={node.id}
                    className="cursor-pointer"
                    onMouseEnter={() => setHoveredNode(node.id)}
                    onMouseLeave={() => setHoveredNode(null)}
                    onClick={() => setSelectedNode(node)}
                    style={{ opacity: active ? 1 : 0.15, transition: 'opacity 0.3s' }}
                  >
                    {/* Pulsing ring outer */}
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={isHovered ? 13 : 9}
                      className={`fill-none stroke-2 transition-all duration-300 ${ringColor}`}
                    />
                    {/* Inner core circle */}
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r={5}
                      fill={dotColor}
                    />
                    {/* Node text labels */}
                    <text
                      x={node.x}
                      y={node.y - 15}
                      textAnchor="middle"
                      fill={isHovered ? '#fff' : '#94a3b8'}
                      fontSize={isHovered ? '9.5px' : '8px'}
                      fontWeight={isHovered ? 'bold' : 'normal'}
                      className="transition-all duration-300 font-mono tracking-tight"
                    >
                      {node.label}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        </div>
      </div>

      {/* RIGHT COLUMN: Node Properties Detail Panel */}
      <div className="glass-panel p-6 rounded-2xl border border-white/5 bg-slate-900/30 flex flex-col h-[520px]">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-white/5 pb-2">
          Node Inspector
        </h4>

        {selectedNode ? (
          <div className="flex-1 flex flex-col justify-between">
            <div className="flex flex-col gap-4">
              <div className="flex items-center gap-3">
                <div className={`p-2.5 rounded-xl border ${
                  selectedNode.type === 'platform' 
                    ? 'bg-cyan-500/10 border-cyan-500/20 text-cyan-400' 
                    : selectedNode.type === 'method'
                    ? 'bg-purple-500/10 border-purple-500/20 text-purple-400'
                    : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                }`}>
                  {selectedNode.type === 'platform' ? <Layers className="w-5 h-5" /> : selectedNode.type === 'method' ? <Cpu className="w-5 h-5" /> : <Database className="w-5 h-5" />}
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white font-outfit truncate max-w-[130px]">{selectedNode.label}</h4>
                  <span className="text-[9px] font-mono uppercase text-slate-400 tracking-wider bg-white/5 px-1.5 py-0.5 rounded border border-white/5">
                    {selectedNode.type}
                  </span>
                </div>
              </div>

              {/* Volume details */}
              <div className="bg-black/30 border border-white/5 p-4 rounded-xl flex flex-col gap-1">
                <span className="text-[10px] text-slate-400 font-medium">Aggregated Inflow Volume</span>
                <span className="text-lg font-bold text-white">
                  {selectedNode.val.toLocaleString('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 })}
                </span>
              </div>

              {/* Connected relationships list */}
              <div className="flex flex-col gap-2">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Connected Relations ({selectedNode.extra?.connections?.length || 0})</span>
                <div className="flex flex-col gap-1.5 max-h-[160px] overflow-y-auto pr-1">
                  {selectedNode.extra?.connections?.map((conn: string, idx: number) => (
                    <div key={idx} className="bg-white/5 border border-white/5 px-2.5 py-1.5 rounded-lg text-[10px] font-mono text-slate-300 truncate">
                      {conn}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {selectedNode.extra?.isAnomalous && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-xl flex items-center gap-2 mt-4">
                <ShieldAlert className="w-4 h-4 text-red-400 shrink-0" />
                <span className="text-[10px] leading-snug">This node shares credentials associated with flagged anomalies!</span>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
            <Network className="w-8 h-8 text-slate-500 mb-3 animate-pulse" />
            <p className="text-xs text-slate-400 leading-normal">
              Hover over network nodes to trace active flows, and **click a node** to audit platform credentials, risk values, and volume allocations in detail.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
