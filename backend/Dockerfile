FROM python:3.11-slim

# System dependencies:
#   ffmpeg        — required by Manim for MP4 rendering
#   fonts-noto*   — Unicode fonts for Kannada, Hindi, Tamil, Telugu, Marathi labels
#   cairo/pango   — required by Manim for text rendering
#   pkg-config    — required to build some Manim dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    fonts-noto \
    fonts-noto-cjk \
    fonts-noto-extra \
    fonts-noto-ui-core \
    libcairo2-dev \
    libpango1.0-dev \
    pkg-config \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (includes manim)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# Create static directory for local file serving fallback
RUN mkdir -p /app/static

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
