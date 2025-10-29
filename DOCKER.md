# Docker Deployment Guide

This guide provides detailed instructions for deploying the OCR Proofread web application using Docker.

## Quick Start

### Using Pre-built Image (Easiest)

```bash
# Pull and run the latest image from GitHub Container Registry
docker run -d -p 5000:5000 --name ocr-proofread ghcr.io/julowe/ocr-proofread:latest

# Access the application
open http://localhost:5000
```

### Building from Source

```bash
# Clone the repository
git clone https://github.com/julowe/ocr-proofread.git
cd ocr-proofread

# Start with Docker Compose
docker-compose up -d

# Access the application
open http://localhost:5000
```

## Automated Builds

Docker images are automatically built and published to GitHub Container Registry (GHCR) when:
- Code is pushed to the `main` branch (tagged as `latest`)
- Version tags are created (e.g., `v1.0.0`)
- Pull requests are opened (for testing, not published)

Images are available at: `ghcr.io/julowe/ocr-proofread:latest`

Multi-platform images are built for:
- `linux/amd64` (x86_64)
- `linux/arm64` (ARM64/Apple Silicon)

## Docker Image Details

The Docker image is built using best practices:

- **Multi-stage build**: Separates build dependencies from runtime, resulting in a smaller image
- **Slim base image**: Uses `python:3.12-slim` for minimal footprint
- **Non-root user**: Runs as user `ocruser` (UID 1000) for security
- **Health checks**: Built-in health monitoring
- **Optimized layers**: Cached dependency installation for faster rebuilds

## Configuration

### Environment Variables

The application accepts the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Host to bind to |
| `PORT` | `5000` | Port to listen on |
| `DEBUG` | `false` | Enable Flask debug mode |
| `PYTHONUNBUFFERED` | `1` | Enable unbuffered Python output |

### Docker Compose Configuration

The default `docker-compose.yml` includes:

- Port mapping: `5000:5000`
- Named volume for persistent uploads
- Resource limits (2 CPU, 2GB RAM)
- Automatic restart policy
- Health checks
- Logging configuration

### Custom Configuration File

To use a custom `config.yaml`:

```yaml
services:
  ocr-proofread-web:
    volumes:
      - ./my-config.yaml:/app/config.yaml:ro
```

## Deployment Scenarios

### Development Deployment

```bash
# Enable debug mode
docker-compose up

# View live logs
docker-compose logs -f
```

### Production Deployment

1. **Disable debug mode** in `docker-compose.yml`:
   ```yaml
   environment:
     - DEBUG=false
   ```

2. **Use a reverse proxy** (nginx, Traefik, Caddy) for SSL/TLS

3. **Set resource limits** based on workload

4. **Configure backups** for the upload volume

5. **Set up monitoring** using health check endpoints

### Example: Production with nginx

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  ocr-proofread-web:
    build: .
    environment:
      - DEBUG=false
      - HOST=0.0.0.0
      - PORT=5000
    volumes:
      - ./config.yaml:/app/config.yaml:ro
      - ocr-uploads:/app/uploads
    restart: unless-stopped
    networks:
      - internal
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 1G

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - ocr-proofread-web
    restart: unless-stopped
    networks:
      - internal

networks:
  internal:
    driver: bridge

volumes:
  ocr-uploads:
    driver: local
```

Run with:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Docker Commands Reference

### Building

```bash
# Build the image
docker build -t ocr-proofread:latest .

# Build with custom tag
docker build -t ocr-proofread:v1.0.0 .

# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 -t ocr-proofread:latest .
```

### Running

```bash
# Start with Docker Compose
docker-compose up -d

# Start in foreground (see logs)
docker-compose up

# Stop
docker-compose down

# Restart
docker-compose restart

# Stop and remove volumes
docker-compose down -v
```

### Running without Docker Compose

```bash
# Create a volume for uploads
docker volume create ocr-uploads

# Run the container
docker run -d \
  --name ocr-proofread \
  -p 5000:5000 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v ocr-uploads:/app/uploads \
  -e DEBUG=false \
  --restart unless-stopped \
  ocr-proofread:latest

# View logs
docker logs -f ocr-proofread

# Stop and remove
docker stop ocr-proofread
docker rm ocr-proofread
```

### Maintenance

```bash
# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f ocr-proofread-web

