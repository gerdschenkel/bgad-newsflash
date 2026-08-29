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


def read_text_tolerantly(path):
    """PowerShell writes UTF-16 with a BOM by default, Notepad adds a UTF-8 BOM,
    and redirects can leave trailing whitespace. Accept all of it."""
    raw = open(path, "rb").read()
    for bom, enc in ((b"\xff\xfe", "utf-16-le"), (b"\xfe\xff", "utf-16-be"),
                     (b"\xef\xbb\xbf", "utf-8-sig")):
        if raw.startswith(bom):
            return raw.decode(enc, errors="replace").lstrip("﻿").strip()
    return raw.decode("utf-8", errors="replace").strip()


def load_token():
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    if os.path.exists(TOKEN_FILE):
        tok = read_text_tolerantly(TOKEN_FILE)
        if tok in ("%t%", "$t"):
            fail(
                f"{TOKEN_FILE} contains the literal text {tok!r}, not a token",
                "The shell did not expand the variable. In PowerShell run:\n"
                '  $t = Read-Host "paste token"\n'
                f'  Set-Content -Path "{TOKEN_FILE}" -Value $t -NoNewline -Encoding ascii',
            )
        if tok:
            return tok
    fail(
        "no GitHub token found",
        "Create a fine grained token with Contents: read and write on the\n"
        "bgad-newsflash repo only, at\n"
        "  https://github.com/settings/personal-access-tokens/new\n"
        f"then save it as a single line in:\n  {TOKEN_FILE}",
    )


def prune():
    """Trim the archive to its rolling window. Never blocks a publish: a failure
    here means some old files linger, which matters far less than today's issue
    going out, so it is reported and stepped over."""
    script = os.path.join(ROOT, "tools", "prune_archive.py")
    if not os.path.exists(script):
        return
    r = subprocess.run([sys.executable, script], capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if out:
        print(out)
    if r.returncode != 0:
        print("continuing with the publish despite the prune failure", file=sys.stderr)


def main():
    token = load_token()
    if not re.match(r"^(github_pat_|ghp_)[A-Za-z0-9_]+$", token):
        fail("the token in .github-token does not look like a GitHub token")

    remote = f"https://x-access-token:{token}@{REPO}"

    if "--check" in sys.argv:
        # git ls-remote is not a real test: this repo is public, so a read
        # succeeds even with a token that cannot write. A dry run push does
        # exercise write permission without changing anything.
        rc, out = git("push", "--dry-run", remote, f"HEAD:{BRANCH}",
                      token=token, check=False)
        if rc == 0:
            print("token works and has write access, publishing will succeed")
            return
        if "403" in out or "denied" in out.lower():
            fail(
                "token is valid but cannot write, so pushes will be rejected",
                "Open https://github.com/settings/personal-access-tokens, click\n"
                "this token, and under Repository permissions set Contents to\n"
                '"Read and write", then Save. Metadata read alone is not enough,\n'
                "and read access looks fine here only because the repo is public.",
            )
        fail("dry run push failed\n" + out)

    message = sys.argv[1] if len(sys.argv) > 1 else "News Flash update"

    # Trim the archive to its rolling window before staging, so the removals
    # ride along in the same commit as the new issue rather than dangling as
    # uncommitted deletions. Pass --no-prune to publish an issue without it.
    if "--no-prune" not in sys.argv:
        prune()

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
