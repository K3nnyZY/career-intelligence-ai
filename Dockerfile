FROM node:24-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY requirements.lock .
COPY logging.json .
COPY career_ai ./career_ai
COPY --from=frontend-build /app/career_ai/static ./career_ai/static
RUN pip install --no-cache-dir -c requirements.lock '.[api]'
EXPOSE 8000
CMD ["uvicorn", "career_ai.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--log-config", "logging.json"]
