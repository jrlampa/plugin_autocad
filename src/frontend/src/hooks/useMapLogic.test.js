import { renderHook, act } from '@testing-library/react'

import { useMapLogic } from './useMapLogic'

function makeDataTransfer() {
  const store = new Map()
  return {
    setData: (k, v) => store.set(k, v),
    getData: (k) => store.get(k),
    types: [],
    effectAllowed: '',
  }
}

describe('useMapLogic', () => {
  it('handleDragStart define o tipo no dataTransfer', () => {
    const { result } = renderHook(() => useMapLogic())
    const dt = makeDataTransfer()
    const e = { dataTransfer: dt }

    act(() => result.current.handleDragStart(e, 'POSTE'))
    expect(dt.getData('symbolType')).toBe('POSTE')
    expect(dt.effectAllowed).toBe('copy')
  })

  it('confirmMarker adiciona marcador com metadados', () => {
    const { result } = renderHook(() => useMapLogic())

    act(() => {
      result.current.handleSymbolDrop({ lat: 1.23, lng: 4.56 }, 'ARVORE')
      result.current.setMetaInput({ desc: 'Teste', altura: '12m' })
    })

    act(() => result.current.confirmMarker())

    expect(result.current.markers.length).toBe(1)
    expect(result.current.markers[0]).toEqual({
      lat: 1.23,
      lon: 4.56,
      tipo: 'ARVORE',
      meta: { desc: 'Teste', altura: '12m' },
    })
  })
})

