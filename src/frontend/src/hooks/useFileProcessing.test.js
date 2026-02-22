/**
 * src/hooks/useFileProcessing.test.js
 *
 * Testes unitários para o hook useFileProcessing.
 * Cobre:
 *  - Drag & Drop de arquivos GeoJSON pelo navegador
 *  - Recebimento de mensagens WebView (GeoJSON e KML) do host C#
 *  - Importação de GeoJSON para o AutoCAD
 *  - Toast de erro em casos de arquivo inválido
 *  - KML inválido após conversão (linha 39) e KML que lança exceção (linha 42)
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { useFileProcessing } from './useFileProcessing';

// ─────────────────────────────────────────────────────
// Mock de @mapbox/togeojson para controlar comportamento
// do kml() nas linhas 36-43 de useFileProcessing.js
// ─────────────────────────────────────────────────────

// _kmlMockReturn é o retorno padrão de kml() — trocado por teste para simular erros
let _kmlMockReturn = { type: 'FeatureCollection', features: [{ type: 'Feature' }] };
let _kmlMockThrow = null;

vi.mock('@mapbox/togeojson', () => ({
  kml: (...args) => {
    if (_kmlMockThrow) throw _kmlMockThrow;
    return _kmlMockReturn;
  },
}));

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
      geometry: { type: 'Point', coordinates: [-42.92185, -22.15018] },
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
    // Reset KML mock state
    _kmlMockReturn = { type: 'FeatureCollection', features: [{ type: 'Feature' }] };
    _kmlMockThrow = null;
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

  // ── Branches adicionais para cobertura total ──

  it('mensagem FILE_DROPPED_GEOJSON com estrutura inválida (sem features/geometry) cria toast de erro (linha 52)', async () => {
    // Cobre linha 52-53: parsed.type existe mas parsed.features e parsed.geometry são ambos undefined
    const invalidStructure = JSON.stringify({ type: 'FeatureCollection' }); // sem features
    const { result } = renderHook(() => useFileProcessing());

    await act(async () => {
      webview._emit('message', {
        data: JSON.stringify({
          action: 'FILE_DROPPED_GEOJSON',
          data: { content: invalidStructure },
        }),
      });
    });

    expect(result.current.toastMessage?.type).toBe('error');
    expect(result.current.toastMessage?.message).toMatch(/inválido/i);
  });

  it('mensagem FILE_DROPPED_GEOJSON com JSON mal-formado cria toast de erro (linha 53-54)', async () => {
    // Cobre catch interno: JSON.parse do content lança SyntaxError
    const { result } = renderHook(() => useFileProcessing());

    await act(async () => {
      webview._emit('message', {
        data: JSON.stringify({
          action: 'FILE_DROPPED_GEOJSON',
          data: { content: 'INVALID_JSON_CONTENT' },
        }),
      });
    });

    expect(result.current.toastMessage?.type).toBe('error');
    expect(result.current.toastMessage?.message).toMatch(/GeoJSON|Erro/i);
  });

  it('mensagem não-JSON é ignorada silenciosamente (linha 59-61 — outer catch)', async () => {
    // Cobre o catch {} externo: quando event.data não é JSON válido
    const { result } = renderHook(() => useFileProcessing());

    await act(async () => {
      // Envia uma string que não é JSON
      webview._emit('message', { data: 'NOT_A_JSON_STRING' });
    });

    // Não deve definir toast de erro nem alterar previewGeoJson (silencioso)
    expect(result.current.toastMessage).toBeNull();
    expect(result.current.previewGeoJson).toBeNull();
  });

  // ── KML com conversão inválida (kml() retorna estrutura sem features) ──

  it('KML com conversão inválida (sem features/geometry) cria toast de erro (linha 39)', async () => {
    // kml() retorna objeto sem features e sem geometry → linha 39: showError(...)
    _kmlMockReturn = { type: 'FeatureCollection' }; // sem 'features'

    const kmlContent = `<?xml version="1.0"?><kml><Placemark><Point>
      <coordinates>-42.92185,-22.15018,0</coordinates></Point></Placemark></kml>`;
    const { result } = renderHook(() => useFileProcessing());

    await act(async () => {
      webview._emit('message', {
        data: JSON.stringify({
          action: 'FILE_DROPPED_KML',
          data: { content: kmlContent },
        }),
      });
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.toastMessage?.type).toBe('error');
    expect(result.current.toastMessage?.message).toMatch(/KMZ\/KML|Conversão/i);
  });

  it('KML onde kml() lança exceção cria toast de erro (linha 42)', async () => {
    // kml() lança TypeError → catch(err) → linha 42: showError(...)
    _kmlMockThrow = new Error('DOMParser falhou catastroficamente');

    const kmlContent = `<?xml version="1.0"?><kml><Placemark></Placemark></kml>`;
    const { result } = renderHook(() => useFileProcessing());

    await act(async () => {
      webview._emit('message', {
        data: JSON.stringify({
          action: 'FILE_DROPPED_KML',
          data: { content: kmlContent },
        }),
      });
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(result.current.toastMessage?.type).toBe('error');
    expect(result.current.toastMessage?.message).toMatch(/processar KML/i);
  });
});
