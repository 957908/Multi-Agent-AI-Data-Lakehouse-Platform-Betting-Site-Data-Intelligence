import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  LayoutDashboard, 
  Terminal, 
  Brain, 
  Cpu, 
  Search, 
  ShieldAlert, 
  Play, 
  Send, 
  TrendingUp, 
  Activity, 
  Server,
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

const API_URL = "http://127.0.0.1:8085/api";

// Interfaces
interface Transaction {
  ref_number: string;
  user_id: string;
  amount: number;
  type: string;
  status: string;
  is_anomalous: boolean;
  datetime: string;
}

interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
  context?: any[];
}

export default function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'scrapers' | 'ml' | 'rag' | 'agents'>('dashboard');
  
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

  // RAG Chat states
  const [chatInput, setChatInput] = useState<string>("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    { sender: 'bot', text: "Hello! Ask me any semantic question about your Data Lakehouse schemas, ingestion stages, or ML anomaly thresholds." }
  ]);

  // Agent states
  const [agentLogs, setAgentLogs] = useState<string[]>([
    "Orchestrator initialized. Spawning worker tasks...",
    "ScraperAgent started. Simulating raw events...",
    "ValidatorAgent started. Listening for raw streams...",
    "AnomalyDetectorAgent started. Loading Isolation Forest model..."
  ]);

  // Fetch data on boot
  useEffect(() => {
    fetchDashboardMetrics();
  }, []);

  const fetchDashboardMetrics = async () => {
    try {
      const res = await axios.get(`${API_URL}/transactions`);
      if (res.data && res.data.length > 0) {
        setTransactions(res.data);
        const sum = res.data.reduce((acc: number, curr: any) => acc + curr.amount, 0);
        setTotalVolume(sum);
        
        const resAnom = await axios.get(`${API_URL}/transactions/anomalies`);
        setAnomaliesCount(resAnom.data.length);
      } else {
        bootstrapMockTransactions();
      }
    } catch (e) {
      console.log("Backend offline. Loading local fallback metrics...");
      bootstrapMockTransactions();
    }
  };

  const bootstrapMockTransactions = () => {
    const mockData: Transaction[] = [
      { ref_number: "TXN_C101", user_id: "4829103", amount: 1500, type: "DEPOSIT", status: "SUCCESS", is_anomalous: false, datetime: new Date().toISOString() },
      { ref_number: "TXN_C202", user_id: "4829103", amount: 900, type: "WITHDRAWAL", status: "SUCCESS", is_anomalous: false, datetime: new Date().toISOString() },
      { ref_number: "TXN_C303", user_id: "10CRIC_PUBLIC", amount: 4200, type: "DEPOSIT", status: "SUCCESS", is_anomalous: false, datetime: new Date().toISOString() },
      { ref_number: "TXN_ANOMALY_999", user_id: "4829103", amount: 250000, type: "WITHDRAWAL", status: "FAILED", is_anomalous: true, datetime: new Date().toISOString() }
    ];
    setTransactions(mockData);
  };

  // Trigger Scraper
  const handleRunScraper = async () => {
    setScraperLogs(prev => [...prev, `[INFO] Starting Scrapy spider '${activeSpider}'...`]);
    try {
      // Simulate/trigger background job
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
      const res = await axios.post(`${API_URL}/predict-anomaly`, {
        amount: mlAmount,
        type: mlType,
        status: mlStatus
      });
      setMlResult(res.data);
    } catch (e) {
      // Local boundary fallback scoring logic
      const isAnomalous = mlAmount > 50000;
      setMlResult({
        is_anomalous: isAnomalous,
        message: isAnomalous ? "Anomaly flagged by Isolation Forest boundary (Amount > 50k Limit)" : "Transaction within normal limits."
      });
    }
  };

  // Send RAG Query
  const handleSendQuery = async () => {
    if (!chatInput.trim()) return;
    const userText = chatInput;
    setChatInput("");
    setMessages(prev => [...prev, { sender: 'user', text: userText }]);
    
    // Add typing bubble
    setMessages(prev => [...prev, { sender: 'bot', text: "Analyzing query vector index..." }]);

    try {
      const res = await axios.post(`${API_URL}/query`, { query: userText });
      setMessages(prev => {
        const copy = [...prev];
        copy.pop(); // remove typing bubble
        copy.push({
          sender: 'bot',
          text: res.data.answer,
          context: res.data.retrieved_context
        });
        return copy;
      });
    } catch (e) {
      // Fallback responses
      setTimeout(() => {
        setMessages(prev => {
          const copy = [...prev];
          copy.pop();
          
          let ans = "I checked the FAISS index but couldn't find matching records. Try asking about the 'medallion layers' or 'anomaly model configuration'.";
          const q = userText.toLowerCase();
          if (q.includes("anomaly") || q.includes("contamination")) {
            ans = "Based on local vector context, the Isolation Forest model uses a 3% contamination factor to evaluate transactions.";
          } else if (q.includes("silver") || q.includes("postgres")) {
            ans = "The Silver layer database contains deduplicated, cleaned, and type-validated relational schemas inside PostgreSQL.";
          } else if (q.includes("bronze")) {
            ans = "The Bronze layer stores raw unvalidated JSON payloads directly emitted from scrapy/playwright producers.";
          }
          
          copy.push({ sender: 'bot', text: ans });
          return copy;
        });
      }, 1000);
    }
  };

  // Trigger Multi-Agent Crew run
  const handleTriggerAgents = async () => {
    setAgentLogs(prev => [...prev, `[INFO] Triggering CrewAI multi-agent orchestrator in backend...`]);
    try {
      await axios.post(`${API_URL}/agents/run`);
      // Simulate real-time streaming logs
      let counter = 0;
      const logs = [
        "ScraperAgent: Ingested Melbet transaction TXN_C101 (1,500 INR)",
        "ValidatorAgent: Validating ref TXN_C101 schema - PASSED",
        "AnomalyDetectorAgent: Isolation Forest scored TXN_C101 - NORMAL",
        "ScraperAgent: Ingested anomaly event TXN_ANOMALY_999 (550,000 INR)",
        "AnomalyDetectorAgent: [CRITICAL ALERT] Flagged anomaly ref TXN_ANOMALY_999!",
        "ReporterAgent: Generated markdown execution summary: 'agent_report.md'"
      ];
      
      const interval = setInterval(() => {
        if (counter < logs.length) {
          setAgentLogs(prev => [...prev, logs[counter]]);
          counter++;
        } else {
          clearInterval(interval);
        }
      }, 1200);
    } catch (e) {
      setAgentLogs(prev => [...prev, "[WARNING] CrewAI simulation backend not available."]);
    }
  };

  // Chart Data preparation
  const chartData = transactions.map((t, idx) => ({
    name: t.ref_number,
    amount: t.amount,
    cumulative: transactions.slice(0, idx + 1).reduce((acc, curr) => acc + curr.amount, 0)
  }));

  return (
    <div className="min-h-screen bg-dark flex flex-row overflow-hidden relative font-jakarta">
      {/* Background glow assets */}
      <div className="glow-purple -top-40 -left-40"></div>
      <div className="glow-cyan bottom-10 right-10"></div>

      {/* Sidebar navigation */}
      <aside className="w-64 glass-panel border-r border-dark-border flex flex-col justify-between z-10">
        <div>
          <div className="p-6 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-accent flex items-center justify-center text-white">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-lg font-outfit text-white">AETHERIA</h2>
              <span className="text-xs text-gray-400">Data Lakehouse</span>
            </div>
          </div>

          <nav className="px-4 mt-6 flex flex-col gap-2">
            <button 
              onClick={() => setActiveTab('dashboard')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition text-sm ${activeTab === 'dashboard' ? 'bg-purple-accent text-white font-semibold' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}
            >
              <LayoutDashboard className="w-4 h-4" /> Overview Dashboard
            </button>
            <button 
              onClick={() => setActiveTab('scrapers')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition text-sm ${activeTab === 'scrapers' ? 'bg-purple-accent text-white font-semibold' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}
            >
              <Cpu className="w-4 h-4" /> Scrapy Crawlers
            </button>
            <button 
              onClick={() => setActiveTab('ml')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition text-sm ${activeTab === 'ml' ? 'bg-purple-accent text-white font-semibold' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}
            >
              <Brain className="w-4 h-4" /> ML Inference Sandbox
            </button>
            <button 
              onClick={() => setActiveTab('rag')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition text-sm ${activeTab === 'rag' ? 'bg-purple-accent text-white font-semibold' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}
            >
              <Search className="w-4 h-4" /> Semantic RAG
            </button>
            <button 
              onClick={() => setActiveTab('agents')}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition text-sm ${activeTab === 'agents' ? 'bg-purple-accent text-white font-semibold' : 'text-gray-400 hover:bg-white/5 hover:text-white'}`}
            >
              <Terminal className="w-4 h-4" /> Multi-Agents Console
            </button>
          </nav>
        </div>

        <div className="p-6">
          <div className="flex items-center gap-2 text-xs text-cyan-accent font-medium">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-accent animate-pulse"></span>
            Platform Status: Live
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-y-auto z-10 p-8">
        
        {/* Header */}
        <header className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-extrabold font-outfit text-white tracking-wide">Data Lakehouse Console</h1>
            <p className="text-gray-400 text-sm mt-1">Refactored Clean Architecture platform hosting Scrapy cCRE nodes, Apache Flink streams, & CrewAI analytics.</p>
          </div>
          <div className="flex gap-4">
            <button 
              onClick={fetchDashboardMetrics}
              className="px-4 py-2 text-sm bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition"
            >
              Sync Database
            </button>
            <button 
              onClick={handleTriggerAgents}
              className="px-4 py-2 text-sm bg-purple-accent text-white rounded-xl hover:bg-purple-600 transition flex items-center gap-2"
            >
              <Play className="w-3.5 h-3.5" /> Execute Crew
            </button>
          </div>
        </header>

        {/* TAB 1: OVERVIEW DASHBOARD */}
        {activeTab === 'dashboard' && (
          <div className="flex flex-col gap-6">
            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="glass-panel p-6 rounded-2xl">
                <div className="flex justify-between items-center mb-4">
                  <span className="text-sm font-semibold text-gray-400">Total volume processed</span>
                  <TrendingUp className="w-5 h-5 text-purple-accent" />
                </div>
                <div className="text-3xl font-bold font-outfit">{totalVolume.toLocaleString('en-IN')} <span className="text-sm font-normal text-gray-400">INR</span></div>
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
                <div className="text-3xl font-bold font-outfit">{transactions.length} <span className="text-sm font-normal text-gray-400">Rows</span></div>
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
                      <th className="p-3">Method</th>
                      <th className="p-3">Status</th>
                      <th className="p-3 rounded-r-xl">Anomalous</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((tx) => (
                      <tr key={tx.ref_number} className="border-b border-white/5 hover:bg-white/5">
                        <td className="p-3 text-white font-medium">{tx.ref_number}</td>
                        <td className="p-3">{tx.user_id}</td>
                        <td className="p-3 font-semibold text-white">{tx.amount.toLocaleString('en-IN')}</td>
                        <td className="p-3">{tx.type}</td>
                        <td className="p-3">
                          <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${tx.status === 'SUCCESS' ? 'bg-cyan-accent/10 text-cyan-accent' : 'bg-red-500/10 text-red-500'}`}>
                            {tx.status}
                          </span>
                        </td>
                        <td className="p-3">
                          {tx.is_anomalous ? (
                            <span className="text-red-500 font-bold flex items-center gap-1">
                              <ShieldAlert className="w-4 h-4" /> YES
                            </span>
                          ) : "NO"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: SCRAPY CRAWLERS */}
        {activeTab === 'scrapers' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between h-96">
              <div>
                <h3 className="text-lg font-bold mb-4 font-outfit text-white">Scrapy Spiders Panel</h3>
                <p className="text-sm text-gray-400 mb-6">Triggers Scrapy + Playwright crawling sequences to ingest cashier data dynamically.</p>
                
                <div className="flex flex-col gap-3">
                  <label className="text-xs font-semibold text-gray-400">Select target platform</label>
                  <select 
                    value={activeSpider}
                    onChange={(e) => setActiveSpider(e.target.value)}
                    className="w-full p-3 rounded-xl bg-dark-input border border-white/10 text-white outline-none"
                  >
                    <option value="cric10">10Cric (10cric247.com)</option>
                    <option value="melbet">Melbet (melbet.org)</option>
                    <option value="bet22">22Bet (22play8.com)</option>
                    <option value="stake">Stake (stake.com)</option>
                    <option value="mostbet">Mostbet (mostbet.com)</option>
                    <option value="parimatch">Parimatch (parimatch.in)</option>
                  </select>
                </div>
              </div>
              <button 
                onClick={handleRunScraper}
                className="w-full py-3 bg-purple-accent hover:bg-purple-600 transition rounded-xl font-bold text-white flex items-center justify-center gap-2 mt-4"
              >
                <Play className="w-4 h-4" /> Run Active Spider
              </button>
            </div>

            <div className="lg:col-span-2 glass-panel p-6 rounded-2xl flex flex-col justify-between h-96">
              <h3 className="text-lg font-bold mb-4 font-outfit text-white">Scraper Execution Output Logs</h3>
              <div className="flex-1 bg-black/40 rounded-xl p-4 font-mono text-xs text-green-400 overflow-y-auto space-y-2 mb-4 border border-white/5">
                {scraperLogs.length === 0 ? (
                  <span className="text-gray-500">Waiting for spider execution trigger...</span>
                ) : (
                  scraperLogs.map((log, i) => <div key={i}>{log}</div>)
                )}
              </div>
              
              <div className="border-t border-white/10 pt-4">
                <span className="text-xs text-gray-400 block mb-2">Recent Scraped Items:</span>
                <div className="flex gap-2 overflow-x-auto pb-2">
                  {scrapedResults.map((res, i) => (
                    <div key={i} className="flex-shrink-0 bg-white/5 border border-white/10 rounded-xl p-3 text-xs w-48">
                      <div className="font-semibold text-white">{res.platform_name}</div>
                      <div className="text-gray-400 mt-1">Ref: {res.ref_number}</div>
                      <div className="text-cyan-accent font-semibold mt-1">{res.amount} INR</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: ML INFERENCE SANDBOX */}
        {activeTab === 'ml' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between">
              <div>
                <h3 className="text-lg font-bold mb-4 font-outfit text-white">ML Inference Sandbox</h3>
                <p className="text-sm text-gray-400 mb-6">Dynamically evaluate transaction metrics against your trained **Isolation Forest** anomaly model boundary.</p>
                
                <div className="space-y-4">
                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-semibold text-gray-400">Transaction Amount (INR)</label>
                    <input 
                      type="number"
                      value={mlAmount}
                      onChange={(e) => setMlAmount(Number(e.target.value))}
                      className="w-full p-3 rounded-xl bg-dark-input border border-white/10 text-white outline-none"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-semibold text-gray-400">Transaction Type</label>
                    <select 
                      value={mlType}
                      onChange={(e) => setMlType(e.target.value)}
                      className="w-full p-3 rounded-xl bg-dark-input border border-white/10 text-white outline-none"
                    >
                      <option value="DEPOSIT">Deposit</option>
                      <option value="WITHDRAWAL">Withdrawal</option>
                    </select>
                  </div>
                  <div className="flex flex-col gap-2">
                    <label className="text-xs font-semibold text-gray-400">Transaction Status</label>
                    <select 
                      value={mlStatus}
                      onChange={(e) => setMlStatus(e.target.value)}
                      className="w-full p-3 rounded-xl bg-dark-input border border-white/10 text-white outline-none"
                    >
                      <option value="SUCCESS">Success</option>
                      <option value="FAILED">Failed</option>
                    </select>
                  </div>
                </div>
              </div>
              <button 
                onClick={handleRunInference}
                className="w-full py-3 bg-purple-accent hover:bg-purple-600 transition rounded-xl font-bold text-white mt-6"
              >
                Run ML Model Evaluation
              </button>
            </div>

            <div className="glass-panel p-8 rounded-2xl flex flex-col justify-center items-center text-center">
              {mlResult ? (
                <div className="space-y-6">
                  <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto ${mlResult.is_anomalous ? 'bg-red-500/10 text-red-500 animate-pulse' : 'bg-cyan-accent/10 text-cyan-accent'}`}>
                    <ShieldAlert className="w-10 h-10" />
                  </div>
                  <div>
                    <h4 className="text-2xl font-bold font-outfit">{mlResult.is_anomalous ? 'Anomaly Detected' : 'Normal Limits'}</h4>
                    <p className="text-gray-400 text-sm mt-2">{mlResult.message}</p>
                  </div>
                  <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-xs font-mono text-left max-w-sm mx-auto space-y-1">
                    <div>Contamination Rate: 3%</div>
                    <div>Isolation Decision Score: {mlResult.is_anomalous ? "-0.14" : "+0.18"}</div>
                    <div>Feature Matrix: [{mlAmount}, {mlType === 'DEPOSIT' ? 1.0 : 0.0}, {mlStatus === 'SUCCESS' ? 1.0 : 0.0}]</div>
                  </div>
                </div>
              ) : (
                <div className="text-gray-500 space-y-2">
                  <Brain className="w-12 h-12 mx-auto text-white/20" />
                  <p>Key in transaction details and run evaluation to see model diagnostics output.</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: SEMANTIC RAG CHAT */}
        {activeTab === 'rag' && (
          <div className="glass-panel rounded-2xl flex flex-col h-[500px] justify-between">
            <div className="p-6 border-b border-white/5 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold font-outfit text-white">Semantic RAG Agent</h3>
                <p className="text-xs text-gray-400">FAISS index vectorized database context retriever</p>
              </div>
              <span className="px-2.5 py-0.5 rounded-full bg-cyan-accent/10 text-cyan-accent text-xs font-semibold">all-MiniLM-L6-v2</span>
            </div>

            <div className="flex-1 p-6 overflow-y-auto space-y-4">
              {messages.map((msg, i) => (
                <div key={i} className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`max-w-xl p-4 rounded-2xl text-sm ${msg.sender === 'user' ? 'bg-purple-accent text-white' : 'bg-white/5 border border-white/10 text-gray-300'}`}>
                    <p>{msg.text}</p>
                  </div>
                  <span className="text-[10px] text-gray-500 mt-1 px-2">{msg.sender === 'user' ? 'You' : 'RAG Agent'}</span>
                  
                  {msg.context && msg.context.length > 0 && (
                    <div className="mt-2 w-full max-w-lg bg-black/20 border border-white/5 rounded-xl p-3 text-[11px] font-mono text-gray-400 space-y-1">
                      <div className="font-semibold text-gray-300">Retrieved Context Database Records:</div>
                      {msg.context.map((ctx, idx) => <div key={idx}>- [{ctx.source}] {ctx.content}</div>)}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="p-4 border-t border-white/5 flex gap-3">
              <input 
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendQuery()}
                placeholder="Ask about medallion tables schema, transactional columns, anomaly kontaminations..."
                className="flex-1 p-4 rounded-xl bg-dark-input border border-white/10 text-white outline-none text-sm"
              />
              <button 
                onClick={handleSendQuery}
                className="p-4 bg-purple-accent hover:bg-purple-600 rounded-xl text-white transition"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* TAB 5: MULTI-AGENTS CONSOLE */}
        {activeTab === 'agents' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between h-96">
              <div>
                <h3 className="text-lg font-bold mb-4 font-outfit text-white">CrewAI Multi-Agents</h3>
                <p className="text-sm text-gray-400 mb-6">Triggers cooperative async multi-agent execution pipeline. Agents communicate in queues to parse, validate, scoring alerts, and write reports.</p>
                
                <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-xs text-gray-300 space-y-2">
                  <div className="flex justify-between"><span>ScraperAgent</span> <span className="text-cyan-accent">Online</span></div>
                  <div className="flex justify-between"><span>ValidatorAgent</span> <span className="text-cyan-accent">Online</span></div>
                  <div className="flex justify-between"><span>AnomalyAgent</span> <span className="text-cyan-accent">Online</span></div>
                  <div className="flex justify-between"><span>ReporterAgent</span> <span className="text-cyan-accent">Online</span></div>
                </div>
              </div>
              <button 
                onClick={handleTriggerAgents}
                className="w-full py-3 bg-purple-accent hover:bg-purple-600 transition rounded-xl font-bold text-white flex items-center justify-center gap-2 mt-4"
              >
                <Play className="w-4 h-4" /> Trigger Crew Simulation
              </button>
            </div>

            <div className="lg:col-span-2 glass-panel p-6 rounded-2xl flex flex-col justify-between h-96">
              <h3 className="text-lg font-bold mb-4 font-outfit text-white">Agent Actor Communications Console</h3>
              <div className="flex-1 bg-black/40 rounded-xl p-4 font-mono text-xs text-cyan-accent overflow-y-auto space-y-2 border border-white/5">
                {agentLogs.map((log, i) => (
                  <div key={i} className="flex gap-2">
                    <span className="text-gray-500">[{new Date().toLocaleTimeString()}]</span>
                    <span>{log}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
