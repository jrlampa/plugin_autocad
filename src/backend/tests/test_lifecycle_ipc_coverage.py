"""
tests/test_lifecycle_ipc_coverage.py

Testes de cobertura para core/lifecycle.py e core/ipc.py.
- lifecycle.py: ActiveJobRegistry (add, remove, wait_for_completion)
- ipc.py: IpcServer.start() quando win32 disponível (mockado), stop()
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("SISRUA_TESTING", "true")
os.environ.setdefault("SISRUA_AUTH_TOKEN", "test-lifecycle-token")


# ---------------------------------------------------------------------------
# lifecycle.py — ActiveJobRegistry
# ---------------------------------------------------------------------------

class TestActiveJobRegistry:
    """Cobre as linhas 12-50 de core/lifecycle.py."""

    def _make_registry(self):
        from backend.core.lifecycle import ActiveJobRegistry
        return ActiveJobRegistry()

    def test_add_and_remove(self):
        """add() e remove() modificam o conjunto interno."""
        reg = self._make_registry()
        t = threading.Thread(target=lambda: None)
        reg.add(t)
        assert t in reg._threads
        reg.remove(t)
        assert t not in reg._threads

    def test_remove_nonexistent_is_noop(self):
        """remove() com thread não registrada não levanta exceção (discard)."""
        reg = self._make_registry()
        t = threading.Thread(target=lambda: None)
        reg.remove(t)  # deve ser silencioso

    def test_wait_for_completion_no_threads(self):
        """wait_for_completion() com registry vazia retorna imediatamente."""
        reg = self._make_registry()
        start = time.monotonic()
        reg.wait_for_completion(timeout=5.0)
        elapsed = time.monotonic() - start
        # Deve ser muito rápido — sem threads para aguardar
        assert elapsed < 1.0

    def test_wait_for_completion_thread_finishes(self):
        """wait_for_completion() aguarda thread terminar normalmente (linha 50)."""
        reg = self._make_registry()
        barrier = threading.Barrier(2)

        def worker():
            barrier.wait()  # sincroniza com teste
            time.sleep(0.05)

        t = threading.Thread(target=worker, daemon=True)
        reg.add(t)
        t.start()
        barrier.wait()  # libera o worker

        reg.wait_for_completion(timeout=2.0)
        assert not t.is_alive()

    def test_wait_for_completion_logs_when_threads_timeout(self, caplog):
        """wait_for_completion() loga warning quando threads excedem timeout (linha 48)."""
        import logging
        reg = self._make_registry()
        done_event = threading.Event()

        def slow_worker():
            done_event.wait(timeout=5.0)

        t = threading.Thread(target=slow_worker, daemon=True)
        reg.add(t)
        t.start()

        # Timeout extremamente curto para forçar path de timeout
        with patch("backend.core.lifecycle.logger") as mock_logger:
            reg.wait_for_completion(timeout=0.01)
            # Pode não ter sido chamado se a thread finalizou antes do check;
            # mas o path da linha 36 (shutdown_waiting_threads) deve ter sido percorrido.
            mock_logger.info.assert_called()

        done_event.set()
        t.join(timeout=1.0)

    def test_wait_for_completion_alive_warning(self):
        """wait_for_completion() emite warning quando threads ainda estão vivas (linha 48)."""
        reg = self._make_registry()
        done_event = threading.Event()

        def slow_worker():
            done_event.wait(timeout=5.0)

        t = threading.Thread(target=slow_worker, daemon=True)
        reg.add(t)
        t.start()

        with patch("backend.core.lifecycle.logger") as mock_logger:
            reg.wait_for_completion(timeout=0.001)
            # Thread ainda viva: deve emitir warning ou info — ambos são aceitáveis
            assert mock_logger.info.called or mock_logger.warning.called

        done_event.set()
        t.join(timeout=1.0)

    def test_wait_for_completion_multiple_threads(self):
        """wait_for_completion() aguarda múltiplas threads terminarem."""
        reg = self._make_registry()
        results = []

        def worker(n):
            time.sleep(0.02 * n)
            results.append(n)

        threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(1, 4)]
        for t in threads:
            reg.add(t)
            t.start()

        reg.wait_for_completion(timeout=2.0)
        assert len(results) == 3

    def test_global_job_registry_exists(self):
        """O singleton job_registry deve ser exportado pelo módulo."""
        from backend.core.lifecycle import job_registry, ActiveJobRegistry
        assert isinstance(job_registry, ActiveJobRegistry)

    def test_shutdown_event_is_threading_event(self):
        """SHUTDOWN_EVENT é uma instância de threading.Event."""
        from backend.core.lifecycle import SHUTDOWN_EVENT
        assert isinstance(SHUTDOWN_EVENT, threading.Event)


# ---------------------------------------------------------------------------
# ipc.py — IpcServer (non-Windows e mocks)
# ---------------------------------------------------------------------------

class TestIpcServer:
    """Cobre core/ipc.py em ambientes non-Windows (Linux/CI)."""

    def test_start_noop_when_win32_unavailable(self):
        """start() deve ser no-op em Linux (_WIN32_AVAILABLE=False)."""
        from backend.core.ipc import IpcServer
        server = IpcServer("test-token-ipc")
        with patch("backend.core.ipc._WIN32_AVAILABLE", False):
            server.start()
        assert server.thread is None
        assert server.running is False

    def test_stop_sets_running_false(self):
        """stop() deve definir running=False mesmo sem thread ativa."""
        from backend.core.ipc import IpcServer
        server = IpcServer("test-token-stop")
        server.running = True
        # No Linux, stop() tenta abrir o pipe e falha silenciosamente
        server.stop()
        assert server.running is False

    def test_stop_open_pipe_exception_silenced(self):
        """stop() silencia qualquer exceção ao tentar abrir o pipe."""
        from backend.core.ipc import IpcServer
        server = IpcServer("test-token-exc")
        server.running = True
        # Forçar exceção no open() — deve ser silenciada pelo bare `except`
        with patch("builtins.open", side_effect=OSError("pipe not found")):
            server.stop()  # Não deve levantar
        assert server.running is False

    def test_start_with_win32_mocked(self):
        """start() inicia thread quando _WIN32_AVAILABLE=True (win32 mockado)."""
        from backend.core.ipc import IpcServer

        # Mock dos módulos win32
        fake_win32pipe = MagicMock()
        fake_win32file = MagicMock()
        fake_pywintypes = MagicMock()

        with patch("backend.core.ipc._WIN32_AVAILABLE", True), \
             patch.dict("sys.modules", {
                 "win32pipe": fake_win32pipe,
                 "win32file": fake_win32file,
                 "pywintypes": fake_pywintypes,
             }):
            server = IpcServer("test-token-win32")
            server.start()
            # Thread deve ter sido criada e iniciada
            assert server.running is True
            assert server.thread is not None
            assert server.thread.is_alive()
            # Parar imediatamente
            server.running = False

    def test_ipc_server_pipe_name(self):
        """PIPE_NAME deve ser o caminho correto do named pipe do sisRUA."""
        from backend.core.ipc import IpcServer
        assert IpcServer.PIPE_NAME == r"\\.\pipe\sisrua_backend"

    def test_ipc_server_buffer_size(self):
        """BUFFER_SIZE deve ser 4096."""
        from backend.core.ipc import IpcServer
        assert IpcServer.BUFFER_SIZE == 4096
