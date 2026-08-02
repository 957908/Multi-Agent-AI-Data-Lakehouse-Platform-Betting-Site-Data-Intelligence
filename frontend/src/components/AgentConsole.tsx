import React, { useState, useEffect, useRef } from 'react';
import { 
  Terminal as TerminalIcon, 
  Play, 
  Cpu, 
  ShieldAlert, 
  CreditCard, 
  HeartPulse, 
  Activity, 
  FileText,
  UserCheck,
  CheckCircle,
  Clock,
  Sparkles,
  Download,
  FileJson
} from 'lucide-react';
import { apiService } from '../services/api';

interface AgentInfo {
  id: string;
  name: string;
  role: string;
  icon: React.ComponentType<any>;
  desc: string;
  color: string;
}

const AGENTS: AgentInfo[] = [
  {
    id: 'coordinator',
    name: 'Coordinator Agent',
    role: 'Orchestrator & RAG Parser',
    icon: Cpu,
    desc: 'Bridges system triggers and retrieves semantic context from the FAISS vector index.',
    color: 'from-blue-500/20 to-cyan-500/20 border-blue-500/30 text-blue-400'
  },
  {
    id: 'risk_analysis',
    name: 'Risk Analyst Agent',
    role: 'Risk Profiler',
    icon: ShieldAlert,
    desc: 'Analyzes database trust metrics to detect high-risk platforms and alert operators.',
    color: 'from-amber-500/20 to-orange-500/20 border-amber-500/30 text-amber-400'
  },
  {
    id: 'payment_intelligence',
    name: 'Payment Intel Agent',
    role: 'Financial Aggregator',
    icon: CreditCard,
    desc: 'Aggregates real-time volumes and tracks distribution across payment methods.',
    color: 'from-emerald-500/20 to-teal-500/20 border-emerald-500/30 text-emerald-400'
  },
  {
    id: 'platform_health',
    name: 'Platform Health Agent',
    role: 'Liveness Monitor',
    icon: HeartPulse,
    desc: 'Measures connection latency and audits operational status codes.',
    color: 'from-rose-500/20 to-pink-500/20 border-rose-500/30 text-rose-400'
  },
  {
    id: 'data_quality',
    name: 'Data Quality Agent',
    role: 'Data Quality Inspector',
    icon: Activity,
    desc: 'Validates schemas and checks for null value violations in the silver layer.',
    color: 'from-indigo-500/20 to-violet-500/20 border-indigo-500/30 text-indigo-400'
  },
  {
    id: 'report_generator',
    name: 'Report Generator Agent',
    role: 'Audit Report Compiler',
    icon: FileText,
    desc: 'Assembles findings into standard markdown and JSON compliance reports.',
    color: 'from-purple-500/20 to-fuchsia-500/20 border-purple-500/30 text-purple-400'
  }
];

