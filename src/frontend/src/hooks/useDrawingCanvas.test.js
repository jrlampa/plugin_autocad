/**
 * src/hooks/useDrawingCanvas.test.js
 *
 * Testes unitários para o hook useDrawingCanvas.
 * Cobre:
 *  - toggleDrawing liga/desliga o modo de desenho
 *  - addPoint acumula coordenadas quando em modo de desenho
 *  - finishDrawing converte pontos para FeatureCollection GeoJSON
 *  - Guarda contra duplicatas
 *  - Mínimo de 2 pontos para encerrar o desenho
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import { useDrawingCanvas } from './useDrawingCanvas';

describe('useDrawingCanvas', () => {
  // ── Estado inicial ──────────────────────────

  it('estado inicial: não está desenhando, sem pontos', () => {
    const setPreview = vi.fn();
    const { result } = renderHook(() => useDrawingCanvas(setPreview));

    expect(result.current.isDrawing).toBe(false);
    expect(result.current.drawingPoints).toHaveLength(0);
  });

  // ── toggleDrawing ────────────────────────────

  it('toggleDrawing liga o modo de desenho', () => {
    const { result } = renderHook(() => useDrawingCanvas(vi.fn()));
    act(() => result.current.toggleDrawing());
    expect(result.current.isDrawing).toBe(true);
  });

  it('toggleDrawing desliga o modo e limpa pontos', () => {
    const { result } = renderHook(() => useDrawingCanvas(vi.fn()));

    // Liga e espera atualização
    act(() => result.current.toggleDrawing());
    expect(result.current.isDrawing).toBe(true);

    // Adiciona ponto
    act(() => result.current.addPoint({ lat: -22.15, lng: -42.92 }));
    expect(result.current.drawingPoints).toHaveLength(1);

    // Desliga e verifica limpeza
    act(() => result.current.toggleDrawing());
    expect(result.current.isDrawing).toBe(false);
    expect(result.current.drawingPoints).toHaveLength(0);
  });

  // ── addPoint ────────────────────────────────

  it('addPoint não adiciona ponto quando não está desenhando', () => {
    const { result } = renderHook(() => useDrawingCanvas(vi.fn()));
    act(() => result.current.addPoint({ lat: -22.15, lng: -42.92 }));
    expect(result.current.drawingPoints).toHaveLength(0);
  });

  it('addPoint acumula múltiplos pontos durante o desenho', () => {
    const { result } = renderHook(() => useDrawingCanvas(vi.fn()));

    act(() => result.current.toggleDrawing());
    expect(result.current.isDrawing).toBe(true);

    act(() => result.current.addPoint({ lat: -22.15018, lng: -42.92185 }));
    act(() => result.current.addPoint({ lat: -22.151, lng: -42.923 }));
    act(() => result.current.addPoint({ lat: -22.152, lng: -42.924 }));

    expect(result.current.drawingPoints).toHaveLength(3);
    // Coordenadas armazenadas como [lng, lat] (GeoJSON padrão)
    expect(result.current.drawingPoints[0]).toEqual([-42.92185, -22.15018]);
  });

  // ── finishDrawing ────────────────────────────

  it('finishDrawing com menos de 2 pontos não chama setPreviewGeoJson', () => {
    const setPreview = vi.fn();
    const { result } = renderHook(() => useDrawingCanvas(setPreview));

    act(() => {
      result.current.toggleDrawing();
      result.current.addPoint({ lat: -22.15, lng: -42.92 });
      result.current.finishDrawing();
    });

    expect(setPreview).not.toHaveBeenCalled();
  });

  it('finishDrawing com 2+ pontos cria FeatureCollection e encerra o modo', () => {
    const setPreview = vi.fn();
    const { result } = renderHook(() => useDrawingCanvas(setPreview));

    act(() => result.current.toggleDrawing());
    act(() => result.current.addPoint({ lat: -22.15018, lng: -42.92185 })); // REF_2
    act(() => result.current.addPoint({ lat: -22.155, lng: -42.928 }));
    act(() => result.current.finishDrawing());

    expect(setPreview).toHaveBeenCalled();
    // Verifica a função updater passada ao setPreview
    const updaterFn = setPreview.mock.calls[0][0];
    const result2 = updaterFn(null);
    expect(result2.type).toBe('FeatureCollection');
    expect(result2.features).toHaveLength(1);
    expect(result2.features[0].geometry.type).toBe('LineString');
    expect(result2.features[0].properties.highway).toBe('residential');

    // Deve encerrar o modo de desenho
    expect(result.current.isDrawing).toBe(false);
    expect(result.current.drawingPoints).toHaveLength(0);
  });

  it('finishDrawing adiciona à FeatureCollection existente', () => {
    const setPreview = vi.fn();
    const { result } = renderHook(() => useDrawingCanvas(setPreview));

    const existing = {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [0, 0] },
          properties: {},
        },
      ],
    };

    act(() => result.current.toggleDrawing());
    act(() => result.current.addPoint({ lat: -22.15, lng: -42.92 }));
    act(() => result.current.addPoint({ lat: -22.16, lng: -42.93 }));
    act(() => result.current.finishDrawing());

    const updaterFn = setPreview.mock.calls[0][0];
    const result2 = updaterFn(existing);
    expect(result2.features).toHaveLength(2);
  });

  it('finishDrawing não adiciona feature duplicada', () => {
    const setPreview = vi.fn();
    const { result } = renderHook(() => useDrawingCanvas(setPreview));

    // Primeiro desenho
    act(() => result.current.toggleDrawing());
    act(() => result.current.addPoint({ lat: -22.15, lng: -42.92 }));
    act(() => result.current.addPoint({ lat: -22.16, lng: -42.93 }));
    act(() => result.current.finishDrawing());

    const updaterFn1 = setPreview.mock.calls[0][0];
    const stateAfterFirst = updaterFn1(null);
    expect(stateAfterFirst.features).toHaveLength(1);

    // Segundo desenho com as mesmas coordenadas
    act(() => result.current.toggleDrawing());
    act(() => result.current.addPoint({ lat: -22.15, lng: -42.92 }));
    act(() => result.current.addPoint({ lat: -22.16, lng: -42.93 }));
    act(() => result.current.finishDrawing());

    const updaterFn2 = setPreview.mock.calls[1][0];
    const stateAfterSecond = updaterFn2(stateAfterFirst);

    // Não deve duplicar a feature idêntica
    expect(stateAfterSecond.features).toHaveLength(1);
  });
});
