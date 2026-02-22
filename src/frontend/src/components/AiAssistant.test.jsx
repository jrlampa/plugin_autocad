/**
 * src/components/AiAssistant.test.jsx
 *
 * Testes unitários para o componente AiAssistant.
 *
 * Cobre:
 *   - Renderização inicial (botão 🤖 visível, janela fechada)
 *   - Abrir e fechar o painel de chat
 *   - Envio de mensagem via botão "Env"
 *   - Envio de mensagem via tecla Enter
 *   - Não envia quando input está vazio
 *   - Não envia quando isLoading=true
 *   - Exibe "Digitando..." durante carregamento
 *   - Exibe resposta da IA após envio
 *   - Mensagem inicial de boas-vindas
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { AiAssistant } from './AiAssistant';

// Usa o mock global de aiService (setupTests.js mocka todo o módulo api)
// Mas aiService não está no setupTests.js — precisamos mockar manualmente.
vi.mock('../services/aiService', () => ({
  aiService: {
    sendMessage: vi.fn().mockResolvedValue('Resposta da IA: projeto carregado com sucesso.'),
  },
}));

import { aiService } from '../services/aiService';

describe('AiAssistant — estado inicial', () => {
  it('renderiza o botão 🤖 inicialmente', () => {
    render(<AiAssistant />);
    expect(screen.getByText('🤖')).toBeInTheDocument();
  });

  it('não exibe a janela de chat inicialmente', () => {
    render(<AiAssistant />);
    expect(screen.queryByText('sisRUA AI (Beta)')).not.toBeInTheDocument();
  });
});

describe('AiAssistant — abrir e fechar', () => {
  it('abre o painel ao clicar no botão 🤖', () => {
    render(<AiAssistant />);
    fireEvent.click(screen.getByText('🤖'));
    expect(screen.getByText('sisRUA AI (Beta)')).toBeInTheDocument();
  });

  it('exibe mensagem inicial de boas-vindas após abrir', () => {
    render(<AiAssistant />);
    fireEvent.click(screen.getByText('🤖'));
    expect(
      screen.getByText('Olá! Sou o assistente sisRUA. Como posso ajudar com seu projeto hoje?')
    ).toBeInTheDocument();
  });

  it('fecha o painel ao clicar no botão ×', () => {
    render(<AiAssistant />);
    fireEvent.click(screen.getByText('🤖'));
    expect(screen.getByText('sisRUA AI (Beta)')).toBeInTheDocument();

    fireEvent.click(screen.getByText('×'));
    expect(screen.queryByText('sisRUA AI (Beta)')).not.toBeInTheDocument();
    // Botão 🤖 reaparece
    expect(screen.getByText('🤖')).toBeInTheDocument();
  });
});

describe('AiAssistant — envio de mensagem', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    aiService.sendMessage.mockResolvedValue('Resposta da IA para o projeto.');
  });

  it('envia mensagem ao clicar no botão Env', async () => {
    render(<AiAssistant />);
    fireEvent.click(screen.getByText('🤖'));

    const input = screen.getByPlaceholderText('Pergunte algo...');
    fireEvent.change(input, { target: { value: 'Quais ruas estão no projeto?' } });
    fireEvent.click(screen.getByText('Env'));

    // Mensagem do usuário aparece imediatamente
    await waitFor(() => {
      expect(screen.getByText('Quais ruas estão no projeto?')).toBeInTheDocument();
    });

    // aiService.sendMessage deve ser chamado
    expect(aiService.sendMessage).toHaveBeenCalledWith('Quais ruas estão no projeto?');
  });

  it('envia mensagem ao pressionar Enter no campo de texto', async () => {
    render(<AiAssistant />);
    fireEvent.click(screen.getByText('🤖'));

    const input = screen.getByPlaceholderText('Pergunte algo...');
    fireEvent.change(input, { target: { value: 'Que CRS está ativo?' } });
    fireEvent.keyPress(input, { key: 'Enter', code: 'Enter', charCode: 13 });

    await waitFor(() => {
      expect(aiService.sendMessage).toHaveBeenCalledWith('Que CRS está ativo?');
    });
  });

  it('exibe resposta da IA após envio', async () => {
    render(<AiAssistant />);
    fireEvent.click(screen.getByText('🤖'));

    const input = screen.getByPlaceholderText('Pergunte algo...');
    fireEvent.change(input, { target: { value: 'Olá IA' } });
    fireEvent.click(screen.getByText('Env'));

    await waitFor(() => {
      expect(screen.getByText('Resposta da IA para o projeto.')).toBeInTheDocument();
    });
  });

  it('limpa o campo de texto após envio', async () => {
    render(<AiAssistant />);
    fireEvent.click(screen.getByText('🤖'));

    const input = screen.getByPlaceholderText('Pergunte algo...');
    fireEvent.change(input, { target: { value: 'Mensagem de teste' } });
    fireEvent.click(screen.getByText('Env'));

    await waitFor(() => {
      expect(input.value).toBe('');
    });
  });
});

describe('AiAssistant — guards de envio', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('não envia quando o campo de texto está vazio', () => {
    render(<AiAssistant />);
    fireEvent.click(screen.getByText('🤖'));

    const input = screen.getByPlaceholderText('Pergunte algo...');
    expect(input.value).toBe('');
    fireEvent.click(screen.getByText('Env'));

    expect(aiService.sendMessage).not.toHaveBeenCalled();
  });

  it('não envia quando o campo contém apenas espaços', () => {
    render(<AiAssistant />);
    fireEvent.click(screen.getByText('🤖'));

    const input = screen.getByPlaceholderText('Pergunte algo...');
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.click(screen.getByText('Env'));

    expect(aiService.sendMessage).not.toHaveBeenCalled();
  });

  it('exibe "Digitando..." enquanto aguarda resposta da IA', async () => {
    // Promise que nunca resolve → mantém estado de loading
    aiService.sendMessage.mockReturnValue(new Promise(() => {}));

    render(<AiAssistant />);
    fireEvent.click(screen.getByText('🤖'));

    const input = screen.getByPlaceholderText('Pergunte algo...');
    fireEvent.change(input, { target: { value: 'Pergunta longa' } });
    fireEvent.click(screen.getByText('Env'));

    await waitFor(() => {
      expect(screen.getByText('Digitando...')).toBeInTheDocument();
    });
  });
});
