FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Europe/Moscow

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tzdata curl \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN mkdir -p /app/data \
    && chmod +x /app/entrypoint.sh || true

EXPOSE 1030

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD curl -fsS http://127.0.0.1:1030/api/info/version || exit 1

CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "1030"]
