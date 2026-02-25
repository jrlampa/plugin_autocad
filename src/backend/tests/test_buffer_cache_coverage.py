"""
tests/test_buffer_cache_coverage.py

Testes de cobertura para core/buffer.py e services/cache.py (caminhos com Redis mockado).
- PersistenceBuffer: stop(), _worker (sentinel + batch final), _flush com exceção
- CacheService: Redis hit, Redis set path, _safe_redis_set, file write error
"""
from __future__ import annotations

import os
import json
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("SISRUA_TESTING", "true")
os.environ.setdefault("SISRUA_AUTH_TOKEN", "test-buffer-cache")


# ---------------------------------------------------------------------------
# core/buffer.py — PersistenceBuffer
# ---------------------------------------------------------------------------

class TestPersistenceBuffer:
    """Cobre linhas 32-34 (stop), 48 (sentinel break), 67-68 (final flush), 73-74 (_flush exc)."""

    def test_add_and_flush_via_batch_size(self):
        """Itens são enviados ao callback quando batch_size é atingido."""
        flushed = []

        def callback(batch):
            flushed.extend(batch)

        from backend.shared.buffer import PersistenceBuffer
        buf = PersistenceBuffer(flush_callback=callback, batch_size=3, flush_interval=10.0)
        buf.add(1)
        buf.add(2)
        buf.add(3)
        # Aguardar o worker processar
        time.sleep(0.3)
        buf.stop()
        assert flushed == [1, 2, 3]

    def test_stop_flushes_remaining_items(self):
        """stop() faz flush final dos itens pendentes (linhas 67-68)."""
        flushed = []

        def callback(batch):
            flushed.extend(batch)

        from backend.shared.buffer import PersistenceBuffer
        buf = PersistenceBuffer(flush_callback=callback, batch_size=100, flush_interval=10.0)
        buf.add("item_a")
        buf.add("item_b")
        buf.stop()  # Deve aguardar thread e fazer flush final
        assert "item_a" in flushed
        assert "item_b" in flushed

    def test_stop_sends_sentinel_and_joins_thread(self):
        """stop() sinaliza sentinel (None) e aguarda a thread (linhas 32-34)."""
        from backend.shared.buffer import PersistenceBuffer
        buf = PersistenceBuffer(flush_callback=lambda b: None, batch_size=10, flush_interval=5.0)
        thread = buf._thread
        assert thread.is_alive()
        buf.stop()
        assert not thread.is_alive()
        assert buf.running is False

    def test_flush_callback_exception_is_silenced(self):
        """Exceção em flush_callback é capturada e logada (linhas 73-74)."""
        call_count = [0]

        def bad_callback(batch):
            call_count[0] += 1
            raise ValueError("Flush failed!")

        from backend.shared.buffer import PersistenceBuffer
        buf = PersistenceBuffer(flush_callback=bad_callback, batch_size=1, flush_interval=10.0)
        buf.add("trigger_flush")
        time.sleep(0.2)
        buf.running = False
        buf.queue.put(None)  # sentinel to end worker
        buf._thread.join(timeout=1.0)
        # Callback was called and exception was silenced (no propagation)
        assert call_count[0] >= 1

    def test_flush_on_time_interval(self):
        """Worker faz flush após flush_interval mesmo com batch incompleto."""
        flushed = []

        def callback(batch):
            flushed.extend(batch)

        from backend.shared.buffer import PersistenceBuffer
        buf = PersistenceBuffer(flush_callback=callback, batch_size=100, flush_interval=0.1)
        buf.add("time_flush_item")
        time.sleep(0.5)  # Aguardar flush por tempo
        buf.stop()
        assert "time_flush_item" in flushed


# ---------------------------------------------------------------------------
# services/cache.py — CacheService com Redis mockado
# ---------------------------------------------------------------------------

class TestCacheServiceRedis:
    """Cobre linhas de cache com Redis ativo (linhas 33-34, 49-50, 61-62, 66, 72-73)."""

    def _make_svc(self, tmp_path: Path):
        os.environ["LOCALAPPDATA"] = str(tmp_path)
        from backend.application.cache import CacheService
        return CacheService()

    def test_redis_get_hit_returns_cached_value(self, tmp_path):
        """get() com Redis hit retorna o valor cacheado (linhas 33-34)."""
        svc = self._make_svc(tmp_path)
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({"redis": True}).encode()
        svc.redis = mock_redis

        result = svc.get("redis_key")
        assert result == {"redis": True}
        mock_redis.get.assert_called_once_with("redis_key")

    def test_redis_get_miss_falls_back_to_filesystem(self, tmp_path):
        """get() com Redis miss faz fallback para filesystem."""
        svc = self._make_svc(tmp_path)
        # Salvar no filesystem primeiro
        svc.redis = None
        svc.set("fs_key", {"fs": True})

        # Configurar Redis para retornar None (miss)
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        svc.redis = mock_redis

        result = svc.get("fs_key")
        assert result == {"fs": True}
        # Deve ter tentado popular Redis na leitura (read-through)
        mock_redis.set.assert_called()

    def test_redis_set_called_on_cache_set(self, tmp_path):
        """set() com Redis ativo chama _safe_redis_set (linha 66)."""
        svc = self._make_svc(tmp_path)
        mock_redis = MagicMock()
        svc.redis = mock_redis

        svc.set("set_key", {"v": 42})
        mock_redis.set.assert_called()
        args = mock_redis.set.call_args
        assert "set_key" in args[0]

    def test_safe_redis_set_serializes_and_stores(self, tmp_path):
        """_safe_redis_set chama redis.set com JSON (linhas 72-73)."""
        svc = self._make_svc(tmp_path)
        mock_redis = MagicMock()
        svc.redis = mock_redis

        svc._safe_redis_set("test_key", {"data": 1}, ttl=600)
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "test_key"
        assert json.loads(call_args[0][1]) == {"data": 1}
        assert call_args[1]["ex"] == 600

    def test_safe_redis_set_exception_silenced(self, tmp_path):
        """_safe_redis_set silencia exceções do Redis (linha 73)."""
        svc = self._make_svc(tmp_path)
        mock_redis = MagicMock()
        mock_redis.set.side_effect = RuntimeError("Redis down")
        svc.redis = mock_redis

        # Não deve levantar exceção
        svc._safe_redis_set("key", {"v": 1})

    def test_file_write_error_is_logged(self, tmp_path):
        """set() com erro de escrita loga o erro (linhas 61-62)."""
        svc = self._make_svc(tmp_path)
        svc.redis = None

        with patch.object(Path, "write_text", side_effect=OSError("no space")):
            # Não deve levantar — erro é logado
            svc.set("error_key", {"value": 99})

    def test_file_read_error_returns_none(self, tmp_path):
        """get() com erro ao ler filesystem retorna None silenciosamente (linha 49-50)."""
        svc = self._make_svc(tmp_path)
        svc.redis = None
        svc.set("corrupt_key", {"v": 1})

        with patch.object(Path, "read_text", side_effect=OSError("read error")):
            result = svc.get("corrupt_key")
        assert result is None
