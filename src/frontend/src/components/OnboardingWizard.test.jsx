import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import OnboardingWizard, {
  _parseCoordsInput,
  isOnboardingDone,
  resetOnboarding,
} from './OnboardingWizard';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const noop = () => {};

function renderWizard(props = {}) {
  return render(
    <OnboardingWizard
      onComplete={props.onComplete ?? noop}
      onClose={props.onClose ?? noop}
    />
  );
}

// Navigate to step N (0-indexed) with valid coords
async function navigateTo(step) {
  renderWizard();
  if (step >= 1) {
    fireEvent.click(screen.getByText('Próximo')); // welcome → coords
  }
  if (step >= 2) {
    fireEvent.change(screen.getByLabelText('Coordenadas de referência'), {
      target: { value: '-22.15018, -42.92185' },
    });
    fireEvent.click(screen.getByText('Próximo')); // coords → modo
  }
  if (step >= 3) {
    fireEvent.click(screen.getByText('Próximo')); // modo → pronto
  }
}

// ---------------------------------------------------------------------------
// _parseCoordsInput — utilitário de parse de coordenadas
// ---------------------------------------------------------------------------
describe('_parseCoordsInput', () => {
  it('parseia coordenadas válidas com vírgula', () => {
    expect(_parseCoordsInput('-22.15018, -42.92185')).toEqual({ lat: -22.15018, lon: -42.92185 });
  });

  it('parseia coordenadas com espaço como separador', () => {
    expect(_parseCoordsInput('-22.15018 -42.92185')).toEqual({ lat: -22.15018, lon: -42.92185 });
  });

  it('parseia coordenadas com ponto-e-vírgula', () => {
    expect(_parseCoordsInput('-22.15018;-42.92185')).toEqual({ lat: -22.15018, lon: -42.92185 });
  });

  it('retorna null para string vazia', () => {
    expect(_parseCoordsInput('')).toBeNull();
  });

  it('retorna null para null', () => {
    expect(_parseCoordsInput(null)).toBeNull();
  });

  it('retorna null para texto sem dois valores', () => {
    expect(_parseCoordsInput('-22.15018')).toBeNull();
  });

  it('retorna null para valores não numéricos', () => {
    expect(_parseCoordsInput('abc, def')).toBeNull();
  });

  it('retorna null para latitude fora do intervalo', () => {
    expect(_parseCoordsInput('91.0, -42.0')).toBeNull();
  });

  it('retorna null para longitude fora do intervalo', () => {
    expect(_parseCoordsInput('-22.0, 181.0')).toBeNull();
  });

  it('parseia coordenadas de campo REF_2', () => {
    const result = _parseCoordsInput('-22.15018, -42.92185');
    expect(result).not.toBeNull();
    expect(result.lat).toBeCloseTo(-22.15018);
    expect(result.lon).toBeCloseTo(-42.92185);
  });
});

