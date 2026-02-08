import React, { Suspense } from 'react';
import { Loader2 } from 'lucide-react';

// Map loading fallback
const MapLoadingFallback = () => (
  <div className="h-full w-full bg-slate-900 flex items-center justify-center">
    <div className="text-center">
      <Loader2 className="animate-spin text-blue-400 mx-auto" size={48} />
      <p className="text-slate-400 text-sm mt-4 font-medium">Carregando mapa...</p>
    </div>
  </div>
);

export default function MapCanvas({
  MapView,
  coords,
  baseLayer,
  tileProviders,
  radius,
  previewGeoJson,
  isDrawing,
  drawingPoints,
  mapLogic,
  handleMapClick
}) {
  return (
    <div className="flex-1 relative z-0">
      <Suspense fallback={<MapLoadingFallback />}>
        <MapView
          coords={coords}
          tileProvider={tileProviders[baseLayer]}
          radius={radius}
          previewGeoJson={previewGeoJson}
          isDrawing={isDrawing}
          drawingPoints={drawingPoints}
          markers={mapLogic.markers}
          onSymbolDrop={mapLogic.handleSymbolDrop}
          onMapClick={handleMapClick}
        />
      </Suspense>
    </div>
  );
}
