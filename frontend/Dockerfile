# ═══════════════════════════════════════════════════════
# Edtronaut AI Coworker — Frontend Dockerfile
# Multi-stage: build React app → serve with Nginx
# ═══════════════════════════════════════════════════════

# ── Stage 1: Build ──
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files for layer caching
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# ── Stage 2: Serve ──
FROM nginx:alpine

# Custom Nginx config for SPA routing
RUN echo 'server { \
    listen 80; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
    try_files $uri $uri/ /index.html; \
    } \
    location /api { \
    proxy_pass http://backend:8000; \
    proxy_set_header Host $host; \
    proxy_set_header X-Real-IP $remote_addr; \
    } \
    }' > /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -q --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
