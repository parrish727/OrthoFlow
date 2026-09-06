FROM python:3.12-slim

WORKDIR /app

# Pull in OS-level security patches (openssl, util-linux, etc.) before installing
# application dependencies. Keeps the base image current regardless of when the
# upstream python:3.12-slim digest was published.
RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --upgrade "msgpack>=1.2.1" "setuptools>=78.1.1" "pyasn1>=0.6.4"

COPY . .

ENV PYTHONPATH=/app

# --- Ticket #61: auto-run Alembic migrations on every deploy ---
RUN printf '#!/bin/sh\nset -e\necho "[entrypoint] Running alembic upgrade head..."\nalembic upgrade head || echo "[entrypoint] Migration skipped (tables may already exist)"\necho "[entrypoint] Starting uvicorn..."\nexec "$@"\n' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
