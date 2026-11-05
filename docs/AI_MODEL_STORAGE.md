# AI Model Storage Architecture & Lifecycle Management

**Project:** Northstar — Indian Equity AI Quantitative Research & Paper-Trading Platform  
**Target:** Model Weight Checkpoints, Manifests, and Quantization Formats  

---

## 1. Physical Storage Topology

To maximize disk throughput and prevent system drive bloat on C: (Windows OS), model assets in Northstar follow a designated multi-tier layout:

```
D:\Algo trading\
├── models\
│   ├── saved\
│   │   ├── Fin-R1-q4_k_m.gguf          # 4.68 GB (4,683,073,664 bytes)
│   │   └── registry.json               # Checkpoint hashes & metadata
│   ├── Modelfile.fin-r1                # Ollama declarative build manifest
│   └── cache\                          # Temporary scratch cache
└── docs\
    └── LOCAL_AI_MACHINE_AUDIT.md       # Hardware baseline snapshot
```

In addition, Ollama maintains internal model reference pointers under:
`%USERPROFILE%\.ollama\models\manifests\`
and blob storage pointers linking to the local GGUF layer.

---

## 2. Checkpoint Provenance & Cryptographic Verification

| Field | Detail |
| :--- | :--- |
| **Model Name** | Fin-R1 7B Q4_K_M |
| **Origin URL** | `https://huggingface.co/Mungert/Fin-R1-GGUF/resolve/main/Fin-R1-q4_k_m.gguf` |
| **Hugging Face Commit** | `a2f39af9bfc3c49d129996e2e74c3bb5ad4e3a50` |
| **File Size** | 4,683,073,664 bytes (4.36 GiB / 4.68 GB) |
| **Quantization Format** | GGUF Q4_K_M (4-bit medium k-quant) |
| **Target Hardware Architecture** | NVIDIA Ada Lovelace / Blackwell mobile GPU architectures (Compute Capability 8.9 / 12.0) |

---

## 3. Storage Capacity Headroom Analysis

- **Host D: Drive Available Capacity:** ~250 GB free (NVMe high-speed SSD).
- **Fin-R1 Checkpoint Footprint:** 4.68 GB (<1.9% of free drive space).
- **Ollama System Directory Footprint:** ~1.6 GB for runtime binaries under `%LOCALAPPDATA%\Programs\Ollama\`.
- **Operating Margin:** Northstar can comfortably store Fin-R1 alongside multiple historical backtesting datasets and full NIFTY 500 tick logs without storage contention.
