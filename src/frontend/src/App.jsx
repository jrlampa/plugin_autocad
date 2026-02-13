import React, { useState, useEffect, Suspense, lazy } from 'react';
import { SdkTest } from './components/SdkTest';
import { UploadCloud, AlertTriangle, X, Clock } from 'lucide-react';
import { useMapLogic } from './hooks/useMapLogic';
import { useFileProcessing } from './hooks/useFileProcessing';
import { useDrawingCanvas } from './hooks/useDrawingCanvas';
import { api } from './api';
import LoadingScreen from './components/LoadingScreen';

// New Components
import Sidebar from './components/Sidebar';
import SettingsPanel from './components/SettingsPanel';
import JobOverlay from './components/JobOverlay';
import MapCanvas from './components/MapCanvas';
import Toast from './components/Toast';

// Lazy load heavy components for faster TTI
const MapView = lazy(() => import('./components/MapView'));
const AiAssistant = lazy(() =>
  import('./components/AiAssistant').then((mod) => ({ default: mod.AiAssistant }))
);

// --- APP PRINCIPAL ---
export default function App() {
  const mapLogic = useMapLogic();

  // ** Hooks Customizados **
  const {
    isDraggingFile,
    previewGeoJson,
    handleGlobalDrop,
    handleDragOver,
    handleDragLeave,
    handleImportGeoJson,
    setPreviewGeoJson,
    toastMessage: fileToast,
    clearToast: clearFileToast,
  } = useFileProcessing();

  const { isDrawing, drawingPoints, toggleDrawing, finishDrawing, addPoint } =
    useDrawingCanvas(setPreviewGeoJson);

  // ** Estado de Carregamento Inicial (Backend Health Check) **
  const [isBackendReady, setIsBackendReady] = useState(false);

  // ** Global Error State (Resilience) **
  const [globalError, setGlobalError] = useState(null);

  // ** UI State **
  const [coords, setCoords] = useState({ lat: -21.7634, lng: -41.3235 });
  const [inputText, setInputText] = useState('-21.763400, -41.323500');
  const [inputLoading, setInputLoading] = useState(false);
  const [hostJob, setHostJob] = useState(null);
  const uiJob = hostJob;
  const loading = uiJob && !['completed', 'failed'].includes(uiJob.status);

  const [baseLayer, setBaseLayer] = useState('satellite');
  const [radius, setRadius] = useState(500);
  const [radiusInput, setRadiusInput] = useState(500);
  const [showSettings, setShowSettings] = useState(false);

  const [engConfig, setEngConfig] = useState({
    profile_name: 'PADRAO_URBANO',
    crs_out: 'EPSG:31984',
    unit: 'm',
    override_generate_axis: null,
  });

  // ** Backend Check Effect **
  useEffect(() => {
    let isMounted = true;
    const checkBackend = async () => {
      const isHealthy = await api.checkHealth();
      if (isHealthy && isMounted) {
        if (typeof process !== 'undefined' && process.env.NODE_ENV === 'test') {
          setIsBackendReady(true);
        } else {
          setTimeout(() => setIsBackendReady(true), 500);
        }
      } else if (isMounted) {
        setTimeout(checkBackend, 500);
      }
    };
    checkBackend();
    return () => {
      isMounted = false;
    };
  }, []);

  // ** Global Error Listener **
  useEffect(() => {
    const handleApiError = (event) => {
      const { type, message } = event.detail;
      setGlobalError({ type, message });
      setTimeout(() => setGlobalError(null), 5000);
    };
    window.addEventListener('api-error', handleApiError);
    return () => window.removeEventListener('api-error', handleApiError);
  }, []);

  // ** Handshake & WebView Listeners (Geolocation, JobProgress) **
  useEffect(() => {
    if (isBackendReady && window.chrome?.webview) {
      console.log('React is ready. Sending APP_READY handshake...');
      window.chrome.webview.postMessage({ action: 'APP_READY' });
    }

    const handleWebViewMessage = (event) => {
      if (typeof event.data === 'string') {
        try {
          const message = JSON.parse(event.data);
          // Auth handled in useFileProcessing or here?
          // Auth is critical, let's keep it here or shared.
          if (message.action === 'INIT_AUTH_TOKEN' && message.data.token) {
            console.log('Master token received from host. Establishing secure session...');
            api.setupSecurity(message.data.token);
          }
          if (message.action === 'JOB_PROGRESS' && message.data) {
            setHostJob(message.data);
          }
          if (message.action === 'GEOLOCATION_SYNC' && message.data) {
            console.log('Geolocation sync received from C#:', message.data);
            setCoords({ lat: message.data.latitude, lng: message.data.longitude });
            setInputText(
              `${message.data.latitude.toFixed(6)}, ${message.data.longitude.toFixed(6)}`
            );
          }
        } catch (e) {
          console.error(e);
        }
      }
    };

    if (window.chrome && window.chrome.webview) {
      window.chrome.webview.addEventListener('message', handleWebViewMessage);
    }
    return () => {
      if (window.chrome && window.chrome.webview) {
        window.chrome.webview.removeEventListener('message', handleWebViewMessage);
      }
    };
  }, [isBackendReady]);

  // ** Actions **
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
    } catch (err) {
      console.error(err);
    } finally {
      setInputLoading(false);
    }
  };

  const handleMapClick = (latlng) => {
    if (isDrawing) {
      addPoint(latlng);
    } else {
      setCoords(latlng);
      setInputText(`${latlng.lat.toFixed(6)}, ${latlng.lng.toFixed(6)}`);
    }
  };

  const handleGenerate = () => {
    if (window.chrome && window.chrome.webview) {
      const message = {
        action: 'GENERATE_OSM',
        data: {
          latitude: coords.lat,
          longitude: coords.lng,
          radius: radius,
        },
      };
      window.chrome.webview.postMessage(message);
    } else {
      // Use Toast instead of alert!
      // For now, simpler to alert or we can add a local state for this warning
      alert('Esta funcionalidade está disponível apenas ao rodar o sisRUA dentro do AutoCAD.');
    }
  };

  const tileProviders = {
    satellite: {
      url: 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
      attribution: '&copy; Google',
      subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
    },
    clean: {
      url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
      attribution: '&copy; CartoDB',
    },
    osm: {
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap contributors</a>',
    },
  };

  if (!isBackendReady) {
    return <LoadingScreen />;
  }

  return (
    <div
      data-testid="app-root"
      className={`relative w-full h-full overflow-hidden bg-slate-900 font-sans flex ${isDrawing ? 'cursor-crosshair' : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleGlobalDrop}
    >
      <SdkTest />

      {/* TOASTS */}
      {fileToast && (
        <Toast message={fileToast.message} type={fileToast.type} onClose={clearFileToast} />
      )}

      {/* OVERLAY DE UPLOAD */}
      {isDraggingFile && (
        <div className="absolute inset-0 z-[3000] bg-slate-900/60 backdrop-blur-md flex items-center justify-center m-4 rounded-3xl border-4 border-dashed border-blue-400/50 pointer-events-none animate-pulse">
          <div className="flex flex-col items-center p-8 bg-white/10 rounded-3xl backdrop-blur-xl border border-white/20">
            <UploadCloud size={64} className="text-white mb-4" />
            <span className="text-2xl font-bold text-white tracking-wide">
              Solte o arquivo GeoJSON aqui
            </span>
          </div>
        </div>
      )}

      {/* GLOBAL ERROR BANNER */}
      {globalError && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[4000] animate-in slide-in-from-top duration-300">
          <div
            className={`px-6 py-3 rounded-full shadow-2xl flex items-center gap-3 border ${globalError.type === 'RATE_LIMIT' ? 'bg-amber-100 text-amber-800 border-amber-200' : 'bg-red-100 text-red-800 border-red-200'}`}
          >
            {globalError.type === 'RATE_LIMIT' ? <Clock size={20} /> : <AlertTriangle size={20} />}
            <span className="text-xs font-bold">{globalError.message}</span>
            <button
              onClick={() => setGlobalError(null)}
              className="ml-2 hover:bg-black/5 rounded-full p-1"
            >
              <X size={14} />
            </button>
          </div>
        </div>
      )}

      {/* 1. SIDEBAR */}
      <Sidebar
        mapLogic={mapLogic}
        isDrawing={isDrawing}
        drawingPoints={drawingPoints}
        loading={loading}
        onToggleDrawing={toggleDrawing}
        onFinishDrawing={finishDrawing}
        onGenerate={handleGenerate}
      />

      {/* 2. MAPA */}
      <MapCanvas
        MapView={MapView}
        coords={coords}
        baseLayer={baseLayer}
        tileProviders={tileProviders}
        radius={radius}
        previewGeoJson={previewGeoJson}
        isDrawing={isDrawing}
        drawingPoints={drawingPoints}
        mapLogic={mapLogic}
        handleMapClick={handleMapClick}
      />

      {/* 3. PAINEL DIREITO + SETTINGS */}
      <SettingsPanel
        showSettings={showSettings}
        setShowSettings={setShowSettings}
        loading={loading}
        previewGeoJson={previewGeoJson}
        handleImportGeoJson={handleImportGeoJson}
        setPreviewGeoJson={setPreviewGeoJson}
        inputText={inputText}
        setInputText={setInputText}
        handleGeocode={handleGeocode}
        inputLoading={inputLoading}
        radius={radius}
        setRadius={setRadius}
        radiusInput={radiusInput}
        setRadiusInput={setRadiusInput}
        baseLayer={baseLayer}
        setBaseLayer={setBaseLayer}
        tileProviders={tileProviders}
        engConfig={engConfig}
        setEngConfig={setEngConfig}
        uiJob={uiJob}
        api={api}
      />

      {/* 4. JOB OVERLAY (Should be visible when settings are closed too? Or handled inside settings?
          Original code had Job Status INSIDE the settings panel area when !showSettings.
          The separate JobOverlay component can be used inside SettingsPanel or here.
          Since SettingsPanel handles the right sidebar logic, let's keep it there or exact match original.
          Original: Inside "Painel Direito" -> !showSettings -> uiJob render.
          So SettingsPanel already includes the UI Job rendering logic.
          But if we want a floating overlay, we can use JobOverlay.
          Wait, SettingsPanel code I wrote DOES NOT include JobOverlay component invocation, 
          it just receives uiJob. I need to make sure SettingsPanel Uses JobOverlay.
          Let's re-read SettingsPanel code I wrote.
      */}

      {/* 5. MODAL DE EDIÇÃO DE PONTO (Do we move this too? Keeps in App for now or move to MapCanvas?) */}
      {/* MapLogic modal state is here. Let's keep it here for z-index context or move to a component. */}
      {/* For simplicity/safety, I'll keep the Modal rendering block here or create a Modal component if needed, 
          but simpler to keep it if it's small. Actually, it's quite verbose. Let's start with this. */}

      {mapLogic.isModalOpen && (
        <div className="absolute inset-0 z-[2000] bg-slate-900/40 backdrop-blur-sm flex items-center justify-center animate-in fade-in zoom-in duration-200">
          {/* ... Modal Content ... */}
          {/* I should probably extract this to SymbolModal.jsx later, but for now I will inline or use existing logic if possible.
                 Wait, I can't inline "existing logic" if I overwrite App.jsx.
                 I must write the full content.
             */}
          <div className="modal-glass p-8 w-96">
            <div className="flex justify-between items-center mb-6">
              {/* ... header ... */}
              <h3 className="font-black text-slate-800 flex items-center gap-3 text-lg">
                <span className="bg-blue-100 p-2 rounded-xl text-blue-600">{/* icon? */}</span>
                Novo {mapLogic.currentDrop?.type}
              </h3>
              <button onClick={mapLogic.cancelMarker}>
                <X size={20} className="text-slate-400 hover:text-red-500 transition-colors" />
              </button>
            </div>
            {/* Body */}
            <div className="space-y-5">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider ml-1">
                  Descrição Técnica
                </label>
                <input
                  className="w-full bg-white border border-slate-200 rounded-2xl p-3.5 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all font-medium text-slate-700"
                  autoFocus
                  placeholder="Ex: Poste Bifásico..."
                  value={mapLogic.metaInput.desc}
                  onChange={(e) =>
                    mapLogic.setMetaInput({ ...mapLogic.metaInput, desc: e.target.value })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider ml-1">
                  Altura
                </label>
                <input
                  className="w-full bg-white border border-slate-200 rounded-2xl p-3.5 text-sm outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all font-medium text-slate-700"
                  placeholder="Ex: 12m"
                  value={mapLogic.metaInput.altura}
                  onChange={(e) =>
                    mapLogic.setMetaInput({ ...mapLogic.metaInput, altura: e.target.value })
                  }
                />
              </div>
              <button
                onClick={mapLogic.confirmMarker}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-2xl font-bold text-sm flex justify-center gap-2 transition-all shadow-lg shadow-blue-500/30"
              >
                SALVAR PONTO
              </button>
            </div>
          </div>
        </div>
      )}

      <AiAssistant />
    </div>
  );
}
