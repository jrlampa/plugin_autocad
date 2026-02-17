import requests
import time
import statistics

BASE_URL = "http://127.0.0.1:8000"
TOKEN = "test-token" # Default from CI environment
HEADERS = {"X-SisRua-Token": TOKEN}

ENDPOINTS = [
    ("/api/v1/health", "GET", {}),
    ("/api/v1/auth/check", "GET", {}),
    ("/api/v1/jobs/prepare", "POST", {"kind": "osm", "latitude": -21.7634, "longitude": -41.3235, "radius": 100}),
    ("/api/v1/tools/elevation/query", "POST", {"latitude": -21.7634, "longitude": -41.3235}),
]

def benchmark():
    print(f"Benchmarking API: {BASE_URL}")
    print("-" * 50)
    
    for path, method, body in ENDPOINTS:
        url = f"{BASE_URL}{path}"
        latencies = []
        
        # Warmup
        try:
            requests.request(method, url, json=body, headers=HEADERS, timeout=5)
        except Exception as e:
            print(f"Error during warmup for {path}: {e}")
            continue
            
        for _ in range(5):
            start = time.perf_counter()
            try:
                res = requests.request(method, url, json=body, headers=HEADERS, timeout=5)
                end = time.perf_counter()
                if res.status_code < 400:
                    latencies.append((end - start) * 1000)
                else:
                    print(f"Error {res.status_code} for {path}")
            except Exception as e:
                print(f"Exception for {path}: {e}")
        
        if latencies:
            avg = statistics.mean(latencies)
            std = statistics.stdev(latencies) if len(latencies) > 1 else 0
            print(f"{method} {path:30} | Avg: {avg:6.2f}ms | Std: {std:6.2f}ms")
        else:
            print(f"{method} {path:30} | FAILED")

if __name__ == "__main__":
    # Note: Make sure the server is running before executing this
    benchmark()
