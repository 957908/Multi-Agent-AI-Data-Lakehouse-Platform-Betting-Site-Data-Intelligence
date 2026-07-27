import React, { useState, useEffect } from 'react';
import { Server, Activity, ShieldAlert } from 'lucide-react';
import { apiService } from '../services/api';

export default function StreamingStatus() {
  const [ragStatus, setRagStatus] = useState<string>("UNKNOWN");
  const [vectorCount, setVectorCount] = useState<number>(0);
  const [agentStatus, setAgentStatus] = useState<string>("IDLE");

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const rag = await apiService.getRAGHealth();
        setRagStatus(rag.healthy ? "HEALTHY" : "UNHEALTHY");
        
        const stats = await apiService.getVectorStats();
        setVectorCount(stats.total_vectors);
        
        const agent = await apiService.getAgentsStatus();
        setAgentStatus(agent.status);
      } catch (e) {
        setRagStatus("OFFLINE");
      }
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <div className="glass-panel p-6 rounded-2xl flex items-center gap-4">
        <Server className="w-8 h-8 text-cyan-accent" />
        <div>
          <h4 className="text-sm font-semibold text-gray-400">RAG Engine Health</h4>
          <span className={`text-base font-bold ${ragStatus === "HEALTHY" ? "text-cyan-accent" : "text-red-500"}`}>{ragStatus}</span>
        </div>
      </div>
      <div className="glass-panel p-6 rounded-2xl flex items-center gap-4">
        <Activity className="w-8 h-8 text-purple-accent" />
        <div>
          <h4 className="text-sm font-semibold text-gray-400">Vector Index Size</h4>
          <span className="text-base font-bold text-white">{vectorCount} Embeddings</span>
        </div>
      </div>
      <div className="glass-panel p-6 rounded-2xl flex items-center gap-4">
        <ShieldAlert className="w-8 h-8 text-yellow-500" />
        <div>
          <h4 className="text-sm font-semibold text-gray-400">Coordinator Agent</h4>
          <span className={`text-base font-bold ${agentStatus === "RUNNING" ? "text-yellow-500" : "text-gray-300"}`}>{agentStatus}</span>
        </div>
      </div>
    </div>
  );
}
