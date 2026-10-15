FROM node:24-bookworm-slim
WORKDIR /app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
# A dropped registry connection (ECONNRESET) is retried instead of failing the build.
ENV npm_config_fetch_retries=5     npm_config_fetch_retry_mintimeout=10000     npm_config_fetch_retry_maxtimeout=120000
RUN npm ci && npx playwright install --with-deps chromium
COPY scripts/explainer scripts/explainer
USER node
EXPOSE 8010
CMD ["node", "scripts/explainer/checker-server.mjs"]