// ---------------------------------------------------------------------------
// localStorage helpers
// ---------------------------------------------------------------------------
describe('isOnboardingDone / resetOnboarding', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('retorna false quando wizard não foi concluído', () => {
    expect(isOnboardingDone()).toBe(false);
  });

  it('retorna true após salvar flag no localStorage', () => {
    localStorage.setItem('sisrua_onboarding_done', '1');
    expect(isOnboardingDone()).toBe(true);
  });

  it('resetOnboarding remove a flag', () => {
    localStorage.setItem('sisrua_onboarding_done', '1');
    resetOnboarding();
    expect(isOnboardingDone()).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Renderização e navegação
// ---------------------------------------------------------------------------
describe('OnboardingWizard — renderização e navegação', () => {
  beforeEach(() => localStorage.clear());

  it('renderiza etapa 1 (Boas-vindas) ao abrir', () => {
    renderWizard();
    expect(screen.getByText('Bem-vindo ao sisRUA')).toBeInTheDocument();
    expect(screen.getByText(/Motor GIS de Design Urbano/)).toBeInTheDocument();
  });

  it('exibe botão "Próximo" na etapa 1', () => {
    renderWizard();
    expect(screen.getByText('Próximo')).toBeInTheDocument();
  });

  it('não exibe "Voltar" na primeira etapa', () => {
    renderWizard();
    expect(screen.queryByText('Voltar')).not.toBeInTheDocument();
  });

  it('avança para etapa 2 ao clicar em Próximo', () => {
    renderWizard();
    fireEvent.click(screen.getByText('Próximo'));
    expect(screen.getByText('Coordenadas de Referência')).toBeInTheDocument();
  });

  it('exibe "Voltar" a partir da etapa 2', () => {
    renderWizard();
    fireEvent.click(screen.getByText('Próximo'));
    expect(screen.getByText('Voltar')).toBeInTheDocument();
  });

  it('volta para etapa anterior ao clicar em Voltar', () => {
    renderWizard();
    fireEvent.click(screen.getByText('Próximo'));
    fireEvent.click(screen.getByText('Voltar'));
    expect(screen.getByText('Bem-vindo ao sisRUA')).toBeInTheDocument();
  });

  it('exibe erro de validação ao tentar avançar sem coordenadas', () => {
    renderWizard();
    fireEvent.click(screen.getByText('Próximo')); // vai para step 2
    fireEvent.click(screen.getByText('Próximo')); // tenta avançar sem coords
    expect(screen.getByRole('alert')).toHaveTextContent('Formato inválido');
  });

  it('avança após inserir coordenadas válidas', () => {
    renderWizard();
    fireEvent.click(screen.getByText('Próximo'));
    const input = screen.getByLabelText('Coordenadas de referência');
    fireEvent.change(input, { target: { value: '-22.15018, -42.92185' } });
    fireEvent.click(screen.getByText('Próximo'));
    expect(screen.getByText('Modo de Operação')).toBeInTheDocument();
  });

  it('botão "Usar coordenadas de teste" preenche o input', () => {
    renderWizard();
    fireEvent.click(screen.getByText('Próximo'));
    fireEvent.click(screen.getByText('Usar coordenadas de teste →'));
    const input = screen.getByLabelText('Coordenadas de referência');
    expect(input.value).toBe('-22.15018, -42.92185');
  });

  it('exibe opções Cloud e Local na etapa 3 (Modo)', async () => {
    await navigateTo(2);
    expect(screen.getByText(/sisRUA LT/)).toBeInTheDocument();
    expect(screen.getByText(/sisRUA Full/)).toBeInTheDocument();
  });

  it('avança para etapa 4 (Tudo Pronto)', async () => {
    await navigateTo(3);
    expect(screen.getByText('Tudo Pronto!')).toBeInTheDocument();
  });

  it('exibe resumo CRS na etapa final', async () => {
    await navigateTo(3);
    expect(screen.getByText('SIRGAS 2000 UTM (auto-detect)')).toBeInTheDocument();
  });

  it('exibe coordenadas de referência no resumo final', async () => {
    await navigateTo(3);
    expect(screen.getByText(/-22\.15/)).toBeInTheDocument();
  });

  it('exibe botão "Começar" na etapa final', async () => {
    await navigateTo(3);
    expect(screen.getByText('Começar')).toBeInTheDocument();
  });

  it('chama onComplete ao clicar em Começar', async () => {
    const onComplete = vi.fn();
    render(<OnboardingWizard onComplete={onComplete} onClose={noop} />);
    fireEvent.click(screen.getByText('Próximo'));
    fireEvent.change(screen.getByLabelText('Coordenadas de referência'), {
      target: { value: '-22.15018, -42.92185' },
    });
    fireEvent.click(screen.getByText('Próximo'));
    fireEvent.click(screen.getByText('Próximo'));
    await waitFor(() => expect(screen.getByText('Começar')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Começar'));
    expect(onComplete).toHaveBeenCalledOnce();
    const config = onComplete.mock.calls[0][0];
    expect(config.coords).not.toBeNull();
    expect(config.coords.lat).toBeCloseTo(-22.15018);
    expect(config.modo).toBe('cloud');
    expect(config.timestamp).toBeTruthy();
  });

  it('chama onComplete e salva flag no localStorage', async () => {
    const onComplete = vi.fn();
    render(<OnboardingWizard onComplete={onComplete} onClose={noop} />);
    fireEvent.click(screen.getByText('Próximo'));
    fireEvent.change(screen.getByLabelText('Coordenadas de referência'), {
      target: { value: '-22.15018, -42.92185' },
    });
    fireEvent.click(screen.getByText('Próximo'));
    fireEvent.click(screen.getByText('Próximo'));
    await waitFor(() => expect(screen.getByText('Começar')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Começar'));
    expect(localStorage.getItem('sisrua_onboarding_done')).toBe('1');
  });

  it('chama onClose ao clicar no botão fechar (X)', () => {
    const onClose = vi.fn();
    render(<OnboardingWizard onComplete={noop} onClose={onClose} />);
    fireEvent.click(screen.getByLabelText('Fechar assistente'));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('renderiza com role="dialog" e aria-modal=true', () => {
    renderWizard();
    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
  });

  it('indicador de progresso tem 4 segmentos', () => {
    renderWizard();
    // Barras de progresso são divs com h-1, deveriam ser 4
    const dialog = screen.getByRole('dialog');
    // O wizard tem 4 STEPS — o título "Etapa 1 de 4" deve estar visível
    expect(dialog.textContent).toMatch(/Etapa 1 de 4/);
  });

  it('onComplete funciona sem coordenadas (modo apenas)', async () => {
    const onComplete = vi.fn();
    render(<OnboardingWizard onComplete={onComplete} onClose={noop} />);
    // Avança sem inserir coords (usa botão "Usar coords de teste")
    fireEvent.click(screen.getByText('Próximo'));
    fireEvent.click(screen.getByText('Usar coordenadas de teste →'));
    fireEvent.click(screen.getByText('Próximo'));
    fireEvent.click(screen.getByText('Próximo'));
    await waitFor(() => expect(screen.getByText('Começar')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Começar'));
    expect(onComplete).toHaveBeenCalledOnce();
  });
});
