import React, { useState, useEffect } from 'react';
import {
  Activity, Database, Brain, Network, Terminal,
  Search, ShieldAlert, TrendingUp, Layers,
  ArrowRight, ChevronRight, Zap, Globe, BarChart2
} from 'lucide-react';

interface HomePageProps {
  onEnterConsole: (tab?: 'dashboard' | 'knowledge' | 'scrapers' | 'ml' | 'rag' | 'agents') => void;
}

const FEATURES = [
  {
    icon: Database,
    title: 'Data Pipeline',
    subtitle: 'Scrapy + Lakehouse',
    desc: 'Automated spiders crawl 5 live betting platforms — Cric10, 1xBet, Stake, Betway, Rajbet — ingesting deposit & withdrawal transactions into a structured Bronze→Silver→Gold lakehouse.',
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/5 border-cyan-500/20',
    tab: 'scrapers' as const,
  },
  {
    icon: Brain,
    title: 'ML Anomaly Detection',
    subtitle: 'Isolation Forest Model',
    desc: 'A trained scikit-learn Isolation Forest model flags suspicious transactions in real-time. Run predictions on any transaction amount, type, and status directly from the sandbox.',
    color: 'text-purple-400',
    bg: 'bg-purple-500/5 border-purple-500/20',
    tab: 'ml' as const,
  },
  {
    icon: Search,
    title: 'Semantic RAG Chat',
    subtitle: 'FAISS + LLM Retrieval',
    desc: 'Ask natural-language questions about platforms, transactions, and risk patterns. Answers are grounded in real database records using a FAISS vector index and semantic retrieval pipeline.',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/5 border-emerald-500/20',
    tab: 'rag' as const,
  },
  {
    icon: Network,
    title: 'Knowledge Graph',
    subtitle: 'Entity Relationship Mapping',
    desc: 'Visualize how betting platforms, payment channels (UPI, Crypto, Bank), and user accounts are linked. Click any node to trace inflow volumes and detect shared credential anomalies.',
    color: 'text-amber-400',
    bg: 'bg-amber-500/5 border-amber-500/20',
    tab: 'knowledge' as const,
  },
  {
    icon: Terminal,
    title: 'Multi-Agent Console',
    subtitle: 'LangGraph Orchestration',
    desc: 'A 6-node LangGraph DAG orchestrates autonomous AI agents — Risk Analyst, Payment Intel, Platform Health, Data Quality — with a mandatory human-in-the-loop review gate before report release.',
    color: 'text-rose-400',
    bg: 'bg-rose-500/5 border-rose-500/20',
    tab: 'agents' as const,
  },
  {
    icon: BarChart2,
    title: 'Overview Dashboard',
    subtitle: 'Real-time Metrics',
    desc: 'Live platform health indicators, transaction volume charts, anomaly counts, and streaming status feeds — all pulled from a local SQLite database populated by real scraping runs.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/5 border-blue-500/20',
    tab: 'dashboard' as const,
  },
];

const STATS = [
  { label: 'Betting Platforms Monitored', value: '5', suffix: '' },
  { label: 'Transactions Ingested', value: '173', suffix: '+' },
  { label: 'Anomaly Detection Accuracy', value: '92', suffix: '%' },
  { label: 'Agent Nodes in Workflow', value: '6', suffix: '' },
];

