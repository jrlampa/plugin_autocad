import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { initSentry } from './utils/dynamicSentry';
import ErrorBoundary from './components/ErrorBoundary';
import './index.css'; // <--- ESSA LINHA É OBRIGATÓRIA

// Initialize Sentry dynamically
initSentry();

// Fase 4: Registro do Service Worker para suporte offline (App Campo)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // Service worker pode não estar disponível em ambientes WebView2/AutoCAD
    });
  });
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
