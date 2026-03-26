#!/usr/bin/env bash
# Interactive installer: clone this template, apply project identity, refresh lockfile.
# Usage:
#   curl -LsSf https://raw.githubusercontent.com/OWNER/REPO/main/setup.sh | bash
#   (Interactive prompts read from /dev/tty so they do not consume the script on stdin.)
#   curl ... | bash -s -- --help
#   SETUP_NONINTERACTIVE=1 SETUP_PROJECT_NAME="My App" SETUP_REPO_URL="https://github.com/me/repo.git" bash setup.sh
set -euo pipefail

# --- Template literals (must match repository contents before customization) ---
readonly TPL_PROJECT_NAME="Katesthe-core"
readonly TPL_CONTACT_NAME="Katesthe-core Dev Team"
readonly TPL_CONTACT_EMAIL="support@katesthe-core.com"
readonly TPL_CONTACT_URL="https://github.com/katesthe-core"
readonly TPL_PROFILING_EMAIL="admin@katesthe-core.com"
readonly TPL_PROJECT_DESCRIPTION='A Django REST Framework starter project with ready-to-use authentication, custom user management, and modular app structure.'
readonly TPL_PYPROJECT_NAME="drf-starter"
readonly TPL_PYPROJECT_DESCRIPTION="Add your description here"
readonly DEFAULT_CLONE_URL="https://github.com/Katestheimeno/Katesthe-core.git"

usage() {
  sed -n '1,80p' <<'EOF'
Usage: setup.sh [options]

Clone the template into the current directory, strip .git, apply branding and
pyproject metadata, then run `uv lock` when uv is available.

Options:
  --project-name NAME       Display / API project name (required in non-interactive mode)
  --pyproject-name SLUG     PEP 508 name (lowercase, hyphens). Default: derived from project name
  --pyproject-description S One-line description for pyproject.toml and config defaults
  --contact-name NAME       Defaults to "<project> Dev Team"
  --contact-email EMAIL
  --contact-url URL         e.g. https://github.com/your-org/your-repo
  --profiling-email EMAIL   Default: admin@<domain of contact email>
  --repo-url URL            Git clone URL (default: upstream template URL)
  --non-interactive, -y     Use env/flags only; do not prompt
  --help, -h                Show this help

Environment (same meaning as flags; flags override env):
  SETUP_PROJECT_NAME
  SETUP_PYPROJECT_NAME
  SETUP_PYPROJECT_DESCRIPTION
  SETUP_CONTACT_NAME
  SETUP_CONTACT_EMAIL
  SETUP_CONTACT_URL
  SETUP_PROFILING_EMAIL
  SETUP_REPO_URL
  SETUP_NONINTERACTIVE=1

Examples:
  ./setup.sh
  SETUP_NONINTERACTIVE=1 SETUP_PROJECT_NAME="Acme API" SETUP_PYPROJECT_NAME="acme-api" \
    SETUP_REPO_URL="https://github.com/acme/backend.git" ./setup.sh --non-interactive
EOF
}

# Empty or whitespace-only (bash 3.2–safe; do not use ${var// } — requires bash 4+).
is_blank() {
  case "${1-}" in *[![:space:]]*) return 1 ;; *) return 0 ;; esac
}

slugify_pyproject_name() {
  local s="${1:?}"
  s=$(printf '%s' "$s" | tr '[:upper:]' '[:lower:]')
  s=$(printf '%s' "$s" | tr ' _' '--')
  s=$(printf '%s' "$s" | tr -cd 'a-z0-9.-')
  # Collapse repeated hyphens
  s=$(printf '%s' "$s" | sed 's/-\{2,\}/-/g; s/^-\|-$//g')
  if [[ -z "$s" ]]; then
    printf '%s' "my-project"
    return
  fi
  printf '%s' "$s"
}

email_domain() {
  local e="${1:?}"
  if [[ "$e" == *@* ]]; then
    printf '%s' "${e#*@}"
  else
    printf '%s' "example.com"
  fi
}

