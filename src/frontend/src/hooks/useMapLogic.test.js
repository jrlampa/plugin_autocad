import { renderHook, act } from '@testing-library/react';

import { useMapLogic } from './useMapLogic';

function makeDataTransfer() {
  const store = new Map();
  return {
    setData: (k, v) => store.set(k, v),
    getData: (k) => store.get(k),
    types: [],
    effectAllowed: '',
  };
}

describe('useMapLogic', () => {
  it('handleDragStart define o tipo no dataTransfer', () => {
    const { result } = renderHook(() => useMapLogic());
    const dt = makeDataTransfer();
    const e = { dataTransfer: dt };

    act(() => result.current.handleDragStart(e, 'POSTE'));
    expect(dt.getData('symbolType')).toBe('POSTE');
    expect(dt.effectAllowed).toBe('copy');
  });

  it('confirmMarker adiciona marcador com metadados', () => {
    const { result } = renderHook(() => useMapLogic());

    act(() => {
      result.current.handleSymbolDrop({ lat: 1.23, lng: 4.56 }, 'ARVORE');
      result.current.setMetaInput({ desc: 'Teste', altura: '12m' });
    });

    act(() => result.current.confirmMarker());

    expect(result.current.markers.length).toBe(1);
    expect(result.current.markers[0]).toEqual({
      lat: 1.23,
      lon: 4.56,
      tipo: 'ARVORE',
      meta: { desc: 'Teste', altura: '12m' },
    });
  });

  it('cancelMarker fecha o modal e limpa currentDrop (linhas 37-38)', () => {
    const { result } = renderHook(() => useMapLogic());

    // Abre o modal via drop de símbolo
    act(() => {
      result.current.handleSymbolDrop({ lat: -22.15018, lng: -42.92185 }, 'POSTE');
    });

    // Confirma que o modal está aberto e currentDrop foi definido
    expect(result.current.isModalOpen).toBe(true);
    expect(result.current.currentDrop).not.toBeNull();

    // Cancela o marcador (cobre linhas 37-38)
    act(() => result.current.cancelMarker());

    expect(result.current.isModalOpen).toBe(false);
    expect(result.current.currentDrop).toBeNull();
    // Não deve ter adicionado nenhum marcador
    expect(result.current.markers).toHaveLength(0);
  });

  it('confirmMarker retorna sem fazer nada quando currentDrop é null (linha 22)', () => {
    const { result } = renderHook(() => useMapLogic());

    // currentDrop é null no estado inicial — confirmMarker deve retornar no guard (linha 22)
    expect(result.current.currentDrop).toBeNull();
    expect(result.current.markers).toHaveLength(0);

    act(() => result.current.confirmMarker());

    // Nenhum marcador deve ser adicionado
    expect(result.current.markers).toHaveLength(0);
    // Modal permanece fechado
    expect(result.current.isModalOpen).toBe(false);
  });
});
