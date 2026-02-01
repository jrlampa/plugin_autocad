import React, { useState } from 'react';
import { aiService } from '../services/aiService';

// Styles could be moved to CSS/Tailwind, but inline for now for single-file portability
const styles = {
  container: {
    position: 'fixed',
    bottom: '20px',
    right: '20px',
    zIndex: 1000,
    fontFamily: 'sans-serif',
  },
  button: {
    backgroundColor: '#0F172A',
    color: 'white',
    border: 'none',
    borderRadius: '50%',
    width: '56px',
    height: '56px',
    cursor: 'pointer',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '24px',
  },
  chatWindow: {
    backgroundColor: 'white',
    width: '350px',
    height: '500px',
    borderRadius: '12px',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
    display: 'flex',
    flexDirection: 'column',
    marginBottom: '16px',
    overflow: 'hidden',
    border: '1px solid #E2E8F0',
  },
  header: {
    backgroundColor: '#0F172A',
    color: 'white',
    padding: '16px',
    fontWeight: 'bold',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  messages: {
    flex: 1,
    padding: '16px',
    overflowY: 'auto',
    backgroundColor: '#F8FAFC',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  inputArea: {
    padding: '12px',
    borderTop: '1px solid #E2E8F0',
    display: 'flex',
    gap: '8px',
  },
  input: {
    flex: 1,
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #CBD5E1',
    outline: 'none',
  },
  sendBtn: {
    backgroundColor: '#3B82F6',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    padding: '8px 16px',
    cursor: 'pointer',
  },
  messageBubble: (isUser) => ({
    alignSelf: isUser ? 'flex-end' : 'flex-start',
    backgroundColor: isUser ? '#3B82F6' : 'white',
    color: isUser ? 'white' : '#1E293B',
    padding: '8px 12px',
    borderRadius: '8px',
    maxWidth: '85%',
    border: isUser ? 'none' : '1px solid #E2E8F0',
    fontSize: '14px',
    lineHeight: '1.5',
  }),
};

export const AiAssistant = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { id: 1, text: 'Olá! Sou o assistente sisRUA. Como posso ajudar com seu projeto hoje?', isUser: false }
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMsg = input;
    setMessages(prev => [...prev, { id: Date.now(), text: userMsg, isUser: true }]);
    setInput('');
    setIsLoading(true);

    // Call backend
    const response = await aiService.sendMessage(userMsg);

    setMessages(prev => [...prev, { id: Date.now() + 1, text: response, isUser: false }]);
    setIsLoading(false);
  };

  return (
    <div style={styles.container}>
      {isOpen && (
        <div style={styles.chatWindow}>
          <div style={styles.header}>
            <span>sisRUA AI (Beta)</span>
            <button
              onClick={() => setIsOpen(false)}
              style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', fontSize: '18px' }}
            >
              ×
            </button>
          </div>
          <div style={styles.messages}>
            {messages.map(msg => (
              <div key={msg.id} style={styles.messageBubble(msg.isUser)}>
                {msg.text}
              </div>
            ))}
            {isLoading && (
              <div style={{ alignSelf: 'flex-start', color: '#94A3B8', fontSize: '12px', marginLeft: '12px' }}>
                Digitando...
              </div>
            )}
          </div>
          <div style={styles.inputArea}>
            <input
              style={styles.input}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Pergunte algo..."
              disabled={isLoading}
            />
            <button style={styles.sendBtn} onClick={handleSend} disabled={isLoading}>
              Env
            </button>
          </div>
        </div>
      )}

      {!isOpen && (
        <button style={styles.button} onClick={() => setIsOpen(true)}>
          🤖
        </button>
      )}
    </div>
  );
};
