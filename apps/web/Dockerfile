FROM node:24-alpine AS build
WORKDIR /app
ARG API_INTERNAL_URL=http://api:8000
ENV API_INTERNAL_URL=$API_INTERNAL_URL
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
RUN npm ci
COPY apps/web apps/web
RUN npm run build --workspace @socrat/web

FROM node:24-alpine AS runtime
LABEL org.opencontainers.image.source="https://github.com/Bhatta2006/Socrat"
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build /app/package.json /app/package-lock.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/apps/web ./apps/web
USER node
EXPOSE 3000
CMD ["npm", "run", "start", "--workspace", "@socrat/web"]
