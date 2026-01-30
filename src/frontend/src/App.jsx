import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Circle, Marker, Popup, useMap, GeoJSON, Polyline } from 'react-leaflet';
import 'leaflet/dist/images/marker-icon.png';
import 'leaflet/dist/images/marker-shadow.png';
import 'leaflet/dist/leaflet.css';
import {
  Loader2, Download, Zap, CheckCircle2, AlertTriangle,
  Search, MapPin, Settings, ArrowLeft, Lightbulb, TreePine,
  CircleDot, X, PenTool, Save, Globe, UploadCloud, LayoutTemplate, FileJson, Spline
} from 'lucide-react';
import L from 'leaflet';
import { kml } from '@mapbox/togeojson'; // Import the togeojson library

import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';
import { useMapLogic } from './hooks/useMapLogic';
import { api } from './api';
import LoadingScreen from './components/LoadingScreen';

// Configuração do Ícone Padrão do Leaflet
let DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34]
});
L.Marker.prototype.options.icon = DefaultIcon;

// --- Handlers do Mapa ---
function MapDropHandler({ onSymbolDrop }) {
  const map = useMap();
  useEffect(() => {
    const container = map.getContainer();
    const handleDrop = (e) => {
      const symbolType = e.dataTransfer.getData("symbolType");
      if (symbolType) {
        e.preventDefault();
        const latlng = map.mouseEventToLatLng(e);
        onSymbolDrop(latlng, symbolType);
      }
    };
    const handleDragOver = (e) => {
      if (e.dataTransfer.types.includes("symbolType")) e.preventDefault();
    };
    container.addEventListener('drop', handleDrop);
    container.addEventListener('dragover', handleDragOver);
    return () => {
      container.removeEventListener('drop', handleDrop);
      container.removeEventListener('dragover', handleDragOver);
    };
  }, [map, onSymbolDrop]);
  return null;
}

function MapClickHandler({ onMapClick }) {
  const map = useMap();
  const isDragging = useRef(false);

  useEffect(() => {
    map.on('dragstart', () => { isDragging.current = true; });
    map.on('dragend', () => { setTimeout(() => { isDragging.current = false; }, 50); });
    map.on('click', (e) => {
      if (!isDragging.current) onMapClick(e.latlng);
    });
  }, [map, onMapClick]);
  return null;
}

function MapController({ coords }) {
  const map = useMap();
  useEffect(() => { if (coords) map.flyTo(coords, 18, { animate: true, duration: 1.5 }); }, [coords, map]);
  return null;
}

