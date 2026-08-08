#!/usr/bin/env python3
"""Where the flow library lives.

The skill ships a seed library inside its own directory, but flows are tied to a
specific person's phone (app set, language, device model), so the editable copy
belongs in the user's home, not in an installed plugin that gets overwritten on
update.

Resolution order:
    1. $IPHONE_AUTOMATION_HOME
    2. ~/.iphone-automation   (if it has been seeded — see init_home.py)
    3. the bundled seed library inside this skill  (read-only in practice)
"""

import os
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
BUNDLED_SCRIPTS = SKILL_ROOT / "action_scripts"


def home() -> Path:
    env = os.environ.get("IPHONE_AUTOMATION_HOME")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".iphone-automation"


def scripts_dir() -> Path:
    """The active flow library. User copy wins once it exists."""
    user = home() / "action_scripts"
    if (user / "meta.json").exists():
        return user
    return BUNDLED_SCRIPTS


def meta_path() -> Path:
    return scripts_dir() / "meta.json"


def log_path() -> Path:
    return home() / "runs" / "flow_log.jsonl"
