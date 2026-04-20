#!/usr/bin/env sh
set -eu

REPO_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$REPO_ROOT"

usage() {
  cat <<'EOF'
Usage:
  scripts/setup_git_identity.sh "Public Name" "public-email@example.com"

Notes:
  - Set an explicit repo-local identity for this clone/worktree only.
  - Use a public-safe email. GitHub noreply is recommended for public repos.
  - If this repo already has a local identity configured, you may rerun the
    script without arguments to keep the current local values and reapply hooks.
EOF
}

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

name=${FA_GIT_NAME:-}
email=${FA_GIT_EMAIL:-}

if [ "$#" -eq 2 ]; then
  name=$1
  email=$2
elif [ "$#" -ne 0 ]; then
  usage >&2
  exit 1
fi

if [ -z "$name" ]; then
  name=$(git config --local --get user.name || true)
fi

if [ -z "$email" ]; then
  email=$(git config --local --get user.email || true)
fi

if [ -z "$name" ] || [ -z "$email" ]; then
  echo "setup_git_identity: missing repo-local identity." >&2
  usage >&2
  exit 1
fi

case "$email" in
  *@users.noreply.github.com)
    ;;
  *)
    echo "setup_git_identity: using $email" >&2
    echo "Prefer a public-safe email for this repo. GitHub noreply is recommended." >&2
    ;;
esac

git config --local user.name "$name"
git config --local user.email "$email"
git config --local user.useConfigOnly true
git config --local core.hooksPath .githooks

echo "Configured repo-local git identity for $REPO_ROOT"
echo "user.name=$name"
echo "user.email=$email"
echo "user.useConfigOnly=true"
echo "core.hooksPath=.githooks"
