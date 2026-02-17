import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import App from './App';
import React from 'react';

// Mock do api.js localmente para garantir
vi.mock('./api', () => ({
  api: {
    checkHealth: vi.fn(() => Promise.resolve(true)),
    smartGeocode: vi.fn(),
  },
}));

describe('App (UI básica)', () => {
  it('renderiza o título', async () => {
    render(<App />);
    // "sisRUA" está no SettingsPanel header, sempre visível
    const el = await screen.findByText(/sisRUA/i, {}, { timeout: 4000 });
    expect(el).toBeInTheDocument();
  });
});
