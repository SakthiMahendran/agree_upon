# ----------------------------------------
# Dockerfile for AgreeUpon FastAPI Service
# ----------------------------------------

# 1️⃣ Use slim Python base image
FROM python:3.10-slim

# 2️⃣ Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

# 3️⃣ System dependencies (incl. for psycopg2, uvicorn, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
        git \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 4️⃣ Set working directory
WORKDIR /app

# 5️⃣ Copy requirements & install
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# 6️⃣ Copy source code
COPY . .

# 7️⃣ Ensure app starts with uvicorn on port 8000 (required by HF Spaces)
EXPOSE 8000

# 8️⃣ Run with Uvicorn –auto-reload can be disabled for prod if needed
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
