FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app

CMD ["sh", "-c", "alembic stamp head 2>/dev/null; alembic upgrade head; uvicorn app.main:app --host 0.0.0.0 --port 8000"]
