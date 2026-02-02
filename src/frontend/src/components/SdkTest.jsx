import { useState, useEffect } from 'react';
import { SdkService } from '../services/SdkService';

export function SdkTest() {
  const [status, setStatus] = useState('Checking...');
  const [details, setDetails] = useState('');

  useEffect(() => {
    async function check() {
      try {
        const health = await SdkService.checkHealth();
        setStatus('OK');
        setDetails(JSON.stringify(health, null, 2));
      } catch (err) {
        setStatus('ERROR');
        setDetails(err.toString());
      }
    }
    check();
  }, []);

  if (status === 'OK') return null; // Hide if successful to not clutter UI

  return (
    <div style={{ padding: 10, background: '#fee', border: '1px solid red', margin: 10 }}>
      <strong>SDK Health: {status}</strong>
      <pre>{details}</pre>
    </div>
  );
}
