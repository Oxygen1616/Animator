# Animator: AI-powered whiteboard video explainer studio & agent API
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg curl git \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ANIMATOR_OUTPUT_DIR=/app/outputs

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY animator ./animator
COPY examples ./examples

RUN mkdir -p /app/outputs && chmod -R 777 /app/outputs

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=15s \
    CMD curl -f http://127.0.0.1:8000/api/health || exit 1

CMD ["python", "-m", "uvicorn", "animator.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
