import {
  MapContainer,
  TileLayer,
  Circle,
  Marker,
  Popup,
  useMap,
  GeoJSON,
  Polyline,
  Polygon,
} from 'react-leaflet';

// ... (MapDropHandler, MapClickHandler, MapController unchanged) ...

// Main Map View Component
export default function MapView({
  coords,
  tileProvider,
  radius,
  previewGeoJson,
  isDrawing,
  drawingPoints,
  drawingMode,
  extractionPolygon,
  markers,
  onSymbolDrop,
  onMapClick,
}) {
  return (
    <MapContainer
      center={coords}
      zoom={18}
      zoomControl={false}
      className="h-full w-full outline-none bg-slate-900"
    >
      <TileLayer
        key={tileProvider.url}
        {...tileProvider}
        eventHandlers={{
          tileerror: () => {
            const event = new CustomEvent('api-error', {
              detail: {
                type: 'MAP_BLOCKED',
                message: 'Serviço de mapas bloqueado pela rede/TI. Funções CAD continuam ativas.',
              },
            });
            window.dispatchEvent(event);
          },
        }}
      />
      <MapController coords={coords} />
      <MapDropHandler onSymbolDrop={onSymbolDrop} />
      <MapClickHandler onMapClick={onMapClick} />

      {previewGeoJson && (
        <GeoJSON
          data={previewGeoJson}
          pathOptions={{ color: '#ff7800', weight: 5, opacity: 0.8 }}
        />
      )}

      {/* DRAWING FEEDBACK */}
      {isDrawing && drawingPoints.length > 0 && (
        <>
          <Polyline
            positions={drawingPoints.map((p) => [p[1], p[0]])}
            pathOptions={{
              color: drawingMode === 'polygon' ? '#3b82f6' : 'lime',
              weight: 4,
              opacity: 0.7,
              dashArray: '10, 10'
            }}
          />
          {drawingMode === 'polygon' && drawingPoints.length > 2 && (
            <Polygon
              positions={[...drawingPoints.map((p) => [p[1], p[0]]), [drawingPoints[0][1], drawingPoints[0][0]]]}
              pathOptions={{ fillColor: '#3b82f6', fillOpacity: 0.1, weight: 0 }}
            />
          )}
        </>
      )}

      {/* ACTIVE EXTRACTION AREA */}
      {extractionPolygon && extractionPolygon.length > 0 && (
        <Polygon
          positions={extractionPolygon.map(p => [p[1], p[0]])}
          pathOptions={{
            color: '#3b82f6',
            weight: 3,
            fillColor: '#3b82f6',
            fillOpacity: 0.15,
            dashArray: '5, 5'
          }}
        />
      )}

      {markers.map((m, idx) => (
        <Marker key={idx} position={[m.lat, m.lon]} opacity={0.9}>
          <Popup>
            <div className="text-slate-800">
              <strong className="block text-sm uppercase mb-1">{m.tipo}</strong>
              <span className="text-xs text-slate-500">{m.meta.desc}</span>
            </div>
          </Popup>
        </Marker>
      ))}

      {!extractionPolygon && (
        <Circle
          center={coords}
          radius={radius}
          pathOptions={{
            color: '#3b82f6',
            fillColor: '#3b82f6',
            fillOpacity: 0.08,
            dashArray: '8, 8',
            weight: 1.5,
          }}
        />
      )}
    </MapContainer>
  );
}
