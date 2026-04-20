# FILE: deployment/Dockerfile
# ===================================
# Multi-Stage Docker Build — FastAPI Backend
# ===================================
#
# MULTI-STAGE BUILDS:
#   Stage 1 (deps):   Installs Python packages. Has gcc, build tools.
#   Stage 2 (runtime): Copies only the installed packages. NO build tools.
#
#   Benefits:
#     - Smaller final image: ~1.2GB → ~600MB (no gcc, headers, pip cache)
#     - Security: fewer packages = smaller attack surface
#     - Faster deployment: smaller image pulls faster from registry
#
# LAYER CACHING:
#   Docker caches each instruction as a layer.
#   We copy requirements.txt BEFORE copying source code so that:
#     - If only source code changes → reuse the cached pip install layer
#     - If requirements.txt changes → reinstall dependencies
#
#   Without this separation, every code change would trigger a full
#   pip install (slow). With it, pip only runs when dependencies change.
#
# INTERVIEW TALKING POINT:
#   "I used a multi-stage build to keep the production image lean.
#   The build stage has all the compilers and build tools; the runtime
#   stage only has the compiled packages. This reduced the image size
#   by ~50% and improved security by removing unnecessary tools."


# ─── Stage 1: Build — Install Python dependencies ────────────────────────────
FROM python:3.11-slim AS deps

WORKDIR /build

# Install system libraries needed by OpenCV and psycopg2
# Combined into one RUN to reduce layer count
# --no-install-recommends prevents installing optional extras (saves ~200MB)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \               
    libpq-dev \         
    libglib2.0-0 \      
    libsm6 \            
    libxrender1 \       
    libxext6 \          
    curl \              
    && rm -rf /var/lib/apt/lists/*   

# Copy ONLY the requirements file first (exploit layer caching)
COPY backend/requirements.txt .

# Install packages into /usr/local (default Python paths)
# --no-cache-dir: don't cache wheel files (saves ~300MB in image)
RUN pip install --no-cache-dir -r requirements.txt


# ─── Stage 2: Runtime — Lean production image ────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed Python packages from the build stage
# This is the key step that makes the image lean: we get the compiled
# packages WITHOUT gcc, libpq-dev headers, or pip's cache
COPY --from=deps /usr/local/lib/python3.11/site-packages \
                 /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy the runtime system libs (shared objects) needed by packages
COPY --from=deps /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu
COPY --from=deps /lib/x86_64-linux-gnu /lib/x86_64-linux-gnu

# Copy backend source code
COPY backend/ .

# Expose the port FastAPI runs on
# EXPOSE is documentation — it doesn't actually publish the port.
# The actual port mapping is done in docker-compose.yml with "ports:"
EXPOSE 8000

# Health check: Docker uses this to know if the container is healthy.
# docker-compose's depends_on condition: service_healthy waits for this.
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Non-root user for security (don't run as root in production)
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Start the FastAPI server
# --host 0.0.0.0: listen on all interfaces (required inside Docker)
# --port 8000:    must match EXPOSE above and docker-compose ports
# --workers 2:    2 worker processes (set to CPU count in production)
# Remove --reload in production (it wastes CPU watching for file changes)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
