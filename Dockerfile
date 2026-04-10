FROM python:3.11-slim

# Set up workspace
WORKDIR /opt/zwanski-bug-bounty

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scripts
COPY scripts/ ./scripts/

# Make scripts executable
RUN chmod +x ./scripts/*.sh ./scripts/*.py

# Set entrypoint to OAuth mapper
ENTRYPOINT ["python3", "./scripts/zwanski-oauth-mapper.py"]
CMD ["--menu"]
