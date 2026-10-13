FROM python:3.12.14-slim AS runtime

LABEL org.opencontainers.image.source="https://github.com/Bhatta2006/Socrat"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=services/api/src:services/execution/src

WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir --require-hashes --requirement requirements.lock.txt

COPY alembic.ini ./
COPY services/api/migrations services/api/migrations
COPY services/api/src services/api/src
COPY services/execution/src services/execution/src
COPY content content
COPY scripts/content/build.py scripts/content/build.py
RUN python scripts/content/build.py

RUN addgroup --system --gid 10001 socrat \
    && adduser --system --uid 10001 --ingroup socrat socrat
USER 10001:10001

EXPOSE 8000
CMD ["uvicorn", "socrat.main:create_app", "--factory", "--app-dir", "services/api/src", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
