import React from 'react';
import { X } from 'lucide-react';

/**
 * Modal para edição de metadados de pontos (Símbolos BricsCAD/AutoCAD)
 */
export default function SymbolModal({ mapLogic }) {
    if (!mapLogic.isModalOpen) return null;

    return (
        <div className="absolute inset-0 z-[2000] bg-slate-900/40 backdrop-blur-sm flex items-center justify-center animate-in fade-in zoom-in duration-200">
            <div className="modal-glass p-8 w-96 shadow-2xl border border-white/20">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="font-black text-slate-800 flex items-center gap-3 text-lg">
                        <span className="bg-blue-100 p-2 rounded-xl text-blue-600 block">
                            <svg
                                width="20" height="20" viewBox="0 0 24 24"
                                fill="none" stroke="currentColor" strokeWidth="2.5"
                                strokeLinecap="round" strokeLinejoin="round"
                            >
                                <circle cx="12" cy="12" r="10" />
                                <path d="M12 8l0 8" />
                                <path d="M8 12l8 0" />
                            </svg>
                        </span>
                        Novo {mapLogic.currentDrop?.type || 'Ponto'}
                    </h3>
                    <button
                        onClick={mapLogic.cancelMarker}
                        className="p-1 hover:bg-red-50 hover:text-red-500 rounded-lg transition-colors"
                    >
                        <X size={20} className="text-slate-400" />
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
                            Altura (Z)
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
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-2xl font-bold text-sm flex justify-center gap-2 transition-all shadow-lg shadow-blue-500/30 active:scale-[0.98]"
                    >
                        SALVAR PONTO
                    </button>
                </div>
            </div>
        </div>
    );
}
