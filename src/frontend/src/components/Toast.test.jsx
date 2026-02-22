/**
 * tests/components/Toast.test.jsx
 * Testes para o componente Toast (pt-BR).
 */
import React from 'react';
import { render, screen, act, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import Toast from '../../src/components/Toast';

describe('Toast', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renderiza a mensagem passada', () => {
    render(<Toast message="Teste de mensagem" onClose={() => {}} />);
    expect(screen.getByText('Teste de mensagem')).toBeInTheDocument();
  });

  it('exibe ícone e estilo correto para type=error', () => {
    const { container } = render(<Toast message="Erro!" type="error" onClose={() => {}} />);
    const div = container.querySelector('.bg-red-100');
    expect(div).toBeInTheDocument();
  });

  it('exibe estilo correto para type=success', () => {
    const { container } = render(<Toast message="Sucesso!" type="success" onClose={() => {}} />);
    expect(container.querySelector('.bg-emerald-100')).toBeInTheDocument();
  });

  it('exibe estilo correto para type=warning', () => {
    const { container } = render(<Toast message="Aviso!" type="warning" onClose={() => {}} />);
    expect(container.querySelector('.bg-amber-100')).toBeInTheDocument();
  });

  it('exibe estilo correto para type=info (padrão)', () => {
    const { container } = render(<Toast message="Info!" onClose={() => {}} />);
    expect(container.querySelector('.bg-blue-100')).toBeInTheDocument();
  });

  it('chama onClose após a duração padrão (5000ms)', () => {
    const onClose = vi.fn();
    render(<Toast message="Fechar auto" onClose={onClose} duration={5000} />);
    expect(onClose).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('chama onClose após duração personalizada', () => {
    const onClose = vi.fn();
    render(<Toast message="Fechar rápido" onClose={onClose} duration={1000} />);
    act(() => {
      vi.advanceTimersByTime(999);
    });
    expect(onClose).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('não inicia timer quando duration é 0', () => {
    const onClose = vi.fn();
    render(<Toast message="Sem timer" onClose={onClose} duration={0} />);
    act(() => {
      vi.advanceTimersByTime(99999);
    });
    expect(onClose).not.toHaveBeenCalled();
  });

  it('chama onClose ao clicar no botão fechar', () => {
    const onClose = vi.fn();
    render(<Toast message="Clique fechar" onClose={onClose} />);
    const btn = screen.getByRole('button');
    fireEvent.click(btn);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('usa type=info como fallback para tipo desconhecido', () => {
    const { container } = render(
      <Toast message="Tipo desconhecido" type="desconhecido" onClose={() => {}} />
    );
    // tipo desconhecido → usa fallback info
    expect(container.querySelector('.bg-blue-100')).toBeInTheDocument();
  });
});
