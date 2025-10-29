# Multi-stage Dockerfile for OCR Proofreading Web Application
# Following Docker best practices: multi-stage build, minimal base image, layer optimization

# Build stage: Install dependencies and prepare application
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /build

# Install system dependencies required for building Python packages
# Combine RUN commands to minimize layers and clean up in same layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libxml2-dev \
        libxslt1-dev \
        libopenjp2-7-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker layer caching
# Dependencies change less frequently than application code
COPY requirements.txt .

# Create requirements file without desktop-only dependencies
# PyQt6 and pyinstaller are not needed for web application
RUN grep -v "PyQt6\|pyinstaller" requirements.txt > requirements-web.txt

# Install Python dependencies to a temporary location
RUN pip install --no-cache-dir --user -r requirements-web.txt

# Runtime stage: Minimal image with only runtime dependencies
FROM python:3.12-slim

# Set metadata labels following OCI image spec
LABEL org.opencontainers.image.title="OCR Proofread Web App"
LABEL org.opencontainers.image.description="Web application for proofreading, editing, and outputting hOCR formatted files from OCR processes"
LABEL org.opencontainers.image.source="https://github.com/julowe/ocr-proofread"
LABEL maintainer="julowe"

# Create non-root user for security best practices
# Running as non-root reduces security risks
RUN useradd -m -u 1000 -s /bin/bash ocruser

# Set working directory
WORKDIR /app

# Install only runtime system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libxml2 \
        libxslt1.1 \
        libopenjp2-7 \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /home/ocruser/.local

# Copy application code
COPY --chown=ocruser:ocruser ocr_proofread /app/ocr_proofread
COPY --chown=ocruser:ocruser run_web.py /app/
COPY --chown=ocruser:ocruser config.yaml /app/

# Create directory for temporary uploads with proper permissions
RUN mkdir -p /app/uploads && chown ocruser:ocruser /app/uploads

# Switch to non-root user
USER ocruser

# Add Python packages to PATH
ENV PATH=/home/ocruser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose Flask default port
EXPOSE 5000

# Health check to ensure application is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000').read()" || exit 1

# Run the web application
# Use exec form to ensure proper signal handling
CMD ["python", "run_web.py"]
