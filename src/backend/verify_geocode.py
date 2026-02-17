import requests
import os

# Use the token from environment or a dummy one for local testing if needed
# Note: The backend generates a random one if not specified
TOKEN = os.environ.get("SISRUA_AUTH_TOKEN", "dummy_token_if_needed") 
BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_geocode(query):
    print(f"\nTesting geocode with query: '{query}'")
    try:
        headers = {"X-SisRua-Token": TOKEN}
        response = requests.get(f"{BASE_URL}/tools/geocode", params={"query": query}, headers=headers)
        if response.status_code == 200:
            print("Success:", response.json())
        else:
            print(f"Failed ({response.status_code}):", response.text)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    # Test cases
    test_geocode("-21.7634, -41.3235") # Lat/Lon
    test_geocode("K 216330 7528658")   # UTM
    test_geocode("Rio de Janeiro")      # Address (Nominatim)
    test_geocode("Invalid Location 123456789") # Expect 404
