# ToothWise backend: FastAPI + YOLOv8/YOLOv12 ensemble + KNN recommender.
# Built for Hugging Face Spaces (Docker SDK, port 7860, runs as uid 1000),
# but works on any container host that sets $PORT.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=7860 \
    HOME=/home/user \
    YOLO_CONFIG_DIR=/tmp/Ultralytics \
    MPLCONFIGDIR=/tmp/matplotlib

# OpenCV / PyTorch runtime libraries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
WORKDIR /app

# CPU-only PyTorch first, so ultralytics does not pull the multi-GB CUDA
# build. Versions match the local development environment.
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
        torch==2.13.0 torchvision==0.28.0

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=user:user . .
RUN mkdir -p uploads app/ml/artifacts && chown -R user:user /app

USER user
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers --forwarded-allow-ips='*'"]
