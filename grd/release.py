"""Public build identity contains no provider settings or credentials."""

import json
import os
from pathlib import Path
import re
import subprocess


def release_info():
    result = json.loads(Path(__file__).with_name("release.json").read_text())
    commit = os.getenv("RENDER_GIT_COMMIT") or os.getenv("GRD_SOURCE_COMMIT", "")
    if not commit:
        try:
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1], text=True, stderr=subprocess.DEVNULL, timeout=2).strip()
        except (OSError, subprocess.SubprocessError):
            commit = ""
    result["commit"] = commit if re.fullmatch(r"[0-9a-f]{40}", commit) else "unreported"
    result["source_url"] = result["repository"] + "/tree/" + result["commit"] if result["commit"] != "unreported" else result["repository"] + "/tree/" + result["tag"]
    result["release_url"] = result["repository"] + "/releases/tag/" + result["tag"]
    return result
