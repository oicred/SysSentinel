# ── Build stage ────────────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ──────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Non-root user for security (Cloud Run best practice)
RUN useradd --create-home syssentinel
USER syssentinel
WORKDIR /home/syssentinel/app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source
COPY --chown=syssentinel:syssentinel app/ ./

# Environment defaults (override at runtime via Cloud Run env vars or .env)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

EXPOSE 8080

# Run the FastAPI server
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
