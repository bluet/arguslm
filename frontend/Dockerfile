# Stage 1: Build - Node.js build environment
FROM node:20-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Runtime - nginx serving static files
FROM nginx:alpine

# Remove default nginx config and copy custom configuration
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built application from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Set proper permissions for nginx user (already exists in alpine)
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx && \
    chmod -R 755 /usr/share/nginx/html

# Switch to non-root user
USER nginx

EXPOSE 80

# Health check - use 127.0.0.1 because localhost resolves to IPv6 in Alpine
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
