import React from 'react';
import { Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function JobOverlay({ uiJob }) {
  if (!uiJob) return null;

  return (
    <div className="bg-white/60 rounded-3xl border border-white/80 p-6 flex flex-col gap-4 shadow-lg animate-enter ring-1 ring-black/5 mt-4">
      <div className="flex justify-between items-start pb-3 border-b border-slate-200/50">
        <div className="flex items-center gap-3">
          <div
            className={`p-2 rounded-xl ${uiJob.status === 'completed' ? 'bg-emerald-100 text-emerald-600' : uiJob.status === 'failed' ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'}`}
          >
            {uiJob.status === 'completed' ? (
              <CheckCircle2 size={20} />
            ) : uiJob.status === 'failed' ? (
              <AlertTriangle size={20} />
            ) : (
              <Loader2 size={20} className="animate-spin" />
            )}
          </div>
          <div className="flex flex-col">
            <span
              className={`text-xs font-black uppercase tracking-wide ${uiJob.status === 'failed' ? 'text-red-600' : 'text-slate-700'}`}
            >
              {uiJob.status === 'queued'
                ? 'Aguardando'
                : uiJob.status === 'processing'
                  ? 'Processando'
                  : 'Concluído'}
            </span>
            {uiJob.message && uiJob.status !== 'completed' && uiJob.status !== 'failed' && (
              <span className="text-[10px] text-slate-500 font-medium animate-pulse">
                {uiJob.message}
              </span>
            )}
          </div>
        </div>
        <div className="text-[10px] font-mono text-slate-500">
          {typeof uiJob.progress === 'number' ? `${Math.round(uiJob.progress * 100)}%` : ''}
        </div>
      </div>

      {typeof uiJob.progress === 'number' && (
        <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
          <div
            className="h-2 bg-blue-500"
            style={{
              width: `${Math.max(0, Math.min(100, Math.round(uiJob.progress * 100)))}%`,
            }}
          />
        </div>
      )}
    </div>
  );
}
