FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    PORT=8000

WORKDIR /app

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && useradd --create-home --uid 10001 appuser

COPY --chown=appuser:appuser backend/app ./backend/app

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/api/health', timeout=3)"

CMD ["sh", "-c", "exec uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port ${PORT:-8000}"]