// --- APP PRINCIPAL ---
export default function App() {
  const mapLogic = useMapLogic();

  // ** Estado de Carregamento Inicial (Backend Health Check) **
  const [isBackendReady, setIsBackendReady] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const checkBackend = async () => {
      const isHealthy = await api.checkHealth();
      if (isHealthy && isMounted) {
        // Pequeno delay artificial para garantir que a transição não seja brusca demais se for instantâneo
        setTimeout(() => setIsBackendReady(true), 500);
      } else if (isMounted) {
        setTimeout(checkBackend, 500); // Tenta novamente em 500ms
      }
    };
    checkBackend();
    return () => { isMounted = false; };
  }, []);

  const [coords, setCoords] = useState({ lat: -21.7634, lng: -41.3235 });
  const [inputText, setInputText] = useState("-21.763400, -41.323500");
  const [inputLoading, setInputLoading] = useState(false);
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [previewGeoJson, setPreviewGeoJson] = useState(null); // ** NOVO ESTADO PARA PREVIEW **
  const [hostJob, setHostJob] = useState(null);
  const uiJob = hostJob;
  const loading = uiJob && !['completed', 'failed'].includes(uiJob.status);
  const error = uiJob?.status === 'failed' ? (uiJob.error || uiJob.message || 'Falhou.') : null;

  // State para desenho manual
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingPoints, setDrawingPoints] = useState([]);

  const [baseLayer, setBaseLayer] = useState("satellite");
  const [radius, setRadius] = useState(500);
  const [radiusInput, setRadiusInput] = useState(500);
  const [showSettings, setShowSettings] = useState(false);

  const [engConfig, setEngConfig] = useState({
    profile_name: "PADRAO_URBANO",
    crs_out: "EPSG:31984",
    unit: "m",
    override_generate_axis: null
  });

  // Efeito para escutar mensagens do C# (Drag & Drop de arquivo na paleta)
  useEffect(() => {
    const handleWebViewMessage = (event) => {
      if (typeof event.data === 'string') {
        try {
          const message = JSON.parse(event.data);
          // Handle KML files from C# plugin (KMZ extraction)
          if (message.action === 'FILE_DROPPED_KML' && message.data.content) {
            console.log("KML content received from C# host via drag-drop (KMZ extraction). Converting to GeoJSON.");
            try {
              // Convert KML string to GeoJSON object
              const parser = new DOMParser();
              const kmlDoc = parser.parseFromString(message.data.content, "text/xml");
              const convertedGeoJson = kml(kmlDoc); // Use the kml function from @mapbox/togeojson

              if (convertedGeoJson && convertedGeoJson.type && (convertedGeoJson.features || convertedGeoJson.geometry)) {
                setPreviewGeoJson(convertedGeoJson);
              } else {
                alert("Arquivo KMZ/KML inválido. O conteúdo KML não pôde ser convertido para GeoJSON válido.");
              }
            } catch (kmlError) {
              alert(`Erro ao processar o arquivo KMZ/KML: ${kmlError.message}`);
              console.error("Erro ao converter KML para GeoJSON:", kmlError);
            }
          }
          // Handle standard GeoJSON files from C# plugin
          else if (message.action === 'FILE_DROPPED_GEOJSON' && message.data.content) {
            console.log("GeoJSON content received from C# host via drag-drop.");

            // Limpa o preview anterior
            setPreviewGeoJson(null);

            const parsedJson = JSON.parse(message.data.content);

            // Validação básica de GeoJSON
            if (parsedJson && parsedJson.type && (parsedJson.features || parsedJson.geometry)) {
              setPreviewGeoJson(parsedJson);
            } else {
              alert("Arquivo inválido recebido. O conteúdo não parece ser um GeoJSON válido.");
            }
          }
          if (message.action === 'JOB_PROGRESS' && message.data) {
            setHostJob(message.data);
          }
          if (message.action === 'GEOLOCATION_SYNC' && message.data) {
            console.log("Geolocation sync received from C#:", message.data);
            setCoords({ lat: message.data.latitude, lng: message.data.longitude });
            setInputText(`${message.data.latitude.toFixed(6)}, ${message.data.longitude.toFixed(6)}`);
          }
        } catch (error) {
          alert(`Erro ao processar o arquivo recebido: ${error.message}`);
          console.error("Erro ao processar mensagem da WebView:", error);
        }
      }
    };

    if (window.chrome && window.chrome.webview) {
      window.chrome.webview.addEventListener('message', handleWebViewMessage);
    }

    // Cleanup
    return () => {
      if (window.chrome && window.chrome.webview) {
        window.chrome.webview.removeEventListener('message', handleWebViewMessage);
      }
    };
  }, []); // Array de dependências vazio garante que o listener seja adicionado apenas uma vez.

  // --- Ações ---

  const handleGeocode = async () => {
    const query = inputText.trim();
    if (!query || inputLoading) return;
    setInputLoading(true);
    try {
      const res = await api.smartGeocode(query);
      if (res.latitude) {
        setCoords({ lat: res.latitude, lng: res.longitude });
        setInputText(`${res.latitude.toFixed(6)}, ${res.longitude.toFixed(6)}`);
      }
    } catch (err) { console.error(err); } finally { setInputLoading(false); }
  };

  // ** LÓGICA DE DRAG & DROP ATUALIZADA **
  const handleGlobalDrop = (e) => {
    e.preventDefault();
    setIsDraggingFile(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];

      // Limpa o preview anterior
      setPreviewGeoJson(null);

      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const content = event.target.result;
          const parsedJson = JSON.parse(content);
          // Validação básica de GeoJSON
          if (parsedJson && parsedJson.type && (parsedJson.features || parsedJson.geometry)) {
            setPreviewGeoJson(parsedJson);
          } else {
            alert("Arquivo inválido. Por favor, arraste um arquivo GeoJSON válido.");
          }
        } catch (error) {
          alert(`Erro ao ler o arquivo: ${error.message}`);
          console.error("Erro ao processar GeoJSON:", error);
        }
      };
      reader.readAsText(file);
    }
  };

  // ** NOVA FUNÇÃO PARA ENVIAR GEOJSON PARA C# **
  const handleImportGeoJson = () => {
    if (!previewGeoJson) return;

    if (window.chrome && window.chrome.webview) {
      const message = {
        action: 'IMPORT_GEOJSON',
        data: JSON.stringify(previewGeoJson)
      };
      window.chrome.webview.postMessage(message);
      // Opcional: limpar o preview após o envio
      setPreviewGeoJson(null);
    } else {
      alert('Esta funcionalidade está disponível apenas ao rodar o sisRUA dentro do AutoCAD.');
    }
  };

  const handleMapClick = (latlng) => {
    if (isDrawing) {
      setDrawingPoints(prevPoints => [...prevPoints, [latlng.lng, latlng.lat]]);
    } else {
      setCoords(latlng);
      setInputText(`${latlng.lat.toFixed(6)}, ${latlng.lng.toFixed(6)}`);
    }
  };

  const handleFinishDrawing = () => {
    if (drawingPoints.length < 2) return;

    const newFeature = {
      type: "Feature",
      properties: { name: "Rua Desenhada Manualmente", highway: "residential", layer: "V_LOCAL" },
      geometry: { type: "LineString", coordinates: drawingPoints }
    };

    setPreviewGeoJson(prev => {
      const base = prev || { type: "FeatureCollection", features: [] };
      const existingFeatures = base.type === "FeatureCollection" ? base.features : [base];

      // Evita adicionar features duplicadas se o usuário clicar duas vezes
      const isDuplicate = existingFeatures.some(f => JSON.stringify(f.geometry.coordinates) === JSON.stringify(newFeature.geometry.coordinates));
      if (isDuplicate) return base;

      return {
        type: "FeatureCollection",
        features: [...existingFeatures, newFeature]
      };
    });

    setIsDrawing(false);
    setDrawingPoints([]);
  };

  const handleToggleDrawing = () => {
    const newIsDrawing = !isDrawing;
    setIsDrawing(newIsDrawing);
    // Se estava desenhando e cancelou, limpa os pontos
    if (!newIsDrawing) {
      setDrawingPoints([]);
    }
  }

  const handleGenerate = () => {
    if (window.chrome && window.chrome.webview) {
      const message = {
        action: 'GENERATE_OSM',
        data: {
          latitude: coords.lat,
          longitude: coords.lng,
          radius: radius
        }
      };
      // Importante: enviar OBJETO. Se enviar string, o C# recebe como JSON-string e o parse quebra.
      window.chrome.webview.postMessage(message);
    } else {
      alert('Esta funcionalidade está disponível apenas ao rodar o sisRUA dentro do AutoCAD.');
    }
  };

  const tileProviders = {
    satellite: { url: "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attribution: "&copy; Google", subdomains: ['mt0', 'mt1', 'mt2', 'mt3'] },
    clean: { url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", attribution: "&copy; CartoDB" },
    osm: {
      url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
      // ODbL exige atribuição visível quando dados OSM são exibidos/gerados.
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap contributors</a>'
    }
  };

  if (!isBackendReady) {
    return <LoadingScreen />;
  }

  return (
    <div
      data- testid="app-root"
      className={`relative w-full h-full overflow-hidden bg-slate-900 font-sans flex ${isDrawing ? 'cursor-crosshair' : ''}`
      }
      onDragOver={(e) => { e.preventDefault(); if (e.dataTransfer.types.includes("Files")) setIsDraggingFile(true); }}
      onDragLeave={() => setIsDraggingFile(false)}
      onDrop={handleGlobalDrop}
    >

      {/* OVERLAY DE UPLOAD ATUALIZADO */}
      {
        isDraggingFile && (
          <div className="absolute inset-0 z-[3000] bg-slate-900/60 backdrop-blur-md flex items-center justify-center m-4 rounded-3xl border-4 border-dashed border-blue-400/50 pointer-events-none animate-pulse">
            <div className="flex flex-col items-center p-8 bg-white/10 rounded-3xl backdrop-blur-xl border border-white/20">
              <UploadCloud size={64} className="text-white mb-4" />
              <span className="text-2xl font-bold text-white tracking-wide">Solte o arquivo GeoJSON aqui</span>
            </div>
          </div>
        )
      }

      {/* 1. SIDEBAR DE FERRAMENTAS */}
      <div className="absolute left-4 top-4 bottom-4 w-20 z-[1000] flex flex-col items-center py-6 gap-5 bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl shadow-2xl transition-all hover:bg-white/20 hover:scale-[1.01]">
        <div className="mb-2 w-12 h-12 flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl shadow-lg border border-white/10 text-white font-black text-xl">R</div>
        <div className="w-10 border-t border-white/20 my-1"></div>
        <DraggableTool icon={<Lightbulb size={24} className="text-amber-400 fill-amber-400/20" />} label="Poste" type="POSTE" onDragStart={mapLogic.handleDragStart} description="Rede Elétrica" />
        <DraggableTool icon={<TreePine size={24} className="text-emerald-400 fill-emerald-400/20" />} label="Árvore" type="ARVORE" onDragStart={mapLogic.handleDragStart} description="Paisagismo" />

        <div className="w-10 border-t border-white/20 my-1"></div>

        <button onClick={handleToggleDrawing} className={`p-4 rounded-2xl shadow-xl transition-all active:scale-95 group relative ${isDrawing ? 'bg-red-500 hover:bg-red-600' : 'bg-green-500 hover:bg-green-600'}`}>
          <Spline size={24} className="text-white" />
          <span className="absolute left-full ml-4 bg-slate-900 text-white text-xs font-bold px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">{isDrawing ? 'Cancelar Desenho' : 'Desenhar Rua'}</span>
        </button>

        {isDrawing && drawingPoints.length > 1 && (
          <button onClick={handleFinishDrawing} className="p-4 rounded-2xl shadow-xl transition-all active:scale-95 group relative bg-blue-600 hover:bg-blue-500">
            <CheckCircle2 size={24} className="text-white" />
            <span className="absolute left-full ml-4 bg-slate-900 text-white text-xs font-bold px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">Finalizar Rua</span>
          </button>
        )}

        <div className="flex-1"></div>
        <button aria-label="Gerar Projeto (OSM)" data-testid="btn-generate-osm" onClick={handleGenerate} disabled={loading} className={`p-4 rounded-2xl shadow-xl transition-all active:scale-95 group relative ${loading ? 'bg-slate-500 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500 hover:shadow-blue-500/40'}`}>
          {loading ? <Loader2 className="animate-spin text-white" /> : <Zap className="text-white fill-white" />}
          <span className="absolute left-full ml-4 bg-slate-900 text-white text-xs font-bold px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">Gerar Projeto (OSM)</span>
        </button>
      </div>

      {/* 2. MAPA (Z-Index 0) */}
      <div className="flex-1 relative z-0">
        <MapContainer center={coords} zoom={18} zoomControl={false} className="h-full w-full outline-none bg-slate-900">
          <TileLayer key={baseLayer} {...tileProviders[baseLayer]} />
          <MapController coords={coords} />
          <MapDropHandler onSymbolDrop={mapLogic.handleSymbolDrop} />
          <MapClickHandler onMapClick={handleMapClick} />

          {previewGeoJson && <GeoJSON data={previewGeoJson} pathOptions={{ color: '#ff7800', weight: 5, opacity: 0.8 }} />}

          {isDrawing && drawingPoints.length > 0 && (
            <Polyline
              positions={drawingPoints.map(p => [p[1], p[0]])}
              pathOptions={{ color: 'lime', weight: 4, opacity: 0.7, dashArray: '10, 10' }}
            />
          )}

          {mapLogic.markers.map((m, idx) => (
            <Marker key={idx} position={[m.lat, m.lon]} opacity={0.9}><Popup><div className="text-slate-800"><strong className="block text-sm uppercase mb-1">{m.tipo}</strong><span className="text-xs text-slate-500">{m.meta.desc}</span></div></Popup></Marker>
          ))}
          <Circle center={coords} radius={radius} pathOptions={{ color: '#3b82f6', fillColor: '#3b82f6', fillOpacity: 0.08, dashArray: '8, 8', weight: 1.5 }} />
        </MapContainer>
      </div>

      {/* 3. PAINEL DIREITO */}
      <div className="absolute top-6 right-6 z-[1000] w-[400px] animate-enter">
        <div className="relative bg-white/85 backdrop-blur-2xl shadow-2xl rounded-[32px] border border-white/50 overflow-hidden ring-1 ring-black/5">
          <div className="px-8 py-6 border-b border-white/50 flex justify-between items-center bg-gradient-to-r from-white/60 to-transparent">
            <div className="flex flex-col gap-0.5"><span className="text-2xl font-black text-slate-800 tracking-tight flex items-center gap-2">sisRUA <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded border border-blue-200">v0.5.0</span></span><p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">Generative Urban Design</p></div>
            <button onClick={() => !loading && setShowSettings(!showSettings)} className="p-3 rounded-full hover:bg-white/60 transition-colors border border-transparent hover:border-white/50">{showSettings ? <ArrowLeft size={20} className="text-slate-600" /> : <Settings size={20} className="text-slate-600" />}</button>
          </div>
          <div className="p-8 pb-8">
            {!showSettings ? (
              <div className="space-y-7">

                {/* ** PAINEL DE IMPORTAÇÃO GEOJSON (NOVO) ** */}
                {previewGeoJson && (
                  <div className="bg-amber-50/80 rounded-3xl border-2 border-amber-200/50 p-6 flex flex-col gap-4 shadow-lg animate-enter ring-1 ring-amber-500/10">
                    <div className="flex items-center gap-3">
                      <div className='p-2 rounded-xl bg-amber-100 text-amber-600'><FileJson size={20} /></div>
                      <div className="flex flex-col">
                        <span className="text-xs font-black uppercase tracking-wide text-amber-800">Preview de Campo</span>
                        <span className="text-[10px] text-amber-700/80 font-medium">GeoJSON carregado no mapa.</span>
                      </div>
                    </div>
                    <button data-testid="btn-import-geojson" onClick={handleImportGeoJson} className="mt-1 w-full bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold py-4 rounded-2xl text-center transition-all shadow-lg shadow-amber-500/20 flex items-center justify-center gap-2 group">
                      <Download size={16} className="group-hover:animate-bounce" /> IMPORTAR PARA O AUTOCAD
                    </button>
                    <button onClick={() => setPreviewGeoJson(null)} className="text-center text-[10px] text-slate-500 hover:text-red-500 font-bold transition-colors">Cancelar</button>
                  </div>
                )}

                <div className="space-y-2.5">
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest ml-1 flex items-center gap-1"><MapPin size={10} /> Localização do Projeto</label>
                  <div className={`flex items-center gap-3 bg-white/60 border rounded-2xl px-4 py-4 shadow-sm transition-all focus-within:ring-2 focus-within:ring-blue-400/30 ${inputLoading ? 'border-blue-400' : 'border-white/60 hover:border-blue-200'}`}>{inputLoading ? <Loader2 className="animate-spin text-blue-500" size={20} /> : <Search className="text-slate-400" size={20} />}<input value={inputText} onChange={(e) => setInputText(e.target.value)} onBlur={handleGeocode} onKeyDown={(e) => e.key === 'Enter' && handleGeocode()} className="flex-1 bg-transparent outline-none text-sm font-semibold text-slate-700 placeholder:text-slate-400" placeholder="Buscar endereço, Lat/Lon..." /></div>
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between items-end px-1"><label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Raio de Abrangência</label><span className="text-2xl font-black text-slate-700 tracking-tight">{radius}<span className="text-sm font-bold text-slate-400 ml-0.5">m</span></span></div>
                  <input type="range" min="100" max="5000" step="100" value={radiusInput} onChange={e => setRadiusInput(Number(e.target.value))} onMouseUp={() => setRadius(radiusInput)} className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer hover:bg-slate-300 transition-colors" disabled={loading} />
                </div>
                {uiJob && (
                  <div className="bg-white/60 rounded-3xl border border-white/80 p-6 flex flex-col gap-4 shadow-lg animate-enter ring-1 ring-black/5">
                    <div className="flex justify-between items-start pb-3 border-b border-slate-200/50">
                      <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-xl ${uiJob.status === 'completed' ? 'bg-emerald-100 text-emerald-600' : uiJob.status === 'failed' ? 'bg-red-100 text-red-600' : 'bg-blue-100 text-blue-600'}`}>
                          {uiJob.status === 'completed' ? <CheckCircle2 size={20} /> : uiJob.status === 'failed' ? <AlertTriangle size={20} /> : <Loader2 size={20} className="animate-spin" />}
                        </div>
                        <div className="flex flex-col">
                          <span className={`text-xs font-black uppercase tracking-wide ${uiJob.status === 'failed' ? 'text-red-600' : 'text-slate-700'}`}>
                            {uiJob.status === 'queued' ? 'Aguardando' : uiJob.status === 'processing' ? 'Processando' : 'Concluído'}
                          </span>
                          {uiJob.message && uiJob.status !== 'completed' && uiJob.status !== 'failed' && (
                            <span className="text-[10px] text-slate-500 font-medium animate-pulse">{uiJob.message}</span>
                          )}
                        </div>
                      </div>
                      <div className="text-[10px] font-mono text-slate-500">
                        {typeof uiJob.progress === 'number' ? `${Math.round(uiJob.progress * 100)}%` : ''}
                      </div>
                    </div>

                    {typeof uiJob.progress === 'number' && (
                      <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
                        <div className="h-2 bg-blue-500" style={{ width: `${Math.max(0, Math.min(100, Math.round(uiJob.progress * 100)))}%` }} />
                      </div>
                    )}
                  </div>
                )}
                {error && <div className="bg-red-50 text-red-600 p-4 rounded-2xl text-xs font-bold border border-red-100 flex gap-3 items-center shadow-sm"><AlertTriangle size={18} /> {error}</div>}
              </div>
            ) : (
              <div className="space-y-7 animate-enter">
                <div className="space-y-3"><label className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1 ml-1"><Globe size={12} /> Mapa Base</label><div className="grid grid-cols-3 gap-3">{Object.entries(tileProviders).map(([key, provider]) => (<button key={key} onClick={() => setBaseLayer(key)} className={`text-[10px] font-bold py-3 rounded-2xl border transition-all ${baseLayer === key ? 'bg-blue-500 text-white border-blue-500 shadow-lg shadow-blue-500/20' : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300 hover:bg-slate-50'}`}>{key === 'osm' ? 'RUAS' : key === 'clean' ? 'CLEAN' : 'SATÉLITE'}</button>))}</div></div>
                <div className="space-y-3"><label className="text-[10px] font-bold text-slate-400 uppercase flex items-center gap-1 ml-1"><LayoutTemplate size={12} /> Perfil Técnico</label><div className="relative"><select value={engConfig.profile_name} onChange={(e) => setEngConfig({ ...engConfig, profile_name: e.target.value })} className="w-full bg-white border border-slate-200 rounded-2xl p-4 text-xs font-bold text-slate-700 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all appearance-none cursor-pointer hover:border-slate-300"><option value="PADRAO_URBANO">Padrão Urbano (Veículos)</option><option value="PEDESTRE_CALCADAO">Pedestres / Calçadão</option><option value="MACRO_PLANEJAMENTO">Macro Planejamento</option></select><div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">▼</div></div><p className="text-[10px] text-slate-400 px-2 leading-relaxed">O perfil selecionado define automaticamente as larguras de via, tolerância de simplificação geométrica e geração de eixos.</p></div>
                <div className="pt-8 border-t border-slate-200/50"><button onClick={() => setShowSettings(false)} className="w-full py-4 text-xs font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-2xl transition-colors">VOLTAR PARA O PROJETO</button></div>
              </div>
            )}
          </div>
        </div>
      </div>

      {mapLogic.isModalOpen && (<div className="absolute inset-0 z-[2000] bg-slate-900/40 backdrop-blur-sm flex items-center justify-center animate-in fade-in zoom-in duration-200"><div className="modal-glass p-8 w-96"><div className="flex justify-between items-center mb-6"><h3 className="font-black text-slate-800 flex items-center gap-3 text-lg"><span className="bg-blue-100 p-2 rounded-xl text-blue-600"><PenTool size={18} /></span>Novo {mapLogic.currentDrop?.type}</h3><button onClick={mapLogic.cancelMarker}><X size={20} className="text-slate-400 hover:text-red-500 transition-colors" /></button></div><div className="space-y-5"><div className="space-y-1.5"><label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider ml-1">Descrição Técnica</label><input className="w-full bg-white border border-slate-200 rounded-2xl p-3.5 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all font-medium text-slate-700" autoFocus placeholder="Ex: Poste Bifásico com Transformador" value={mapLogic.metaInput.desc} onChange={e => mapLogic.setMetaInput({ ...mapLogic.metaInput, desc: e.target.value })} /></div><div className="space-y-1.5"><label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider ml-1">Altura / Especificação</label><input className="w-full bg-white border border-slate-200 rounded-2xl p-3.5 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all font-medium text-slate-700" placeholder="Ex: 12m" value={mapLogic.metaInput.altura} onChange={e => mapLogic.setMetaInput({ ...mapLogic.metaInput, altura: e.target.value })} /></div><button onClick={mapLogic.confirmMarker} className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-2xl font-bold text-sm flex justify-center gap-2 transition-all shadow-lg shadow-blue-500/30 mt-2 hover:-translate-y-0.5"><Save size={18} /> SALVAR PONTO</button></div></div></div>)}
    </div >
  );
}

function DraggableTool({ icon, label, type, onDragStart, description }) {
  return (
    <div
      draggable
      onDragStart={(e) => onDragStart(e, type)}
      className="group relative p-4 rounded-2xl cursor-grab active:cursor-grabbing transition-all hover:bg-white/20 hover:shadow-lg border border-transparent hover:border-white/30"
    >
      {icon}
      <div className="absolute left-20 top-1/2 -translate-y-1/2 bg-slate-800 text-white px-3 py-2 rounded-xl opacity-0 group-hover:opacity-100 transition-all pointer-events-none whitespace-nowrap z-50 shadow-xl translate-x-2 group-hover:translate-x-0 border border-slate-700">
        <span className="block text-xs font-bold">{label}</span>
        {description && <span className="block text-[9px] text-slate-400 font-medium uppercase tracking-wider">{description}</span>}
      </div>
    </div>
  )
}