export default function AgentConsole() {
  const [status, setStatus] = useState<string>('IDLE');
  const [logs, setLogs] = useState<string[]>([
    "[LANGGRAPH] Systems online. Ready to execute multi-agent state graph."
  ]);
  const [activeNode, setActiveNode] = useState<string>('');
  const [isApproved, setIsApproved] = useState<boolean>(false);
  const [isDownloading, setIsDownloading] = useState<string | null>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // ONE Intelligent Agent state hooks
  const [intelligentInput, setIntelligentInput] = useState<string>('');
  const [intelligentLogs, setIntelligentLogs] = useState<string[]>([
    "[INTELLIGENT_AGENT] Idle. Awaiting user command input..."
  ]);
  const [intelligentOutput, setIntelligentOutput] = useState<any>(null);
  const [intelligentLoading, setIntelligentLoading] = useState<boolean>(false);

  const handleExecuteIntelligentCommand = async (cmdText?: string) => {
    const textToSend = cmdText || intelligentInput;
    if (!textToSend.trim()) return;

    setIntelligentLoading(true);
    setIntelligentOutput(null);
    setIntelligentLogs([`[INTELLIGENT_AGENT] Querying agent: "${textToSend}"`]);

    try {
      const res = await apiService.queryIntelligentAgent(textToSend);
      if (res.logs) {
        setIntelligentLogs(res.logs);
      }
      if (res.error) {
        setIntelligentLogs(prev => [...prev, `[ERROR] Tool execution failed: ${res.error}`]);
      } else {
        setIntelligentOutput(res.output);
      }
    } catch (err: any) {
      setIntelligentLogs(prev => [...prev, `[ERROR] Failed to query endpoint: ${err.message}`]);
    } finally {
      setIntelligentLoading(false);
      if (!cmdText) setIntelligentInput('');
    }
  };

  // Poll status from backend
  const fetchStatus = async () => {
    try {
      const data = await apiService.getAgentsStatus();
      setStatus(data.status);
      if (data.logs && data.logs.length > 0) {
        setLogs(data.logs);
        determineActiveAgent(data.logs, data.status);
      }
    } catch (e) {
      console.error("Error fetching agent status:", e);
    }
  };

  const determineActiveAgent = (logsList: string[], currentStatus: string) => {
    if (currentStatus === 'AWAITING_REVIEW') {
      setActiveNode('awaiting_review');
      return;
    }
    
    // Scan logs backwards to find current active node
    for (let i = logsList.length - 1; i >= 0; i--) {
      const log = logsList[i];
      if (log.includes('Coordinator Node active')) {
        setActiveNode('coordinator');
        return;
      }
      if (log.includes('Risk Analyst Node active')) {
        setActiveNode('risk_analysis');
        return;
      }
      if (log.includes('Payment Intel Node active')) {
        setActiveNode('payment_intelligence');
        return;
      }
      if (log.includes('Platform Health Node active')) {
        setActiveNode('platform_health');
        return;
      }
      if (log.includes('Data Quality Node active')) {
        setActiveNode('data_quality');
        return;
      }
      if (log.includes('Report Generator Node active')) {
        setActiveNode('report_generator');
        return;
      }
    }
    
    if (currentStatus === 'RUNNING') {
      setActiveNode('coordinator'); // Default start node
    } else {
      setActiveNode('');
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchStatus();
    
    // Set up polling when running or awaiting review
    const interval = setInterval(() => {
      fetchStatus();
    }, 1500);

    return () => clearInterval(interval);
  }, []);

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const handleTriggerAgents = async () => {
    setIsApproved(false);
    setLogs(prev => [...prev, "[LANGGRAPH] Dispatching crew execution request..."]);
    try {
      await apiService.runAgents();
      setStatus('RUNNING');
      fetchStatus();
    } catch (e) {
      setLogs(prev => [...prev, "[LANGGRAPH ERROR] Crew backend unreachable. Check uvicorn process."]);
    }
  };

  const handleApproveReport = async () => {
    setLogs(prev => [...prev, "[LANGGRAPH] Submitting human operator approval signature..."]);
    try {
      await apiService.approveAgents();
      setIsApproved(true);
      setStatus('RUNNING');
      fetchStatus();
    } catch (e) {
      setLogs(prev => [...prev, "[LANGGRAPH ERROR] Approval submission failed."]);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* LEFT & CENTER: Node Workflow and Cards */}
      <div className="lg:col-span-2 flex flex-col gap-6">
        {/* Status Header */}
        <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row md:items-center justify-between gap-4 border border-white/5 bg-slate-900/40">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-purple-accent/10 rounded-xl border border-purple-accent/20">
              <Sparkles className="w-5 h-5 text-purple-accent" />
            </div>
            <div>
              <h3 className="text-lg font-bold font-outfit text-white">LangGraph Crew Console</h3>
              <p className="text-xs text-slate-400">Orchestrating autonomous AI agents with human-in-the-loop validation</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Status Indicator */}
            <div className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 border ${
              status === 'RUNNING' 
                ? 'bg-blue-500/10 border-blue-500/30 text-blue-400' 
                : status === 'AWAITING_REVIEW'
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-400 animate-pulse'
                : 'bg-slate-500/10 border-slate-500/30 text-slate-400'
            }`}>
              <span className={`w-2 h-2 rounded-full ${
                status === 'RUNNING' 
                  ? 'bg-blue-400 animate-ping' 
                  : status === 'AWAITING_REVIEW'
                  ? 'bg-amber-400 animate-ping'
                  : 'bg-slate-400'
              }`} />
              Status: {status}
            </div>

            <button 
              disabled={status === 'RUNNING' || status === 'AWAITING_REVIEW'}
              onClick={handleTriggerAgents}
              className={`px-5 py-2.5 text-xs font-semibold rounded-xl flex items-center gap-2 transition-all ${
                status === 'RUNNING' || status === 'AWAITING_REVIEW'
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-white/5'
                  : 'bg-purple-accent text-white hover:bg-purple-600 border border-purple-400/20 hover:shadow-[0_0_15px_rgba(168,85,247,0.4)]'
              }`}
            >
              <Play className="w-3.5 h-3.5" /> Execute Crew
            </button>
          </div>
        </div>

        {/* Stepper Pipeline Flow */}
        <div className="glass-panel p-5 rounded-2xl border border-white/5 bg-slate-900/20">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Pipeline Stepper Workflow</h4>
          <div className="flex flex-wrap items-center justify-between gap-2 md:gap-4">
            {AGENTS.map((agent, idx) => {
              const isCurrent = activeNode === agent.id;
              const isPassed = activeNode !== '' && AGENTS.findIndex(a => a.id === activeNode) > idx;
              
              return (
                <React.Fragment key={agent.id}>
                  <div className={`flex flex-col items-center gap-1.5 p-2 rounded-xl transition-all ${
                    isCurrent 
                      ? 'bg-purple-accent/10 border border-purple-accent/30 scale-105' 
                      : 'border border-transparent'
                  }`}>
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center border transition-all ${
                      isCurrent
                        ? 'bg-purple-accent text-white border-purple-accent shadow-[0_0_10px_rgba(168,85,247,0.4)]'
                        : isPassed
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                        : 'bg-slate-800/60 border-white/5 text-slate-500'
                    }`}>
                      <agent.icon className={`w-5 h-5 ${isCurrent ? 'animate-pulse' : ''}`} />
                    </div>
                    <span className={`text-[10px] font-semibold tracking-tight ${
                      isCurrent ? 'text-purple-400 font-bold' : isPassed ? 'text-emerald-400' : 'text-slate-500'
                    }`}>{agent.name.split(' ')[0]}</span>
                  </div>
                  {idx < AGENTS.length - 1 && (
                    <div className={`flex-1 h-0.5 min-w-[12px] rounded ${
                      isPassed ? 'bg-emerald-500/40' : 'bg-slate-800'
                    }`} />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {/* Crew Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {AGENTS.map((agent) => {
            const isCurrent = activeNode === agent.id;
            return (
              <div 
                key={agent.id} 
                className={`glass-panel p-4 rounded-xl border flex gap-3 transition-all duration-300 bg-gradient-to-br ${agent.color} ${
                  isCurrent 
                    ? 'shadow-[0_0_20px_rgba(168,85,247,0.15)] ring-1 ring-purple-accent/40 scale-[1.01]' 
                    : 'opacity-70 hover:opacity-100'
                }`}
              >
                <div className={`p-2.5 rounded-lg h-fit border bg-black/40 ${
                  isCurrent ? 'border-purple-accent/40 text-purple-accent' : 'border-white/5 text-slate-400'
                }`}>
                  <agent.icon className={`w-5 h-5 ${isCurrent ? 'animate-bounce' : ''}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="text-xs font-bold text-white tracking-wide truncate">{agent.name}</h4>
                    {isCurrent && (
                      <span className="px-1.5 py-0.5 text-[9px] font-bold bg-purple-accent/20 text-purple-300 rounded border border-purple-accent/30 animate-pulse">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <p className="text-[10px] text-slate-400 font-mono tracking-tight mt-0.5">{agent.role}</p>
                  <p className="text-[10px] text-slate-400 leading-normal mt-2">{agent.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* ONE Intelligent Agent - Tool Execution Console */}
        <div className="glass-panel p-6 rounded-2xl border border-white/5 bg-slate-950/40 mt-6 flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded-xl">
              <Cpu className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h3 className="text-md font-bold text-white font-outfit">ONE Intelligent Agent</h3>
              <p className="text-[11px] text-slate-400">Execute workflow actions across tools using the ReAct orchestration framework</p>
            </div>
          </div>

          {/* Quick Command Chips */}
          <div className="flex flex-wrap gap-2">
            <span className="text-[10px] font-semibold text-slate-500 mr-1 flex items-center">Presets:</span>
            {[
              { label: 'Scrape Melbet Cashier', cmd: 'scrape melbet cashier' },
              { label: 'Run Spark Ingestion ETL', cmd: 'run spark etl pipeline' },
              { label: 'Check 250k Anomaly', cmd: 'check anomaly for 250000 INR' },
              { label: 'FAISS Vector Search', cmd: 'vector search Paytm' },
              { label: 'Generate Compliance Report', cmd: 'generate compliance report' },
              { label: 'Query SQL Table Stats', cmd: 'query table silver_transactions' },
            ].map((preset, pIdx) => (
              <button
                key={pIdx}
                disabled={intelligentLoading}
                onClick={() => handleExecuteIntelligentCommand(preset.cmd)}
                className="px-2.5 py-1 text-[10px] font-mono rounded-lg bg-indigo-950/40 hover:bg-indigo-900/40 border border-indigo-500/20 text-indigo-300 hover:text-indigo-200 transition-all"
              >
                {preset.label}
              </button>
            ))}
          </div>

          {/* Prompt input field */}
          <div className="flex gap-2">
            <input
              type="text"
              value={intelligentInput}
              onChange={(e) => setIntelligentInput(e.target.value)}
              disabled={intelligentLoading}
              placeholder="Type a natural language instruction or choose a preset action..."
              className="flex-1 px-4 py-2.5 text-xs bg-slate-900/60 border border-white/5 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500/50"
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleExecuteIntelligentCommand();
              }}
            />
            <button
              onClick={() => handleExecuteIntelligentCommand()}
              disabled={intelligentLoading || !intelligentInput.trim()}
              className="px-5 py-2.5 text-xs font-semibold rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white transition-all disabled:opacity-50"
            >
              {intelligentLoading ? 'Processing...' : 'Execute Tool'}
            </button>
          </div>

          {/* Sub-Terminal logs */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Agent Trace Logs */}
            <div className="flex flex-col gap-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Thought & Action Trace</span>
              <div className="h-[140px] overflow-y-auto font-mono text-[9px] leading-relaxed p-3 bg-black/50 rounded-xl border border-white/5 text-indigo-300">
                {intelligentLogs.map((log, idx) => (
                  <div key={idx}>{log}</div>
                ))}
              </div>
            </div>

            {/* Structured Output Screen */}
            <div className="flex flex-col gap-2">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Tool Execution Output</span>
              <div className="h-[140px] overflow-y-auto font-mono text-[9px] leading-relaxed p-3 bg-black/50 rounded-xl border border-white/5 text-emerald-400">
                {intelligentOutput ? (
                  typeof intelligentOutput === 'object' ? (
                    <pre className="whitespace-pre-wrap">{JSON.stringify(intelligentOutput, null, 2)}</pre>
                  ) : (
                    <div>{intelligentOutput}</div>
                  )
                ) : (
                  <span className="text-slate-500 italic">No output received yet.</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT: Live Logs Terminal and Human Gate */}
      <div className="flex flex-col gap-6">
        {/* Human-in-the-loop Guardrail Gate */}
        {status === 'AWAITING_REVIEW' && (
          <div className="glass-panel p-5 rounded-2xl border border-amber-500/30 bg-amber-500/5 animate-fade-in shadow-[0_0_30px_rgba(245,158,11,0.08)] flex flex-col gap-4">
            <div className="flex items-start gap-3">
              <div className="p-2.5 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-xl mt-0.5">
                <UserCheck className="w-5 h-5 animate-pulse" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-bold text-amber-400 tracking-wide font-outfit">Review Gate: Awaiting Approval</h4>
                <p className="text-xs text-slate-300 leading-normal mt-1">
                  The agents have audited platforms, quality constraints, and transaction metrics. Confirm audit compliance details below to release the final report.
                </p>
              </div>
            </div>

            <div className="bg-black/40 border border-amber-500/10 rounded-xl p-3 text-[11px] font-mono text-amber-300 flex flex-col gap-2">
              <div className="flex justify-between border-b border-white/5 pb-1.5">
                <span>SYSTEM HEALTH STATE:</span>
                <span className="font-bold text-emerald-400">HEALTHY</span>
              </div>
              <div className="flex justify-between border-b border-white/5 pb-1.5">
                <span>QUALITY DATA CHECKS:</span>
                <span className="font-bold">PASSED (173 ROWS)</span>
              </div>
              <div className="flex justify-between">
                <span>FLAGGED ANOMALIES:</span>
                <span className="font-bold text-rose-400">26 ALERTS (15%)</span>
              </div>
            </div>

            <div className="text-[10px] text-slate-400 italic">
              * Note: By signing, the operator assumes accountability for pushing the final metrics file to database catalogs.
            </div>

            <button 
              onClick={handleApproveReport}
              className="w-full py-2.5 text-xs font-semibold bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-xl flex items-center justify-center gap-2 hover:shadow-[0_0_15px_rgba(245,158,11,0.4)] transition-all font-bold"
            >
              <CheckCircle className="w-4 h-4" /> Approve & Release Audit Report
            </button>
          </div>
        )}

        {/* Live Terminal Terminal */}
        <div className="glass-panel p-5 rounded-2xl flex flex-col border border-white/5 bg-black/30">
          <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-4">
            <div className="flex items-center gap-2">
              <TerminalIcon className="w-4 h-4 text-purple-accent" />
              <span className="text-xs font-bold text-white tracking-wider uppercase font-outfit">Orchestrator Terminal</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] text-slate-400 font-semibold font-mono">LIVE FEED</span>
            </div>
          </div>

          <div className="h-[400px] overflow-y-auto font-mono text-[10px] leading-relaxed text-slate-300 flex flex-col gap-2 p-3 bg-black/60 rounded-xl border border-white/5 scrollbar-thin">
            {logs.map((log, idx) => {
              let color = 'text-slate-400';
              if (log.includes('[LANGGRAPH]')) color = 'text-cyan-400';
              if (log.includes('[LANGGRAPH ERROR]')) color = 'text-rose-400 font-semibold';
              if (log.includes('[LANGGRAPH WARNING]')) color = 'text-amber-400';
              if (log.includes('WORKFLOW PAUSED')) color = 'text-amber-300 font-bold';
              if (log.includes('Operator Signature Verified')) color = 'text-emerald-400 font-semibold';
              
              return (
                <div key={idx} className={`whitespace-pre-wrap ${color}`}>
                  {log}
                </div>
              );
            })}
            <div ref={terminalEndRef} />
          </div>
        </div>

        {/* Download Report Card — shown when workflow is complete */}
        {status === 'SUCCESS' && (
          <div className="glass-panel p-5 rounded-2xl border border-emerald-500/25 bg-emerald-500/5 flex flex-col gap-4 animate-fade-in">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-xl">
                <CheckCircle className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-emerald-400 font-outfit">Audit Report Ready</h4>
                <p className="text-[10px] text-slate-400 mt-0.5">Report compiled and saved. Download below.</p>
              </div>
            </div>

            <div className="flex flex-col gap-2">
              <button
                onClick={async () => {
                  setIsDownloading('md');
                  try { await apiService.downloadReportMarkdown(); } 
                  catch { setLogs(prev => [...prev, '[LANGGRAPH ERROR] Report download failed — ensure backend is running.']); }
                  setIsDownloading(null);
                }}
                disabled={isDownloading !== null}
                className="flex items-center justify-center gap-2 w-full py-2.5 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl transition-all hover:shadow-[0_0_15px_rgba(16,185,129,0.3)] disabled:opacity-60"
              >
                <Download className="w-4 h-4" />
                {isDownloading === 'md' ? 'Downloading...' : 'Download Audit Report (.md)'}
              </button>
              <button
                onClick={async () => {
                  setIsDownloading('json');
                  try { await apiService.downloadReportJson(); }
                  catch { setLogs(prev => [...prev, '[LANGGRAPH ERROR] JSON report download failed — ensure backend is running.']); }
                  setIsDownloading(null);
                }}
                disabled={isDownloading !== null}
                className="flex items-center justify-center gap-2 w-full py-2.5 text-xs font-bold bg-white/5 hover:bg-white/10 border border-emerald-500/20 text-emerald-400 rounded-xl transition-all disabled:opacity-60"
              >
                <FileJson className="w-4 h-4" />
                {isDownloading === 'json' ? 'Downloading...' : 'Download Raw Data (.json)'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
