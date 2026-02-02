import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { initSentry } from './utils/dynamicSentry';
import ErrorBoundary from './components/ErrorBoundary';
import './index.css'; // <--- ESSA LINHA É OBRIGATÓRIA

// Initialize Sentry dynamically
initSentry();

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
