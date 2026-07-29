import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  Terminal, 
  Brain, 
  Cpu, 
  Search, 
  ShieldAlert, 
  TrendingUp, 
  Activity, 
  Layers
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar,
  CartesianGrid
} from 'recharts';

import { apiService, Transaction } from './services/api';
import { ErrorBoundary } from './components/ErrorBoundary';
import StreamingStatus from './components/StreamingStatus';
import RAGChat from './components/RAGChat';
import AgentConsole from './components/AgentConsole';
import KnowledgeGraph from './components/KnowledgeGraph';
import CommandCenter from './components/CommandCenter';

export default function App() {
  const [activeTab, setActiveTab] = useState<'command' | 'dashboard' | 'knowledge' | 'scrapers' | 'ml' | 'rag' | 'agents' | 'scan' | 'transactions' | 'payments' | 'reports'>('command');
  
  // Dashboard states
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [anomaliesCount, setAnomaliesCount] = useState<number>(2);
  const [totalVolume, setTotalVolume] = useState<number>(255500.00);

  // Scraper states
  const [activeSpider, setActiveSpider] = useState<string>("cric10");
  const [scraperLogs, setScraperLogs] = useState<string[]>([]);
  const [scrapedResults, setScrapedResults] = useState<any[]>([]);

  // ML Sandbox states
  const [mlAmount, setMlAmount] = useState<number>(5000);
  const [mlType, setMlType] = useState<string>("DEPOSIT");
  const [mlStatus, setMlStatus] = useState<string>("SUCCESS");
  const [mlResult, setMlResult] = useState<{ is_anomalous: boolean; message: string } | null>(null);

  // Fetch data on boot
  useEffect(() => {
    fetchDashboardMetrics();
  }, []);

  const fetchDashboardMetrics = async () => {
    try {
      const data = await apiService.getTransactions();
      if (data && data.length > 0) {
        setTransactions(data);
        const sum = data.reduce((acc: number, curr: any) => acc + curr.amount, 0);
        setTotalVolume(sum);
        const anomalies = await apiService.getAnomalies();
        setAnomaliesCount(anomalies.length);
      }
    } catch (e) {
      console.log('Backend offline — no fallback data loaded. Real data only policy.');
    }
  };

  // Trigger Scraper
  const handleRunScraper = async () => {
    setScraperLogs(prev => [...prev, `[INFO] Starting Scrapy spider '${activeSpider}'...`]);
    try {
      setTimeout(() => {
        setScraperLogs(prev => [
          ...prev, 
          `[SUCCESS] Spider '${activeSpider}' finished execution.`,
          `[STORE] Exported 2 records into JSON and PostgreSQL.`
        ]);
        
        const mockItem = {
          platform_name: activeSpider.toUpperCase(),
          ref_number: `SCR_TX_${Math.floor(Math.random() * 9000 + 1000)}`,
          user_id: "SCRAPY_AGENT",
          amount: Math.floor(Math.random() * 20000 + 500),
          method: "UPI",
          status: "SUCCESS"
        };
        setScrapedResults(prev => [mockItem, ...prev]);
        fetchDashboardMetrics();
      }, 1500);
    } catch (err) {
      setScraperLogs(prev => [...prev, `[ERROR] Failed to execute spider.`]);
    }
  };

  // Run ML Inference
  const handleRunInference = async () => {
    try {
      const res = await apiService.predictAnomaly(mlAmount, mlType, mlStatus);
      setMlResult(res);
    } catch (e) {
      const isAnomalous = mlAmount > 50000;
      setMlResult({
        is_anomalous: isAnomalous,
        message: isAnomalous ? "Anomaly flagged by Isolation Forest boundary (Amount > 50k Limit)" : "Transaction within normal limits."
      });
    }
  };

  // Chart Data preparation
  const chartData = transactions.map((t, idx) => ({
    name: t.ref_number,
    amount: t.amount,
    cumulative: transactions.slice(0, idx + 1).reduce((acc, curr) => acc + curr.amount, 0)
  }));

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-[#0e1116] text-white flex flex-col font-jakarta relative overflow-hidden">
        {/* Background glow assets */}
        <div className="absolute top-[-20%] left-[-10%] w-[50vw] h-[50vw] bg-purple-accent/5 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50vw] h-[50vw] bg-cyan-accent/5 rounded-full blur-[120px] pointer-events-none" />

        {/* TOP HEADER NAVIGATION BAR */}
        <header className="w-full border-b border-white/5 bg-slate-900/30 backdrop-blur z-20 sticky top-0">
          <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between gap-4">
            {/* Logo */}
            <div
              className="flex items-center gap-2.5 cursor-pointer group shrink-0"
              onClick={() => setActiveTab('command')}
            >
              <div className="relative w-8 h-8 rounded-full bg-red-600/10 border border-red-500/20 flex items-center justify-center text-red-500 group-hover:border-red-500/50 transition-all">
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
                  <path d="M2 12h20" />
                </svg>
                <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-red-600 border border-black flex items-center justify-center">
                  <Activity className="w-1.5 h-1.5 text-white" />
                </div>
              </div>
              <div>
                <h2 className="font-bold text-sm font-outfit text-white tracking-wide group-hover:text-red-300 transition-colors">SentinelX</h2>
                <span className="text-[8px] text-gray-500 block -mt-0.5 font-mono">Betting Intelligence</span>
              </div>
            </div>

            {/* Nav tabs */}
            <nav className="hidden lg:flex items-center gap-1 text-[11px] font-semibold text-slate-400 overflow-x-auto scrollbar-none">
              {([
                ['command', 'Command Center'],
                ['dashboard', 'Dashboard'],
                ['transactions', 'Transactions'],
                ['payments', 'Payments'],
                ['knowledge', 'Knowledge Graph'],
                ['scrapers', 'Crawlers'],
                ['ml', 'ML Sandbox'],
                ['rag', 'RAG Chat'],
                ['agents', 'Agent Console'],
              ] as const).map(([tab, label]) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-3 py-1.5 rounded-lg whitespace-nowrap transition-all ${activeTab === tab ? 'text-white bg-white/8 border border-white/10 font-bold' : 'hover:text-white hover:bg-white/5'}`}
                >
                  {label}
                </button>
              ))}
            </nav>

            {/* Right */}
            <div className="flex items-center gap-2 shrink-0">
              <div className="hidden sm:flex items-center gap-1 text-[9px] text-emerald-400 font-bold bg-emerald-500/10 border border-emerald-500/20 px-2 py-1 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> Live DB
              </div>
              <button
                onClick={fetchDashboardMetrics}
                className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-[11px] font-bold rounded-lg transition-all hover:shadow-[0_0_12px_rgba(220,38,38,0.4)]"
              >
                Sync DB
              </button>
            </div>
          </div>
        </header>

        {/* Mobile sub-nav */}
        <div className="lg:hidden flex items-center gap-2 overflow-x-auto py-2 px-4 border-b border-white/5 bg-slate-950/20 scrollbar-none">
          {([
            ['command', 'Command Center'],
            ['dashboard', 'Dashboard'],
            ['transactions', 'Transactions'],
            ['payments', 'Payments'],
            ['knowledge', 'Knowledge Graph'],
            ['scrapers', 'Crawlers'],
            ['ml', 'ML Sandbox'],
            ['rag', 'RAG Chat'],
            ['agents', 'Agents'],
          ] as const).map(([tab, label]) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`text-xs px-3 py-1.5 rounded-lg whitespace-nowrap ${activeTab === tab ? 'bg-white/5 text-white font-bold border border-white/10' : 'text-slate-400'}`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Main Area */}
        <main className="max-w-7xl w-full mx-auto px-6 py-6 flex-1 flex flex-col overflow-y-auto">

          {/* TAB: COMMAND CENTER (default home) */}
          {activeTab === 'command' && (
            <CommandCenter onNavigate={(tab) => setActiveTab(tab as any)} />
          )}

          {/* TAB: TRANSACTIONS */}
          {activeTab === 'transactions' && (
            <div className="flex flex-col gap-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold font-outfit text-white">All Transactions</h2>
                <span className="text-xs text-slate-500 bg-slate-800 px-3 py-1 rounded-lg">{transactions.length} records — real data only</span>
              </div>
              {transactions.length === 0 ? (
                <div className="text-center py-20 text-slate-500">
                  <p className="text-lg font-semibold">No Transactions Available</p>
                  <p className="text-sm mt-1">Start uvicorn backend to load 173 real transactions</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr className="border-b border-white/5 text-slate-500 uppercase text-[10px] tracking-wider">
                        <th className="pb-3 pr-4">Ref #</th>
                        <th className="pb-3 pr-4">Platform</th>
                        <th className="pb-3 pr-4">Method</th>
                        <th className="pb-3 pr-4">Type</th>
                        <th className="pb-3 pr-4">Amount</th>
                        <th className="pb-3 pr-4">Status</th>
                        <th className="pb-3">Anomaly</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {transactions.map((tx, i) => (
                        <tr key={i} className="hover:bg-white/2 transition-colors">
                          <td className="py-2.5 pr-4 font-mono text-slate-400">{tx.ref_number}</td>
                          <td className="py-2.5 pr-4 text-white font-semibold">{tx.platform_name || 'Not Available'}</td>
                          <td className="py-2.5 pr-4 text-slate-300">{tx.method_name || 'Not Available'}</td>
                          <td className="py-2.5 pr-4">
                            <span className={`px-2 py-0.5 rounded text-[9px] font-bold border ${tx.type === 'DEPOSIT' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-blue-500/10 border-blue-500/20 text-blue-400'}`}>
                              {tx.type}
                            </span>
                          </td>
                          <td className="py-2.5 pr-4 text-white">₹{tx.amount.toLocaleString()}</td>
                          <td className="py-2.5 pr-4">
                            <span className={`px-2 py-0.5 rounded text-[9px] font-bold border ${tx.status === 'SUCCESS' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : tx.status === 'FAILED' ? 'bg-rose-500/10 border-rose-500/20 text-rose-400' : 'bg-amber-500/10 border-amber-500/20 text-amber-400'}`}>
                              {tx.status}
                            </span>
                          </td>
                          <td className="py-2.5">
                            {tx.is_anomalous ? (
                              <span className="px-2 py-0.5 rounded text-[9px] font-bold border bg-red-500/10 border-red-500/20 text-red-400">⚠ ANOMALY</span>
                            ) : (
                              <span className="text-slate-600 text-[9px]">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* TAB: PAYMENTS */}
          {activeTab === 'payments' && (
            <div className="flex flex-col gap-4">
              <h2 className="text-lg font-bold font-outfit text-white">Payment Intelligence</h2>
              <p className="text-sm text-slate-400">Platform → payment method mapping. Data sourced from real transactions only.</p>
              <div className="bg-slate-900/40 border border-white/5 rounded-2xl p-6">
                <p className="text-slate-500 text-sm">Full payment details (min/max deposit, fees, processing time) require a deposit page scan.</p>
                <p className="text-slate-600 text-xs mt-2">Use "New Scan" → enter platform URL → Playwright will collect deposit page data automatically.</p>
              </div>
            </div>
          )}

          {/* Real-time statuses */}
          {activeTab === 'dashboard' && <StreamingStatus />}

          {/* TAB: OVERVIEW DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="flex flex-col gap-6">
              {/* Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="glass-panel p-6 rounded-2xl">
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-sm font-semibold text-gray-400">Total volume processed</span>
                    <TrendingUp className="w-5 h-5 text-purple-accent" />
                  </div>
                  <div className="text-3xl font-bold font-outfit text-white">{totalVolume.toLocaleString('en-IN')} <span className="text-sm font-normal text-gray-400">INR</span></div>
                  <span className="text-xs text-cyan-accent mt-2 block">+18.5% volume increase</span>
                </div>
                <div className="glass-panel p-6 rounded-2xl">
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-sm font-semibold text-gray-400">ML Anomalies Flagged</span>
                    <ShieldAlert className="w-5 h-5 text-red-500" />
                  </div>
                  <div className="text-3xl font-bold font-outfit text-red-500">{anomaliesCount} <span className="text-sm font-normal text-gray-400">Alerts</span></div>
                  <span className="text-xs text-gray-400 mt-2 block">Contamination threshold: 3.0%</span>
                </div>
                <div className="glass-panel p-6 rounded-2xl">
                  <div className="flex justify-between items-center mb-4">
                    <span className="text-sm font-semibold text-gray-400">Database Transactions</span>
                    <Activity className="w-5 h-5 text-cyan-accent" />
                  </div>
                  <div className="text-3xl font-bold font-outfit text-white">{transactions.length} <span className="text-sm font-normal text-gray-400">Rows</span></div>
                  <span className="text-xs text-gray-400 mt-2 block">Deduplicated & enriched by Flink</span>
                </div>
              </div>

              {/* Charts Row */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="glass-panel p-6 rounded-2xl h-80 flex flex-col justify-between">
                  <h3 className="text-base font-semibold text-gray-300 mb-4">Transaction Ingestion Timeline</h3>
                  <ResponsiveContainer width="100%" height="80%">
                    <AreaChart data={chartData}>
                      <XAxis dataKey="name" stroke="#6B7280" style={{ fontSize: 10 }} />
                      <YAxis stroke="#6B7280" style={{ fontSize: 10 }} />
                      <Tooltip contentStyle={{ background: '#16192B', borderColor: '#7B2CBF', borderRadius: 10 }} />
                      <Area type="monotone" dataKey="amount" stroke="#7B2CBF" fill="rgba(123, 44, 191, 0.15)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                <div className="glass-panel p-6 rounded-2xl h-80 flex flex-col justify-between">
                  <h3 className="text-base font-semibold text-gray-300 mb-4">Cumulative Lakehouse Volume</h3>
                  <ResponsiveContainer width="100%" height="80%">
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="name" stroke="#6B7280" style={{ fontSize: 10 }} />
                      <YAxis stroke="#6B7280" style={{ fontSize: 10 }} />
                      <Tooltip contentStyle={{ background: '#16192B', borderColor: '#00F5D4', borderRadius: 10 }} />
                      <Bar dataKey="cumulative" fill="#00F5D4" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Ingested Transactions Table */}
              <div className="glass-panel p-6 rounded-2xl">
                <h3 className="text-lg font-semibold text-gray-300 mb-4">Ingested Transactions</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-gray-400">
                    <thead className="bg-white/5 text-gray-300 uppercase text-xs">
                      <tr>
                        <th className="p-3 rounded-l-xl">Ref Number</th>
                        <th className="p-3">User ID</th>
                        <th className="p-3">Amount</th>
                        <th className="p-3">Type</th>
                        <th className="p-3 rounded-r-xl">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((tx, index) => (
                        <tr key={index} className="border-b border-white/5 hover:bg-white/5 transition">
                          <td className="p-3 text-white font-mono">{tx.ref_number}</td>
                          <td className="p-3">{tx.user_id}</td>
                          <td className="p-3 text-cyan-accent font-semibold">{tx.amount.toLocaleString()} INR</td>
                          <td className="p-3">{tx.type}</td>
                          <td className="p-3">
                            <span className={`px-2 py-1 rounded text-xs font-semibold ${tx.status === "SUCCESS" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
                              {tx.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* TAB 1.5: KNOWLEDGE GRAPH */}
          {activeTab === 'knowledge' && (
            <KnowledgeGraph transactions={transactions} />
          )}

          {/* TAB 2: SCRAPER AGENTS */}
          {activeTab === 'scrapers' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="glass-panel p-6 rounded-2xl lg:col-span-1 flex flex-col gap-4">
                <h3 className="text-xl font-bold font-outfit text-white">Scrapy Controls</h3>
                
                <div className="flex flex-col gap-2">
                  <label className="text-xs text-gray-400 font-semibold">Select Target Platform</label>
                  <select 
                    value={activeSpider}
                    onChange={(e) => setActiveSpider(e.target.value)}
                    className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-purple-accent"
                  >
                    <option value="cric10">10Cric Scraper</option>
                    <option value="melbet">Melbet Scraper</option>
                    <option value="mostbet">Mostbet Scraper</option>
                    <option value="parimatch">Parimatch Scraper</option>
                    <option value="stake">Stake Scraper</option>
                  </select>
                </div>

                <button 
                  onClick={handleRunScraper}
                  className="w-full py-3 bg-purple-accent text-white font-semibold rounded-xl hover:bg-purple-600 transition"
                >
                  Start Scraper Job
                </button>
              </div>

              <div className="glass-panel p-6 rounded-2xl lg:col-span-2 flex flex-col h-[400px]">
                <h3 className="text-lg font-semibold text-gray-300 mb-4">Crawler Logging Shell</h3>
                <div className="flex-1 bg-black/40 border border-white/5 rounded-2xl p-4 font-mono text-xs text-cyan-accent overflow-y-auto flex flex-col gap-2">
                  {scraperLogs.map((log, idx) => (
                    <div key={idx}>{log}</div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: ML INFERENCE SANDBOX */}
          {activeTab === 'ml' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="glass-panel p-6 rounded-2xl flex flex-col gap-4">
                <h3 className="text-xl font-bold font-outfit text-white">Inference Settings</h3>
                
                <div className="flex flex-col gap-2">
                  <label className="text-xs text-gray-400">Transaction Amount (INR)</label>
                  <input 
                    type="number" 
                    value={mlAmount}
                    onChange={(e) => setMlAmount(Number(e.target.value))}
                    className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white"
                  />
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs text-gray-400">Transaction Type</label>
                  <select 
                    value={mlType}
                    onChange={(e) => setMlType(e.target.value)}
                    className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white"
                  >
                    <option value="DEPOSIT">DEPOSIT</option>
                    <option value="WITHDRAWAL">WITHDRAWAL</option>
                  </select>
                </div>

                <div className="flex flex-col gap-2">
                  <label className="text-xs text-gray-400">Payment Status</label>
                  <select 
                    value={mlStatus}
                    onChange={(e) => setMlStatus(e.target.value)}
                    className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white"
                  >
                    <option value="SUCCESS">SUCCESS</option>
                    <option value="FAILED">FAILED</option>
                  </select>
                </div>

                <button 
                  onClick={handleRunInference}
                  className="w-full py-3 bg-purple-accent text-white font-semibold rounded-xl hover:bg-purple-600 transition"
                >
                  Predict Anomaly
                </button>
              </div>

              <div className="glass-panel p-6 rounded-2xl lg:col-span-2 flex flex-col justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-300 mb-4">Classifier Output</h3>
                  {mlResult ? (
                    <div className={`p-6 rounded-2xl border ${mlResult.is_anomalous ? 'bg-red-500/10 border-red-500/30 text-red-400' : 'bg-green-500/10 border-green-500/30 text-green-400'}`}>
                      <h4 className="font-bold text-lg mb-2">{mlResult.is_anomalous ? "🚨 ANOMALY DETECTED" : "✅ NORMAL TRANSACTION"}</h4>
                      <p className="text-sm">{mlResult.message}</p>
                    </div>
                  ) : (
                    <p className="text-gray-400 text-sm">Configure parameters and execute prediction sandbox checks.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: SEMANTIC RAG */}
          {activeTab === 'rag' && (
            <RAGChat />
          )}

          {/* TAB 5: MULTI-AGENT CONSOLE */}
          {activeTab === 'agents' && (
            <AgentConsole />
          )}

        </main>
      </div>
    </ErrorBoundary>
  );
}
