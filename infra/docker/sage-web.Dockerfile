FROM node:24.13.0-alpine AS build

WORKDIR /src
ARG VITE_CLOUD_AUTH_REQUIRED=true
ENV VITE_CLOUD_AUTH_REQUIRED=$VITE_CLOUD_AUTH_REQUIRED
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM caddy:2.10.2-alpine

COPY infra/proxy/Caddyfile.private /etc/caddy/Caddyfile
COPY --from=build /src/dist /srv

EXPOSE 8080
