#!/usr/bin/env python3
"""
Trim the News Flash archive to a rolling 30 day window.

The site kept every issue ever published. At roughly 160 KB of cover art plus
20 KB of HTML per day that is about 65 MB a year of near duplicate files in a
repo that is cloned fresh on every Railway deploy, so the archive is now capped.

What gets removed, from public/:
  issues/YYYY-MM-DD.html         dated before the cutoff
  assets/covers/YYYY-MM-DD.png   dated before the cutoff, including orphan
                                 covers that never had a matching issue

Nothing else in public/ is touched. Only files whose names are exactly a date
are ever considered, so assets such as bgad-logo.png and newsflash-banner.jpg
are structurally out of scope.

Removals are not destructive in practice: publish.py commits them, so any
pruned issue stays recoverable from git history with
    git show <sha>:public/issues/2026-08-13.html

Safety rails:
  - the newest issue is never removed, whatever its date, so a long gap in
    publishing can never empty the site
  - if the newest issue is more than two windows behind today the run aborts,
    which catches a wrong system clock without punishing a real backlog
  - --dry-run prints the plan and changes nothing

Usage:
    python3 tools/prune_archive.py              # prune, print what went
    python3 tools/prune_archive.py --dry-run    # show the plan only
    python3 tools/prune_archive.py --days 60    # override the window

Called automatically by tools/publish.py, so the daily task needs no extra step.
"""

import os
import re
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PUBLIC = os.path.join(ROOT, "public")
ISSUES = os.path.join(PUBLIC, "issues")
COVERS = os.path.join(PUBLIC, "assets", "covers")

RETENTION_DAYS = 30

DATED = re.compile(r"^(\d{4}-\d{2}-\d{2})\.(html|png)$")


def sydney_today():
    """Australia/Sydney is UTC+10, or UTC+11 during daylight saving
    (first Sunday in October to first Sunday in April).

    Kept in step with the same helper in make_cover.py: the cutoff has to match
    the date the issues are named with, or the window slips by a day."""
    now_utc = datetime.now(timezone.utc)
    y = now_utc.year

    def first_sunday(year, month):
        d = datetime(year, month, 1, tzinfo=timezone.utc)
        return d + timedelta(days=(6 - d.weekday()) % 7)

    dst_start = first_sunday(y, 10).replace(hour=16)   # 2am AEST
    dst_end = first_sunday(y, 4).replace(hour=16)      # 3am AEDT
    offset = 11 if (now_utc >= dst_start or now_utc < dst_end) else 10
    return (now_utc + timedelta(hours=offset)).date()


def dated_files(directory, suffix):
    """(date string, full path) for every YYYY-MM-DD.<suffix> file, newest first."""
    if not os.path.isdir(directory):
        return []
    found = []
    for name in os.listdir(directory):
        m = DATED.match(name)
        if m and m.group(2) == suffix:
            try:
                datetime.strptime(m.group(1), "%Y-%m-%d")
            except ValueError:
                continue  # something like 2026-13-45.png, leave it alone
            found.append((m.group(1), os.path.join(directory, name)))
    return sorted(found, reverse=True)


class ImplausibleDate(Exception):
    """Today looks wrong relative to the archive, so pruning is not safe."""


def plan(days=RETENTION_DAYS, today=None):
    """Files to remove, oldest first. Pure, so it can be tested without deleting."""
    today = today or sydney_today()
    cutoff = today - timedelta(days=days - 1)  # keep `days` calendar days including today

    issues = dated_files(ISSUES, "html")
    newest_issue = issues[0][0] if issues else None

    # Counting files is the wrong rail here: a real backlog after a week of
    # missed runs removes plenty of files and is perfectly correct. The failure
    # actually worth catching is a wrong clock, which shows up as today being
    # implausibly far ahead of the most recent issue.
    if newest_issue:
        lag = (today - datetime.strptime(newest_issue, "%Y-%m-%d").date()).days
        if lag > days * 2:
            raise ImplausibleDate(
                f"newest issue is {newest_issue}, {lag} days before today ({today}), "
                f"which is more than two {days} day windows. Refusing to prune in case "
                f"the system clock is wrong."
            )

    doomed = []
    for date_str, path in issues + dated_files(COVERS, "png"):
        if date_str == newest_issue:
            continue  # never strand the site with no current issue
        if datetime.strptime(date_str, "%Y-%m-%d").date() < cutoff:
            doomed.append((date_str, path))
    return sorted(doomed), cutoff


def main():
    days = RETENTION_DAYS
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])
    dry = "--dry-run" in sys.argv

    try:
        doomed, cutoff = plan(days)
    except ImplausibleDate as e:
        print(f"prune aborted: {e}", file=sys.stderr)
        return 1

    if not doomed:
        print(f"archive within the {days} day window (nothing before {cutoff}), nothing to prune")
        return 0

    freed = 0
    for date_str, path in doomed:
        size = os.path.getsize(path)
        rel = os.path.relpath(path, ROOT)
        if dry:
            print(f"would remove  {rel}  {size / 1024:.0f} KB")
        else:
            os.remove(path)
            print(f"removed  {rel}  {size / 1024:.0f} KB")
        freed += size

    verb = "would free" if dry else "freed"
    print(f"{len(doomed)} files, {verb} {freed / 1024:.0f} KB, keeping {days} days from {cutoff}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
