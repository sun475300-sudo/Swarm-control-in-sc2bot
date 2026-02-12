import requests
import json

def get_models():
    try:
        response = requests.get("http://127.0.0.1:8317/v1/models")
        if response.status_code == 200:
            models = response.json()
            print(json.dumps(models, indent=2))
        else:
            print(f"Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    get_models()
