FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AUTOCITE_TRANSPORT=streamable-http \
    AUTOCITE_HOST=0.0.0.0 \
    AUTOCITE_ALLOW_REMOTE=1 \
    AUTOCITE_PORT=8000

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin autocite

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src

# Install with the exact dependency versions that CI tested, via the lock file.
RUN pip install --no-cache-dir uv \
    && uv export --frozen --no-dev --no-emit-project --format requirements.txt -o /tmp/requirements.txt \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && pip install --no-cache-dir --no-deps . \
    && pip uninstall -y uv \
    && rm /tmp/requirements.txt

USER autocite
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os, urllib.request; port = os.environ.get('PORT') or os.environ.get('AUTOCITE_PORT') or '8000'; urllib.request.urlopen('http://127.0.0.1:' + port + '/health', timeout=3)"

CMD ["autocite-mcp"]
