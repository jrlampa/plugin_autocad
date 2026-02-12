import sys
import os
import time
import subprocess
import win32pipe, win32file, pywintypes

# Configuration: Relative to where this script is run (project root)
# Assumes structure: tools/test_ipc_regression.py -> run from root
BACKEND_EXE = os.path.join(os.getcwd(), "bundle-template", "sisRUA.bundle", "Contents", "backend", "sisrua_backend.exe")
PIPE_NAME = r'\\.\pipe\sisrua_backend'
BUFFER_SIZE = 4096

def main():
    global BACKEND_EXE
    print(f"[TEST] Starting Regression Test: IPC Token Generation")
    print(f"[TEST] Backend Path: {BACKEND_EXE}")

    if not os.path.exists(BACKEND_EXE):
        print(f"[ERROR] Backend executable not found at {BACKEND_EXE}")
        # Fallback to verify release folder if bundle-template is empty
        fallback = os.path.join(os.getcwd(), "release", "sisRUA.bundle", "Contents", "backend", "sisrua_backend.exe")
        if os.path.exists(fallback):
             print(f"[INFO] Found in release folder, using that: {fallback}")
             BACKEND_EXE = fallback
        else:
             sys.exit(1)

    # 1. Kill potential zombies
    subprocess.run("taskkill /F /IM sisrua_backend.exe", shell=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    time.sleep(1)

    # 2. Launch Backend cleanly (No Auth Token in Env)
    # This simulates the "double-click" or "plugin launch" scenario where env vars might differ
    env = os.environ.copy()
    if "SISRUA_AUTH_TOKEN" in env:
        del env["SISRUA_AUTH_TOKEN"]
    
    # Use a random port to avoid conflicts
    try:
        proc = subprocess.Popen([BACKEND_EXE, "--host", "127.0.0.1", "--port", "57123", "--log-level", "info"], env=env)
        print(f"[TEST] Backend launched (PID: {proc.pid}). Waiting for startup...")
    except OSError as e:
        print(f"[ERROR] Failed to launch backend: {e}")
        sys.exit(1)

    # 3. Wait for Pipe
    start_time = time.time()
    connected = False
    handle = None
    
    while time.time() - start_time < 20:
        try:
            # Try to open the pipe directly. WaitNamedPipe waits for an instance to be available.
            # If 100ms timeout occurs, it raises error.
            win32pipe.WaitNamedPipe(PIPE_NAME, 1000)
            
            # Now try to open
            handle = win32file.CreateFile(
                PIPE_NAME,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None, win32file.OPEN_EXISTING, 0, None
            )
            connected = True
            break
        except pywintypes.error as e:
            # error 2 = file not found (pipe not ready)
            # error 231 = pipe busy (all instances used)
            time.sleep(0.5)
            if proc.poll() is not None:
                print(f"[ERROR] Backend process died unexpectedly with code {proc.returncode}")
                break
    
    if not connected or handle is None:
        print("[ERROR] Timeout waiting for IPC Pipe or Connection Failed.")
        proc.terminate()
        sys.exit(1)

    print("[TEST] Pipe availability confirmed. Connecting...")

    # 4. Connect and Request Token
    try:
        # Determine strict pipe mode
        state = win32pipe.PIPE_READMODE_MESSAGE
        win32pipe.SetNamedPipeHandleState(handle, state, None, None)

        print("[TEST] Sending GET_TOKEN...")
        win32file.WriteFile(handle, b"GET_TOKEN")
        
        resp = win32file.ReadFile(handle, BUFFER_SIZE)
        raw_msg = resp[1]
        token = raw_msg.decode('utf-8').strip()
        
        print(f"[TEST] Received Token: '{token}'")

        if not token:
            print("[FAIL] Token is empty! Regression detected.")
            proc.terminate()
            sys.exit(1)
        
        if len(token) < 10:
             print(f"[FAIL] Token suspicious (too short): {token}")
             proc.terminate()
             sys.exit(1)

        print("[SUCCESS] Valid token received. Fix verified.")

    except Exception as e:
        print(f"[ERROR] IPC Exchange failed: {e}")
        proc.terminate()
        sys.exit(1)
    finally:
        print("[TEST] Cleaning up...")
        if handle:
            win32file.CloseHandle(handle)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

if __name__ == "__main__":
    main()
