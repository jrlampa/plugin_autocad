import React from 'react';
import {
  MapContainer,
  TileLayer,
  Circle,
  Marker,
  Popup,
  useMap,
  GeoJSON,
  Polyline,
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useEffect, useRef } from 'react';

// Map Handlers
function MapDropHandler({ onSymbolDrop }) {
  const map = useMap();
  useEffect(() => {
    const container = map.getContainer();
    const handleDrop = (e) => {
      const symbolType = e.dataTransfer.getData('symbolType');
      if (symbolType) {
        e.preventDefault();
        const latlng = map.mouseEventToLatLng(e);
        onSymbolDrop(latlng, symbolType);
      }
    };
    const handleDragOver = (e) => {
      if (e.dataTransfer.types.includes('symbolType')) e.preventDefault();
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
    map.on('dragstart', () => {
      isDragging.current = true;
    });
    map.on('dragend', () => {
      setTimeout(() => {
        isDragging.current = false;
      }, 50);
    });
    map.on('click', (e) => {
      if (!isDragging.current) onMapClick(e.latlng);
    });
  }, [map, onMapClick]);
  return null;
}

function MapController({ coords }) {
  const map = useMap();
  useEffect(() => {
    if (coords) map.flyTo(coords, 18, { animate: true, duration: 1.5 });
  }, [coords, map]);
  return null;
}

// Main Map View Component
export default function MapView({
  coords,
  tileProvider,
  radius,
  previewGeoJson,
  isDrawing,
  drawingPoints,
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
      <TileLayer key={tileProvider.url} {...tileProvider} />
      <MapController coords={coords} />
      <MapDropHandler onSymbolDrop={onSymbolDrop} />
      <MapClickHandler onMapClick={onMapClick} />

      {previewGeoJson && (
        <GeoJSON
          data={previewGeoJson}
          pathOptions={{ color: '#ff7800', weight: 5, opacity: 0.8 }}
        />
      )}

      {isDrawing && drawingPoints.length > 0 && (
        <Polyline
          positions={drawingPoints.map((p) => [p[1], p[0]])}
          pathOptions={{ color: 'lime', weight: 4, opacity: 0.7, dashArray: '10, 10' }}
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
    </MapContainer>
  );
}
