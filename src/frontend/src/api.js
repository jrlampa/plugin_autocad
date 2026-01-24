import axios from 'axios';

// Em produção, usamos a mesma origem (porta dinâmica do backend).
// Em dev, você pode sobrescrever com VITE_API_URL.
const API_BASE = (import.meta.env.VITE_API_URL || `${window.location.origin}/api/v1`).replace(/\/+$/, '');

export const api = {
    // Decifra entradas inteligentes (UTM, GMS, Lat/Lon)
    smartGeocode: async (text) => {
        const response = await axios.get(`${API_BASE}/tools/geocode`, {
            params: { query: text }
        });
        return response.data;
    }
};