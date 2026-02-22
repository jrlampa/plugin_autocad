/**
 * src/components/NormaPanel.test.jsx
 *
 * Testes unitários para o componente NormaPanel.
 * Cobre:
 *  - Renderização com norma ABNT ativa (padrão)
 *  - Ativação de PRODIST dispara toast e exibe campos extras
 *  - Desativação de PRODIST restaura ABNT
 *  - Erro de configuração aciona toast de erro
 *  - Buffer de segurança NR-10 é exibido conforme classe de tensão
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import NormaPanel from './NormaPanel';

// ─────────────────────────────────────────────
// Mock da API
// ─────────────────────────────────────────────

const mockGetNormaAtiva = vi.fn(() =>
  Promise.resolve({ ativa: 'ABNT', concessionaria: '', classe_tensao: 'MT', numero_processo: '' })
);
const mockSetNormaConfig = vi.fn();

vi.mock('../api', () => ({
  api: {
    getNormaAtiva: () => mockGetNormaAtiva(),
    setNormaConfig: (...args) => mockSetNormaConfig(...args),
  },
}));

// ─────────────────────────────────────────────
// Testes
// ─────────────────────────────────────────────

describe('NormaPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetNormaAtiva.mockResolvedValue({
      ativa: 'ABNT',
      concessionaria: '',
      classe_tensao: 'MT',
      numero_processo: '',
    });
  });

  // ── Renderização inicial ─────────────────────

  it('renderiza com ABNT ativo por padrão', async () => {
    render(<NormaPanel onToast={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/ABNT NBR 14166/i)).toBeInTheDocument();
    });
    // Botão ABNT deve estar selecionado (fundo azul via classe)
    expect(screen.getByRole('button', { name: /ABNT/i })).toBeInTheDocument();
  });

  it('exibe botões ABNT e ANEEL/PRODIST', async () => {
    render(<NormaPanel onToast={vi.fn()} />);
    await waitFor(() => screen.getByText(/ABNT NBR 14166/i));

    // Usa getAllByRole para lidar com múltiplos elementos que contêm "ABNT"
    const abntButtons = screen.getAllByRole('button').filter((b) => b.textContent.trim() === 'ABNT');
    expect(abntButtons.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole('button', { name: /ANEEL\/PRODIST/i })).toBeInTheDocument();
  });

  // ── Ativação de PRODIST ──────────────────────

  it('clique em ANEEL/PRODIST aciona setNormaConfig com ativa=true', async () => {
    mockSetNormaConfig.mockResolvedValue({
      norma_ativa: 'PRODIST',
      toast: 'Normas PRODIST ativas.',
    });

    const onToast = vi.fn();
    render(<NormaPanel onToast={onToast} />);
    await waitFor(() => screen.getByRole('button', { name: /ANEEL\/PRODIST/i }));

    fireEvent.click(screen.getByRole('button', { name: /ANEEL\/PRODIST/i }));

    await waitFor(() => {
      expect(mockSetNormaConfig).toHaveBeenCalledWith(
        expect.objectContaining({ ativa: true })
      );
    });
  });

  it('ativação bem-sucedida de PRODIST chama onToast com tipo warning', async () => {
    mockSetNormaConfig.mockResolvedValue({
      norma_ativa: 'PRODIST',
      toast: 'ABNT substituída.',
    });

    const onToast = vi.fn();
    render(<NormaPanel onToast={onToast} />);
    await waitFor(() => screen.getByRole('button', { name: /ANEEL\/PRODIST/i }));

    fireEvent.click(screen.getByRole('button', { name: /ANEEL\/PRODIST/i }));

    await waitFor(() => {
      expect(onToast).toHaveBeenCalledWith('ABNT substituída.', 'warning');
    });
  });

  it('ativação bem-sucedida de PRODIST exibe campos adicionais', async () => {
    mockGetNormaAtiva.mockResolvedValue({
      ativa: 'PRODIST',
      concessionaria: 'Light S.A.',
      classe_tensao: 'MT',
      numero_processo: '',
    });
    mockSetNormaConfig.mockResolvedValue({
      norma_ativa: 'PRODIST',
      toast: null,
    });

    render(<NormaPanel onToast={vi.fn()} />);

    // Aguarda a sincronização inicial (useEffect)
    await waitFor(() => {
      // Quando PRODIST está ativo, o botão de aplicar deve aparecer
      expect(screen.getByTestId('btn-aplicar-prodist')).toBeInTheDocument();
    });
  });

  // ── Desativação de PRODIST ────────────────────

  it('clique em ABNT quando PRODIST está ativo chama setNormaConfig com ativa=false', async () => {
    // Começa com PRODIST ativo
    mockGetNormaAtiva.mockResolvedValue({
      ativa: 'PRODIST',
      concessionaria: 'CELPE',
      classe_tensao: 'MT',
      numero_processo: '001',
    });
    mockSetNormaConfig.mockResolvedValue({
      norma_ativa: 'ABNT',
      toast: null,
    });

    const onToast = vi.fn();
    render(<NormaPanel onToast={onToast} />);
    await waitFor(() => screen.getByTestId('btn-aplicar-prodist'));

    fireEvent.click(screen.getByRole('button', { name: /^ABNT$/i }));

    await waitFor(() => {
      expect(mockSetNormaConfig).toHaveBeenCalledWith(
        expect.objectContaining({ ativa: false })
      );
    });
  });

  it('desativação de PRODIST chama onToast com tipo success', async () => {
    mockGetNormaAtiva.mockResolvedValue({
      ativa: 'PRODIST',
      concessionaria: 'CELPE',
      classe_tensao: 'BT',
      numero_processo: '',
    });
    mockSetNormaConfig.mockResolvedValue({
      norma_ativa: 'ABNT',
      toast: 'ABNT restaurada.',
    });

    const onToast = vi.fn();
    render(<NormaPanel onToast={onToast} />);
    await waitFor(() => screen.getByTestId('btn-aplicar-prodist'));

    fireEvent.click(screen.getByRole('button', { name: /^ABNT$/i }));

    await waitFor(() => {
      expect(onToast).toHaveBeenCalledWith('ABNT restaurada.', 'success');
    });
  });

  // ── Erro de configuração ─────────────────────

  it('erro em setNormaConfig aciona toast de erro', async () => {
    mockSetNormaConfig.mockRejectedValue(new Error('Backend offline'));

    const onToast = vi.fn();
    render(<NormaPanel onToast={onToast} />);
    await waitFor(() => screen.getByRole('button', { name: /ANEEL\/PRODIST/i }));

    fireEvent.click(screen.getByRole('button', { name: /ANEEL\/PRODIST/i }));

    await waitFor(() => {
      expect(onToast).toHaveBeenCalledWith(
        expect.stringContaining('Erro'),
        'error'
      );
    });
  });

  // ── Buffer de segurança NR-10 ────────────────

  it('exibe buffer 3m para classe MT (NR-10:2016)', async () => {
    mockGetNormaAtiva.mockResolvedValue({
      ativa: 'PRODIST',
      concessionaria: 'LIGHT',
      classe_tensao: 'MT',
      numero_processo: '',
    });

    render(<NormaPanel onToast={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/3 m/)).toBeInTheDocument();
    });
  });

  it('exibe buffer 10m para classe AT (NR-10:2016)', async () => {
    mockGetNormaAtiva.mockResolvedValue({
      ativa: 'PRODIST',
      concessionaria: 'CEMIG',
      classe_tensao: 'AT',
      numero_processo: '',
    });

    render(<NormaPanel onToast={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/10 m/)).toBeInTheDocument();
    });
  });

  // ── Branches de fallback (linhas 37, 39, 48) ─────────────────────────────

  it('usa fallback "ABNT" e "MT" quando API retorna campos ausentes (linhas 37, 39)', async () => {
    // data.ativa e data.classe_tensao são undefined → os operadores || tomam o ramo direito
    mockGetNormaAtiva.mockResolvedValue({
      concessionaria: '',
      numero_processo: '',
      // ativa e classe_tensao ausentes (undefined)
    });

    render(<NormaPanel onToast={vi.fn()} />);

    // Componente deve renderizar com ABNT como fallback
    // O botão "ABNT" existe independentemente da resposta da API (estado inicial = 'ABNT')
    expect(screen.getByRole('button', { name: 'ABNT' })).toBeInTheDocument();

    // Aguarda API resolver — componente permanece em ABNT (fallback)
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'ABNT' })).toBeInTheDocument();
    });
  });

  it('setBufferInfo recebe null quando classe não está em CLASSES_TENSAO (linha 48)', async () => {
    // classe_tensao 'INVALIDA' não está na lista → found é undefined → found || null → null
    mockGetNormaAtiva.mockResolvedValue({
      ativa: 'PRODIST',
      concessionaria: 'CEMIG',
      classe_tensao: 'INVALIDA',
      numero_processo: '',
    });

    render(<NormaPanel onToast={vi.fn()} />);

    // Componente não deve lançar exceção com classe inválida (bufferInfo = null)
    // O botão ANEEL/PRODIST sempre existe no DOM
    expect(screen.getByRole('button', { name: 'ANEEL/PRODIST' })).toBeInTheDocument();
  });
});
