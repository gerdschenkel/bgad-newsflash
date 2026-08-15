#!/usr/bin/env python3
"""
Publish the News Flash to GitHub, which triggers a Railway redeploy.

Exists because the daily task runs in a sandbox that has network access to
github.com but no access to the credential store on the host machine, so a
plain `git push` fails with "could not read Username for https://github.com".
This reads a repo scoped token instead.

Token lookup order:
  1. GITHUB_TOKEN environment variable
  2. .github-token in the repo root (gitignored, one line, nothing else)

Usage:
    python3 tools/publish.py "News Flash 2026-08-14"
    python3 tools/publish.py --check          # verify the token works, push nothing

The token never gets written into .git/config, so it cannot leak through a
committed file or a config dump.
"""

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(ROOT, ".github-token")
REPO = "github.com/gerdschenkel/bgad-newsflash.git"
BRANCH = "main"


def fail(msg, hint=None):
    print(f"publish failed: {msg}", file=sys.stderr)
    if hint:
        print(hint, file=sys.stderr)
    sys.exit(1)


def redact(text, token):
    return text.replace(token, "***") if token else text


def git(*args, token=None, check=True):
    r = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)
    out = redact((r.stdout + r.stderr).strip(), token)
    if check and r.returncode != 0:
        fail(f"git {' '.join(a for a in args if not a.startswith('https://'))}\n{out}")
    return r.returncode, out


def load_token():
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    if os.path.exists(TOKEN_FILE):
        tok = open(TOKEN_FILE, encoding="utf-8").read().strip()
        if tok:
            return tok
    fail(
        "no GitHub token found",
        "Create a fine grained token with Contents: read and write on the\n"
        "bgad-newsflash repo only, at\n"
        "  https://github.com/settings/personal-access-tokens/new\n"
        f"then save it as a single line in:\n  {TOKEN_FILE}",
    )


def main():
    token = load_token()
    if not re.match(r"^(github_pat_|ghp_)[A-Za-z0-9_]+$", token):
        fail("the token in .github-token does not look like a GitHub token")

    remote = f"https://x-access-token:{token}@{REPO}"

    if "--check" in sys.argv:
        rc, out = git("ls-remote", "--heads", remote, BRANCH, token=token, check=False)
        if rc != 0:
            fail("token rejected by GitHub\n" + out)
        print("token works, remote reachable")
        return

    message = sys.argv[1] if len(sys.argv) > 1 else "News Flash update"

    git("config", "core.fileMode", "false", token=token)
    git("add", "-A", token=token)

    rc, _ = git("diff", "--cached", "--quiet", token=token, check=False)
    if rc == 0:
        print("nothing to commit, pushing anything unpushed")
    else:
        git("commit", "-q", "-m", message, token=token)
        print(f"committed: {message}")

    rc, out = git("push", remote, f"HEAD:{BRANCH}", token=token, check=False)
    if rc != 0:
        fail("push rejected\n" + out)

    _, sha = git("rev-parse", "--short", "HEAD", token=token)
    print(f"pushed {sha} to {BRANCH}. Railway will redeploy in about a minute.")


if __name__ == "__main__":
    main()
