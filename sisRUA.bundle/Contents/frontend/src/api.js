import axios from 'axios';

// Em produção, a URL vem da variável de ambiente. Em dev, fallback para localhost.
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = {
    // Cria um novo trabalho de arruamento
    createJob: async (payload) => {
        const response = await axios.post(`${API_BASE}/jobs`, payload);
        return response.data;
    },

    // Verifica o status do processamento
    checkStatus: async (jobId) => {
        const response = await axios.get(`${API_BASE}/jobs/${jobId}`);
        return response.data;
    },

    // Extrai coordenadas de arquivos (KML, KMZ, CSV, TXT)
    extractLocation: async (file) => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await axios.post(`${API_BASE}/extract-location`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        return response.data;
    },

    // Decifra entradas inteligentes (UTM, GMS, Lat/Lon)
    smartGeocode: async (text) => {
        const response = await axios.get(`${API_BASE}/tools/geocode`, {
            params: { query: text }
        });
        return response.data;
    },

    // Helper para gerar URL completa de download (Frontend não precisa saber a porta do backend)
    getDownloadUrl: (relativePath) => {
        if (!relativePath) return '#';
        // Remove /api/v1 do base para concatenar com o path relativo que já vem com /api/v1
        // Ou, se o backend mandar path relativo puro, ajusta aqui.
        // Assumindo que backend manda: /api/v1/jobs/.../download
        const rootUrl = API_BASE.replace('/api/v1', '');
        return `${rootUrl}${relativePath}`;
    }
};