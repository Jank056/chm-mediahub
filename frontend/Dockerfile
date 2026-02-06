FROM node:20-alpine AS builder

WORKDIR /app

# Build arg for API URL (baked in at build time)
ARG NEXT_PUBLIC_API_URL=http://localhost:8002
ARG NEXT_PUBLIC_CHATBOT_URL=http://localhost:8000
ARG NEXT_PUBLIC_RECAPTCHA_SITE_KEY=
ENV NEXT_PUBLIC_CHATBOT_URL=$NEXT_PUBLIC_CHATBOT_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_RECAPTCHA_SITE_KEY=$NEXT_PUBLIC_RECAPTCHA_SITE_KEY

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production image
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy built assets
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs && \
    chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