parse_github_owner_repo() {
  # Sets REPO_OWNER REPO_NAME from git HTTPS or SSH URL, or owner/repo short form.
  local url="${1:?}"
  url="${url%.git}"
  if [[ "$url" =~ ^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)$ ]]; then
    REPO_OWNER="${BASH_REMATCH[1]}"
    REPO_NAME="${BASH_REMATCH[2]}"
    return 0
  fi
  if [[ "$url" =~ git@github.com:([^/]+)/([^/]+)$ ]]; then
    REPO_OWNER="${BASH_REMATCH[1]}"
    REPO_NAME="${BASH_REMATCH[2]}"
    return 0
  fi
  if [[ "$url" =~ github\.com/([^/]+)/([^/]+)$ ]]; then
    REPO_OWNER="${BASH_REMATCH[1]}"
    REPO_NAME="${BASH_REMATCH[2]}"
    return 0
  fi
  if [[ "$url" =~ github\.com:([^/]+)/([^/]+)$ ]]; then
    REPO_OWNER="${BASH_REMATCH[1]}"
    REPO_NAME="${BASH_REMATCH[2]}"
    return 0
  fi
  # Local filesystem clone (git clone /path/to/repo or file:///path)
  if [[ "$url" =~ ^file://(.*) ]]; then
    _path="${BASH_REMATCH[1]}"
    REPO_NAME=$(basename "$_path")
    REPO_OWNER="local"
    return 0
  fi
  if [[ "$url" =~ ^/ ]] || [[ "$url" =~ ^\. ]]; then
    REPO_NAME=$(basename "$url")
    REPO_OWNER="local"
    return 0
  fi
  return 1
}

prompt() {
  # With `curl ... | bash`, stdin is the script; `read` must use /dev/tty or it eats the script.
  local msg="$1"
  local default="${2:-}"
  local reply
  local _in=/dev/stdin
  [[ -r /dev/tty ]] && _in=/dev/tty
  if [[ -n "$default" ]]; then
    read -r -p "$msg [$default]: " reply < "$_in" || true
    if is_blank "$reply"; then
      printf '%s' "$default"
    else
      printf '%s' "$reply"
    fi
  else
    read -r -p "$msg: " reply < "$_in" || true
    printf '%s' "$reply"
  fi
}

# --- defaults from env ---
PROJECT_NAME="${SETUP_PROJECT_NAME:-}"
PYPROJECT_NAME="${SETUP_PYPROJECT_NAME:-}"
EXPLICIT_PYPROJECT=0
[[ -n "${SETUP_PYPROJECT_NAME:-}" ]] && EXPLICIT_PYPROJECT=1
PYPROJECT_DESCRIPTION="${SETUP_PYPROJECT_DESCRIPTION:-}"
CONTACT_NAME="${SETUP_CONTACT_NAME:-}"
CONTACT_EMAIL="${SETUP_CONTACT_EMAIL:-}"
CONTACT_URL="${SETUP_CONTACT_URL:-}"
PROFILING_EMAIL="${SETUP_PROFILING_EMAIL:-}"
REPO_URL="${SETUP_REPO_URL:-$DEFAULT_CLONE_URL}"
NONINTERACTIVE="${SETUP_NONINTERACTIVE:-0}"

# --- parse args ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --project-name)
      PROJECT_NAME="${2:?}"
      shift 2
      ;;
    --pyproject-name)
      PYPROJECT_NAME="${2:?}"
      EXPLICIT_PYPROJECT=1
      shift 2
      ;;
    --pyproject-description)
      PYPROJECT_DESCRIPTION="${2:?}"
      shift 2
      ;;
    --contact-name)
      CONTACT_NAME="${2:?}"
      shift 2
      ;;
    --contact-email)
      CONTACT_EMAIL="${2:?}"
      shift 2
      ;;
    --contact-url)
      CONTACT_URL="${2:?}"
      shift 2
      ;;
    --profiling-email)
      PROFILING_EMAIL="${2:?}"
      shift 2
      ;;
    --repo-url)
      REPO_URL="${2:?}"
      shift 2
      ;;
    --non-interactive|-y)
      NONINTERACTIVE=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ "$NONINTERACTIVE" == "1" ]]; then
  if [[ -z "$PROJECT_NAME" ]]; then
    echo "Non-interactive mode requires SETUP_PROJECT_NAME or --project-name" >&2
    exit 1
  fi
else
  echo "=== Project identity (template: ${TPL_PROJECT_NAME}) ==="
  if [[ -z "$PROJECT_NAME" ]]; then
    PROJECT_NAME=$(prompt "Project display name" "$TPL_PROJECT_NAME")
    [[ -z "$PROJECT_NAME" ]] && PROJECT_NAME="$TPL_PROJECT_NAME"
  fi
fi

# Pyproject slug: prompt (interactive), env/flag, or derive from display name
# (Nested if/else only — avoids if/elif edge cases in older bash.)
if [[ "$EXPLICIT_PYPROJECT" == "0" ]]; then
  if [[ "$NONINTERACTIVE" != "1" ]]; then
    _d=$(slugify_pyproject_name "$PROJECT_NAME")
    _r=$(prompt "Pyproject / package name (PEP 508)" "$_d")
    if ! is_blank "$_r"; then
      PYPROJECT_NAME=$(slugify_pyproject_name "$_r")
    else
      PYPROJECT_NAME="$_d"
    fi
  else
    PYPROJECT_NAME=$(slugify_pyproject_name "$PROJECT_NAME")
  fi
