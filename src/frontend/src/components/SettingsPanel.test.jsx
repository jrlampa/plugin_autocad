/**
 * src/components/SettingsPanel.test.jsx
 *
 * Testes unitários para o componente SettingsPanel.
 *
 * Interface em pt-BR conforme requisito do projeto sisRUA.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';
import SettingsPanel from './SettingsPanel';

// Mock NormaPanel para evitar dependências de api externas no painel de config
vi.mock('./NormaPanel', () => ({
  default: () => <div data-testid="norma-panel">NormaPanel Mock</div>,
}));

const TILE_PROVIDERS = {
  satellite: { url: 'https://example.com/{z}/{x}/{y}.png', attribution: 'Google' },
  clean: { url: 'https://carto.com/{z}/{x}/{y}.png', attribution: 'CartoDB' },
  osm: { url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png', attribution: 'OSM' },
};

function makeProps(overrides = {}) {
  return {
    showSettings: false,
    setShowSettings: vi.fn(),
    loading: false,
    previewGeoJson: null,
    handleImportGeoJson: vi.fn(),
    setPreviewGeoJson: vi.fn(),
    inputText: '-22.15018, -42.92185',
    setInputText: vi.fn(),
    handleGeocode: vi.fn(),
    inputLoading: false,
    radius: 500,
    setRadius: vi.fn(),
    setRadiusInput: vi.fn(),
    baseLayer: 'satellite',
    setBaseLayer: vi.fn(),
    tileProviders: TILE_PROVIDERS,
    engConfig: { profile_name: 'PADRAO_URBANO', crs_out: 'EPSG:31984' },
    setEngConfig: vi.fn(),
    uiJob: null,
    api: { exportGeoJSON: vi.fn(), exportGeoPackage: vi.fn(), exportDxf: vi.fn() },
    onToast: vi.fn(),
    ...overrides,
  };
}

// ── Renderização básica ──────────────────────────────────

describe('SettingsPanel — renderização básica', () => {
  it('renderiza sem erros', () => {
    const { container } = render(<SettingsPanel {...makeProps()} />);
    expect(container.firstChild).toBeTruthy();
  });

  it('exibe o título "sisRUA" e versão', () => {
    render(<SettingsPanel {...makeProps()} />);
    expect(screen.getByText('sisRUA')).toBeInTheDocument();
    expect(screen.getByText('v0.5.0')).toBeInTheDocument();
  });

  it('exibe o campo de busca de endereço', () => {
    render(<SettingsPanel {...makeProps()} />);
    expect(screen.getByPlaceholderText('Buscar endereço, Lat/Lon...')).toBeInTheDocument();
  });
});

// ── Loading guard (linha 49) ─────────────────────────────

describe('SettingsPanel — loading guard (linha 49)', () => {
  it('chama setShowSettings quando loading=false', () => {
    const setShowSettings = vi.fn();
    render(<SettingsPanel {...makeProps({ setShowSettings, loading: false })} />);
    // O botão toggle é o único botão no header
    fireEvent.click(screen.getAllByRole('button')[0]);
    expect(setShowSettings).toHaveBeenCalled();
  });

  it('NÃO chama setShowSettings quando loading=true (linha 49)', () => {
    const setShowSettings = vi.fn();
    render(<SettingsPanel {...makeProps({ setShowSettings, loading: true })} />);
    fireEvent.click(screen.getAllByRole('button')[0]);
    expect(setShowSettings).not.toHaveBeenCalled();
  });
});

// ── showSettings = true ──────────────────────────────────

describe('SettingsPanel — painel de configurações (showSettings=true)', () => {
  it('exibe camadas de mapa', () => {
    render(<SettingsPanel {...makeProps({ showSettings: true })} />);
    expect(screen.getByText('SATÉLITE')).toBeInTheDocument();
    expect(screen.getByText('CLEAN')).toBeInTheDocument();
    expect(screen.getByText('RUAS')).toBeInTheDocument();
  });

  it('exibe slider de raio (linha 103)', () => {
    render(<SettingsPanel {...makeProps({ showSettings: true })} />);
    expect(screen.getByText('Raio de Busca')).toBeInTheDocument();
    expect(screen.getByText('500m')).toBeInTheDocument();
  });

  it('chama setBaseLayer ao clicar em camada base', () => {
    const setBaseLayer = vi.fn();
    render(<SettingsPanel {...makeProps({ showSettings: true, setBaseLayer })} />);
    fireEvent.click(screen.getByText('RUAS'));
    expect(setBaseLayer).toHaveBeenCalledWith('osm');
  });

  it('chama setRadius e setRadiusInput ao mover slider (linha 103)', () => {
    const setRadius = vi.fn();
    const setRadiusInput = vi.fn();
    render(<SettingsPanel {...makeProps({ showSettings: true, setRadius, setRadiusInput })} />);
    fireEvent.change(screen.getByRole('slider'), { target: { value: '1000' } });
    expect(setRadius).toHaveBeenCalledWith(1000);
    expect(setRadiusInput).toHaveBeenCalledWith(1000);
  });

  it('chama setEngConfig ao alterar perfil (linha 155-158)', () => {
    const setEngConfig = vi.fn();
    render(<SettingsPanel {...makeProps({ showSettings: true, setEngConfig })} />);
    fireEvent.change(screen.getAllByRole('combobox')[0], { target: { value: 'RURAL_LEVE' } });
    expect(setEngConfig).toHaveBeenCalledWith(
      expect.objectContaining({ profile_name: 'RURAL_LEVE' })
    );
  });

  it('chama setEngConfig ao alterar CRS (linha 155-158)', () => {
    const setEngConfig = vi.fn();
    render(<SettingsPanel {...makeProps({ showSettings: true, setEngConfig })} />);
    fireEvent.change(screen.getAllByRole('combobox')[1], { target: { value: 'EPSG:4326' } });
    expect(setEngConfig).toHaveBeenCalledWith(expect.objectContaining({ crs_out: 'EPSG:4326' }));
  });

  it('chama setShowSettings(false) ao clicar em Voltar', () => {
    const setShowSettings = vi.fn();
    render(<SettingsPanel {...makeProps({ showSettings: true, setShowSettings })} />);
    fireEvent.click(screen.getByText('VOLTAR PARA O PROJETO'));
    expect(setShowSettings).toHaveBeenCalledWith(false);
  });
});

// ── Geocoding ────────────────────────────────────────────

describe('SettingsPanel — geocoding', () => {
  it('chama setInputText ao digitar', () => {
    const setInputText = vi.fn();
    render(<SettingsPanel {...makeProps({ setInputText })} />);
    fireEvent.change(screen.getByPlaceholderText('Buscar endereço, Lat/Lon...'), {
      target: { value: 'Petrópolis, RJ' },
    });
    expect(setInputText).toHaveBeenCalledWith('Petrópolis, RJ');
  });

  it('chama handleGeocode ao pressionar Enter', () => {
    const handleGeocode = vi.fn();
    render(<SettingsPanel {...makeProps({ handleGeocode })} />);
    fireEvent.keyDown(screen.getByPlaceholderText('Buscar endereço, Lat/Lon...'), { key: 'Enter' });
    expect(handleGeocode).toHaveBeenCalled();
  });

  it('chama setInputText("") ao clicar no botão limpar', () => {
    const setInputText = vi.fn();
    render(<SettingsPanel {...makeProps({ inputText: 'Algo', setInputText })} />);
    // O botão limpar é o último (ArrowLeft rotacionado)
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[buttons.length - 1]);
    expect(setInputText).toHaveBeenCalledWith('');
  });

  it('exibe spinner de loading quando inputLoading=true (linha 103)', () => {
    render(<SettingsPanel {...makeProps({ inputLoading: true })} />);
    // O spinner tem a classe animate-spin — quando inputLoading=true, a div de spinner é renderizada
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });
});

// ── Preview GeoJSON ──────────────────────────────────────

describe('SettingsPanel — preview GeoJSON', () => {
  const previewGeoJson = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [-42.92185, -22.15018] },
        properties: {},
      },
    ],
  };

  it('exibe banner preview quando previewGeoJson definido', () => {
    render(<SettingsPanel {...makeProps({ previewGeoJson })} />);
    expect(screen.getByText('Preview de Campo')).toBeInTheDocument();
  });

  it('chama handleImportGeoJson ao clicar importar', () => {
    const handleImportGeoJson = vi.fn();
    render(<SettingsPanel {...makeProps({ previewGeoJson, handleImportGeoJson })} />);
    fireEvent.click(screen.getByTestId('btn-import-geojson'));
    expect(handleImportGeoJson).toHaveBeenCalled();
  });

  it('chama setPreviewGeoJson(null) ao clicar Cancelar', () => {
    const setPreviewGeoJson = vi.fn();
    render(<SettingsPanel {...makeProps({ previewGeoJson, setPreviewGeoJson })} />);
    fireEvent.click(screen.getByText('Cancelar'));
    expect(setPreviewGeoJson).toHaveBeenCalledWith(null);
  });
});

// ── Export GIS ───────────────────────────────────────────

describe('SettingsPanel — export GIS', () => {
  it('botão DXF desabilitado sem project_id', () => {
    render(<SettingsPanel {...makeProps({ showSettings: true })} />);
    expect(screen.getByTestId('btn-export-dxf')).toBeDisabled();
  });

  it('botão DXF habilitado com project_id', () => {
    const uiJob = { status: 'completed', progress: 1.0, project_id: 'p1' };
    render(<SettingsPanel {...makeProps({ showSettings: true, uiJob })} />);
    expect(screen.getByTestId('btn-export-dxf')).not.toBeDisabled();
  });

  it('chama exportDxf ao clicar no botão DXF', () => {
    const exportDxf = vi.fn();
    const api = { exportGeoJSON: vi.fn(), exportGeoPackage: vi.fn(), exportDxf };
    const uiJob = { status: 'completed', progress: 1.0, project_id: 'p2' };
    render(<SettingsPanel {...makeProps({ showSettings: true, uiJob, api })} />);
    fireEvent.click(screen.getByTestId('btn-export-dxf'));
    expect(exportDxf).toHaveBeenCalledWith('p2');
  });
});

// ── JobOverlay integrado ─────────────────────────────────

describe('SettingsPanel — JobOverlay integrado', () => {
  it('exibe JobOverlay quando uiJob definido', () => {
    const uiJob = { status: 'processing', progress: 0.5, message: 'Baixando...' };
    render(<SettingsPanel {...makeProps({ uiJob })} />);
    expect(screen.getByTestId('job-overlay')).toBeInTheDocument();
  });

  it('não exibe JobOverlay quando uiJob é null', () => {
    render(<SettingsPanel {...makeProps({ uiJob: null })} />);
    expect(screen.queryByTestId('job-overlay')).not.toBeInTheDocument();
  });
});
