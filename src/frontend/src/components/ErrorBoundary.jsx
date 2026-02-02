import React, { Component } from 'react';
import PropTypes from 'prop-types';
import * as Sentry from '@sentry/react';

/**
 * Global Error Boundary for graceful degradation.
 * Catches JavaScript errors in child components and displays a fallback UI.
 *
 * Usage:
 *   <ErrorBoundary>
 *     <App />
 *   </ErrorBoundary>
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render shows the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to console (and external service if configured)
    this.setState({ errorInfo });

    // Centralized error logging
    this.logErrorToService(error, errorInfo);
  }

  logErrorToService(error, errorInfo) {
    const errorData = {
      message: error?.message || 'Unknown error',
      stack: error?.stack || '',
      componentStack: errorInfo?.componentStack || '',
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent,
    };

    // Log to console for development
    console.error('[ErrorBoundary] Caught error:', errorData);

    // Send to Sentry if initialized
    Sentry.captureException(error, {
      extra: {
        componentStack: errorInfo?.componentStack,
      },
    });

    // Store in localStorage for debugging
    try {
      const errors = JSON.parse(localStorage.getItem('sisrua_errors') || '[]');
      errors.push(errorData);
      // Keep only last 10 errors
      localStorage.setItem('sisrua_errors', JSON.stringify(errors.slice(-10)));
    } catch {
      // Ignore localStorage errors
    }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleReport = () => {
    const { error, errorInfo } = this.state;
    const errorText = `
Error: ${error?.message || 'Unknown'}
Stack: ${error?.stack || 'N/A'}
Component Stack: ${errorInfo?.componentStack || 'N/A'}
    `.trim();

    // Copy to clipboard
    navigator.clipboard
      .writeText(errorText)
      .then(() => {
        alert('Informações do erro copiadas para a área de transferência.');
      })
      .catch(() => {
        console.log(errorText);
        alert('Erro ao copiar. Verifique o console.');
      });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-boundary__content">
            <div className="error-boundary__icon">⚠️</div>
            <h1 className="error-boundary__title">Algo deu errado</h1>
            <p className="error-boundary__message">
              Ocorreu um erro inesperado. Tente recarregar a página.
            </p>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="error-boundary__details">
                <summary>Detalhes técnicos</summary>
                <pre>{this.state.error.message}</pre>
                <pre>{this.state.error.stack}</pre>
              </details>
            )}

            <div className="error-boundary__actions">
              <button
                onClick={this.handleReload}
                className="error-boundary__button error-boundary__button--primary"
              >
                Recarregar Página
              </button>
              <button
                onClick={this.handleReport}
                className="error-boundary__button error-boundary__button--secondary"
              >
                Copiar Relatório
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

ErrorBoundary.propTypes = {
  children: PropTypes.node.isRequired,
};

export default ErrorBoundary;
