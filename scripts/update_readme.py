from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


USERNAME = os.getenv("GITHUB_USERNAME", "Mr-Rup")
TOKEN = os.getenv("GITHUB_TOKEN")

README_PATH = Path("README.md")

START_MARKER = "<!-- RECENT-ACTIVITY:START -->"
END_MARKER = "<!-- RECENT-ACTIVITY:END -->"

MAX_REPOSITORIES = 4


def github_request(url: str) -> list[dict]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        print(f"GitHub API returned HTTP {exc.code}: {exc.reason}")
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Unable to reach GitHub API: {exc.reason}")
        sys.exit(1)


def get_recent_repositories() -> list[dict]:
    url = (
        f"https://api.github.com/users/{USERNAME}/repos"
        "?per_page=100"
        "&sort=pushed"
        "&direction=desc"
        "&type=owner"
    )

    repositories = github_request(url)

    filtered = [
        repo
        for repo in repositories
        if not repo.get("fork", False)
        and not repo.get("archived", False)
        and not repo.get("disabled", False)
        and repo.get("name", "").lower() != USERNAME.lower()
    ]

    filtered.sort(
        key=lambda repo: repo.get("pushed_at") or "",
        reverse=True,
    )

    return filtered[:MAX_REPOSITORIES]


def clean_description(description: str | None, limit: int = 105) -> str:
    if not description:
        return "Active project under development."

    description = " ".join(description.split()).replace("|", "\\|")

    if len(description) <= limit:
        return description

    return description[: limit - 1].rstrip() + "…"


def format_date(timestamp: str | None) -> str:
    if not timestamp:
        return "Unknown"

    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return dt.strftime("%d %b %Y")


def create_activity_block(repositories: list[dict]) -> str:
    if not repositories:
        return (
            f"{START_MARKER}\n"
            "No recent public repository activity found.\n"
            f"{END_MARKER}"
        )

    lines = [
        START_MARKER,
        "",
        "| Repository | What I'm working on | Stack | Updated |",
        "| :--- | :--- | :---: | :---: |",
    ]

    for repo in repositories:
        name = repo["name"]
        url = repo["html_url"]
        description = clean_description(repo.get("description"))
        language = repo.get("language") or "Mixed"
        updated = format_date(repo.get("pushed_at"))

        lines.append(
            f"| **[{name}]({url})** | "
            f"{description} | "
            f"`{language}` | "
            f"{updated} |"
        )

    lines.extend(
        [
            "",
            "<sub>Updated automatically from recent public GitHub activity.</sub>",
            "",
            END_MARKER,
        ]
    )

    return "\n".join(lines)


def update_readme(activity_block: str) -> bool:
    if not README_PATH.exists():
        raise FileNotFoundError("README.md was not found.")

    content = README_PATH.read_text(encoding="utf-8")

    if START_MARKER not in content or END_MARKER not in content:
        raise ValueError(
            "README activity markers are missing. "
            "Add RECENT-ACTIVITY:START and RECENT-ACTIVITY:END."
        )

    start = content.index(START_MARKER)
    end = content.index(END_MARKER) + len(END_MARKER)

    updated_content = content[:start] + activity_block + content[end:]

    if updated_content == content:
        print("README is already up to date.")
        return False

    README_PATH.write_text(updated_content, encoding="utf-8")
    print("README recent activity section updated.")
    return True


def main() -> None:
    repositories = get_recent_repositories()
    activity_block = create_activity_block(repositories)
    update_readme(activity_block)


if __name__ == "__main__":
    main()