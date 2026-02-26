import React, { useState, useEffect, useCallback } from 'react';
import { MapPin, Cloud, Server, Zap, CheckCircle2, ArrowRight, X } from 'lucide-react';

const WIZARD_DONE_KEY = 'sisrua_onboarding_done';

const STEPS = [
  {
    id: 'welcome',
    titulo: 'Bem-vindo ao sisRUA',
    subtitulo: 'Motor GIS de Design Urbano — Infraestrutura Elétrica MT/BT',
  },
  {
    id: 'coords',
    titulo: 'Coordenadas de Referência',
    subtitulo: 'Cole as coordenadas do centro do seu projeto (WGS84 / lat, lon)',
  },
  {
    id: 'modo',
    titulo: 'Modo de Operação',
    subtitulo: 'Escolha como o sisRUA se comunicará com o backend',
  },
  {
    id: 'pronto',
    titulo: 'Tudo Pronto!',
    subtitulo: 'Seu ambiente está configurado. Vamos começar!',
  },
];

/**
 * OnboardingWizard — Assistente de primeira utilização do sisRUA.
 *
 * Exibido automaticamente na primeira abertura (localStorage flag).
 * Guia o projetista em 4 passos:
 *   1. Boas-vindas e visão geral
 *   2. Definição de coordenadas de referência
 *   3. Seleção do modo de operação (Cloud / Local)
 *   4. Confirmação e início
 *
 * @param {{ onComplete: (config: object) => void, onClose: () => void }} props
 */
