FROM docker:29-cli AS cli
FROM python:3.12.14-slim-bookworm
WORKDIR /app
COPY --from=cli /usr/local/bin/docker /usr/local/bin/docker
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir --require-hashes --requirement requirements.lock.txt
COPY services/api/src services/api/src
COPY services/execution/src services/execution/src
ENV PYTHONPATH=/app/services/api/src:/app/services/execution/src
CMD ["python", "-m", "runner.worker"]
