# Docker Deployment Guide

## Quick Start (Docker)

### Option 1: Using docker-compose (Recommended)

```bash
# Build the image
docker-compose build

# Run interactive mode
docker-compose run --rm zwanski-oauth-mapper

# Run with target URL
docker-compose run --rm -e TARGET_URL="https://target.com" zwanski-oauth-mapper --target https://target.com
```

### Option 2: Using Docker directly

```bash
# Build the image
docker build -t zwanski/oauth-mapper .

# Run interactive
docker run -it zwanski/oauth-mapper

# Run with target
docker run -it zwanski/oauth-mapper --target https://target.com

# Run with output mounted to host
docker run -it -v $(pwd)/output:/opt/zwanski-bug-bounty/output zwanski/oauth-mapper --target https://target.com --output /opt/zwanski-bug-bounty/output/findings.json
```

## Authentication with Docker

```bash
# With a bearer token
docker run -it zwanski/oauth-mapper --target https://target.com --token "YOUR_JWT_TOKEN"

# Or using environment variable
docker run -it -e BEARER_TOKEN="YOUR_JWT_TOKEN" zwanski/oauth-mapper --target https://target.com --token "$BEARER_TOKEN"
```

## Persistent Output

Create an output directory and mount it:

```bash
mkdir -p ./output
docker run -it -v $(pwd)/output:/opt/zwanski-bug-bounty/output \
  zwanski/oauth-mapper --target https://target.com \
  --output /opt/zwanski-bug-bounty/output/findings.json
```

## Docker Hub (Optional)

```bash
# Push to Docker Hub (requires account setup)
docker tag zwanski/oauth-mapper:latest yourusername/zwanski-oauth-mapper
docker push yourusername/zwanski-oauth-mapper
```

## Requirements

- Docker 20.10+
- docker-compose 1.29+ (for compose method)
- Network access to target OAuth endpoints

## Troubleshooting

**Container exits immediately:**
```bash
docker run -it zwanski/oauth-mapper --menu
```

**Permission denied on volumes:**
```bash
sudo chown -R $(id -u):$(id -g) ./output
```

**Cannot reach target:**
Ensure the target is accessible from the container's network context. Use `--network host` if needed (Linux only):
```bash
docker run -it --network host zwanski/oauth-mapper --target https://target.com
```
