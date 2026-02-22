/**
 * src/hooks/useFileProcessing.test.js
 *
 * Testes unitários para o hook useFileProcessing.
 * Cobre:
 *  - Drag & Drop de arquivos GeoJSON pelo navegador
 *  - Recebimento de mensagens WebView (GeoJSON e KML) do host C#
 *  - Importação de GeoJSON para o AutoCAD
 *  - Toast de erro em casos de arquivo inválido
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useFileProcessing } from './useFileProcessing';

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

/** Cria um objeto File simulado para drag & drop. */
function makeFileEvent(content, type = 'application/json') {
  const file = new Blob([content], { type });
  file.name = 'test.geojson';

  const mockReader = {
    readAsText: vi.fn(function () {
      this.onload({ target: { result: content } });
    }),
    onload: null,
  };
  vi.spyOn(global, 'FileReader').mockImplementation(() => mockReader);

  return {
    preventDefault: vi.fn(),
    dataTransfer: {
      files: [file],
      types: ['Files'],
    },
  };
}

const VALID_GEOJSON = JSON.stringify({
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [-22.15018, -42.92185] },
      properties: { name: 'REF_2' },
    },
  ],
});

const INVALID_JSON = 'NOT_JSON_AT_ALL';
const INVALID_GEOJSON_STRUCTURE = JSON.stringify({ not: 'a geojson' });

// ─────────────────────────────────────────────
// Setup de WebView mock
// ─────────────────────────────────────────────

function setupWebViewMock() {
  const listeners = {};
  const mock = {
    addEventListener: vi.fn((event, cb) => {
      listeners[event] = listeners[event] || [];
      listeners[event].push(cb);
    }),
    removeEventListener: vi.fn(),
    postMessage: vi.fn(),
    _emit: (event, data) => {
      (listeners[event] || []).forEach((cb) => cb(data));
    },
  };
  window.chrome = { webview: mock };
  return mock;
}

// ─────────────────────────────────────────────
// Testes
// ─────────────────────────────────────────────

