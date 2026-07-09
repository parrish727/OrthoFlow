FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

# --- Ticket #61: auto-run Alembic migrations on every deploy ---
RUN printf '#!/bin/sh\nset -e\necho "[entrypoint] Running alembic upgrade head..."\nalembic upgrade head || echo "[entrypoint] Migration skipped (tables may already exist)"\necho "[entrypoint] Starting uvicorn..."\nexec "$@"\n' > /entrypoint.sh && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
