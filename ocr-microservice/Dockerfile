# ─── Stage 1: Builder ────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies first (better layer caching)
COPY package*.json ./
RUN npm ci --frozen-lockfile

# Copy source and compile
COPY tsconfig.json ./
COPY src/ ./src/
RUN npm run build

# ─── Stage 2: Production ─────────────────────────────────────────────────────
FROM node:22-alpine AS production

WORKDIR /app

ENV NODE_ENV=production

# Install only production dependencies
COPY package*.json ./
RUN npm ci --frozen-lockfile --omit=dev && \
    npm cache clean --force

# Copy compiled output from builder
COPY --from=builder /app/dist ./dist

# Create non-root user for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1

CMD ["node", "dist/server.js"]