# Execute command in container
docker-compose exec ocr-proofread-web /bin/bash

# View resource usage
docker stats

# Inspect container
docker inspect ocr-proofread-web
```

## Using Pre-built Images

When images are published to GitHub Container Registry:

```bash
# Pull the image
docker pull ghcr.io/julowe/ocr-proofread:latest

# Run the pre-built image
docker run -d -p 5000:5000 ghcr.io/julowe/ocr-proofread:latest

# Or use in docker-compose.yml
services:
  ocr-proofread-web:
    image: ghcr.io/julowe/ocr-proofread:latest
    ports:
      - "5000:5000"
```

## Persistent Data

### Upload Volume

The application uses a named volume `ocr-uploads` for uploaded files:

```bash
# Inspect the volume
docker volume inspect ocr-uploads

# Backup the volume
docker run --rm -v ocr-uploads:/data -v $(pwd):/backup \
  alpine tar czf /backup/uploads-backup.tar.gz -C /data .

# Restore the volume
docker run --rm -v ocr-uploads:/data -v $(pwd):/backup \
  alpine tar xzf /backup/uploads-backup.tar.gz -C /data
```

### Configuration

Mount your own configuration file as read-only:

```yaml
volumes:
  - ./config.yaml:/app/config.yaml:ro
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose logs

# Check container status
docker ps -a

# Inspect container
docker inspect ocr-proofread-web
```

### Permission Issues

The container runs as UID 1000. For mounted directories:

```bash
# On Linux, adjust ownership
sudo chown -R 1000:1000 ./uploads
```

### Port Already in Use

```bash
# Find what's using port 5000
lsof -i :5000

# Use a different port
docker-compose down
# Edit docker-compose.yml to change port mapping
docker-compose up -d
```

### Out of Memory

Increase memory limits in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 4G
```

### Health Check Failing

The health check waits 40 seconds for the application to start. If it continues to fail:

```bash
# Check application logs
docker-compose logs -f

# Manually test the health check
docker-compose exec ocr-proofread-web \
  python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:5000').read())"
```

### Rebuild After Code Changes

```bash
# Rebuild and restart
docker-compose build
docker-compose up -d

# Or force rebuild
docker-compose up -d --build
```

## Security Considerations

1. **Non-root user**: The container runs as UID 1000, not root
2. **Read-only config**: Mount config.yaml as read-only (`:ro`)
3. **Resource limits**: Set CPU and memory limits to prevent DoS
4. **Network isolation**: Use Docker networks to isolate containers
5. **Regular updates**: Keep base images and dependencies updated
6. **Secrets management**: Use Docker secrets or environment variables for sensitive data
7. **SSL/TLS**: Use a reverse proxy (nginx) for HTTPS in production

## Performance Optimization

1. **Resource limits**: Adjust based on workload
2. **Volume drivers**: Use appropriate volume drivers for your storage
3. **Network mode**: Consider host networking for high throughput
4. **Image caching**: Use layer caching for faster builds
5. **Multi-stage builds**: Already implemented to minimize image size

## Monitoring

### Health Checks

The container includes a built-in health check:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' ocr-proofread-web

# View health check logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}}{{end}}' ocr-proofread-web
```

### Resource Monitoring

```bash
# Real-time stats
docker stats ocr-proofread-web

# Export metrics for monitoring systems
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

## Advanced Topics

### Custom Dockerfile

If you need to customize the Dockerfile:

```dockerfile
# Extend the existing image
FROM ocr-proofread:latest

# Add custom dependencies
RUN pip install --no-cache-dir custom-package

# Copy custom configuration
COPY custom-config.yaml /app/config.yaml
```

### Multi-container Setup

For high-availability or load balancing:

```yaml
version: '3.8'

services:
  ocr-proofread-web-1:
    build: .
    # ... configuration

  ocr-proofread-web-2:
    build: .
    # ... configuration

  load-balancer:
    image: nginx:alpine
    depends_on:
      - ocr-proofread-web-1
      - ocr-proofread-web-2
    # ... load balancing configuration
```

## Support

For issues or questions:
- Check the logs: `docker-compose logs -f`
- Review the [main README](../README.md)
- File an issue on GitHub
