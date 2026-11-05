import requests
import json
import time

def test_fin_r1():
    print("[1] Probing Ollama version...")
    ver = requests.get("http://127.0.0.1:11434/api/version").json()
    print("    Version:", ver)

    print("\n[2] Probing Ollama tags...")
    tags = requests.get("http://127.0.0.1:11434/api/tags").json()
    for m in tags.get("models", []):
        print(f"    Model: {m.get('name')} | Size: {m.get('size') / (1024**3):.2f} GB")

    print("\n[3] Sending Financial Reasoning inference to fin-r1:7b-q4_k_m...")
    t0 = time.time()
    payload = {
        "model": "fin-r1:7b-q4_k_m",
        "prompt": "Explain how debt-to-equity ratio and interest coverage ratio are used in corporate financial health analysis in 2 concise sentences.",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096,
        }
    }
    resp = requests.post("http://127.0.0.1:11434/api/generate", json=payload, timeout=120)
    elapsed = time.time() - t0
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"\n[4] Inference Completed in {elapsed:.2f}s:")
        print("--- Fin-R1 Output ---")
        print(data.get("response", "").strip())
        print("---------------------")
        print("Eval count:", data.get("eval_count"), "tokens")
        print("Eval duration:", round(data.get("eval_duration", 0) / 1e9, 2), "s")
        if data.get("eval_duration"):
            tps = data.get("eval_count") / (data.get("eval_duration") / 1e9)
            print(f"Token generation speed: {tps:.2f} tokens/sec")
    else:
        print("Error:", resp.status_code, resp.text)

    print("\n[5] Checking active VRAM allocation in Ollama /api/ps:")
    ps = requests.get("http://127.0.0.1:11434/api/ps").json()
    for pm in ps.get("models", []):
        vram_mb = pm.get("size_vram", 0) / (1024**2)
        total_mb = pm.get("size", 0) / (1024**2)
        print(f"    Loaded Model: {pm.get('name')} | VRAM: {vram_mb:.1f} MB / {total_mb:.1f} MB | Processor: {pm.get('details', {}).get('format', 'GPU')}")

if __name__ == "__main__":
    test_fin_r1()
