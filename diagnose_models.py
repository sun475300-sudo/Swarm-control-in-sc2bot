import os
import google.generativeai as genai

def load_env():
    env_path = r"C:\Users\sun47\.openclaw\workspace\.env.jarvis"
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ[k] = v
        return True
    return False

def diagnose():
    load_env()
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    output_path = r"d:\Swarm-contol-in-sc2bot\model_diag.txt"
    
    with open(output_path, "w", encoding="utf-8") as f:
        if not api_key:
            f.write("Error: No API Key found.\n")
            return
        
        genai.configure(api_key=api_key)
        f.write(f"API Key: {api_key[:5]}...{api_key[-5:]}\n")
        
        f.write("\n--- Listing Available Models ---\n")
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    f.write(f"ID: {m.name}, Display: {m.display_name}\n")
        except Exception as e:
            f.write(f"Error listing models: {e}\n")

        test_models = ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-pro-latest"]
        f.write("\n--- Testing String-based Tool Support ---\n")
        for m in test_models:
            try:
                model = genai.GenerativeModel(
                    model_name=m,
                    tools=["google_search_retrieval"]
                )
                response = model.generate_content("오늘 서울 날씨 어때?", generation_config={"max_output_tokens": 100})
                f.write(f"SUCCESS [{m}] with string tool: {response.text.strip()[:50]}...\n")
            except Exception as e:
                f.write(f"FAILED  [{m}] with string tool: {e}\n")

    print(f"Results written to {output_path}")

if __name__ == "__main__":
    diagnose()
