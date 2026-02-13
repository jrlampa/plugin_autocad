import { useState, useCallback } from 'react';

export function useDrawingCanvas(setPreviewGeoJson) {
  const [isDrawing, setIsDrawing] = useState(false);
  const [drawingPoints, setDrawingPoints] = useState([]);

  const toggleDrawing = useCallback(() => {
    setIsDrawing((prev) => {
      if (prev) setDrawingPoints([]); // Clear on cancel
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

    setIsDrawing(false);
    setDrawingPoints([]);
  }, [drawingPoints, setPreviewGeoJson]);

  return {
    isDrawing,
    drawingPoints,
    toggleDrawing,
    addPoint,
    finishDrawing,
  };
}
