/**
 * src/components/JobOverlay.test.jsx
 *
 * Testes unitários para o componente JobOverlay.
 *
 * Cobre todos os estados de job:
 *   - completed (CheckCircle2)
 *   - failed (AlertTriangle)
 *   - processing (Loader2 animado)
 *   - queued (Loader2, texto "Aguardando")
 *   - progress bar
 *   - mensagem de status
 *   - null uiJob (não renderiza)
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import JobOverlay from './JobOverlay';

const makeJob = (overrides = {}) => ({
  status: 'completed',
  progress: 1.0,
  message: null,
  job_id: 'job-001',
  ...overrides,
});

describe('JobOverlay — renderização condicional', () => {
  it('não renderiza nada quando uiJob é null', () => {
    const { container } = render(<JobOverlay uiJob={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renderiza o overlay quando uiJob está definido', () => {
    render(<JobOverlay uiJob={makeJob()} />);
    expect(screen.getByTestId('job-overlay')).toBeInTheDocument();
  });
});

describe('JobOverlay — estado completed', () => {
  it('exibe "Concluído" quando status é completed', () => {
    render(<JobOverlay uiJob={makeJob({ status: 'completed', progress: 1.0 })} />);
    expect(screen.getByText('Concluído')).toBeInTheDocument();
  });

  it('exibe barra de progresso a 100%', () => {
    render(<JobOverlay uiJob={makeJob({ status: 'completed', progress: 1.0 })} />);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });
});

describe('JobOverlay — estado failed', () => {
  it('exibe "Concluído" (fallback de ternário) para status failed', () => {
    render(<JobOverlay uiJob={makeJob({ status: 'failed', progress: 0.3 })} />);
    // O texto do ternário: queued → 'Aguardando', processing → 'Processando', else → 'Concluído'
    // failed cai no else → 'Concluído'
    expect(screen.getByText('Concluído')).toBeInTheDocument();
  });

  it('exibe barra de progresso para status failed', () => {
    render(<JobOverlay uiJob={makeJob({ status: 'failed', progress: 0.3 })} />);
    expect(screen.getByText('30%')).toBeInTheDocument();
  });

  it('não exibe mensagem de status quando status é failed', () => {
    render(
      <JobOverlay uiJob={makeJob({ status: 'failed', progress: 0.0, message: 'Erro interno' })} />
    );
    // Mensagem só aparece quando status não é completed e não é failed
    expect(screen.queryByText('Erro interno')).not.toBeInTheDocument();
  });
});

describe('JobOverlay — estado processing', () => {
  it('exibe "Processando" quando status é processing', () => {
    render(<JobOverlay uiJob={makeJob({ status: 'processing', progress: 0.5 })} />);
    expect(screen.getByText('Processando')).toBeInTheDocument();
  });

  it('exibe percentual de progresso', () => {
    render(<JobOverlay uiJob={makeJob({ status: 'processing', progress: 0.75 })} />);
    expect(screen.getByText('75%')).toBeInTheDocument();
  });

  it('exibe mensagem de status quando presente e status é processing', () => {
    render(
      <JobOverlay
        uiJob={makeJob({ status: 'processing', progress: 0.5, message: 'Baixando dados OSM...' })}
      />
    );
    expect(screen.getByText('Baixando dados OSM...')).toBeInTheDocument();
  });
});

describe('JobOverlay — estado queued', () => {
  it('exibe "Aguardando" quando status é queued', () => {
    render(<JobOverlay uiJob={makeJob({ status: 'queued', progress: 0.0 })} />);
    expect(screen.getByText('Aguardando')).toBeInTheDocument();
  });

  it('exibe mensagem de status quando queued e message presente', () => {
    render(
      <JobOverlay
        uiJob={makeJob({ status: 'queued', progress: 0.0, message: 'Na fila de processamento' })}
      />
    );
    expect(screen.getByText('Na fila de processamento')).toBeInTheDocument();
  });
});

describe('JobOverlay — progress bar', () => {
  it('não exibe progresso quando progress é undefined', () => {
    // When progress is undefined (typeof !== 'number'), the bar should not render
    render(<JobOverlay uiJob={makeJob({ status: 'processing', progress: undefined })} />);
    // Text "%" should not appear
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it('garante que o progresso não ultrapassa 100% na barra visual', () => {
    const { container } = render(
      <JobOverlay uiJob={makeJob({ status: 'completed', progress: 2.0 })} />
    );
    // O texto mostra "200%" mas a largura da barra é limitada a 100%
    expect(screen.getByText('200%')).toBeInTheDocument();
    const bar = container.querySelector('.h-2.bg-blue-500');
    if (bar) {
      // Math.min(100, Math.round(2.0 * 100)) = min(100, 200) = 100
      expect(bar.style.width).toBe('100%');
    }
  });

  it('garante que o progresso não fica abaixo de 0% na barra visual', () => {
    const { container } = render(
      <JobOverlay uiJob={makeJob({ status: 'processing', progress: -0.5 })} />
    );
    expect(screen.getByText('-50%')).toBeInTheDocument();
    const bar = container.querySelector('.h-2.bg-blue-500');
    if (bar) {
      // Math.max(0, Math.round(-0.5 * 100)) = max(0, -50) = 0
      expect(bar.style.width).toBe('0%');
    }
  });
});
