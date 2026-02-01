import { API_BASE_URL } from '../config';

export const aiService = {
  async sendMessage(message, context = {}) {
    // Retrieve token from storage (assumed logic from auth system)
    const token = localStorage.getItem('sisrua_token');

    try {
      const res = await fetch(`${API_BASE_URL}/ai/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-SisRua-Token': token || '',
        },
        body: JSON.stringify({ message, context }),
      });

      if (!res.ok) {
        // Handle non-200 responses gracefully
        return "Desculpe, não consegui processar sua solicitação no momento.";
      }

      const data = await res.json();
      return data.response;
    } catch (err) {
      console.error('AI Service Error:', err);
      return "Erro de conexão com o assistente.";
    }
  }
};