fi
if [[ -z "$PYPROJECT_NAME" ]]; then
  PYPROJECT_NAME=$(slugify_pyproject_name "$PROJECT_NAME")
fi
# Portable PEP 508-style name check (grep -E; avoids [[ =~ ]] differences across bash 3.2/4+/zsh).
if ! printf '%s\n' "$PYPROJECT_NAME" | grep -E -q '^[a-z0-9]([a-z0-9.-]*[a-z0-9])?$'; then
  echo "Invalid --pyproject-name / SETUP_PYPROJECT_NAME: use lowercase letters, digits, dots, hyphens (PEP 508)." >&2
  exit 1
fi

REPO_OWNER=""
REPO_NAME=""
if parse_github_owner_repo "$REPO_URL"; then
  :
else
  echo "Warning: could not parse owner/repo from SETUP_REPO_URL; README curl URL may be wrong." >&2
  REPO_OWNER="YOUR_ORG"
  REPO_NAME="YOUR_REPO"
fi

if [[ -z "$CONTACT_NAME" ]]; then
  if [[ "$NONINTERACTIVE" == "1" ]]; then
    CONTACT_NAME="${PROJECT_NAME} Dev Team"
  else
    CONTACT_NAME=$(prompt "Contact name for API docs" "${PROJECT_NAME} Dev Team")
    [[ -z "$CONTACT_NAME" ]] && CONTACT_NAME="${PROJECT_NAME} Dev Team"
  fi
fi

DEFAULT_EMAIL="support@${PYPROJECT_NAME}.local"
if [[ -z "$CONTACT_EMAIL" ]]; then
  if [[ "$NONINTERACTIVE" == "1" ]]; then
    CONTACT_EMAIL="$DEFAULT_EMAIL"
  else
    CONTACT_EMAIL=$(prompt "Contact email (API docs / examples)" "$DEFAULT_EMAIL")
    [[ -z "$CONTACT_EMAIL" ]] && CONTACT_EMAIL="$DEFAULT_EMAIL"
  fi
fi

DEFAULT_URL="https://github.com/${REPO_OWNER}/${REPO_NAME}"
if [[ -z "$CONTACT_URL" ]]; then
  if [[ "$NONINTERACTIVE" == "1" ]]; then
    CONTACT_URL="$DEFAULT_URL"
  else
    CONTACT_URL=$(prompt "Contact / repo URL" "$DEFAULT_URL")
    [[ -z "$CONTACT_URL" ]] && CONTACT_URL="$DEFAULT_URL"
  fi
fi

DOM=$(email_domain "$CONTACT_EMAIL")
if [[ -z "$PROFILING_EMAIL" ]]; then
  PROFILING_EMAIL="admin@${DOM}"
fi

if [[ -z "$PYPROJECT_DESCRIPTION" ]]; then
  if [[ "$NONINTERACTIVE" == "1" ]]; then
    PYPROJECT_DESCRIPTION="$TPL_PROJECT_DESCRIPTION"
  else
    PYPROJECT_DESCRIPTION=$(prompt "Short project description (pyproject + config defaults)" "$TPL_PROJECT_DESCRIPTION")
    [[ -z "$PYPROJECT_DESCRIPTION" ]] && PYPROJECT_DESCRIPTION="$TPL_PROJECT_DESCRIPTION"
  fi
fi

echo ""
echo "Using:"
echo "  PROJECT_NAME=$PROJECT_NAME"
echo "  PYPROJECT_NAME=$PYPROJECT_NAME"
echo "  CONTACT_NAME=$CONTACT_NAME"
echo "  CONTACT_EMAIL=$CONTACT_EMAIL"
echo "  CONTACT_URL=$CONTACT_URL"
echo "  CLONE_URL=$REPO_URL"
echo ""

# --- clone (do not use name TMPDIR — it overwrites the standard temp env var) ---
SETUP_CLONE_DIR="tmp-core-$$"
git clone "$REPO_URL" "$SETUP_CLONE_DIR"

rm -rf "${SETUP_CLONE_DIR:?}/.git"

