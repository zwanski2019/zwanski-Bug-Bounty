#!/usr/bin/env bash
set -euo pipefail

# Sync in-repo docs/wiki/* to the GitHub Wiki repo (<repo>.wiki.git)
# Usage:
#   scripts/sync-github-wiki.sh
#   scripts/sync-github-wiki.sh --repo zwanski2019/zwanski-Bug-Bounty

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_DIR="$ROOT_DIR/docs/wiki"
TMP_DIR="$ROOT_DIR/.tmp/wiki-sync"

REPO_SLUG=""
if [[ "${1:-}" == "--repo" ]]; then
  REPO_SLUG="${2:-}"
  if [[ -z "$REPO_SLUG" ]]; then
    echo "error: missing value for --repo" >&2
    exit 1
  fi
fi

if [[ ! -d "$DOCS_DIR" ]]; then
  echo "error: docs/wiki not found at $DOCS_DIR" >&2
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "error: git is required" >&2
  exit 1
fi

if [[ -z "$REPO_SLUG" ]]; then
  origin_url="$(git -C "$ROOT_DIR" remote get-url origin 2>/dev/null || true)"
  if [[ -z "$origin_url" ]]; then
    echo "error: cannot detect origin; pass --repo owner/name" >&2
    exit 1
  fi
  # Handles:
  # - git@github.com:owner/name.git
  # - https://github.com/owner/name.git
  REPO_SLUG="$(echo "$origin_url" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')"
fi

WIKI_URL="https://github.com/${REPO_SLUG}.wiki.git"

echo "[wiki-sync] Repo: $REPO_SLUG"
echo "[wiki-sync] Wiki URL: $WIKI_URL"
echo "[wiki-sync] Source: $DOCS_DIR"

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

if ! git clone "$WIKI_URL" "$TMP_DIR/wiki" >/dev/null 2>&1; then
  cat <<'EOF'
error: failed to clone wiki repository.
Make sure:
  1) GitHub Wiki is enabled in repository Settings -> Features -> Wikis
  2) You have push access (SSH/HTTPS auth configured)
EOF
  exit 1
fi

WIKI_WORKTREE="$TMP_DIR/wiki"

# Replace wiki content with docs/wiki markdown files.
find "$WIKI_WORKTREE" -mindepth 1 -maxdepth 1 ! -name ".git" -exec rm -rf {} +
cp -R "$DOCS_DIR"/. "$WIKI_WORKTREE"/

# GitHub Wiki expects Home.md as landing page.
if [[ ! -f "$WIKI_WORKTREE/Home.md" ]]; then
  if [[ -f "$WIKI_WORKTREE/README.md" ]]; then
    cp "$WIKI_WORKTREE/README.md" "$WIKI_WORKTREE/Home.md"
  else
    first_md="$(ls "$WIKI_WORKTREE"/*.md 2>/dev/null | head -n 1 || true)"
    if [[ -n "$first_md" ]]; then
      cp "$first_md" "$WIKI_WORKTREE/Home.md"
    fi
  fi
fi

git -C "$WIKI_WORKTREE" add .
if git -C "$WIKI_WORKTREE" diff --cached --quiet; then
  echo "[wiki-sync] No changes to publish."
  exit 0
fi

git -C "$WIKI_WORKTREE" commit -m "docs: sync wiki from docs/wiki"
git -C "$WIKI_WORKTREE" push origin master

echo "[wiki-sync] Wiki sync completed."
