import os
import time
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

# Configuration
PORT = 9999
WEBHOOK_URL = f"http://127.0.0.1:{PORT}/webhook"
API_URL = "http://127.0.0.1:8000/api/v1"
AUTH_TOKEN = os.environ.get("SISRUA_AUTH_TOKEN", "test-token-123")

received_events = []

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        payload = json.loads(post_data.decode('utf-8'))
        
        print(f"[listener] Received event: {payload.get('event')}")
        received_events.append(payload)
        
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        return # Silence logging

def start_listener():
    server = HTTPServer(('127.0.0.1', PORT), WebhookHandler)
    server.serve_forever()

def test_webhooks():
    print("--- Phase 23: Webhook Integration Test ---")
    
    # 1. Start local listener
    listener_thread = threading.Thread(target=start_listener, daemon=True)
    listener_thread.start()
    print(f"Listener started at {WEBHOOK_URL}")

    # 2. Register webhook
    print("Registering webhook...")
    headers = {"X-SisRua-Token": AUTH_TOKEN}
    try:
        r = requests.post(f"{API_URL}/webhooks/register", 
                         json={"url": WEBHOOK_URL}, 
                         headers=headers)
        if r.status_code != 200:
            print(f"Failed to register: {r.status_code} - {r.text}")
            return
    except Exception as e:
        print(f"Error connecting to API: {e}. Is the backend running?")
        return

    # 3. Trigger a job (minimal geojson job)
    print("Triggering job...")
    minimal_geojson = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [-41.3235, -21.7634]},
            "properties": {"name": "Test Point"}
        }]
    }
    
    r = requests.post(f"{API_URL}/jobs/prepare", 
                     json={"kind": "geojson", "geojson": minimal_geojson}, 
                     headers=headers)
    assert r.status_code == 200, f"Job creation failed: {r.text}"
    job_id = r.json()["job_id"]
    print(f"Job created: {job_id}")

    # 4. Wait for events
    print("Waiting for events...")
    deadline = time.time() + 10
    required_events = ["job_started", "job_completed"]
    found_events = []
    
    while time.time() < deadline:
        found_events = [e["event"] for e in received_events]
        if all(re in found_events for re in required_events):
            break
        time.sleep(0.5)

    print(f"Final events received: {found_events}")
    
    # Validation
    assert "job_started" in found_events, "Missing job_started event"
    assert "job_completed" in found_events, "Missing job_completed event"
    
    # Verify data integrity in the last event
    last_event = next(e for e in received_events if e["event"] == "job_completed")
    assert last_event["data"]["job_id"] == job_id
    assert last_event["data"]["status"] == "completed"
    
    print("\n--- PASSED: Webhooks integration verified. ---")

if __name__ == "__main__":
    test_webhooks()
