#!/usr/bin/env bash
# ============================================================
#  ŞEYH TUĞRUL — kurulum betiği (Linux / macOS)
#  Modeli SİSTEMİN İÇİNE kurar: API anahtarı yok, dış servis yok.
# ============================================================
set -e
cd "$(dirname "$0")/.."

echo "▸ 1/4 Python bağımlılıkları"
python3 -m pip install -r requirements.txt

echo "▸ 2/5 Tarayıcı modeli kütüphanesi (transformers.js + onnxruntime WASM)"
python3 -m scripts.vendor_indir || echo "  (yerel kopya kurulamadı — tarayıcı motoru CDN'den yüklenir)"

echo "▸ 3/5 Yerel çıkarım motoru (llama-cpp-python, isteğe bağlı)"
# Ollama kullanacaksanız bu adımı atlayabilirsiniz.
python3 -m pip install llama-cpp-python || echo "  (llama-cpp-python kurulamadı — Ollama'yı kullanabilirsiniz)"

echo "▸ 4/5 Model dosyası (qwen2.5:7b — ~4.7 GB)"
if command -v ollama >/dev/null 2>&1; then
  echo "  Ollama bulundu: ollama pull qwen2.5:7b"
  ollama pull qwen2.5:7b || true
else
  python3 -m app.model_indir qwen2.5:7b || echo "  (indirme atlandı; models/ klasörüne kendi GGUF dosyanızı koyabilirsiniz)"
fi

echo "▸ 5/5 Uygulama başlatılıyor → http://localhost:8000"
echo "  (Arayüzde 'Dil Modeli Ayarları' panelinde 'Sistem içi model' bağlı görünmeli.)"
python3 -m app.main
