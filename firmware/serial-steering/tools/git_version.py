Import("env")

import subprocess

try:
    git_hash = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], text=True
    ).strip()
except (OSError, subprocess.CalledProcessError):
    git_hash = "unknown"

env.Append(CPPDEFINES=[("APP_GIT_HASH", '\\"' + git_hash + '\\"')])
