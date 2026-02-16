import { Spline, CheckCircle2, Zap, Loader2, Scissors, Lightbulb } from 'lucide-react';

export default function Sidebar({
  mapLogic,
  isDrawing,
  drawingPoints,
  drawingMode,
  loading,
  onToggleDrawing,
  onFinishDrawing,
  onGenerate,
}) {
  return (
    <div className="absolute left-4 top-4 bottom-4 w-20 z-[1000] flex flex-col items-center py-6 gap-5 bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl shadow-2xl transition-all hover:bg-white/20 hover:scale-[1.01]">
      <div className="mb-2 w-12 h-12 flex items-center justify-center bg-gradient-to-br from-slate-800 to-slate-900 rounded-2xl shadow-lg border border-white/10 text-white font-black text-xl">
        R
      </div>
      <div className="w-10 border-t border-white/20 my-1"></div>

      <DraggableTool
        icon={<Lightbulb size={22} className="text-amber-400 fill-amber-400/20" />}
        label="Poste"
        type="POSTE"
        onDragStart={mapLogic.handleDragStart}
        description="Rede Elétrica"
      />

      <div className="w-10 border-t border-white/20 my-1"></div>

      {/* Manual Street Drawing */}
      <button
        aria-label="Desenhar Rua"
        onClick={() => onToggleDrawing('line')}
        className={`p-4 rounded-2xl shadow-xl transition-all active:scale-95 group relative ${isDrawing && drawingMode === 'line' ? 'bg-red-500 hover:bg-red-600' : 'bg-slate-700/50 hover:bg-slate-700'}`}
      >
        <Spline size={24} className="text-white" />
        <span className="absolute left-full ml-4 bg-slate-900 text-white text-xs font-bold px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
          {isDrawing && drawingMode === 'line' ? 'Cancelar' : 'Desenhar Rua'}
        </span>
      </button>

      {/* Area Selection (Polygon) */}
      <button
        aria-label="Selecionar Área"
        onClick={() => onToggleDrawing('polygon')}
        className={`p-4 rounded-2xl shadow-xl transition-all active:scale-95 group relative ${isDrawing && drawingMode === 'polygon' ? 'bg-red-500 hover:bg-red-600' : 'bg-blue-600/50 hover:bg-blue-600'}`}
      >
        <Scissors size={24} className="text-white" />
        <span className="absolute left-full ml-4 bg-slate-900 text-white text-xs font-bold px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
          {isDrawing && drawingMode === 'polygon' ? 'Cancelar' : 'Selecionar Área'}
        </span>
      </button>

      {isDrawing && drawingPoints.length > 2 && (
        <button
          onClick={onFinishDrawing}
          className="p-4 rounded-2xl shadow-xl transition-all active:scale-95 group relative bg-green-600 hover:bg-green-500 animate-in zoom-in"
        >
          <CheckCircle2 size={24} className="text-white" />
          <span className="absolute left-full ml-4 bg-slate-900 text-white text-xs font-bold px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
            Confirmar
          </span>
        </button>
      )}

      <div className="flex-1"></div>
      <button
        aria-label="Gerar Projeto (OSM)"
        data-testid="btn-generate-osm"
        onClick={onGenerate}
        disabled={loading}
        className={`p-4 rounded-2xl shadow-xl transition-all active:scale-95 group relative ${loading ? 'bg-slate-500 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-500 hover:shadow-blue-500/40'}`}
      >
        {loading ? (
          <Loader2 className="animate-spin text-white" />
        ) : (
          <Zap className="text-white fill-white" />
        )}
        <span className="absolute left-full ml-4 bg-slate-900 text-white text-xs font-bold px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
          Gerar Projeto (OSM)
        </span>
      </button>
    </div>
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
        {description && (
          <span className="block text-[9px] text-slate-400 font-medium uppercase tracking-wider">
            {description}
          </span>
        )}
      </div>
    </div>
  );
}
