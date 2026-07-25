FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV DATABASE_URL=sqlite:////data/app.db
ENV UPLOAD_DIR=/data/uploads
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434
ENV OLLAMA_MODEL=qwen2.5:7b
ENV LLM_PROVIDER=ollama
ENV CORS_ORIGINS=http://localhost:5173,http://localhost:3000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
