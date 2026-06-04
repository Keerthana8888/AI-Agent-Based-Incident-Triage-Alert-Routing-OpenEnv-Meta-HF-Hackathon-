# ── Incident Triage & Alert Routing — OpenEnv Environment ──
# Python 3.11-slim, FastAPI backend on port 7860

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Expose FastAPI port (required by Hugging Face Spaces)
EXPOSE 7860

# Health check — HF Space gate requires /health to return 200
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')"

# Start FastAPI server
# backend/ is the working directory so all imports resolve correctly
WORKDIR /app/backend
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
