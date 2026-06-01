import os
import re
import requests

TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = "Mestane"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

MERGED_BADGE = "![merged](https://img.shields.io/badge/merged-8250df?style=flat&logo=git-merge&logoColor=white)"
OPEN_BADGE   = "![pr](https://img.shields.io/badge/pr-238636?style=flat&logo=git-pull-request&logoColor=white)"
COMMIT_BADGE = "![commit](https://img.shields.io/badge/commit-1f6feb?style=flat&logo=git&logoColor=white)"

def get_pr_details(repo_name, number):
    url = f"https://api.github.com/repos/{repo_name}/pulls/{number}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("title", ""), data.get("html_url", ""), data.get("merged", False)
    url2 = f"https://api.github.com/repos/{repo_name}/issues/{number}"
    resp2 = requests.get(url2, headers=HEADERS)
    if resp2.status_code == 200:
        data = resp2.json()
        merged = data.get("pull_request", {}).get("merged_at") is not None
        return data.get("title", ""), data.get("html_url", ""), merged
    return "", "", False

def get_contributions():
    url = f"https://api.github.com/users/{USERNAME}/events/public"
    resp = requests.get(url, headers=HEADERS, params={"per_page": 100})
    resp.raise_for_status()

    repos = {}
    for event in resp.json():
        if event["type"] not in ("PushEvent", "PullRequestEvent"):
            continue
        repo_name = event["repo"]["name"]
        owner = repo_name.split("/")[0]
        if owner == USERNAME:
            continue

        if repo_name not in repos:
            repos[repo_name] = {
                "name": repo_name,
                "url": f"https://github.com/{repo_name}",
                "commits": [],
                "prs": [],
            }

        if event["type"] == "PushEvent":
            for commit in event["payload"].get("commits", [])[:2]:
                msg = commit["message"].split("\n")[0][:72]
                sha = commit["sha"][:7]
                commit_url = f"https://github.com/{repo_name}/commit/{commit['sha']}"
                entry = f"{COMMIT_BADGE} [`{sha}`]({commit_url}) {msg}"
                if entry not in repos[repo_name]["commits"]:
                    repos[repo_name]["commits"].append(entry)

        elif event["type"] == "PullRequestEvent":
            number = event["payload"].get("number")
            if not number:
                continue
            title, pr_url, merged = get_pr_details(repo_name, number)
            if not title or not pr_url:
                continue
            badge = MERGED_BADGE if merged else OPEN_BADGE
            entry = f"{badge} [#{number}]({pr_url}) {title[:72]}"
            if entry not in repos[repo_name]["prs"]:
                repos[repo_name]["prs"].append(entry)

    return list(repos.values())[:5]

def get_repo_description(full_name):
    url = f"https://api.github.com/repos/{full_name}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json().get("description") or ""
    return ""

def build_section(repos):
    if not repos:
        return "no recent public contributions found.\n"

    lines = []
    for repo in repos:
        desc = get_repo_description(repo["name"])
        short = f" — {desc}" if desc else ""
        lines.append(f"- **[{repo['name']}]({repo['url']})**{short}")

        for pr in repo["prs"][:2]:
            lines.append(f"  - {pr}")

        for commit in repo["commits"][:3]:
            lines.append(f"  - {commit}")

        lines.append("")

    return "\n".join(lines)

def update_readme(section_content):
    with open("README.md", "r") as f:
        content = f.read()

    pattern = r"(<!-- contributions-start -->).*?(<!-- contributions-end -->)"
    replacement = f"<!-- contributions-start -->\n{section_content}\n<!-- contributions-end -->"
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    with open("README.md", "w") as f:
        f.write(new_content)

    print("README.md updated.")

if __name__ == "__main__":
    repos = get_contributions()
    section = build_section(repos)
    update_readme(section)
