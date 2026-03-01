import React, { useState, useEffect, useCallback } from 'react';
import { Zap, Shield, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { api } from '../api';

const CLASSES_TENSAO = [
  { value: 'BT', label: 'BT — Baixa Tensão (≤ 1 kV)', buffer: 1.0 },
  { value: 'MT', label: 'MT — Média Tensão (1–36,2 kV)', buffer: 3.0 },
  { value: 'AT', label: 'AT — Alta Tensão (> 36,2 kV)', buffer: 10.0 },
];

/**
 * NormaPanel — Painel de configuração de norma técnica ativa (ABNT / ANEEL/PRODIST).
 *
 * Quando PRODIST é ativado, exibe toast informando que as regras ABNT foram
 * substituídas pelas normas da concessionária de energia elétrica.
 *
 * Referências:
 *   - PRODIST Módulo 1 §4 (ANEEL REN 956/2021) — identificação do levantamento
 *   - PRODIST Módulo 3 §3.4 — faixas de segurança
 *   - NR-10:2016 Tabela 1 — distâncias mínimas de segurança
 *
 * @param {{ onToast: (msg: string, type: string) => void }} props
 */
export default function NormaPanel({ onToast }) {
  const [normaAtiva, setNormaAtiva] = useState('ABNT');
  const [concessionaria, setConcessionaria] = useState('');
  const [classeTensao, setClasseTensao] = useState('MT');
  const [numeroProcesso, setNumeroProcesso] = useState('');
  const [loading, setLoading] = useState(false);
  const [bufferInfo, setBufferInfo] = useState(null);

  // Sincroniza estado inicial com o backend
  useEffect(() => {
    api
      .getNormaAtiva()
      .then((data) => {
        setNormaAtiva(data.ativa || 'ABNT');
        setConcessionaria(data.concessionaria || '');
        setClasseTensao(data.classe_tensao || 'MT');
        setNumeroProcesso(data.numero_processo || '');
      })
      .catch(() => {
        /* silently ignore — backend may not be ready */
      });
  }, []);

  // Atualiza info de buffer quando classe muda
  useEffect(() => {
    const found = CLASSES_TENSAO.find((c) => c.value === classeTensao);
    setBufferInfo(found || null);
  }, [classeTensao]);

  const handleToggle = useCallback(
    async (ativar) => {
      setLoading(true);
      try {
        const payload = {
          ativa: ativar,
          concessionaria: concessionaria || 'Não informada',
          classe_tensao: classeTensao,
          numero_processo: numeroProcesso,
        };
        const result = await api.setNormaConfig(payload);
        setNormaAtiva(result.norma_ativa);
        if (onToast && result.toast) {
          onToast(result.toast, ativar ? 'warning' : 'success');
        }
      } catch {
        if (onToast) {
          onToast('Erro ao configurar norma. Verifique a conexão.', 'error');
        }
      } finally {
        setLoading(false);
      }
    },
    [concessionaria, classeTensao, numeroProcesso, onToast]
  );

  const isProdist = normaAtiva === 'PRODIST';

  return (
    <div className="pt-4 border-t border-slate-200/50 space-y-3">
      {/* Cabeçalho */}
      <label className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1 ml-1">
        <Zap size={12} /> Norma Técnica Ativa
      </label>

      {/* Toggle ABNT / ANEEL PRODIST */}
      <div className="grid grid-cols-2 gap-2">
        <button
          onClick={() => !loading && isProdist && handleToggle(false)}
          disabled={loading || !isProdist}
          className={`py-3 rounded-2xl text-[10px] font-bold border transition-all ${
            !isProdist
              ? 'bg-blue-500 text-white border-blue-500 shadow-lg shadow-blue-500/20'
              : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
          }`}
        >
          ABNT
        </button>
        <button
          onClick={() => !loading && !isProdist && handleToggle(true)}
          disabled={loading || isProdist}
          className={`py-3 rounded-2xl text-[10px] font-bold border transition-all ${
            isProdist
              ? 'bg-amber-500 text-white border-amber-500 shadow-lg shadow-amber-500/20'
              : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'
          }`}
        >
          ANEEL/PRODIST
        </button>
      </div>

      {/* Status */}
      <div
        className={`flex items-center gap-2 px-3 py-2 rounded-xl text-[10px] font-bold ${
          isProdist
            ? 'bg-amber-50 text-amber-700 border border-amber-200'
            : 'bg-blue-50 text-blue-700 border border-blue-200'
        }`}
      >
        {isProdist ? (
          <>
            <AlertTriangle size={12} />
            Normas da concessionária ativas — ABNT substituída
          </>
        ) : (
          <>
            <CheckCircle2 size={12} />
            ABNT NBR 14166 / NBR 13133 ativas
          </>
        )}
      </div>

      {/* Campos PRODIST (visíveis apenas quando PRODIST está selecionado) */}
      {isProdist && (
        <div className="space-y-3 animate-in fade-in duration-200">
          {/* Concessionária */}
          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-3 flex flex-col gap-1">
            <span className="text-[9px] font-bold text-slate-400 uppercase">Concessionária</span>
            <input
              type="text"
              value={concessionaria}
              onChange={(e) => setConcessionaria(e.target.value)}
              placeholder="Ex: Light S.A."
              className="bg-transparent text-xs font-bold text-slate-700 outline-none placeholder:text-slate-300"
            />
          </div>

          {/* Classe de tensão */}
          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-3 flex flex-col gap-1">
            <span className="text-[9px] font-bold text-slate-400 uppercase">Classe de Tensão</span>
            <select
              value={classeTensao}
              onChange={(e) => setClasseTensao(e.target.value)}
              className="bg-transparent text-xs font-bold text-slate-700 outline-none"
            >
              {CLASSES_TENSAO.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {/* Buffer de segurança (informativo, NR-10:2016) */}
          {bufferInfo && (
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl">
              <Shield size={12} className="text-slate-400 shrink-0" />
              <span className="text-[10px] text-slate-500 font-medium">
                Buffer de segurança NR-10:{' '}
                <span className="font-bold text-slate-700">{bufferInfo.buffer} m</span>
              </span>
            </div>
          )}

          {/* Nº do processo ANEEL (opcional) */}
          <div className="bg-slate-50 border border-slate-200 rounded-2xl p-3 flex flex-col gap-1">
            <span className="text-[9px] font-bold text-slate-400 uppercase">
              Nº Processo ANEEL (opcional)
            </span>
            <input
              type="text"
              value={numeroProcesso}
              onChange={(e) => setNumeroProcesso(e.target.value)}
              placeholder="Ex: 48500.004321/2024-01"
              className="bg-transparent text-xs font-bold text-slate-700 outline-none placeholder:text-slate-300"
            />
          </div>

          {/* Botão de aplicar */}
          <button
            data-testid="btn-aplicar-prodist"
            onClick={() => handleToggle(true)}
            disabled={loading}
            className="w-full py-3 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white text-[10px] font-bold rounded-2xl transition-all shadow-lg shadow-amber-500/20"
          >
            {loading ? 'APLICANDO...' : 'APLICAR NORMA ANEEL/PRODIST'}
          </button>
        </div>
      )}
    </div>
  );
}
