"""Regenerates the activity block in README.md from the public GitHub API.

Stdlib only. Needs env: GH_USER, and optionally GITHUB_TOKEN (raises rate limit).
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER = os.environ.get("GH_USER", "girjashankar01")
TOKEN = os.environ.get("GITHUB_TOKEN")
README = Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!--START_ACTIVITY-->", "<!--END_ACTIVITY-->"
MAX_REPOS = 5
MSG_WIDTH = 46


def api(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{USER}-profile-readme",
            **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def when(iso):
    # absolute date, so the output only changes when there is a new commit
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%b %d")


def clip(text, width):
    text = text.splitlines()[0].strip()
    return text if len(text) <= width else text[: width - 1] + "…"


def latest_commits():
    repos = api(f"/users/{USER}/repos?sort=pushed&per_page=30&type=owner")
    rows = []
    for repo in repos:
        if repo["fork"] or repo["name"].lower() == USER.lower():
            continue  # skip forks and this profile repo (its bot commits are noise)
        commits = api(f"/repos/{USER}/{repo['name']}/commits?author={USER}&per_page=1")
        if not commits:
            continue
        c = commits[0]["commit"]
        rows.append((repo["name"], c["message"], c["author"]["date"]))
        if len(rows) == MAX_REPOS:
            break
    return rows


def build_block():
    user = api(f"/users/{USER}")
    rows = latest_commits()
    name_w = max((len(r[0]) for r in rows), default=4)
    lines = [
        f"girja@github:~$ git log --author={USER} --recent",
        *(f"{when(d)}  {n:<{name_w}}  {clip(m, MSG_WIDTH)}" for n, m, d in rows),
        "",
        "girja@github:~$ stats",
        f"public repos : {user['public_repos']}",
        f"followers    : {user['followers']}",
    ]
    return "```console\n" + "\n".join(lines) + "\n```"


def main():
    text = README.read_text(encoding="utf-8")
    block = f"{START}\n{build_block()}\n{END}"
    new = re.sub(f"{re.escape(START)}.*?{re.escape(END)}", lambda _: block, text, flags=re.S)
    if new != text:
        README.write_text(new, encoding="utf-8")
        print("README updated")
    else:
        print("no change")


if __name__ == "__main__":
    main()
