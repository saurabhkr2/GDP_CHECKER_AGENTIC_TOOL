# Agentic DHF backend (Flask + LangGraph + LDAP auth)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code.
COPY . .

# Session artefacts live here; mount a volume to persist across restarts.
ENV WORKSPACE_DIR=/app/.agent_workspace
RUN mkdir -p /app/.agent_workspace

EXPOSE 5003

# Single worker: graph state uses LangGraph's in-process MemorySaver and a
# daemon thread per session, so the process must not be forked into many
# workers. Use threads for request concurrency instead.
CMD ["gunicorn", "--workers", "1", "--threads", "8", "--timeout", "600", \
     "--bind", "0.0.0.0:5003", "agentic_api:create_app()"]
