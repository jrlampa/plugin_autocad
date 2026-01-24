import { useState, useRef, useCallback, useEffect } from 'react';
import { api } from '../api';

export function useJobManager(POLLING_TIMEOUT_MS = 120000) {
    const [job, setJob] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Refs para evitar loops e memory leaks
    const pollTimeoutRef = useRef(null);
    const startTimeRef = useRef(null);
    const isMounted = useRef(true);

    useEffect(() => {
        isMounted.current = true;
        return () => {
            isMounted.current = false;
            if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current);
        };
    }, []);

    const pollStatus = useCallback(async (jobId) => {
        if (!isMounted.current) return;

        // Timeout de segurança
        if (Date.now() - startTimeRef.current > POLLING_TIMEOUT_MS) {
            setLoading(false);
            setError("Tempo limite excedido.");
            return;
        }

        try {
            const data = await api.checkStatus(jobId);

            if (!isMounted.current) return;

            setJob(data);

            // Lógica inteligente de parada (igual ao enabled do React Query)
            if (['completed', 'failed'].includes(data.status)) {
                setLoading(false);
                if (data.status === 'failed') setError(data.message);
                return; // PARE O POLLING
            }

            // Continua polling se estiver queued ou processing
            pollTimeoutRef.current = setTimeout(() => pollStatus(jobId), 2000);

        } catch (err) {
            if (isMounted.current) {
                // Backoff simples em erro de rede
                pollTimeoutRef.current = setTimeout(() => pollStatus(jobId), 3000);
            }
        }
    }, [POLLING_TIMEOUT_MS]);

    const createJob = async (payload) => {
        if (loading) return;
        setLoading(true);
        setError(null);
        setJob(null);
        startTimeRef.current = Date.now();

        try {
            const res = await api.createJob(payload);
            if (isMounted.current) {
                setJob(res);
                pollStatus(res.job_id); // Inicia o ciclo
            }
        } catch (err) {
            if (isMounted.current) {
                setError("Erro ao conectar com o servidor.");
                setLoading(false);
            }
        }
    };

    return { job, loading, error, createJob };
}