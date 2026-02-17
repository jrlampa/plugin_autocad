import { useState, useEffect, useCallback } from 'react';

export function useFileProcessing() {
  const [isDraggingFile, setIsDraggingFile] = useState(false);
  const [previewGeoJson, setPreviewGeoJson] = useState(null);
  const [toastMessage, setToastMessage] = useState(null); // Local toast state or callback

  // Helper to show errors (replace with Toast system later)
  const showError = (msg) => {
    console.error(msg);
    // For now, we might rely on the parent to handle toasts,
    // or expose an error state. Let's expose an error state/callback.
    setToastMessage({ type: 'error', message: msg });
  };

  const clearToast = () => setToastMessage(null);

  // ** Handle WebView Messages (C# -> JS) **
  useEffect(() => {
    const handleWebViewMessage = async (event) => {
      if (typeof event.data === 'string') {
        try {
          const message = JSON.parse(event.data);

          // INIT_AUTH_TOKEN is handled elsewhere (or we can keep it here?)
          // App.jsx usually handles auth. We focus on FILES here.

          if (message.action === 'FILE_DROPPED_KML' && message.data.content) {
            console.log('KML content received from C# host. Converting...');
            try {
              const { kml } = await import('@mapbox/togeojson');
              const parser = new DOMParser();
              const kmlDoc = parser.parseFromString(message.data.content, 'text/xml');
              const converted = kml(kmlDoc);

              if (converted && converted.type && (converted.features || converted.geometry)) {
                setPreviewGeoJson(converted);
              } else {
                showError('Arquivo KMZ/KML inválido. Conversão falhou.');
              }
            } catch (err) {
              showError(`Erro ao processar KML: ${err.message}`);
            }
          } else if (message.action === 'FILE_DROPPED_GEOJSON' && message.data.content) {
            console.log('GeoJSON received from C# host.');
            setPreviewGeoJson(null); // Clear previous
            try {
              const parsed = JSON.parse(message.data.content);
              if (parsed && parsed.type && (parsed.features || parsed.geometry)) {
                setPreviewGeoJson(parsed);
              } else {
                showError('GeoJSON inválido recebido do C#.');
              }
            } catch (err) {
              showError(`Erro ao processar GeoJSON do C#: ${err.message}`);
            }
          }
        } catch {
          // Ignore non-JSON messages or unrelated events?
          // console.error('Error parsing WebView message in useFileProcessing:', error);
        }
      }
    };

    if (window.chrome && window.chrome.webview) {
      window.chrome.webview.addEventListener('message', handleWebViewMessage);
    }
    return () => {
      if (window.chrome && window.chrome.webview) {
        window.chrome.webview.removeEventListener('message', handleWebViewMessage);
      }
    };
  }, []);

  // ** Browser Drag & Drop **
  const handleGlobalDrop = useCallback((e) => {
    e.preventDefault();
    setIsDraggingFile(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setPreviewGeoJson(null);

      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const content = event.target.result;
          const parsed = JSON.parse(content);
          if (parsed && parsed.type && (parsed.features || parsed.geometry)) {
            setPreviewGeoJson(parsed);
          } else {
            showError('Arquivo inválido. Use um GeoJSON válido.');
          }
        } catch (error) {
          showError(`Erro ao ler arquivo: ${error.message}`);
        }
      };
      reader.readAsText(file);
    }
  }, []);

  const handleDragOver = (e) => {
    e.preventDefault();
    if (e.dataTransfer.types.includes('Files')) setIsDraggingFile(true);
  };

  const handleDragLeave = () => setIsDraggingFile(false);

  // ** Import Action **
  const handleImportGeoJson = useCallback(() => {
    if (!previewGeoJson) return;

    if (window.chrome && window.chrome.webview) {
      window.chrome.webview.postMessage({
        action: 'IMPORT_GEOJSON',
        data: JSON.stringify(previewGeoJson),
      });
      setPreviewGeoJson(null); // Clear after import
    } else {
      showError('Importação disponível apenas dentro do AutoCAD.');
    }
  }, [previewGeoJson]);

  const clearPreview = () => setPreviewGeoJson(null);

  return {
    isDraggingFile,
    previewGeoJson,
    toastMessage,
    clearToast,
    handleGlobalDrop,
    handleDragOver,
    handleDragLeave,
    handleImportGeoJson,
    clearPreview,
    setPreviewGeoJson, // Exposed for manual drawing additions
  };
}
