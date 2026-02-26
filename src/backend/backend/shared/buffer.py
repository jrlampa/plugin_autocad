"""
backend/shared/buffer.py
Buffer de persistência assíncrono com flush por tamanho de batch ou intervalo de tempo.

Responsabilidade única: agrupar itens e enviá-los em lotes para um callback de persistência,
reduzindo overhead de I/O. Thread-safe via Queue.
"""
from __future__ import annotations

import queue
import threading
import time
from typing import Any, Callable, List

from backend.shared.logger import get_logger

logger = get_logger(__name__)

_SENTINEL = None


class PersistenceBuffer:
    """
    Buffer assíncrono que acumula itens e os envia em lotes para flush_callback.

    Args:
        flush_callback: Função chamada com uma lista de itens a persistir.
        batch_size:     Número máximo de itens por lote (dispara flush imediato).
        flush_interval: Intervalo máximo em segundos entre flushes (mesmo com batch incompleto).
    """

    def __init__(
        self,
        flush_callback: Callable[[List[Any]], None],
        batch_size: int = 50,
        flush_interval: float = 5.0,
    ) -> None:
        self._callback = flush_callback
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self.queue: queue.Queue = queue.Queue()
        self.running: bool = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def add(self, item: Any) -> None:
        """Enfileira um item para persistência assíncrona."""
        self.queue.put(item)

    def stop(self) -> None:
        """Sinaliza parada e aguarda o worker concluir o flush final."""
        self.running = False
        self.queue.put(_SENTINEL)
        self._thread.join()

    def _flush(self, batch: List[Any]) -> None:
        """Envia o lote ao callback, capturando exceções para não interromper o worker."""
        if not batch:
            return
        try:
            self._callback(batch)
        except Exception as exc:
            logger.error("persistence_buffer_flush_error", error=str(exc))

    def _worker(self) -> None:
        """Loop de background: acumula itens e realiza flush por tamanho ou tempo."""
        pending: List[Any] = []
        last_flush = time.monotonic()

        while True:
            timeout = max(0.0, self._flush_interval - (time.monotonic() - last_flush))
            try:
                item = self.queue.get(timeout=timeout)
            except queue.Empty:
                # Timeout: flush por intervalo de tempo
                if pending:
                    self._flush(pending)
                    pending = []
                last_flush = time.monotonic()
                continue

            # Sentinel: encerrar worker após flush final
            if item is _SENTINEL:
                if pending:
                    self._flush(pending)
                break

            pending.append(item)
            if len(pending) >= self._batch_size:
                self._flush(pending)
                pending = []
                last_flush = time.monotonic()
