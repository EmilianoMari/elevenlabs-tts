FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .

# Environment
ENV PYTHONUNBUFFERED=1

EXPOSE 8005

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8005/health', timeout=5).raise_for_status()"

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8005"]