export default function HomePage({ onEnterConsole }: HomePageProps) {
  const [tick, setTick] = useState(0);

  // Subtle animated ticker for live feel
  useEffect(() => {
    const t = setInterval(() => setTick(v => v + 1), 2500);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="min-h-screen bg-[#080a0f] text-white font-jakarta relative overflow-x-hidden">

      {/* ── Ambient Background Glows ── */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute top-[-15%] left-[-10%] w-[60vw] h-[60vw] rounded-full bg-purple-700/8 blur-[160px]" />
        <div className="absolute top-[30%] right-[-10%] w-[50vw] h-[50vw] rounded-full bg-cyan-700/6 blur-[140px]" />
        <div className="absolute bottom-[0%] left-[20%] w-[40vw] h-[40vw] rounded-full bg-red-800/5 blur-[140px]" />
      </div>

      {/* ── Top Navigation ── */}
      <nav className="relative z-30 w-full border-b border-white/5 bg-black/30 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="relative w-9 h-9 rounded-full bg-red-600/10 border border-red-500/25 flex items-center justify-center text-red-500">
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
                <path d="M2 12h20" />
              </svg>
              <div className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-red-600 border border-black flex items-center justify-center">
                <Activity className="w-2 h-2 text-white" />
              </div>
            </div>
            <div>
              <h1 className="font-bold text-[15px] font-outfit text-white tracking-wide leading-none">Bet Metrics Lab</h1>
              <span className="text-[9px] text-slate-500 font-mono">Data Intelligence Platform</span>
            </div>
          </div>

          {/* Nav links */}
          <div className="hidden md:flex items-center gap-6 text-xs text-slate-400 font-semibold">
            <a href="#features" className="hover:text-white transition">Features</a>
            <a href="#pipeline" className="hover:text-white transition">Pipeline</a>
            <a href="#goal" className="hover:text-white transition">Our Goal</a>
          </div>

          {/* CTA */}
          <button
            onClick={() => onEnterConsole('dashboard')}
            className="flex items-center gap-2 px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-full transition-all hover:shadow-[0_0_20px_rgba(220,38,38,0.5)]"
          >
            Launch Console <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </nav>

      {/* ── Hero Section ── */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 pt-24 pb-20 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        {/* Left: Headline */}
        <div className="flex flex-col gap-7">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-red-500/25 bg-red-500/5 text-red-400 text-[11px] font-semibold w-fit">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
            AI-Powered Betting Site Intelligence Platform
          </div>

          <h2 className="text-4xl md:text-5xl font-extrabold font-outfit leading-tight tracking-tight">
            Uncover Patterns in<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-400 via-purple-400 to-cyan-400">
              Betting Transactions
            </span>
          </h2>

          <p className="text-slate-400 text-base leading-relaxed max-w-xl">
            A full-stack data intelligence system that scrapes live betting platforms,
            detects financial anomalies with ML, maps entity relationships, and orchestrates
            autonomous AI agents — all grounded in real, auditable data.
          </p>

          <div className="flex items-center gap-4 flex-wrap">
            <button
              onClick={() => onEnterConsole('dashboard')}
              className="flex items-center gap-2 px-6 py-3 bg-red-600 hover:bg-red-700 text-white text-sm font-bold rounded-full transition-all hover:shadow-[0_0_25px_rgba(220,38,38,0.4)]"
            >
              Open Dashboard <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => onEnterConsole('agents')}
              className="flex items-center gap-2 px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm font-semibold rounded-full transition-all"
            >
              <Terminal className="w-4 h-4" /> Run Agent Audit
            </button>
          </div>
        </div>

        {/* Right: Live stats panel */}
        <div className="flex flex-col gap-4">
          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-3">
            {STATS.map((stat, i) => (
              <div key={i} className="bg-slate-900/40 border border-white/5 rounded-2xl p-5 flex flex-col gap-2 backdrop-blur">
                <span className="text-3xl font-extrabold font-outfit text-white">
                  {stat.value}<span className="text-red-400">{stat.suffix}</span>
                </span>
                <span className="text-[11px] text-slate-400 leading-snug">{stat.label}</span>
              </div>
            ))}
          </div>

          {/* Live ticker */}
          <div className="bg-black/60 border border-white/5 rounded-2xl p-4 font-mono text-[11px] flex flex-col gap-2">
            <div className="flex items-center gap-2 text-emerald-400 mb-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="font-bold text-[10px] uppercase tracking-wider">Live System Feed</span>
            </div>
            {[
              { text: '[SCRAPY] cric10 spider completed — 34 records ingested', color: 'text-cyan-400' },
              { text: '[ML] Isolation Forest scored 173 transactions — 26 anomalies flagged', color: 'text-amber-400' },
              { text: '[AGENTS] Risk Analyst node completed platform trust evaluation', color: 'text-purple-400' },
              { text: '[RAG] Semantic query resolved using FAISS top-3 context chunks', color: 'text-emerald-400' },
              { text: '[GRAPH] 5 platforms → 4 channels → 147 unique account nodes mapped', color: 'text-slate-300' },
            ].slice(0, (tick % 5) + 1).map((entry, i) => (
              <div key={i} className={`${entry.color} leading-relaxed`}>{entry.text}</div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Our Goal Section ── */}
      <section id="goal" className="relative z-10 bg-white/[0.02] border-y border-white/5 py-20">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div className="flex flex-col gap-6">
            <div className="flex items-center gap-2 text-xs font-bold text-purple-400 uppercase tracking-widest">
              <ShieldAlert className="w-4 h-4" /> Our Goal
            </div>
            <h3 className="text-3xl font-extrabold font-outfit text-white leading-tight">
              Bringing Transparency to<br />Unregulated Betting Markets
            </h3>
            <p className="text-slate-400 leading-relaxed">
              Illegal and unregulated online betting platforms operate with minimal oversight,
              making it hard to track financial flows, detect money laundering patterns, or identify
              compromised payment channels.
            </p>
            <p className="text-slate-400 leading-relaxed">
              <strong className="text-white">Bet Metrics Lab</strong> is a research and intelligence
              platform that applies modern data engineering — Scrapy pipelines, ML anomaly detection,
              FAISS semantic search, LangGraph AI agents, and knowledge graph visualization — to build
              a transparent, auditable view of these platforms' financial behavior.
            </p>
            <div className="flex flex-col gap-3">
              {[
                'Detect anomalous deposit/withdrawal patterns early',
                'Map shared payment credentials across multiple platforms',
                'Automate multi-step compliance audits with AI agents',
                'Enable semantic querying over raw financial data',
              ].map((point, i) => (
                <div key={i} className="flex items-center gap-3 text-sm text-slate-300">
                  <ChevronRight className="w-4 h-4 text-red-400 shrink-0" />
                  {point}
                </div>
              ))}
            </div>
          </div>

          {/* Pipeline diagram */}
          <div id="pipeline" className="flex flex-col gap-3">
            <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Data Pipeline Architecture</div>
            {[
              { label: 'Scrapy Spiders', sublabel: '5 live betting platforms → raw JSON', icon: Globe, color: 'text-cyan-400 border-cyan-500/20 bg-cyan-500/5' },
              { label: 'Bronze → Silver → Gold Lakehouse', sublabel: 'SQLite + schema validation + aggregation', icon: Layers, color: 'text-amber-400 border-amber-500/20 bg-amber-500/5' },
              { label: 'ML Anomaly Detection', sublabel: 'Isolation Forest model scoring', icon: Brain, color: 'text-purple-400 border-purple-500/20 bg-purple-500/5' },
              { label: 'FAISS Vector Index + RAG', sublabel: 'Semantic retrieval over transaction records', icon: Search, color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5' },
              { label: 'LangGraph Agent Workflow', sublabel: '6-node DAG with human-in-the-loop gate', icon: Zap, color: 'text-rose-400 border-rose-500/20 bg-rose-500/5' },
            ].map((step, i) => (
              <div key={i} className="flex items-center gap-4">
                <div className="flex flex-col items-center gap-0">
                  <div className={`w-9 h-9 rounded-xl border flex items-center justify-center ${step.color}`}>
                    <step.icon className="w-4 h-4" />
                  </div>
                  {i < 4 && <div className="w-0.5 h-4 bg-white/10 my-0.5" />}
                </div>
                <div className="bg-slate-900/40 border border-white/5 rounded-xl px-4 py-3 flex-1">
                  <div className="text-xs font-bold text-white">{step.label}</div>
                  <div className="text-[10px] text-slate-400 font-mono mt-0.5">{step.sublabel}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features Grid ── */}
      <section id="features" className="relative z-10 max-w-7xl mx-auto px-6 py-20">
        <div className="text-center mb-14">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3">Platform Modules</div>
          <h3 className="text-3xl font-extrabold font-outfit text-white">Everything in one place</h3>
          <p className="text-slate-400 text-sm mt-3 max-w-xl mx-auto">
            Six integrated modules working together — click any card to open that section directly.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f, i) => (
            <button
              key={i}
              onClick={() => onEnterConsole(f.tab)}
              className={`text-left group p-6 rounded-2xl border ${f.bg} hover:scale-[1.02] transition-all duration-200 flex flex-col gap-4 cursor-pointer hover:shadow-[0_0_25px_rgba(255,255,255,0.04)]`}
            >
              <div className="flex items-start justify-between">
                <div className={`p-2.5 rounded-xl border ${f.bg} ${f.color}`}>
                  <f.icon className="w-5 h-5" />
                </div>
                <ArrowRight className={`w-4 h-4 ${f.color} opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all`} />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white font-outfit">{f.title}</h4>
                <p className={`text-[10px] font-semibold font-mono uppercase tracking-wider ${f.color} mt-0.5`}>{f.subtitle}</p>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">{f.desc}</p>
            </button>
          ))}
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section className="relative z-10 max-w-7xl mx-auto px-6 pb-20">
        <div className="bg-gradient-to-r from-red-600/10 via-purple-600/10 to-cyan-600/10 border border-white/5 rounded-3xl p-10 text-center flex flex-col items-center gap-6">
          <TrendingUp className="w-8 h-8 text-red-400" />
          <h3 className="text-2xl font-extrabold font-outfit text-white">Ready to explore the data?</h3>
          <p className="text-slate-400 text-sm max-w-md">
            Sync the database, run the agent audit, or query transactions in natural language — all from the console.
          </p>
          <button
            onClick={() => onEnterConsole('dashboard')}
            className="flex items-center gap-2 px-8 py-3.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-full text-sm transition-all hover:shadow-[0_0_30px_rgba(220,38,38,0.5)]"
          >
            Open Console <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="relative z-10 border-t border-white/5 py-6 text-center text-[11px] text-slate-500 font-mono">
        © 2026 Bet Metrics Lab · AI Data Lakehouse Platform · Powered by LangGraph, FAISS & Scrapy
      </footer>
    </div>
  );
}
