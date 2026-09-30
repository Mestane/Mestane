import os
import re
import requests

TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = "Mestane"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

MERGED_BADGE = (
    "![merged](https://img.shields.io/badge/"
    "merged-8250df?style=flat&logo=git-merge&logoColor=white)"
)

VISIBLE_PR_COUNT = 6


def get_merged_prs():
    """
    Get merged PRs authored by USERNAME and group them by repository.

    GitHub Search API has a maximum accessible result window of 1000
    results, so we paginate through up to 10 pages with 100 results each.
    """

    url = "https://api.github.com/search/issues"

    all_prs = []

    for page in range(1, 11):
        params = {
            "q": f"is:pr is:merged author:{USERNAME} -user:{USERNAME}",
            "sort": "updated",
            "order": "desc",
            "per_page": 100,
            "page": page,
        }

        resp = requests.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()

        items = resp.json().get("items", [])

        if not items:
            break

        for item in items:
            repo_name = item["repository_url"].replace(
                "https://api.github.com/repos/",
                ""
            )

            entry = (
                f"{MERGED_BADGE} "
                f"[#{item['number']}]({item['html_url']}) "
                f"{item['title'][:72]}"
            )

            all_prs.append(
                {
                    "repo": repo_name,
                    "entry": entry,
                    "updated_at": item.get("updated_at", ""),
                }
            )

        if len(items) < 100:
            break

    # Repo bazında grupla
    repos = {}

    for item in all_prs:
        repo_name = item["repo"]

        if repo_name not in repos:
            repos[repo_name] = []

        repos[repo_name].append(item)

    return repos


def get_repo_description(full_name):
    url = f"https://api.github.com/repos/{full_name}"

    resp = requests.get(url, headers=HEADERS)

    if resp.status_code == 200:
        return resp.json().get("description") or ""

    return ""


def build_section(merged_repos):
    if not merged_repos:
        return "no recent public contributions found.\n"

    lines = []

    for repo_name, prs in merged_repos.items():
        desc = get_repo_description(repo_name)
        short = f" — {desc}" if desc else ""

        lines.append(
            f"- **[{repo_name}](https://github.com/{repo_name})**{short}"
        )

        visible_prs = prs[:VISIBLE_PR_COUNT]
        hidden_prs = prs[VISIBLE_PR_COUNT:]

        # İlk 6 PR direkt görünür
        for pr in visible_prs:
            lines.append(f"  - {pr['entry']}")

        # 6'dan sonraki PR'lar dropdown içinde
        if hidden_prs:
            lines.append("")
            lines.append(
                f"  <details>"
            )
            lines.append(
                f"  <summary>Show more merged PRs "
                f"({len(hidden_prs)})</summary>"
            )
            lines.append("")

            for pr in hidden_prs:
                lines.append(f"  - {pr['entry']}")

            lines.append("")
            lines.append("  </details>")

        lines.append("")

    return "\n".join(lines)


def update_readme(section_content):
    with open("README.md", "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"(<!-- contributions-start -->).*?(<!-- contributions-end -->)"

    replacement = (
        f"<!-- contributions-start -->\n"
        f"{section_content}\n"
        f"<!-- contributions-end -->"
    )

    new_content = re.sub(
        pattern,
        replacement,
        content,
        flags=re.DOTALL,
    )

    with open("README.md", "w", encoding="utf-8") as f:
        f.write(new_content)

    print("README.md updated.")


if __name__ == "__main__":
    merged_repos = get_merged_prs()
    section = build_section(merged_repos)
    update_readme(section)
