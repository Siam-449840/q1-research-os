#!/usr/bin/env bash
# Q1 Research OS installer.
#   ./install.sh                 put `rosctl` on your PATH (~/.local/bin)
#   ./install.sh --with-tools    + install optional literature CLIs with uv (paper-search, PaperQA2, refchecker, bibvet, zotero-mcp)
#   ./install.sh --with-extras   + fetch pinned K-Dense scientific skills and claude-scholar, build a curated extra-skills folder
#   ./install.sh --global-skills + also copy the q1-* skills into ~/.claude/skills (Claude Code, all projects)
# Nothing is overwritten: existing files or skill folders are skipped with a message.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
DATA_DIR="${HOME}/.local/share/q1-research-os"
WITH_TOOLS=0; WITH_EXTRAS=0; GLOBAL_SKILLS=0
for arg in "$@"; do
  case "$arg" in
    --with-tools) WITH_TOOLS=1 ;;
    --with-extras) WITH_EXTRAS=1 ;;
    --global-skills) GLOBAL_SKILLS=1 ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

say() { printf '\033[1m==> %s\033[0m\n' "$*"; }

say "Checking Python (>= 3.9) and git"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' || { echo "Python 3.9+ required" >&2; exit 1; }
command -v git >/dev/null || { echo "git is required" >&2; exit 1; }

say "Linking rosctl into ${BIN_DIR}"
mkdir -p "${BIN_DIR}"
chmod +x "${HERE}/bin/rosctl.py"
if [ -e "${BIN_DIR}/rosctl" ] && [ "$(readlink "${BIN_DIR}/rosctl" || true)" != "${HERE}/bin/rosctl.py" ]; then
  echo "  ${BIN_DIR}/rosctl exists and points elsewhere; leaving it untouched"
else
  ln -sf "${HERE}/bin/rosctl.py" "${BIN_DIR}/rosctl"
fi
case ":${PATH}:" in *":${BIN_DIR}:"*) ;; *) echo "  Add to your shell profile:  export PATH=\"\$HOME/.local/bin:\$PATH\"" ;; esac

if [ "${WITH_TOOLS}" = 1 ]; then
  say "Installing optional literature tools with uv"
  command -v uv >/dev/null || { echo "uv not found: https://docs.astral.sh/uv/getting-started/installation/" >&2; exit 1; }
  for pkg in paper-search-mcp paper-qa academic-refchecker zotero-mcp-server; do
    uv tool install "${pkg}" || echo "  (skipped ${pkg}: install failed or already installed)"
  done
  BIBVET_COMMIT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["bibvet"]["commit"])' "${HERE}/tools.lock")"
  uv tool install "git+https://github.com/dipta007/bibvet@${BIBVET_COMMIT}" || echo "  (skipped bibvet)"
fi

if [ "${WITH_EXTRAS}" = 1 ]; then
  say "Fetching pinned third-party skill collections into ${DATA_DIR}/vendor"
  mkdir -p "${DATA_DIR}/vendor" "${DATA_DIR}/extra-skills"
  fetch() {  # name url commit
    local dir="${DATA_DIR}/vendor/$1"
    [ -d "${dir}/.git" ] || git clone --quiet --filter=blob:none "$2" "${dir}"
    git -C "${dir}" fetch --quiet origin "$3" 2>/dev/null || true
    git -C "${dir}" checkout --quiet "$3"
  }
  lock() { python3 -c 'import json,sys; d=json.load(open(sys.argv[1]))[sys.argv[2]]; print(d["url"], d["commit"])' "${HERE}/tools.lock" "$1"; }
  read -r KD_URL KD_COMMIT <<<"$(lock scientific-agent-skills)"
  read -r CS_URL CS_COMMIT <<<"$(lock claude-scholar)"
  fetch scientific-agent-skills "${KD_URL}" "${KD_COMMIT}"
  fetch claude-scholar "${CS_URL}" "${CS_COMMIT}"
  # Curated subset: enough for the whole pipeline without flooding the agent with 280+ skills.
  KD_SKILLS="literature-review citation-management hypothesis-generation experimental-design statistical-analysis statistical-power statsmodels scikit-learn shap exploratory-data-analysis scientific-visualization matplotlib seaborn scientific-writing peer-review scholar-evaluation scientific-critical-thinking venue-templates geopandas geomaster polars pymc uncertainty-and-units"
  CS_SKILLS="writing-anti-ai paper-self-review review-response results-analysis citation-verification publication-chart-skill"
  for s in ${KD_SKILLS}; do
    src="${DATA_DIR}/vendor/scientific-agent-skills/skills/${s}"
    [ -d "${src}" ] && [ ! -e "${DATA_DIR}/extra-skills/${s}" ] && cp -R "${src}" "${DATA_DIR}/extra-skills/${s}" || true
  done
  for s in ${CS_SKILLS}; do
    src="${DATA_DIR}/vendor/claude-scholar/skills/${s}"
    [ -d "${src}" ] && [ ! -e "${DATA_DIR}/extra-skills/${s}" ] && cp -R "${src}" "${DATA_DIR}/extra-skills/${s}" || true
  done
  echo "  Curated skills: $(ls "${DATA_DIR}/extra-skills" | wc -l | tr -d ' ') in ${DATA_DIR}/extra-skills (licenses: see vendor repos, both MIT at pinned commits)"
  echo "  Add to your shell profile:  export ROS_EXTRA_SKILLS=\"${DATA_DIR}/extra-skills\""
fi

if [ "${GLOBAL_SKILLS}" = 1 ]; then
  say "Copying q1-* skills into ~/.claude/skills"
  mkdir -p "${HOME}/.claude/skills"
  for s in "${HERE}"/skills/*/; do
    name="$(basename "${s}")"
    if [ -e "${HOME}/.claude/skills/${name}" ]; then echo "  skip ${name} (exists)"; else cp -R "${s}" "${HOME}/.claude/skills/${name}"; fi
  done
fi

say "Done. Verify with:  rosctl doctor   then   rosctl init ~/research/my-paper --domain agriculture"
