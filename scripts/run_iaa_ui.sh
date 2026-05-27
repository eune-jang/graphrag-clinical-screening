#!/usr/bin/env bash
# Launch the Stage 1 IAA annotation UI.
#
# First-time setup:
#   pip install -e ".[iaa]"
#
# Usage:
#   bash scripts/run_iaa_ui.sh                    # default workspace ./iaa_workspace
#   bash scripts/run_iaa_ui.sh --port 8502        # custom port
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "ERROR: streamlit not installed. Run:  pip install -e '.[iaa]'" >&2
    exit 1
fi

exec streamlit run iaa_pipeline/streamlit_app.py "$@"
