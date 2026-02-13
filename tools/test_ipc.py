
import time
import win32pipe, win32file

PIPE_NAME = r'\\.\pipe\sisrua_backend'

def test_pipe():
    print(f"Testing connection to {PIPE_NAME}...")
    try:
        handle = win32file.CreateFile(
            PIPE_NAME,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None
        )
        print("Connected to pipe successfully!")
        
        # Test sending GET_TOKEN
        print("Sending GET_TOKEN...")
        win32file.WriteFile(handle, b"GET_TOKEN")
        
        # Read response
        resp = win32file.ReadFile(handle, 4096)
        token = resp[1].decode('utf-8')
        print(f"Received Token: {token}")
        
        win32file.CloseHandle(handle)
        return True
    except Exception as e:
        print(f"Failed to connect: {e}")
        return False

if __name__ == "__main__":
    test_pipe()