export default function OnboardingWizard({ onComplete, onClose }) {
  const [etapa, setEtapa] = useState(0);
  const [coordsText, setCoordsText] = useState('');
  const [coordsError, setCoordsError] = useState('');
  const [modo, setModo] = useState('cloud');

  // Avança para próxima etapa
  const avancar = useCallback(() => {
    if (etapa === 1) {
      // Valida coordenadas (lat, lon WGS84)
      const parsed = _parseCoordsInput(coordsText);
      if (!parsed) {
        setCoordsError('Formato inválido. Use: -22.15018, -42.92185');
        return;
      }
      setCoordsError('');
    }
    setEtapa((e) => Math.min(e + 1, STEPS.length - 1));
  }, [etapa, coordsText]);

  // Finaliza wizard
  const finalizar = useCallback(() => {
    const parsed = coordsText ? _parseCoordsInput(coordsText) : null;
    const config = {
      coords: parsed,
      modo,
      timestamp: new Date().toISOString(),
    };
    localStorage.setItem(WIZARD_DONE_KEY, '1');
    onComplete(config);
  }, [coordsText, modo, onComplete]);

  // Fecha sem salvar
  const fechar = useCallback(() => {
    onClose();
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Assistente de configuração inicial"
      className="fixed inset-0 z-[9000] bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4"
    >
      <div className="bg-white rounded-[32px] shadow-2xl w-full max-w-lg overflow-hidden ring-1 ring-black/5">
        {/* Header com progresso */}
        <div className="bg-gradient-to-br from-slate-900 to-slate-800 px-8 pt-8 pb-6 relative">
          <button
            onClick={fechar}
            aria-label="Fechar assistente"
            className="absolute top-4 right-4 p-2 rounded-full text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X size={16} />
          </button>

          {/* Indicador de etapa */}
          <div className="flex gap-2 mb-6">
            {STEPS.map((_, i) => (
              <div
                key={i}
                className={`h-1 flex-1 rounded-full transition-all duration-300 ${
                  i <= etapa ? 'bg-blue-400' : 'bg-white/20'
                }`}
              />
            ))}
          </div>

          <p className="text-blue-300 text-[11px] font-bold uppercase tracking-widest mb-1">
            Etapa {etapa + 1} de {STEPS.length}
          </p>
          <h2 className="text-white text-2xl font-black">{STEPS[etapa].titulo}</h2>
          <p className="text-slate-400 text-sm mt-1">{STEPS[etapa].subtitulo}</p>
        </div>

        {/* Conteúdo da etapa */}
        <div className="px-8 py-8">
          {etapa === 0 && <StepBemVindo />}
          {etapa === 1 && (
            <StepCoords
              coordsText={coordsText}
              setCoordsText={setCoordsText}
              coordsError={coordsError}
            />
          )}
          {etapa === 2 && <StepModo modo={modo} setModo={setModo} />}
          {etapa === 3 && <StepPronto modo={modo} coordsText={coordsText} />}
        </div>

        {/* Footer com botões */}
        <div className="px-8 pb-8 flex justify-between items-center">
          {etapa > 0 ? (
            <button
              onClick={() => setEtapa((e) => e - 1)}
              className="text-slate-500 text-sm font-semibold hover:text-slate-700 transition-colors"
            >
              Voltar
            </button>
          ) : (
            <div />
          )}

          {etapa < STEPS.length - 1 ? (
            <button
              onClick={avancar}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold px-6 py-3 rounded-2xl transition-all shadow-lg shadow-blue-500/20 active:scale-95"
            >
              Próximo <ArrowRight size={16} />
            </button>
          ) : (
            <button
              onClick={finalizar}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-6 py-3 rounded-2xl transition-all shadow-lg shadow-emerald-500/20 active:scale-95"
            >
              <CheckCircle2 size={16} /> Começar
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-componentes das etapas
// ---------------------------------------------------------------------------

function StepBemVindo() {
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-center">
        <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-slate-800 to-slate-900 flex items-center justify-center shadow-xl">
          <span className="text-white text-4xl font-black">R</span>
        </div>
      </div>
      <p className="text-slate-700 text-sm leading-relaxed text-center">
        O <strong>sisRUA</strong> automatiza o <em>draft</em> de infraestrutura
        elétrica de distribuição MT/BT diretamente no AutoCAD, a partir de
        dados abertos (OSM, IBGE, INEA).
      </p>
      <div className="grid grid-cols-2 gap-3">
        {[
          { icon: <MapPin size={18} />, label: 'Arruamento OSM', desc: 'Meio-fio a meio-fio, 1:1000' },
          { icon: <Zap size={18} />, label: 'Rede Elétrica MT/BT', desc: 'BIM-LITE com XDATA' },
          { icon: <Server size={18} />, label: 'Backend embutido', desc: 'Funciona offline' },
          { icon: <Cloud size={18} />, label: 'Cloud Run', desc: 'Google Cloud (gratuito)' },
        ].map(({ icon, label, desc }) => (
          <div key={label} className="flex gap-3 items-start bg-slate-50 rounded-2xl p-4 border border-slate-100">
            <span className="text-blue-500 mt-0.5">{icon}</span>
            <div>
              <p className="text-slate-800 text-xs font-bold">{label}</p>
              <p className="text-slate-400 text-[11px]">{desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StepCoords({ coordsText, setCoordsText, coordsError }) {
  return (
    <div className="space-y-5">
      <p className="text-slate-600 text-sm leading-relaxed">
        Informe as coordenadas WGS84 do <strong>centro do projeto</strong> (ex.: entrada
        da área ou marco de referência do levantamento).
      </p>
      <div className="space-y-2">
        <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
          Latitude, Longitude (graus decimais)
        </label>
        <input
          type="text"
          placeholder="Ex: -22.15018, -42.92185"
          value={coordsText}
          onChange={(e) => setCoordsText(e.target.value)}
          className={`w-full bg-white border rounded-2xl p-4 text-sm outline-none font-mono transition-all ${
            coordsError
              ? 'border-red-400 focus:ring-4 focus:ring-red-500/10'
              : 'border-slate-200 focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10'
          }`}
          aria-label="Coordenadas de referência"
        />
        {coordsError && (
          <p className="text-red-500 text-[11px] font-semibold ml-1" role="alert">
            {coordsError}
          </p>
        )}
      </div>
      <div className="bg-blue-50 rounded-2xl p-4 border border-blue-100">
        <p className="text-blue-700 text-[11px] font-bold uppercase tracking-wider mb-1">
          Coordenadas de teste (campo)
        </p>
        <p className="text-blue-600 text-xs font-mono">
          REF_2: -22.15018, -42.92185
        </p>
        <p className="text-blue-400 text-[10px] mt-0.5">
          Nova Friburgo/RJ — área de teste homologada
        </p>
        <button
          type="button"
          onClick={() => setCoordsText('-22.15018, -42.92185')}
          className="mt-2 text-blue-600 text-[11px] font-bold hover:underline"
        >
          Usar coordenadas de teste →
        </button>
      </div>
    </div>
  );
}

function StepModo({ modo, setModo }) {
  return (
    <div className="space-y-4">
      <p className="text-slate-600 text-sm">
        Selecione como o sisRUA se conectará ao backend de processamento GIS:
      </p>
      <div className="space-y-3">
        <ModoCard
          value="cloud"
          current={modo}
          onSelect={setModo}
          icon={<Cloud size={24} />}
          titulo="sisRUA LT — Cloud Run"
          descricao="Backend hospedado no Google Cloud Run (gratuito). Requer internet."
          badge="Recomendado"
          badgeColor="bg-blue-100 text-blue-700"
        />
        <ModoCard
          value="local"
          current={modo}
          onSelect={setModo}
          icon={<Server size={24} />}
          titulo="sisRUA Full — Backend Local"
          descricao="Backend Python embutido no plugin. Funciona offline. Requer instalação completa."
          badge="Offline"
          badgeColor="bg-emerald-100 text-emerald-700"
        />
      </div>
    </div>
  );
}

function ModoCard({ value, current, onSelect, icon, titulo, descricao, badge, badgeColor }) {
  const selected = current === value;
  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      className={`w-full text-left p-5 rounded-2xl border-2 transition-all ${
        selected
          ? 'border-blue-500 bg-blue-50 shadow-md shadow-blue-500/10'
          : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
      }`}
    >
      <div className="flex items-start gap-4">
        <span className={`mt-0.5 ${selected ? 'text-blue-600' : 'text-slate-400'}`}>
          {icon}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-slate-800 text-sm">{titulo}</span>
            <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${badgeColor}`}>
              {badge}
            </span>
          </div>
          <p className="text-slate-500 text-xs mt-1 leading-relaxed">{descricao}</p>
        </div>
        <div className={`w-5 h-5 rounded-full border-2 flex-shrink-0 mt-0.5 transition-all ${
          selected ? 'border-blue-500 bg-blue-500' : 'border-slate-300'
        }`}>
          {selected && <CheckCircle2 size={16} className="text-white" />}
        </div>
      </div>
    </button>
  );
}

function StepPronto({ modo, coordsText }) {
  const parsed = _parseCoordsInput(coordsText);
  return (
    <div className="space-y-5">
      <div className="flex flex-col items-center gap-3">
        <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center">
          <CheckCircle2 size={32} className="text-emerald-600" />
        </div>
        <p className="text-slate-700 text-sm text-center">
          Configuração concluída! O sisRUA está pronto para uso.
        </p>
      </div>
      <div className="bg-slate-50 rounded-2xl p-5 space-y-3 border border-slate-100">
        <ResumoItem label="Modo" value={modo === 'cloud' ? 'Cloud Run (LT)' : 'Backend Local (Full)'} />
        {parsed && (
          <ResumoItem
            label="Referência"
            value={`${parsed.lat.toFixed(5)}, ${parsed.lon.toFixed(5)}`}
          />
        )}
        <ResumoItem label="CRS" value="SIRGAS 2000 UTM (auto-detect)" />
        <ResumoItem label="Escala" value="1:1000" />
        <ResumoItem label="Modo 2.5D" value="Elevação como atributo XDATA" />
      </div>
      <p className="text-slate-400 text-[11px] text-center">
        Esta configuração pode ser alterada a qualquer momento em <strong>Configurações</strong>.
      </p>
    </div>
  );
}

function ResumoItem({ label, value }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-slate-500 text-xs font-semibold">{label}</span>
      <span className="text-slate-700 text-xs font-bold">{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Utilitários
// ---------------------------------------------------------------------------

/**
 * Parse de texto "lat, lon" para objeto { lat, lon } ou null se inválido.
 * @param {string} text
 * @returns {{ lat: number, lon: number } | null}
 */
export function _parseCoordsInput(text) {
  if (!text || typeof text !== 'string') return null;
  const parts = text.trim().split(/[\s,;]+/);
  if (parts.length < 2) return null;
  const lat = parseFloat(parts[0]);
  const lon = parseFloat(parts[1]);
  if (Number.isNaN(lat) || Number.isNaN(lon)) return null;
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
  return { lat, lon };
}

/**
 * Retorna true se o wizard já foi concluído (flag no localStorage).
 * @returns {boolean}
 */
export function isOnboardingDone() {
  try {
    return localStorage.getItem(WIZARD_DONE_KEY) === '1';
  } catch {
    return false;
  }
}

/**
 * Reseta o estado do wizard (útil para testes ou "reiniciar configuração").
 */
export function resetOnboarding() {
  try {
    localStorage.removeItem(WIZARD_DONE_KEY);
  } catch { /* noop */ }
}
