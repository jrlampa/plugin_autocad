import React from 'react';
import { Loader2 } from 'lucide-react';

export default function LoadingScreen() {
  return (
    <div className="fixed inset-0 bg-slate-900 flex flex-col items-center justify-center z-[5000]">
      <div className="relative flex flex-col items-center animate-enter">
        <div className="w-24 h-24 bg-gradient-to-br from-blue-600 to-blue-800 rounded-3xl shadow-2xl flex items-center justify-center mb-8 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
          <span className="text-5xl font-black text-white tracking-tighter">R</span>

          {/* Decorative Elements */}
          <div className="absolute -top-2 -right-2 w-6 h-6 bg-blue-400/30 rounded-full blur-xl animate-pulse"></div>
          <div className="absolute -bottom-2 -left-2 w-8 h-8 bg-purple-500/30 rounded-full blur-xl animate-pulse delay-75"></div>
        </div>

        <h1 className="text-3xl font-black text-white tracking-tight mb-2 flex items-center gap-3">
          sisRUA
          <span className="bg-white/10 px-2 py-0.5 rounded text-xs text-blue-300 font-bold border border-white/5 uppercase tracking-wider">Loading</span>
        </h1>
        <p className="text-slate-400 text-sm font-medium tracking-wide uppercase mb-12">Generative Urban Design System</p>

        <div className="flex items-center gap-3 bg-white/5 px-6 py-3 rounded-2xl border border-white/5 backdrop-blur-sm">
          <Loader2 className="animate-spin text-blue-400" size={20} />
          <span className="text-slate-300 text-xs font-bold animate-pulse">Inicializando motor de renderização...</span>
        </div>
      </div>

      <div className="absolute bottom-8 text-[10px] text-slate-600 font-mono">
        v0.5.0 &bull; Build 2026.01
      </div>
    </div>
  );
}
