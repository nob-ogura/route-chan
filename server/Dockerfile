# server/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
  && pip install --no-cache-dir gunicorn

COPY . /app/server

# PYTHONPATH を設定して、相対インポートが動作するようにする
ENV PYTHONPATH=/app

# Cloud Run は $PORT を注入する。JSON 形式の CMD では環境変数展開しないため、sh -c でラップ。
CMD ["sh", "-c", "exec gunicorn -b 0.0.0.0:$PORT -w 2 server.app:app"]
