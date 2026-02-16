import { useState, useCallback } from 'react';

export function useDrawingCanvas(setPreviewGeoJson) {
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingPoints, setDrawingPoints] = useState([]);
  const [drawingMode, setDrawingMode] = useState('line'); // 'line' or 'polygon'

  const toggleDrawing = useCallback((mode = 'line') => {
    setIsDrawing((prev) => {
      if (prev) {
        setDrawingPoints([]); // Clear on cancel
      } else {
        setDrawingMode(mode);
      }
      return !prev;
    });
  }, []);

  const addPoint = useCallback(
    (latlng) => {
      if (isDrawing) {
        setDrawingPoints((prev) => [...prev, [latlng.lng, latlng.lat]]);
      }
    },
    [isDrawing]
  );

  const finishDrawing = useCallback(() => {
    if (drawingPoints.length < 2) return;

    if (drawingMode === 'line') {
      const newFeature = {
        type: 'Feature',
        properties: {
          name: 'Rua Desenhada Manualmente',
          highway: 'residential',
          layer: 'V_LOCAL',
          created_at: new Date().toISOString(),
        },
        geometry: { type: 'LineString', coordinates: drawingPoints },
      };

      setPreviewGeoJson((prev) => {
        const base = prev || { type: 'FeatureCollection', features: [] };
        const existing = base.type === 'FeatureCollection' ? base.features : [base];

        // Avoid duplicates
        const isDuplicate = existing.some(
          (f) =>
            JSON.stringify(f.geometry.coordinates) === JSON.stringify(newFeature.geometry.coordinates)
        );

        if (isDuplicate) return base;

        return {
          type: 'FeatureCollection',
          features: [...existing, newFeature],
        };
      });
    } else if (drawingMode === 'polygon') {
      // For polygon mode, we don't necessarily add it to permanent GeoJSON preview
      // but we return it or let the App handle the "polygon" state.
    }

    setIsDrawing(false);
    setDrawingPoints([]);
  }, [drawingPoints, drawingMode, setPreviewGeoJson]);

  return {
    isDrawing,
    drawingPoints,
    drawingMode,
    toggleDrawing,
    addPoint,
    finishDrawing,
  };
}
