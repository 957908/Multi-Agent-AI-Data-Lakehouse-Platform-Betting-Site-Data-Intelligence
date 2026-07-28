import React from 'react';
import { Sparkles, ArrowRight, Activity, Search } from 'lucide-react';

interface LandingPageProps {
  onEnterConsole: () => void;
  onEnterTab: (tab: 'dashboard' | 'scrapers' | 'ml' | 'rag' | 'agents') => void;
}

export default function LandingPage({ onEnterConsole, onEnterTab }: LandingPageProps) {
  const handleSelectTool = (tab: 'dashboard' | 'scrapers' | 'ml' | 'rag' | 'agents') => {
    onEnterTab(tab);
    onEnterConsole();
  };

  return (
    <div className="min-h-screen bg-[#0e1116] text-white flex flex-col font-jakarta relative overflow-hidden">
      {/* Background glow assets */}
      <div className="absolute top-[-20%] left-[-10%] w-[50vw] h-[50vw] bg-purple-accent/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[50vw] h-[50vw] bg-cyan-accent/5 rounded-full blur-[120px] pointer-events-none" />

      {/* HEADER NAVBAR */}
      <header className="w-full max-w-7xl mx-auto px-6 py-5 flex items-center justify-between z-10 border-b border-white/5">
        <div className="flex items-center gap-3 cursor-pointer" onClick={onEnterConsole}>
          {/* Custom logo: Football with graph chart overlay */}
          <div className="relative w-9 h-9 rounded-full bg-red-600/10 border border-red-500/20 flex items-center justify-center text-red-500">
            <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
              <path d="M2 12h20" />
            </svg>
            <div className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-red-600 border border-white/10 flex items-center justify-center text-[9px] font-bold text-white">
              <Activity className="w-2.5 h-2.5" />
            </div>
          </div>
          <span className="text-lg font-bold font-outfit text-white tracking-wide">Bet Metrics Lab</span>
        </div>

        {/* Center Menu Navigation */}
        <nav className="hidden md:flex items-center gap-8 text-xs font-semibold text-slate-400">
          <a href="#services" className="hover:text-white transition flex items-center gap-1">Services <span className="text-[9px] opacity-60">▼</span></a>
          <a href="#guides" className="hover:text-white transition flex items-center gap-1">Guides <span className="text-[9px] opacity-60">▼</span></a>
          <a href="#calculators" className="hover:text-white transition flex items-center gap-1">Calculators <span className="text-[9px] opacity-60">▼</span></a>
          <a href="#community" className="hover:text-white transition">Community</a>
          <a href="#pricing" className="hover:text-white transition">Pricing</a>
        </nav>

        {/* Right Controls */}
        <div className="flex items-center gap-5">
          <button 
            onClick={onEnterConsole} 
            className="text-xs font-semibold text-slate-300 hover:text-white transition"
          >
            Log In
          </button>
          <button 
            onClick={onEnterConsole} 
            className="px-5 py-2.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-full transition-all hover:shadow-[0_0_15px_rgba(220,38,38,0.4)] flex items-center gap-1.5"
          >
            Get Started Now
          </button>
          <Search className="w-4 h-4 text-slate-400 hover:text-white cursor-pointer hidden sm:block" />
        </div>
      </header>

      {/* HERO SECTION */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-6 py-12 md:py-20 flex flex-col lg:flex-row items-center gap-12 z-10">
        
        {/* Left Side: Glowing Glassmorphism Card */}
        <div className="flex-1 w-full max-w-xl">
          <div className="glass-panel p-8 md:p-10 rounded-3xl border border-white/10 bg-slate-900/30 shadow-[0_20px_50px_rgba(0,0,0,0.3)] relative overflow-hidden group">
            {/* Soft cyan/blue corner glow */}
            <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-accent/20 rounded-full blur-[30px] opacity-50 group-hover:opacity-80 transition-opacity" />
            <div className="absolute -left-10 -bottom-10 w-32 h-32 bg-purple-accent/10 rounded-full blur-[40px]" />

            <div className="flex items-center gap-2 px-3 py-1 bg-white/5 border border-white/10 rounded-full w-fit mb-6">
              <Sparkles className="w-3.5 h-3.5 text-cyan-accent" />
              <span className="text-[10px] font-bold tracking-widest text-cyan-accent uppercase">Professional Analytics Platform</span>
            </div>

            <h1 className="text-3xl md:text-4xl font-extrabold font-outfit text-white leading-tight mb-4">
              Free Betting Tools
            </h1>
            
            <p className="text-sm text-slate-400 leading-relaxed mb-6">
              Every gadget you need for analyzing your betting strategies:
            </p>

            <ul className="flex flex-col gap-4 text-xs font-medium text-slate-200 mb-8">
              <li 
                onClick={() => handleSelectTool('rag')}
                className="flex items-start gap-3 cursor-pointer group/item hover:text-purple-accent transition-colors"
              >
                <span className="text-red-500 mt-0.5">•</span>
                <div>
                  <strong className="text-white group-hover/item:text-purple-accent transition-colors">Football prediction service:</strong> Instant context summaries using semantic RAG model chatbot.
                </div>
              </li>
              <li 
                onClick={() => handleSelectTool('dashboard')}
                className="flex items-start gap-3 cursor-pointer group/item hover:text-purple-accent transition-colors"
              >
                <span className="text-red-500 mt-0.5">•</span>
                <div>
                  <strong className="text-white group-hover/item:text-purple-accent transition-colors">Bet Tracker:</strong> Real-time ledger monitoring for platform channels volume trends.
                </div>
              </li>
              <li 
                onClick={() => handleSelectTool('ml')}
                className="flex items-start gap-3 cursor-pointer group/item hover:text-purple-accent transition-colors"
              >
                <span className="text-red-500 mt-0.5">•</span>
                <div>
                  <strong className="text-white group-hover/item:text-purple-accent transition-colors">Bankroll simulator:</strong> ML outlier classifiers to evaluate anomaly flags.
                </div>
              </li>
              <li 
                onClick={() => handleSelectTool('agents')}
                className="flex items-start gap-3 cursor-pointer group/item hover:text-purple-accent transition-colors"
              >
                <span className="text-red-500 mt-0.5">•</span>
                <div>
                  <strong className="text-white group-hover/item:text-purple-accent transition-colors">Value betting simulator:</strong> Multi-Agent LangGraph verification audit runs.
                </div>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-red-500 mt-0.5">•</span>
                <span className="text-slate-400">Betting analytics & filtering, and many more, 100% free.</span>
              </li>
            </ul>

            <button 
              onClick={onEnterConsole} 
              className="px-6 py-3.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-xl transition-all hover:shadow-[0_0_20px_rgba(220,38,38,0.5)] flex items-center justify-center gap-2 group/btn"
            >
              Access Tools Console <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
            </button>
          </div>
        </div>

        {/* Right Side: Stadium Image Mockup */}
        <div className="flex-1 w-full flex items-center justify-center relative">
          <div className="relative w-full max-w-lg aspect-[16/9] rounded-2xl overflow-hidden border border-white/10 bg-[#121620] shadow-[0_30px_60px_rgba(0,0,0,0.6)] group hover:scale-[1.02] transition-all duration-500">
            {/* Glowing borders */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent z-10" />
            <img 
              src="/bet_metrics_stadium.png" 
              alt="Futuristic Bet Metrics Lab Stadium"
              className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-700"
            />
            {/* Dashboard Mockup overlay floating */}
            <div className="absolute bottom-4 right-4 z-20 w-44 rounded-xl border border-white/10 bg-slate-950/80 p-2.5 backdrop-blur shadow-2xl flex flex-col gap-1.5 animate-bounce-slow">
              <span className="text-[8px] font-bold text-slate-400 uppercase tracking-widest">Active Channels</span>
              <div className="h-1 bg-red-500 w-2/3 rounded" />
              <div className="h-1 bg-cyan-accent w-1/2 rounded" />
              <div className="h-1 bg-purple-accent w-4/5 rounded" />
            </div>
          </div>
        </div>

      </main>

      {/* FOOTER */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-8 text-center text-slate-600 text-[10px] tracking-wider border-t border-white/5 z-10">
        © {new Date().getFullYear()} BET METRICS LAB. ALL RIGHTS RESERVED. POWERED BY LANGGRAPH DATA PLATFORMS.
      </footer>
    </div>
  );
}
