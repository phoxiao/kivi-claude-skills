#!/usr/bin/env python3
"""Copy the bundled seed flows into the user's editable library.

Flows encode one person's phone — their app set, their language, their device
model — so they cannot live inside an installed plugin that a marketplace update
overwrites. This copies the seeds once into ~/.iphone-automation/action_scripts/
(or $IPHONE_AUTOMATION_HOME), after which that copy is the live library and the
bundle is only a reference.

Usage:
    init_home.py [--force]
"""

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from paths import BUNDLED_SCRIPTS, home  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing library (loses local anchor edits)")
    args = ap.parse_args()

    target = home() / "action_scripts"
    if target.exists() and not args.force:
        print(f"already seeded: {target}\n"
              f"this is now the live library; --force overwrites it and loses local edits")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(BUNDLED_SCRIPTS, target)
    print(f"seeded {target} from {BUNDLED_SCRIPTS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
