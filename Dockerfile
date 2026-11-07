# Gunakan base image Python yang ringan dan stabil
FROM python:3.11-slim

# Mencegah penulisan file .pyc dan memastikan output log langsung dialirkan ke stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    U2NET_HOME=/root/.u2net

# Set direktori kerja aplikasi
WORKDIR /app

# Install dependensi sistem yang dibutuhkan untuk OpenCV dan healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Salin dan install dependensi Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download model ONNX silueta saat build agar image berstatus offline-ready dan start dalam hitungan milidetik
RUN python -c "from rembg import new_session; new_session('silueta')"

# Salin source code aplikasi
COPY main.py index.html ./

# Buka port 8000
EXPOSE 8000

# Healthcheck untuk memonitor ketersediaan aplikasi
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Jalankan server Uvicorn dengan multi-workers untuk menangani beban concurrent
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
