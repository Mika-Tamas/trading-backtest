FROM node:22-slim AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.12-slim AS cpp-builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake \
    && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY core/ ./core/
RUN cmake -S core -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build --target backtest_core --parallel


FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=cpp-builder /opt/venv /opt/venv
COPY --from=cpp-builder /app/build/backtest_core*.so ./build/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist
COPY backend/ ./backend/
COPY config.json ./

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
