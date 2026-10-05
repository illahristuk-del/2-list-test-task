FROM python:3.12-slim

# Don't buffer stdout/stderr (logs appear immediately) and don't write .pyc.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first, as a separate layer: this layer is rebuilt only
# when requirements.txt changes, so code edits don't trigger a full reinstall.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code after deps, so the expensive layer above stays cached.
COPY app ./app
COPY cli ./cli

# Run as a non-root user — a basic container-hardening good practice.
RUN useradd --create-home appuser
USER appuser

EXPOSE 8000

# Bind to 0.0.0.0 so the service is reachable from outside the container
# (127.0.0.1 inside a container would only be reachable from within it).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]