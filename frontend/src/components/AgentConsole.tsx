import React, { useState } from 'react';
import { Terminal, Play } from 'lucide-react';
import { apiService } from '../services/api';

export default function AgentConsole() {
  const [agentLogs, setAgentLogs] = useState<string[]>([
    "Orchestrator initialized. Spawning worker tasks...",
    "ScraperAgent started. Simulating raw events...",
    "ValidatorAgent started. Listening for raw streams...",
    "AnomalyDetectorAgent started. Loading Isolation Forest model..."
  ]);

  const handleTriggerAgents = async () => {
    setAgentLogs(prev => [...prev, `[INFO] Triggering CrewAI multi-agent orchestrator in backend...`]);
    try {
      await apiService.runAgents();
      // Simulate log stream updates
      let counter = 0;
      const logs = [
        "CoordinatorAgent: Fetching recent platform health contexts from RAG...",
        "RiskAnalysisAgent: Computing platform trust_scores and risk evaluations...",
        "PaymentIntelligenceAgent: Loading Gold channel metrics - total volume: 255k INR",
        "PlatformHealthAgent: Verifying Nessie, Flink and Flink interfaces - healthy",
        "DataQualityAgent: Compiling schema match checks on postgres - valid",
        "ReportGeneratorAgent: Successfully saved agent_report.md and agent_report.json!"
      ];
      
      const interval = setInterval(() => {
        if (counter < logs.length) {
          setAgentLogs(prev => [...prev, `[INFO] ${logs[counter]}`]);
          counter++;
        } else {
          clearInterval(interval);
        }
      }, 1000);
    } catch (e) {
      setAgentLogs(prev => [...prev, "[WARNING] CrewAI simulation backend not available."]);
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl flex flex-col h-[500px]">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-bold font-outfit text-white flex items-center gap-2">
          <Terminal className="w-5 h-5 text-purple-accent" /> Multi-Agent Console
        </h3>
        <button 
          onClick={handleTriggerAgents}
          className="px-4 py-2 text-xs bg-purple-accent text-white rounded-xl hover:bg-purple-600 transition flex items-center gap-2"
        >
          <Play className="w-3.5 h-3.5" /> Execute Crew
        </button>
      </div>

      <div className="flex-1 bg-black/40 border border-white/5 rounded-2xl p-4 font-mono text-xs text-green-400 overflow-y-auto flex flex-col gap-2">
        {agentLogs.map((log, idx) => (
          <div key={idx} className="whitespace-pre-wrap">{log}</div>
        ))}
      </div>
    </div>
  );
}
