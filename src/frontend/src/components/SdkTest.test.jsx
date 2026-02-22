/**
 * src/components/SdkTest.test.jsx
 *
 * Testes para o componente SdkTest.
 * Cobre:
 *  - Resultado bem-sucedido: componente retorna null (status OK)
 *  - Falha de checkHealth: exibe erro com detalhes (linhas 15-17)
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { SdkTest } from './SdkTest';

// Usa o mock global de SdkService definido em setupTests.js
// O mock expõe SdkService.checkHealth como vi.fn()
import { SdkService } from '../services/SdkService';

describe('SdkTest', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('não renderiza nada quando checkHealth é bem-sucedido (status OK)', async () => {
    // Mock padrão retorna { status: 'healthy' }
    SdkService.checkHealth.mockResolvedValueOnce({ status: 'healthy' });

    const { container } = render(<SdkTest />);

    // Aguarda o useEffect completar
    await waitFor(() => {
      // Componente retorna null quando status === 'OK' — nenhum elemento visível
      expect(container.firstChild).toBeNull();
    });
  });

  it('exibe mensagem de erro quando checkHealth falha (linhas 15-17)', async () => {
    const testError = new Error('Conexão recusada');
    SdkService.checkHealth.mockRejectedValueOnce(testError);

    render(<SdkTest />);

    // Aguarda o estado de erro ser definido
    await waitFor(() => {
      expect(screen.getByText(/SDK Health:/i)).toBeInTheDocument();
    });

    // Status deve ser ERROR (linha 15) — verifica através do strong
    await waitFor(() => {
      expect(screen.getByText(/SDK Health:/)).toBeInTheDocument();
    });
    // Detalhes do erro devem ser exibidos (linha 16)
    expect(screen.getByText(/Conexão recusada/)).toBeInTheDocument();
  });
});
