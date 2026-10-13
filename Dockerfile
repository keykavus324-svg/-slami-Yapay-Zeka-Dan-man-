# ŞEYH TUĞRUL — model sistemin içinde (harici API/anahtar yok)
FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir llama-cpp-python

COPY . .
# Model dosyaları buraya bağlanır (docker-compose.yml'de ./models)
ENV TUGRUL_MODEL_DIZIN=/app/models
EXPOSE 8000
CMD ["python", "-m", "app.main"]
