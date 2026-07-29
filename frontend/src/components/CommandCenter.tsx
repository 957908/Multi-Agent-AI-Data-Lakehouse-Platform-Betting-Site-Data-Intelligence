import React, { useState, useEffect } from 'react';
import {
  Shield, Database, Activity, AlertTriangle, TrendingUp,
  CreditCard, RefreshCw, ExternalLink, Circle,
  ArrowUpRight, ArrowDownRight, Search, BarChart3,
  Wifi, WifiOff, Clock, Globe, Zap, ChevronRight,
  Layers, Server, Box, GitBranch
} from 'lucide-react';
import { apiService, StatsOverview, PlatformBreakdown } from '../services/api';

interface CommandCenterProps {
  onNavigate: (tab: string) => void;
}

const PLATFORM_COLORS: Record<string, string> = {
  'Melbet':  { bg: 'bg-red-500/10',    border: 'border-red-500/25',    text: 'text-red-400',    dot: 'bg-red-500'    } as any,
  '1xBet':   { bg: 'bg-blue-500/10',   border: 'border-blue-500/25',   text: 'text-blue-400',   dot: 'bg-blue-500'   } as any,
  '10Cric':  { bg: 'bg-emerald-500/10',border: 'border-emerald-500/25',text: 'text-emerald-400',dot: 'bg-emerald-500'} as any,
  '22play':  { bg: 'bg-amber-500/10',  border: 'border-amber-500/25',  text: 'text-amber-400',  dot: 'bg-amber-500'  } as any,
};

const METHOD_TYPE_COLORS: Record<string, string> = {
  UPI:    'bg-green-500/15 text-green-400 border-green-500/25',
  CRYPTO: 'bg-orange-500/15 text-orange-400 border-orange-500/25',
  BANK:   'bg-blue-500/15 text-blue-400 border-blue-500/25',
  WALLET: 'bg-purple-500/15 text-purple-400 border-purple-500/25',
  CARD:   'bg-cyan-500/15 text-cyan-400 border-cyan-500/25',
};

function fmt(n: number): string {
  if (n >= 10000000) return `₹${(n/10000000).toFixed(1)}Cr`;
  if (n >= 100000)  return `₹${(n/100000).toFixed(1)}L`;
  if (n >= 1000)    return `₹${(n/1000).toFixed(0)}K`;
  return `₹${n.toFixed(0)}`;
}

