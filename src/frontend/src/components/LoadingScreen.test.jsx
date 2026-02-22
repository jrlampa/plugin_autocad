/**
 * tests/components/LoadingScreen.test.jsx
 * Testes para o componente LoadingScreen (pt-BR).
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import LoadingScreen from '../../src/components/LoadingScreen';

describe('LoadingScreen', () => {
  it('renderiza sem erros', () => {
    const { container } = render(<LoadingScreen />);
    expect(container.firstChild).toBeTruthy();
  });

  it('exibe o texto "sisRUA"', () => {
    render(<LoadingScreen />);
    expect(screen.getByText('sisRUA')).toBeInTheDocument();
  });

  it('exibe mensagem de inicialização em pt-BR', () => {
    render(<LoadingScreen />);
    expect(
      screen.getByText(/Inicializando motor de renderização/i)
    ).toBeInTheDocument();
  });

  it('exibe a versão do sistema', () => {
    render(<LoadingScreen />);
    expect(screen.getByText(/v0\.5\.0/i)).toBeInTheDocument();
  });

  it('exibe o indicador de carregamento animado (spinner)', () => {
    const { container } = render(<LoadingScreen />);
    // Loader2 from lucide-react renders as SVG
    const spinner = container.querySelector('svg');
    expect(spinner).toBeInTheDocument();
  });

  it('exibe o logo com a letra "R"', () => {
    render(<LoadingScreen />);
    expect(screen.getByText('R')).toBeInTheDocument();
  });
});
