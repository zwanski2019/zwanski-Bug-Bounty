# Troubleshooting runbook (ZWANSKI.BB)

Use this page to resolve common operator issues quickly.

## 1) Watchdog cards stay DOWN

Symptoms:

- API/web/classifier show DOWN in Watchdog tab
- `/api/watchdog/status` has connection errors

Checks:

```bash
curl -s http://127.0.0.1:1337/api/watchdog/status
```

Fix order:

1. Start infra (`compose_up`)
2. Run `pnpm_install`
3. Start `api_dev`, `web_dev`, `classifier_dev`
4. Re-check status endpoint

## 2) Docker socket permission denied

Symptoms:

- `permission denied ... /var/run/docker.sock`

Fix:

```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker ps
```

Then restart dashboard from the same shell context.

## 3) Wrapper tools fail from ~/.local/bin

Symptoms:

- `oauth-mapper` or `subdomain-recon` cannot find local scripts/venv

Fix:

- Ensure wrapper scripts resolve symlinks via `readlink -f`
- Reinstall/sync wrappers if needed (`install.sh`)

## 4) Wiki sync fails

Symptoms:

- `failed to clone ... .wiki.git`

Fix:

1. Enable Wiki in repository settings
2. Create first wiki page once (initializes wiki backend repo)
3. Ensure push auth works
4. Run:

```bash
bash scripts/sync-github-wiki.sh --repo zwanski2019/zwanski-Bug-Bounty
```

## 5) Setup wizard does not appear

Checks:

- `GET /api/setup/checklist` returns `first_launch`
- If completed already, use **Config -> Run setup wizard**

## Escalation packet (for faster support)

Collect and attach:

- `GET /api/health`
- `GET /api/system/health`
- `GET /api/watchdog/status`
- latest task stderr from `/api/tasks/<id>`

## Related pages

- [Docs Home](README.md)
- [Watchdog integration](watchdog.md)
- [HTTP API](api.md)