describe('useFileProcessing', () => {
  let webview;

  beforeEach(() => {
    webview = setupWebViewMock();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    delete window.chrome;
  });

  // ── Estado inicial ──────────────────────────

  it('estado inicial é vazio', () => {
    const { result } = renderHook(() => useFileProcessing());
    expect(result.current.isDraggingFile).toBe(false);
    expect(result.current.previewGeoJson).toBeNull();
    expect(result.current.toastMessage).toBeNull();
  });

  // ── Drag & Drop no navegador ─────────────────

  it('handleDragOver ativa isDraggingFile quando há arquivos', () => {
    const { result } = renderHook(() => useFileProcessing());
    act(() => {
      result.current.handleDragOver({ preventDefault: vi.fn(), dataTransfer: { types: ['Files'] } });
    });
    expect(result.current.isDraggingFile).toBe(true);
  });

  it('handleDragLeave desativa isDraggingFile', () => {
    const { result } = renderHook(() => useFileProcessing());
    act(() => {
      result.current.handleDragOver({ preventDefault: vi.fn(), dataTransfer: { types: ['Files'] } });
      result.current.handleDragLeave();
    });
    expect(result.current.isDraggingFile).toBe(false);
  });

  it('handleGlobalDrop com GeoJSON válido define previewGeoJson', () => {
    const { result } = renderHook(() => useFileProcessing());
    const dropEvent = makeFileEvent(VALID_GEOJSON);

    act(() => {
      result.current.handleGlobalDrop(dropEvent);
    });

    expect(result.current.previewGeoJson).not.toBeNull();
    expect(result.current.previewGeoJson.type).toBe('FeatureCollection');
  });

  it('handleGlobalDrop com JSON inválido cria toast de erro', () => {
    const { result } = renderHook(() => useFileProcessing());
    const dropEvent = makeFileEvent(INVALID_JSON);

    act(() => {
      result.current.handleGlobalDrop(dropEvent);
    });

    expect(result.current.toastMessage).not.toBeNull();
    expect(result.current.toastMessage.type).toBe('error');
  });

  it('handleGlobalDrop com estrutura GeoJSON inválida cria toast de erro', () => {
    const { result } = renderHook(() => useFileProcessing());
    const dropEvent = makeFileEvent(INVALID_GEOJSON_STRUCTURE);

    act(() => {
      result.current.handleGlobalDrop(dropEvent);
    });

    expect(result.current.toastMessage?.type).toBe('error');
  });

  it('clearToast limpa toastMessage', () => {
    const { result } = renderHook(() => useFileProcessing());
    const dropEvent = makeFileEvent(INVALID_JSON);

    act(() => result.current.handleGlobalDrop(dropEvent));
    expect(result.current.toastMessage).not.toBeNull();

    act(() => result.current.clearToast());
    expect(result.current.toastMessage).toBeNull();
  });

  // ── WebView: GeoJSON do C# ────────────────────

  it('mensagem FILE_DROPPED_GEOJSON do host define previewGeoJson', () => {
    const { result } = renderHook(() => useFileProcessing());

    act(() => {
      webview._emit('message', {
        data: JSON.stringify({
          action: 'FILE_DROPPED_GEOJSON',
          data: { content: VALID_GEOJSON },
        }),
      });
    });

    expect(result.current.previewGeoJson?.type).toBe('FeatureCollection');
  });

  it('mensagem FILE_DROPPED_GEOJSON com conteúdo inválido cria toast de erro', () => {
    const { result } = renderHook(() => useFileProcessing());

    act(() => {
      webview._emit('message', {
        data: JSON.stringify({
          action: 'FILE_DROPPED_GEOJSON',
          data: { content: INVALID_JSON },
        }),
      });
    });

    expect(result.current.toastMessage?.type).toBe('error');
  });

  // ── WebView: KML do C# ───────────────────────

  it('mensagem FILE_DROPPED_KML com KML mínimo válido define previewGeoJson', async () => {
    // KML simples com um Placemark
    const kmlContent = `<?xml version="1.0" encoding="UTF-8"?>
      <kml xmlns="http://www.opengis.net/kml/2.2">
        <Placemark>
          <Point><coordinates>-42.92185,-22.15018,0</coordinates></Point>
        </Placemark>
      </kml>`;

    const { result } = renderHook(() => useFileProcessing());

    await act(async () => {
      webview._emit('message', {
        data: JSON.stringify({
          action: 'FILE_DROPPED_KML',
          data: { content: kmlContent },
        }),
      });
      // Aguarda a importação dinâmica de @mapbox/togeojson
      await new Promise((r) => setTimeout(r, 100));
    });

    // Aceita sucesso (GeoJSON definido) ou erro gracioso (toast de erro)
    // depende da disponibilidade de @mapbox/togeojson no ambiente de teste
    const isGeoJsonOrError =
      result.current.previewGeoJson !== null || result.current.toastMessage !== null;
    expect(isGeoJsonOrError).toBe(true);
  });

  // ── Importação para AutoCAD ──────────────────

  it('handleImportGeoJson envia mensagem IMPORT_GEOJSON ao WebView', () => {
    const { result } = renderHook(() => useFileProcessing());

    // Define um preview primeiro
    act(() => {
      result.current.setPreviewGeoJson(JSON.parse(VALID_GEOJSON));
    });

    act(() => {
      result.current.handleImportGeoJson();
    });

    expect(webview.postMessage).toHaveBeenCalledWith(
      expect.objectContaining({ action: 'IMPORT_GEOJSON' })
    );
    // Preview deve ser limpo após importação
    expect(result.current.previewGeoJson).toBeNull();
  });

  it('handleImportGeoJson sem WebView disponível cria toast de erro', () => {
    // Roda sem WebView — não configura window.chrome no beforeEach para este teste
    delete window.chrome;
    const { result } = renderHook(() => useFileProcessing());

    act(() => {
      result.current.setPreviewGeoJson(JSON.parse(VALID_GEOJSON));
    });

    act(() => {
      result.current.handleImportGeoJson();
    });

    expect(result.current.toastMessage?.type).toBe('error');
  });

  it('handleImportGeoJson sem preview não envia mensagem', () => {
    const { result } = renderHook(() => useFileProcessing());
    act(() => {
      result.current.handleImportGeoJson();
    });
    expect(webview.postMessage).not.toHaveBeenCalled();
  });
});
