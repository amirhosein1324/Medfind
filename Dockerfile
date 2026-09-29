<<<<<<< HEAD
# --- MedFind API image ---
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

=======
FROM python:3.12-slim

WORKDIR /app

>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
<<<<<<< HEAD
COPY scripts ./scripts
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
=======
COPY migrations ./migrations
COPY alembic.ini .

ENV DEBUG=false

EXPOSE 8000
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
