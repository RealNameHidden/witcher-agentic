# Stage 1: turn the React/TypeScript source into static browser files.
FROM node:22-bookworm-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: run Python and serve the compiled UI from the same container.
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    FRONTEND_DIST=/app/frontend/dist
WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 witcher
COPY --from=frontend /build/frontend/dist ./frontend/dist/
USER witcher
EXPOSE 8000
CMD ["python", "-m", "witcher_magentic.server"]