function PipelineStage({ label, status, reason }: { label: string; status: string; reason?: string }) {
  const isActive = status === 'ACTIVE' || status === 'AVAILABLE';
  const isOffline = status === 'OFFLINE';
  return (
    <div className="flex flex-col items-center gap-1">
      <div className={`w-full px-3 py-2 rounded-lg border text-[10px] font-bold text-center flex items-center justify-center gap-1.5 ${
        isActive  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
        isOffline ? 'bg-slate-800/60 border-white/5 text-slate-500' :
                    'bg-amber-500/10 border-amber-500/30 text-amber-400'
      }`}>
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isActive ? 'bg-emerald-400 animate-pulse' : isOffline ? 'bg-slate-600' : 'bg-amber-400 animate-pulse'}`} />
        {label}
      </div>
      {isOffline && reason && (
        <span className="text-[9px] text-slate-600 text-center leading-tight px-1">{reason.split('—')[0].trim()}</span>
      )}
    </div>
  );
}

function StatCard({ label, value, sub, icon: Icon, color, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left group bg-slate-900/40 border border-white/5 hover:border-white/10 rounded-2xl p-5 flex flex-col gap-3 transition-all hover:bg-slate-900/60`}
    >
      <div className="flex items-start justify-between">
        <div className={`p-2 rounded-lg border ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
        <ChevronRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-400 group-hover:translate-x-0.5 transition-all" />
      </div>
      <div>
        <div className="text-2xl font-extrabold font-outfit text-white">{value}</div>
        <div className="text-[11px] text-slate-400 mt-0.5 leading-tight">{label}</div>
        {sub && <div className="text-[10px] text-slate-600 mt-1">{sub}</div>}
      </div>
    </button>
  );
}

function PlatformPaymentCard({ platform, detail }: { platform: PlatformBreakdown; detail: any }) {
  const colors = (PLATFORM_COLORS[platform.name] || {
    bg: 'bg-slate-500/10', border: 'border-slate-500/25', text: 'text-slate-400', dot: 'bg-slate-500'
  }) as any;

  const methods = detail?.payment_methods || [];
  const typeGroups: Record<string, number> = {};
  methods.forEach((m: any) => {
    typeGroups[m.type] = (typeGroups[m.type] || 0) + 1;
  });

  return (
    <div className={`rounded-2xl border ${colors.border} ${colors.bg} p-5 flex flex-col gap-4`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${colors.dot}`} />
            <h3 className={`font-bold text-sm font-outfit ${colors.text}`}>{platform.name}</h3>
          </div>
          <a
            href={platform.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] text-slate-500 hover:text-slate-300 flex items-center gap-1 mt-0.5 transition-colors"
          >
            <Globe className="w-3 h-3" /> {platform.url}
          </a>
        </div>
        <div className={`px-2 py-1 rounded text-[9px] font-bold border ${
          platform.scan_status === 'DATA_AVAILABLE'
            ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
            : 'bg-slate-700/40 border-white/5 text-slate-500'
        }`}>
          {platform.scan_status === 'DATA_AVAILABLE' ? 'DATA AVAILABLE' : 'NO DATA'}
        </div>
      </div>

      {/* Transaction stats */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'Transactions', value: platform.transaction_count, sub: null },
          { label: 'Deposits', value: fmt(platform.deposit_volume), sub: null },
          { label: 'Anomalies', value: platform.anomaly_count, sub: null },
        ].map((s, i) => (
          <div key={i} className="bg-black/20 rounded-xl p-3 text-center">
            <div className="text-base font-bold text-white font-outfit">{s.value}</div>
            <div className="text-[9px] text-slate-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Payment method types used */}
      <div>
        <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider mb-2">
          Payment Methods Used ({methods.length})
        </div>
        {methods.length === 0 ? (
          <div className="text-[10px] text-slate-600 italic">Not Yet Collected — Deposit page scan required</div>
        ) : (
          <>
            {/* Type badges */}
            <div className="flex flex-wrap gap-1.5 mb-3">
              {Object.entries(typeGroups).map(([type, count]) => (
                <span key={type} className={`px-2 py-0.5 text-[9px] font-bold rounded border ${METHOD_TYPE_COLORS[type] || 'bg-slate-700 text-slate-400 border-white/5'}`}>
                  {type} × {count}
                </span>
              ))}
            </div>
            {/* Top 5 methods */}
            <div className="flex flex-col gap-1">
              {methods.slice(0, 5).map((m: any, i: number) => (
                <div key={i} className="flex items-center justify-between bg-black/20 rounded-lg px-2.5 py-1.5">
                  <span className="text-[10px] text-slate-300 font-medium truncate max-w-[140px]">{m.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] text-slate-500">{m.transaction_count}×</span>
                    <span className={`px-1.5 py-0.5 text-[8px] font-bold rounded border ${METHOD_TYPE_COLORS[m.type] || 'bg-slate-700 text-slate-400 border-white/5'}`}>
                      {m.type}
                    </span>
                  </div>
                </div>
              ))}
              {methods.length > 5 && (
                <div className="text-[9px] text-slate-500 text-center pt-1">+{methods.length - 5} more methods</div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Data source note */}
      <div className="text-[9px] text-slate-600 border-t border-white/5 pt-3 flex items-center gap-1">
        <Database className="w-3 h-3" />
        Source: SQLite — real transaction records
      </div>
    </div>
  );
}

export default function CommandCenter({ onNavigate }: CommandCenterProps) {
  const [stats, setStats] = useState<StatsOverview | null>(null);
  const [platformDetails, setPlatformDetails] = useState<Record<number, any>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const overview = await apiService.getStatsOverview();
      setStats(overview);
      // Fetch detail for each platform (for payment methods)
      const details: Record<number, any> = {};
      await Promise.all(
        overview.platforms_breakdown.map(async (p) => {
          try {
            details[p.id] = await apiService.getPlatformDetail(p.id);
          } catch { details[p.id] = null; }
        })
      );
      setPlatformDetails(details);
      setLastRefresh(new Date());
    } catch {
      setError('Backend Offline — Start uvicorn to see real data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-96 gap-4">
      <div className="w-10 h-10 border-2 border-red-500/30 border-t-red-500 rounded-full animate-spin" />
      <p className="text-slate-400 text-sm">Loading real data from database...</p>
    </div>
  );

  if (error) return (
    <div className="flex flex-col items-center justify-center h-96 gap-4">
      <WifiOff className="w-12 h-12 text-slate-600" />
      <p className="text-slate-400 text-sm font-semibold">{error}</p>
      <code className="text-xs text-slate-500 bg-black/40 px-3 py-1.5 rounded">
        uvicorn backend.app.main:app --reload --port 8085
      </code>
      <button onClick={fetchData} className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-lg transition-all">
        <RefreshCw className="w-3.5 h-3.5" /> Retry Connection
      </button>
    </div>
  );

  const t = stats!.totals;
  const pipelineStatus = stats!.pipeline_status;

  return (
    <div className="flex flex-col gap-8 pb-10">

      {/* ── Header ── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-extrabold font-outfit text-white flex items-center gap-2">
            <Shield className="w-5 h-5 text-red-400" /> SentinelX Command Center
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            All data sourced from real database records · No fabricated values
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastRefresh && (
            <span className="text-[10px] text-slate-500 flex items-center gap-1">
              <Clock className="w-3 h-3" /> Refreshed {lastRefresh.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10 hover:bg-white/10 text-white text-xs font-semibold rounded-lg transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
          <button
            onClick={() => onNavigate('scan')}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-lg transition-all hover:shadow-[0_0_15px_rgba(220,38,38,0.4)]"
          >
            <Search className="w-3.5 h-3.5" /> New Scan
          </button>
        </div>
      </div>

      {/* ── KPI Stats ── */}
      <div>
        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">
          Platform Overview — {stats!.source}
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <StatCard label="Platforms Monitored" value={t.platforms} icon={Globe}
            color="bg-red-500/10 border-red-500/20 text-red-400"
            onClick={() => onNavigate('platforms')} />
          <StatCard label="Total Transactions" value={t.transactions} icon={Activity}
            color="bg-blue-500/10 border-blue-500/20 text-blue-400"
            sub={`${t.deposits} deposits · ${t.withdrawals} withdrawals`}
            onClick={() => onNavigate('transactions')} />
          <StatCard label="Payment Methods" value={t.payment_methods} icon={CreditCard}
            color="bg-purple-500/10 border-purple-500/20 text-purple-400"
            onClick={() => onNavigate('payments')} />
          <StatCard label="Anomalies Detected" value={t.anomalous_transactions} icon={AlertTriangle}
            color="bg-amber-500/10 border-amber-500/20 text-amber-400"
            sub={`${((t.anomalous_transactions / Math.max(t.transactions,1)) * 100).toFixed(1)}% of all transactions`}
            onClick={() => onNavigate('transactions')} />
          <StatCard label="Successful" value={t.successful_transactions} icon={TrendingUp}
            color="bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
            sub={`${((t.successful_transactions / Math.max(t.transactions,1)) * 100).toFixed(1)}% success rate`}
            onClick={() => onNavigate('transactions')} />
          <StatCard label="Failed" value={t.failed_transactions} icon={AlertTriangle}
            color="bg-rose-500/10 border-rose-500/20 text-rose-400"
            onClick={() => onNavigate('transactions')} />
        </div>
      </div>

      {/* ── Platform → Payment Method Map (MAIN FEATURE) ── */}
      <div>
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div>
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
              Platform Payment Intelligence
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Which betting platform uses which payment methods — sourced from {t.transactions} real transactions
            </p>
          </div>
          <button
            onClick={() => onNavigate('payments')}
            className="text-[10px] text-slate-400 hover:text-white flex items-center gap-1 transition-colors"
          >
            View All Payment Methods <ChevronRight className="w-3 h-3" />
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {stats!.platforms_breakdown.map((platform) => (
            <PlatformPaymentCard
              key={platform.id}
              platform={platform}
              detail={platformDetails[platform.id]}
            />
          ))}
        </div>
      </div>

      {/* ── Payment Methods Breakdown + Top Methods ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By Type */}
        <div className="bg-slate-900/40 border border-white/5 rounded-2xl p-5">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">
            Payment Method Types — All {t.payment_methods} Methods
          </div>
          <div className="flex flex-col gap-2">
            {Object.entries(stats!.payment_methods_by_type).map(([type, count]) => {
              const pct = Math.round((count / t.payment_methods) * 100);
              return (
                <div key={type} className="flex flex-col gap-1">
                  <div className="flex items-center justify-between">
                    <span className={`px-2 py-0.5 text-[9px] font-bold rounded border ${METHOD_TYPE_COLORS[type] || 'bg-slate-700 text-slate-400 border-white/5'}`}>
                      {type}
                    </span>
                    <span className="text-xs text-slate-300 font-bold">{count} <span className="text-slate-500 font-normal text-[10px]">({pct}%)</span></span>
                  </div>
                  <div className="h-1.5 bg-black/40 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        type === 'CRYPTO' ? 'bg-orange-500' :
                        type === 'UPI' ? 'bg-green-500' :
                        type === 'BANK' ? 'bg-blue-500' : 'bg-purple-500'
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="text-[9px] text-slate-600 mt-4 flex items-center gap-1">
            <Database className="w-3 h-3" /> Source: payment_methods table — real scraped data
          </div>
        </div>

        {/* Top Methods by Usage */}
        <div className="bg-slate-900/40 border border-white/5 rounded-2xl p-5">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">
            Most Used Payment Methods (by transaction count)
          </div>
          {stats!.top_payment_methods.length === 0 ? (
            <div className="text-sm text-slate-500 italic">No Data Available</div>
          ) : (
            <div className="flex flex-col gap-2">
              {stats!.top_payment_methods.slice(0, 8).map((m, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-[10px] text-slate-600 w-4 shrink-0">#{i+1}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] text-slate-300 font-medium truncate">{m.name}</span>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-[10px] text-slate-400">{m.transaction_count}×</span>
                        <span className={`px-1.5 py-0.5 text-[8px] font-bold rounded border ${METHOD_TYPE_COLORS[m.type] || ''}`}>
                          {m.type}
                        </span>
                      </div>
                    </div>
                    <div className="h-1 bg-black/40 rounded-full mt-1 overflow-hidden">
                      <div
                        className="h-full bg-white/20 rounded-full"
                        style={{ width: `${Math.min(100, (m.transaction_count / (stats!.top_payment_methods[0]?.transaction_count || 1)) * 100)}%` }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div className="text-[9px] text-slate-600 mt-4 flex items-center gap-1">
            <Database className="w-3 h-3" /> Source: transactions JOIN payment_methods — {t.transactions} real records
          </div>
        </div>
      </div>

      {/* ── Pipeline Status ── */}
      <div className="bg-slate-900/40 border border-white/5 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div>
            <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Live Pipeline Status</div>
            <p className="text-[10px] text-slate-600 mt-0.5">
              Mode: <span className="text-amber-400 font-bold">DIRECT DB</span> — Docker not running · Kafka/Spark offline
            </p>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 bg-amber-500/10 border border-amber-500/25 rounded-lg">
            <Server className="w-3 h-3 text-amber-400" />
            <span className="text-[10px] text-amber-400 font-bold">Direct Mode</span>
          </div>
        </div>
        <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-2">
          {[
            { key: 'playwright', label: 'Playwright' },
            { key: 'kafka', label: 'Kafka' },
            { key: 'bronze', label: 'Bronze' },
            { key: 'spark', label: 'Spark' },
            { key: 'silver', label: 'Silver' },
            { key: 'gold', label: 'Gold' },
            { key: 'postgresql', label: 'PostgreSQL' },
            { key: 'sqlite', label: 'SQLite ✓' },
          ].map((stage) => (
            <PipelineStage
              key={stage.key}
              label={stage.label}
              status={pipelineStatus[stage.key]?.status || 'UNKNOWN'}
              reason={pipelineStatus[stage.key]?.reason}
            />
          ))}
        </div>
        <div className="text-[9px] text-slate-600 mt-3">
          Start Docker and run <code className="text-slate-400">docker-compose up -d</code> to enable full Kafka → Spark pipeline
        </div>
      </div>

      {/* ── Quick Actions ── */}
      <div>
        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">Quick Actions</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'New Platform Scan', sub: 'Scrape deposit page', icon: Search, color: 'bg-red-600 hover:bg-red-700 text-white border-red-600', tab: 'scan' },
            { label: 'View Transactions', sub: `${t.transactions} records available`, icon: Activity, color: 'bg-white/5 hover:bg-white/10 text-slate-200 border-white/10', tab: 'transactions' },
            { label: 'Payment Methods', sub: `${t.payment_methods} methods tracked`, icon: CreditCard, color: 'bg-white/5 hover:bg-white/10 text-slate-200 border-white/10', tab: 'payments' },
            { label: 'Knowledge Graph', sub: 'Platform entity map', icon: GitBranch, color: 'bg-white/5 hover:bg-white/10 text-slate-200 border-white/10', tab: 'knowledge' },
            { label: 'ML Sandbox', sub: 'Anomaly detection', icon: Zap, color: 'bg-white/5 hover:bg-white/10 text-slate-200 border-white/10', tab: 'ml' },
            { label: 'RAG Chat', sub: 'Query from DB only', icon: Search, color: 'bg-white/5 hover:bg-white/10 text-slate-200 border-white/10', tab: 'rag' },
            { label: 'Agent Console', sub: '20-agent workflow', icon: Layers, color: 'bg-white/5 hover:bg-white/10 text-slate-200 border-white/10', tab: 'agents' },
            { label: 'View Reports', sub: 'Audit & change reports', icon: BarChart3, color: 'bg-white/5 hover:bg-white/10 text-slate-200 border-white/10', tab: 'reports' },
          ].map((a, i) => (
            <button
              key={i}
              onClick={() => onNavigate(a.tab)}
              className={`flex items-center gap-3 px-4 py-3.5 rounded-xl border font-semibold text-left transition-all ${a.color}`}
            >
              <a.icon className="w-4 h-4 shrink-0" />
              <div className="min-w-0">
                <div className="text-xs font-bold truncate">{a.label}</div>
                <div className="text-[10px] opacity-60 truncate">{a.sub}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Empty states for uncollected data ── */}
      {(t.reviews === 0 || t.complaints === 0 || t.news_articles === 0) && (
        <div className="bg-slate-900/20 border border-white/5 rounded-2xl p-5">
          <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">Data Not Yet Collected</div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {t.reviews === 0 && (
              <div className="flex flex-col gap-1 p-3 rounded-xl border border-dashed border-white/10">
                <span className="text-xs font-semibold text-slate-400">Reviews</span>
                <span className="text-[10px] text-slate-600">No Reviews Collected — Deposit page scan required</span>
              </div>
            )}
            {t.complaints === 0 && (
              <div className="flex flex-col gap-1 p-3 rounded-xl border border-dashed border-white/10">
                <span className="text-xs font-semibold text-slate-400">Complaints</span>
                <span className="text-[10px] text-slate-600">No Complaints Collected — Authentication may be required</span>
              </div>
            )}
            {t.news_articles === 0 && (
              <div className="flex flex-col gap-1 p-3 rounded-xl border border-dashed border-white/10">
                <span className="text-xs font-semibold text-slate-400">News Articles</span>
                <span className="text-[10px] text-slate-600">No News Collected — Scraping required</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
