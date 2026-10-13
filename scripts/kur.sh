#!/usr/bin/env bash
# ============================================================
#  ŞEYH TUĞRUL — kurulum betiği (Linux / macOS)
#  Modeli SİSTEMİN İÇİNE kurar: API anahtarı yok, dış servis yok.
# ============================================================
set -e
cd "$(dirname "$0")/.."

echo "▸ 1/4 Python bağımlılıkları"
python3 -m pip install -r requirements.txt

echo "▸ 2/4 Yerel çıkarım motoru (llama-cpp-python, isteğe bağlı)"
# Ollama kullanacaksanız bu adımı atlayabilirsiniz.
python3 -m pip install llama-cpp-python || echo "  (llama-cpp-python kurulamadı — Ollama'yı kullanabilirsiniz)"

echo "▸ 3/4 Model dosyası (qwen2.5:7b — ~4.7 GB)"
if command -v ollama >/dev/null 2>&1; then
  echo "  Ollama bulundu: ollama pull qwen2.5:7b"
  ollama pull qwen2.5:7b || true
else
  python3 -m app.model_indir qwen2.5:7b || echo "  (indirme atlandı; models/ klasörüne kendi GGUF dosyanızı koyabilirsiniz)"
fi

echo "▸ 4/4 Uygulama başlatılıyor → http://localhost:8000"
echo "  (Arayüzde 'Dil Modeli Ayarları' panelinde 'Sistem içi model' bağlı görünmeli.)"
python3 -m app.main
