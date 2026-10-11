FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render, Fly and Railway all inject the port to bind on. 8000 is the local default.
ENV PORT=8000
EXPOSE 8000

# Shell form so $PORT expands, and so migrations run before the first request.
# A deploy that serves traffic against an un-migrated database fails on every
# query, which is a confusing way to find out the release step was missing.
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
