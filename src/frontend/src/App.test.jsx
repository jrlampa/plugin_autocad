import { render, screen } from '@testing-library/react'
import App from './App'

describe('App (UI básica)', () => {
  it('renderiza o título e elementos principais do painel', () => {
    render(<App />)

    expect(screen.getByText(/sisRUA/i)).toBeInTheDocument()
    expect(screen.getByText(/Localização do Projeto/i)).toBeInTheDocument()
    expect(screen.getByText(/Raio de Abrangência/i)).toBeInTheDocument()
  })
})