shopt -s dotglob
mv "$SETUP_CLONE_DIR"/* .
shopt -u dotglob
rm -rf "$SETUP_CLONE_DIR"

# --- replace branding (longest strings first) ---
apply_perl_subst() {
  local old="$1"
  local new="$2"
  shift 2
  local f
  if ! command -v perl >/dev/null 2>&1; then
    echo "perl is required for setup substitutions; install perl or run replacements manually." >&2
    exit 1
  fi
  for f in "$@"; do
    [[ -f "$f" ]] || continue
    export O="$old"
    export N="$new"
    perl -i -0777 -pe 'BEGIN { $o = $ENV{O}; $n = $ENV{N} } s/\Q$o\E/$n/g' "$f"
  done
}

# Replace old->new per line unless line matches a pattern (avoids corrupting raw.githubusercontent.com URLs).
apply_perl_subst_skip_line_match() {
  local pattern="$1"
  local old="$2"
  local new="$3"
  shift 3
  local f
  export PATTERN="$pattern"
  export O="$old"
  export N="$new"
  for f in "$@"; do
    [[ -f "$f" ]] || continue
    perl -i -pe 'BEGIN { $p = $ENV{PATTERN}; $o = $ENV{O}; $n = $ENV{N} } $_ =~ /$p/ or s/\Q$o\E/$n/g' "$f"
  done
}

FILES=(
  ".env.local.example"
  ".env.prof.example"
  "env.docker.example"
  "config/settings/config.py"
  "schema.yml"
  "docs/db-primary-replica.md"
)

README_FILE="README.md"

for f in "${FILES[@]}" "$README_FILE"; do
  if [[ ! -f "$f" ]]; then
    echo "Warning: expected file missing (skipped): $f" >&2
  fi
done

apply_perl_subst "$TPL_CONTACT_NAME" "$CONTACT_NAME" "${FILES[@]}" "$README_FILE"
apply_perl_subst "$TPL_CONTACT_EMAIL" "$CONTACT_EMAIL" "${FILES[@]}" "$README_FILE"
apply_perl_subst "$TPL_CONTACT_URL" "$CONTACT_URL" "${FILES[@]}" "$README_FILE"
apply_perl_subst "$TPL_PROFILING_EMAIL" "$PROFILING_EMAIL" "${FILES[@]}" "$README_FILE"

# README: fix curl one-liner before project name replace (any org/repo in template).
NEW_README_URL="https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/main/setup.sh"
export U="$NEW_README_URL"
perl -i -pe 'BEGIN { $u = $ENV{U} } s{https://raw\.githubusercontent\.com/[^/\s]+/[^/\s]+/main/setup\.sh}{$u}g' "$README_FILE"
# Prefer bash (this script uses bash features); legacy README used `| sh`.
perl -i -pe 'if (/raw\.githubusercontent\.com.*setup\.sh/) { s/\|\s*sh\b/\| bash/ }' "$README_FILE"

apply_perl_subst "$TPL_PROJECT_NAME" "$PROJECT_NAME" "${FILES[@]}"
# README: do not change template repo name inside raw.githubusercontent.com lines
apply_perl_subst_skip_line_match "raw\\.githubusercontent\\.com" "$TPL_PROJECT_NAME" "$PROJECT_NAME" "$README_FILE"

# schema.yml default in ${PROJECT_NAME:-...}
apply_perl_subst "\${PROJECT_NAME:-${TPL_PROJECT_NAME}}" "\${PROJECT_NAME:-${PROJECT_NAME}}" "schema.yml"

# config.py / pyproject long description (two places in config)
apply_perl_subst "$TPL_PROJECT_DESCRIPTION" "$PYPROJECT_DESCRIPTION" "config/settings/config.py"

# pyproject.toml name + description via Python (escape-safe)
export SETUP_PY_NAME="$PYPROJECT_NAME"
export SETUP_PY_DESC="$PYPROJECT_DESCRIPTION"
export TPL_PN="$TPL_PYPROJECT_NAME"
export TPL_PD="$TPL_PYPROJECT_DESCRIPTION"
python3 <<'PY'
import os
from pathlib import Path

name = os.environ["SETUP_PY_NAME"]
desc = os.environ["SETUP_PY_DESC"]
tpl_n = os.environ["TPL_PN"]
tpl_d = os.environ["TPL_PD"]
path = Path("pyproject.toml")
text = path.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)
out = []
for line in lines:
    if line.startswith("name = "):
        out.append(f'name = "{name}"\n')
    elif line.startswith("description = "):
        d = desc.replace("\\", "\\\\").replace('"', '\\"')
        out.append(f'description = "{d}"\n')
    else:
        out.append(line)
path.write_text("".join(out), encoding="utf-8")
PY

# Refresh lockfile
if command -v uv >/dev/null 2>&1; then
  ( uv lock ) || echo "Warning: uv lock failed; run 'uv lock' in the project root." >&2
else
  echo "Note: uv not found in PATH; run 'uv lock' after installing uv." >&2
fi

echo ""
echo "Done. Next: copy an env file (e.g. cp .env.local.example .env.local), then follow README Quickstart."
