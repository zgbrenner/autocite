FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AUTOCITE_TRANSPORT=streamable-http \
    AUTOCITE_HOST=0.0.0.0 \
    AUTOCITE_PORT=8000

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin autocite

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir .

USER autocite
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:' + __import__('os').environ.get('PORT', '8000') + '/health', timeout=3)"

CMD ["autocite-mcp"]
