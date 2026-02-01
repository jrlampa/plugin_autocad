
import React, { useEffect, useState } from 'react';
import {
  Activity,
  Database,
  Server,
  Key,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock
} from 'lucide-react';
import axios from 'axios';

// Polling Interval: 30s
const POLL_INTERVAL = 30000;

export default function HealthDashboard({ onClose }) {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHealth = async () => {
    try {
      // Direct call to avoid global interceptors loops if possible, 
      // but strictly we should use the configured axios instance.
      // Using global axios here for simplicity but pointing to the correct URL.
      // In production App.jsx configuration usually handles base URL, 
      // but here we might need to derive it if simple 'axios' is used.
      // Let's assume we can import 'api' or use relative path if proxy is set.
      // But 'api.js' has API_BASE. Let's use relative for now assuming Vite proxy or same origin.

      const API_BASE = (import.meta.env.VITE_API_URL || `/api/v1`).replace(/\/+$/, '');
      const res = await axios.get(`${API_BASE}/health/detailed`);
      setHealth(res.data);
      setError(null);
    } catch (err) {
      console.error("Health check failed", err);
      setError("Não foi possível conectar ao servidor.");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy': return 'text-emerald-500';
      case 'degraded': return 'text-amber-500';
      case 'unhealthy': return 'text-red-500';
      default: return 'text-slate-400';
    }
  };

  const StatusIcon = ({ status }) => {
    switch (status) {
      case 'healthy': return <CheckCircle2 size={16} className="text-emerald-500" />;
      case 'degraded': return <AlertTriangle size={16} className="text-amber-500" />;
      case 'unhealthy': return <XCircle size={16} className="text-red-500" />;
      default: return <Activity size={16} className="text-slate-400" />;
    }
  };

  if (loading && !health) {
    return (
      <div className="p-6 text-center text-slate-500 animate-pulse">
        <Activity className="mx-auto mb-2 animate-spin" />
        Verificando status do sistema...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 text-center text-red-500">
        <AlertTriangle className="mx-auto mb-2" />
        <p className="font-bold">{error}</p>
        <button onClick={fetchHealth} className="mt-4 text-xs underline">Tentar novamente</button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between pb-4 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <Activity size={20} className={getStatusColor(health?.system_status)} />
          <div>
            <h3 className="font-bold text-slate-700">Status do Sistema</h3>
            <p className="text-[10px] text-slate-400">
              Atualizado há {health ? 'poucos segundos' : '-'}
            </p>
          </div>
        </div>
        <div className={`px-2 py-1 rounded text-[10px] font-bold uppercase ${health?.system_status === 'healthy' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
          {health?.system_status}
        </div>
      </div>

      <div className="space-y-3">
        {/* Database */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
          <div className="flex items-center gap-3">
            <Database size={16} className="text-slate-500" />
            <span className="text-xs font-medium text-slate-700">Database</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-400">{health?.components?.database.latency_ms.toFixed(1)}ms</span>
            <StatusIcon status={health?.components?.database.status} />
          </div>
        </div>

        {/* Cache */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
          <div className="flex items-center gap-3">
            <Server size={16} className="text-slate-500" />
            <span className="text-xs font-medium text-slate-700">Redis/Cache</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-slate-400">{health?.components?.cache.latency_ms.toFixed(1)}ms</span>
            <StatusIcon status={health?.components?.cache.status} />
          </div>
        </div>

        {/* External APIs */}
        <div className="flex items-center justify-between p-3 bg-slate-50 rounded-xl">
          <div className="flex items-center gap-3">
            <Key size={16} className="text-slate-500" />
            <span className="text-xs font-medium text-slate-700">External APIs</span>
          </div>
          <StatusIcon status={health?.components?.external_apis.status} />
        </div>

        {/* Detail for External APIs */}
        <div className="pl-4 space-y-1">
          {Object.entries(health?.components?.external_apis.details || {}).map(([key, val]) => (
            <div key={key} className="flex justify-between text-[10px]">
              <span className="text-slate-500 uppercase">{key}</span>
              <span className={val ? "text-emerald-500" : "text-red-400"}>{val ? "CONFIGURADO" : "AUSENTE"}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
