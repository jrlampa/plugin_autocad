import sys
import time
import struct
import threading
import win32pipe, win32file, pywintypes
import win32security, win32api
from backend.core.logger import get_logger

logger = get_logger(__name__)

class IpcServer:
    """
    Secure IPC Server using Windows Named Pipes.
    Facilitates secure token exchange between Plugin (C#) and Backend (Python).
    """
    PIPE_NAME = r'\\.\pipe\sisrua_backend'
    BUFFER_SIZE = 4096

    def __init__(self, auth_token):
        self.auth_token = auth_token
        self.running = False
        self.thread = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._server_loop, daemon=True)
        self.thread.start()
        logger.info("ipc_server_started", pipe=self.PIPE_NAME)

    def stop(self):
        self.running = False
        # Connect to self to unblock Accept
        try:
            with open(self.PIPE_NAME, 'r+b') as f:
                pass
        except:
            pass

    def _server_loop(self):
        while self.running:
            try:
                # Create Named Pipe with restrictive Security Descriptor?
                # For now, default security (Same user usually has access)
                pipe = win32pipe.CreateNamedPipe(
                    self.PIPE_NAME,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
                    1, # Max instances (1 for now, or ensure usage pattern)
                    self.BUFFER_SIZE,
                    self.BUFFER_SIZE,
                    0,
                    None
                )

                # Wait for client
                win32pipe.ConnectNamedPipe(pipe, None)

                # Client connected - Verify Integrity?
                # In a strict scenario, we'd check GetNamedPipeClientProcessId(pipe) -> query user
                # For Phase 10 compliance:
                # Just exchange the token. The pipe ACLs (local user only by default) provide decent security vs TCP
                
                try:
                    # Read Request (Expect "GET_TOKEN")
                    # Peek or Just Read
                    resp = win32file.ReadFile(pipe, self.BUFFER_SIZE)
                    raw_msg = resp[1]
                    msg = raw_msg.decode('utf-8').strip()
                    logger.info(f"IPC Received: {msg!r}")
                    
                    if msg == "GET_TOKEN":
                        # Send Token
                        logger.info("ipc_token_requested")
                        response_bytes = self.auth_token.encode('utf-8')
                        win32file.WriteFile(pipe, response_bytes)
                        win32file.FlushFileBuffers(pipe)
                        logger.info("IPC Token sent and flushed.")
                    else:
                        logger.warning("ipc_invalid_request", msg=msg)
                
                except Exception as e:
                    logger.error("ipc_comm_error", error=str(e))
                finally:
                    win32file.CloseHandle(pipe)

            except Exception as e:
                if self.running:
                    logger.error("ipc_server_error", error=str(e))
                    time.sleep(1) # Backoff
