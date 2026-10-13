@echo off
REM ============================================================
REM  SEYH TUGRUL - kurulum betigi (Windows)
REM  Modeli SISTEMIN ICINE kurar: API anahtari yok, dis servis yok.
REM ============================================================
cd /d "%~dp0.."
echo [1/4] Python bagimliliklari
python -m pip install -r requirements.txt || goto :hata

echo [2/5] Tarayici modeli kutuphanesi (transformers.js + onnxruntime WASM)
python -m scripts.vendor_indir

echo [3/5] Yerel cikarim motoru (llama-cpp-python, istege bagli)
python -m pip install llama-cpp-python

echo [4/5] Model dosyasi (qwen2.5:7b ~4.7 GB)
where ollama >nul 2>nul
if %errorlevel%==0 (
  echo Ollama bulundu: ollama pull qwen2.5:7b
  ollama pull qwen2.5:7b
) else (
  python -m app.model_indir qwen2.5:7b
)

echo [5/5] Uygulama baslatiliyor - http://localhost:8000
python -m app.main
goto :eof

:hata
echo Kurulum sirasinda hata olustu.
exit /b 1
