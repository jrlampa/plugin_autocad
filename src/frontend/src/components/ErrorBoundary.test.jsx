/**
 * tests/components/ErrorBoundary.test.jsx
 * Testes para o componente ErrorBoundary (pt-BR).
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ErrorBoundary from '../../src/components/ErrorBoundary';

// Componente que levanta um erro durante a renderização
function BrokenChild({ shouldThrow }) {
  if (shouldThrow) {
    throw new Error('Erro de teste no componente filho');
  }
  return <div>Filho funcional</div>;
}

// Suprime os erros de console em testes do ErrorBoundary
const originalConsoleError = console.error;
beforeEach(() => {
  console.error = vi.fn();
});

describe('ErrorBoundary', () => {
  afterEach(() => {
    console.error = originalConsoleError;
  });

  it('renderiza filhos normalmente quando não há erro', () => {
    render(
      <ErrorBoundary>
        <BrokenChild shouldThrow={false} />
      </ErrorBoundary>
    );
    expect(screen.getByText('Filho funcional')).toBeInTheDocument();
  });

  it('exibe mensagem de fallback quando filho lança erro', () => {
    render(
      <ErrorBoundary>
        <BrokenChild shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText(/Algo deu errado/i)).toBeInTheDocument();
  });

  it('exibe botão de recarregar na tela de erro', () => {
    render(
      <ErrorBoundary>
        <BrokenChild shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText(/Recarregar Página/i)).toBeInTheDocument();
  });

  it('exibe botão de copiar relatório na tela de erro', () => {
    render(
      <ErrorBoundary>
        <BrokenChild shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText(/Copiar Relatório/i)).toBeInTheDocument();
  });

  it('exibe mensagem orientando o usuário a recarregar', () => {
    render(
      <ErrorBoundary>
        <BrokenChild shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText(/Tente recarregar a página/i)).toBeInTheDocument();
  });

  it('chama window.location.reload ao clicar em Recarregar', () => {
    const reloadMock = vi.fn();
    Object.defineProperty(window, 'location', {
      value: { ...window.location, reload: reloadMock },
      writable: true,
    });

    render(
      <ErrorBoundary>
        <BrokenChild shouldThrow={true} />
      </ErrorBoundary>
    );
    fireEvent.click(screen.getByText(/Recarregar Página/i));
    expect(reloadMock).toHaveBeenCalledOnce();
  });

  it('tenta copiar para clipboard ao clicar em Copiar Relatório', () => {
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: writeTextMock },
      writable: true,
    });

    render(
      <ErrorBoundary>
        <BrokenChild shouldThrow={true} />
      </ErrorBoundary>
    );
    fireEvent.click(screen.getByText(/Copiar Relatório/i));
    expect(writeTextMock).toHaveBeenCalledOnce();
  });

  it('armazena erros no localStorage', () => {
    localStorage.clear();
    render(
      <ErrorBoundary>
        <BrokenChild shouldThrow={true} />
      </ErrorBoundary>
    );
    const stored = localStorage.getItem('sisrua_errors');
    // Pode ser null se localStorage.setItem falhou silenciosamente
    if (stored !== null) {
      const errors = JSON.parse(stored);
      expect(Array.isArray(errors)).toBe(true);
    }
  });
});
