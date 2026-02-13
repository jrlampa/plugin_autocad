import React, { useEffect } from 'react';
import { AlertTriangle, CheckCircle2, X, Info } from 'lucide-react';

export default function Toast({ message, type = 'info', onClose, duration = 5000 }) {
  useEffect(() => {
    if (duration) {
      const timer = setTimeout(onClose, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const bgColors = {
    error: 'bg-red-100 border-red-200 text-red-800',
    success: 'bg-emerald-100 border-emerald-200 text-emerald-800',
    warning: 'bg-amber-100 border-amber-200 text-amber-800',
    info: 'bg-blue-100 border-blue-200 text-blue-800',
  };

  const icons = {
    error: <AlertTriangle size={20} />,
    success: <CheckCircle2 size={20} />,
    warning: <AlertTriangle size={20} />,
    info: <Info size={20} />,
  };

  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[5000] animate-in slide-in-from-top duration-300">
      <div
        className={`px-4 py-3 rounded-full shadow-2xl flex items-center gap-3 border ${bgColors[type] || bgColors.info}`}
      >
        {icons[type] || icons.info}
        <span className="text-xs font-bold mr-2">{message}</span>
        <button onClick={onClose} className="hover:bg-black/5 rounded-full p-1 transition-colors">
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
