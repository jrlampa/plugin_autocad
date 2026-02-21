import React from 'react';
import { ArrowLeft, Settings, Globe, LayoutTemplate, Download, FileJson } from 'lucide-react';
import JobOverlay from './JobOverlay';
import NormaPanel from './NormaPanel';

export default function SettingsPanel({
  showSettings,
  setShowSettings,
  loading,
  previewGeoJson,
  handleImportGeoJson,
  setPreviewGeoJson,
  inputText,
  setInputText,
  handleGeocode,
  inputLoading,
  radius,
  setRadius,
  setRadiusInput,
  baseLayer,
  setBaseLayer,
  tileProviders,
  engConfig,
  setEngConfig,
  uiJob,
  api,
  onToast,
}) {
  return (
    <div className="absolute top-6 right-6 z-[1000] w-[400px] animate-enter">
      <div className="relative bg-white/85 backdrop-blur-2xl shadow-2xl rounded-[32px] border border-white/50 overflow-hidden ring-1 ring-black/5">
        <div className="px-8 py-6 border-b border-white/50 flex justify-between items-center bg-gradient-to-r from-white/60 to-transparent">
          <div className="flex flex-col gap-0.5">
            <span className="text-2xl font-black text-slate-800 tracking-tight flex items-center gap-2">
              sisRUA{' '}
              <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded border border-blue-200">
                v0.5.0
              </span>
            </span>
            <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">
              Generative Urban Design
            </p>
          </div>
          <button
            onClick={() => !loading && setShowSettings(!showSettings)}
            className="p-3 rounded-full hover:bg-white/60 transition-colors border border-transparent hover:border-white/50"
          >
            {showSettings ? (
              <ArrowLeft size={20} className="text-slate-600" />
            ) : (
              <Settings size={20} className="text-slate-600" />
            )}
          </button>
        </div>
        <div className="p-8 pb-8">
          {!showSettings ? (
            <div className="space-y-7">
              {/* ** PAINEL DE IMPORTAÇÃO GEOJSON (NOVO) ** */}
              {previewGeoJson && (
                <div className="bg-amber-50/80 rounded-3xl border-2 border-amber-200/50 p-6 flex flex-col gap-4 shadow-lg animate-enter ring-1 ring-amber-500/10">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-xl bg-amber-100 text-amber-600">
                      <FileJson size={20} />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-xs font-black uppercase tracking-wide text-amber-800">
                        Preview de Campo
                      </span>
                      <span className="text-[10px] text-amber-700/80 font-medium">
                        GeoJSON carregado no mapa.
                      </span>
                    </div>
                  </div>
                  <button
                    data-testid="btn-import-geojson"
                    onClick={handleImportGeoJson}
                    className="mt-1 w-full bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold py-4 rounded-2xl text-center transition-all shadow-lg shadow-amber-500/20 flex items-center justify-center gap-2 group"
                  >
                    <Download size={16} className="group-hover:animate-bounce" /> IMPORTAR PARA O
                    AUTOCAD
                  </button>
                  <button
                    onClick={() => setPreviewGeoJson(null)}
                    className="text-center text-[10px] text-slate-500 hover:text-red-500 font-bold transition-colors"
                  >
                    Cancelar
                  </button>
                </div>
              )}

              {/* LOCATION INPUT */}
              <div className="relative group">
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleGeocode()}
                  placeholder="Buscar endereço, Lat/Lon..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-2xl py-4 pl-12 pr-12 text-sm font-medium text-slate-700 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all placeholder:text-slate-400 group-hover:bg-white group-hover:shadow-lg group-hover:border-slate-300"
                />
                <div className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-hover:text-blue-500 transition-colors pointer-events-none">
                  {inputLoading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-2 border-slate-200 border-t-blue-500" />
                  ) : (
                    <LayoutTemplate size={20} />
                  )}
                </div>
                {inputText && (
                  <button
                    onClick={() => setInputText('')}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1 hover:bg-slate-100 rounded-full transition-all"
                  >
                    <ArrowLeft className="rotate-45" size={16} />
                  </button>
                )}
              </div>

              {/* JOB OVERLAY */}
              {uiJob && <JobOverlay uiJob={uiJob} />}
            </div>
          ) : (
            <div className="space-y-7 animate-enter">
              <div className="space-y-3">
                <label className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1 ml-1">
                  <Globe size={12} /> Mapa Base
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {Object.entries(tileProviders).map(([key]) => (
                    <button
                      key={key}
                      onClick={() => setBaseLayer(key)}
                      className={`text-[10px] font-bold py-3 rounded-2xl border transition-all ${baseLayer === key ? 'bg-blue-500 text-white border-blue-500 shadow-lg shadow-blue-500/20' : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300 hover:bg-slate-50'}`}
                    >
                      {key === 'osm' ? 'RUAS' : key === 'clean' ? 'CLEAN' : 'SATÉLITE'}
                    </button>
                  ))}
                </div>
              </div>
              <div className="pt-4 border-t border-slate-200/50 space-y-3">
                <label className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1 ml-1">
                  Parâmetros de Geração
                </label>
                <div className="bg-slate-50 border border-slate-200 rounded-2xl p-4 flex flex-col gap-2">
                  <div className="flex justify-between text-xs font-bold text-slate-700">
                    <span>Raio de Busca</span>
                    <span>{radius}m</span>
                  </div>
                  <input
                    type="range"
                    min="100"
                    max="2000"
                    step="50"
                    value={radius}
                    onChange={(e) => {
                      const val = parseInt(e.target.value, 10);
                      setRadius(val);
                      setRadiusInput(val);
                    }}
                    className="w-full accent-blue-600 h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                  />
                  <div className="flex justify-between text-[10px] text-slate-400 font-medium">
                    <span>100m</span>
                    <span>2km</span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-200/50 space-y-3">
                <label className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1 ml-1">
                  <LayoutTemplate size={12} /> Engenharia
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-50 border border-slate-200 rounded-2xl p-3 flex flex-col gap-1">
                    <span className="text-[9px] font-bold text-slate-400 uppercase">Perfil</span>
                    <select
                      value={engConfig.profile_name}
                      onChange={(e) => setEngConfig({ ...engConfig, profile_name: e.target.value })}
                      className="bg-transparent text-xs font-bold text-slate-700 outline-none"
                    >
                      <option value="PADRAO_URBANO">Padrão Urbano</option>
                      <option value="RURAL_LEVE">Rural Leve</option>
                      <option value="INDUSTRIAL">Industrial</option>
                    </select>
                  </div>
                  <div className="bg-slate-50 border border-slate-200 rounded-2xl p-3 flex flex-col gap-1">
                    <span className="text-[9px] font-bold text-slate-400 uppercase">CRS Saída</span>
                    <select
                      value={engConfig.crs_out}
                      onChange={(e) => setEngConfig({ ...engConfig, crs_out: e.target.value })}
                      className="bg-transparent text-xs font-bold text-slate-700 outline-none"
                    >
                      <option value="EPSG:31984">SIRGAS 2000 / 24S</option>
                      <option value="EPSG:31983">SIRGAS 2000 / 23S</option>
                      <option value="EPSG:4326">WGS 84 (Lat/Lon)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* GIS EXPORT (HARDENING) */}
              <div className="pt-4 border-t border-slate-200/50 space-y-3">
                <label className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1 ml-1">
                  <Download size={12} /> Interoperabilidade GIS
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    onClick={() => uiJob?.project_id && api.exportGeoJSON(uiJob.project_id)}
                    disabled={!uiJob?.project_id}
                    className="px-3 py-3 bg-white border border-slate-200 rounded-2xl text-[10px] font-bold text-slate-600 hover:bg-slate-50 transition-all flex items-center justify-center gap-1.5 disabled:opacity-40"
                  >
                    <FileJson size={13} className="text-amber-500" />
                    GEOJSON
                  </button>
                  <button
                    onClick={() => uiJob?.project_id && api.exportGeoPackage(uiJob.project_id)}
                    disabled={!uiJob?.project_id}
                    className="px-3 py-3 bg-white border border-slate-200 rounded-2xl text-[10px] font-bold text-slate-600 hover:bg-slate-50 transition-all flex items-center justify-center gap-1.5 disabled:opacity-40"
                  >
                    <Globe size={13} className="text-blue-500" />
                    GEOPACKAGE
                  </button>
                  <button
                    data-testid="btn-export-dxf"
                    onClick={() => uiJob?.project_id && api.exportDxf(uiJob.project_id)}
                    disabled={!uiJob?.project_id}
                    className="px-3 py-3 bg-white border border-slate-200 rounded-2xl text-[10px] font-bold text-slate-600 hover:bg-slate-50 transition-all flex items-center justify-center gap-1.5 disabled:opacity-40"
                  >
                    <Download size={13} className="text-violet-500" />
                    DXF
                  </button>
                </div>
              </div>

              {/* NORMA TÉCNICA (ABNT / ANEEL PRODIST) */}
              <NormaPanel onToast={onToast} />

              <div className="pt-8 border-t border-slate-200/50">
                <button
                  onClick={() => setShowSettings(false)}
                  className="w-full py-4 text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-2xl transition-colors"
                >
                  VOLTAR PARA O PROJETO
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
