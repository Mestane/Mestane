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

def get_merged_prs():
    url = "https://api.github.com/search/issues"
    params = {
        "q": f"is:pr is:merged author:{USERNAME} -user:{USERNAME}",
        "sort": "updated",
        "order": "desc",
        "per_page": 8,  # last 6 merged PRs
    }
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    results = []
    for item in resp.json().get("items", []):
        repo_name = item["repository_url"].replace("https://api.github.com/repos/", "")
        results.append({
            "repo": repo_name,
            "entry": f"{MERGED_BADGE} [#{item['number']}]({item['html_url']}) {item['title'][:72]}",
        })
    return results

def get_open_prs():
    url = "https://api.github.com/search/issues"
    params = {
        "q": f"is:pr is:open author:{USERNAME} -user:{USERNAME}",
        "sort": "updated",
        "order": "desc",
        "per_page": 2,
    }
    resp = requests.get(url, headers=HEADERS, params=params)
    resp.raise_for_status()
    results = []
    for item in resp.json().get("items", []):
        repo_name = item["repository_url"].replace("https://api.github.com/repos/", "")
        results.append({
            "repo": repo_name,
            "entry": f"{OPEN_BADGE} [#{item['number']}]({item['html_url']}) {item['title'][:72]}",
        })
    return results

def get_recent_commits():
    url = f"https://api.github.com/users/{USERNAME}/events/public"
    resp = requests.get(url, headers=HEADERS, params={"per_page": 100})
    resp.raise_for_status()

    repos = {}
    for event in resp.json():
        if event["type"] != "PushEvent":
            continue
        repo_name = event["repo"]["name"]
        owner = repo_name.split("/")[0]
        if owner == USERNAME:
            continue
        if repo_name not in repos:
            repos[repo_name] = []
        for commit in event["payload"].get("commits", [])[:2]:
            msg = commit["message"].split("\n")[0][:72]
            sha = commit["sha"][:7]
            commit_url = f"https://github.com/{repo_name}/commit/{commit['sha']}"
            entry = f"{COMMIT_BADGE} [`{sha}`]({commit_url}) {msg}"
            if entry not in repos[repo_name]:
                repos[repo_name].append(entry)
    return repos

def get_repo_description(full_name):
    url = f"https://api.github.com/repos/{full_name}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json().get("description") or ""
    return ""

def build_section(merged_prs, open_prs, commit_repos):
    # repo başına grupla
    repos = {}

    for item in merged_prs:
        r = item["repo"]
        if r not in repos:
            repos[r] = {"merged": [], "open": [], "commits": []}
        repos[r]["merged"].append(item["entry"])

    for item in open_prs:
        r = item["repo"]
        if r not in repos:
            repos[r] = {"merged": [], "open": [], "commits": []}
        repos[r]["open"].append(item["entry"])

    for r, commits in commit_repos.items():
        if r not in repos:
            repos[r] = {"merged": [], "open": [], "commits": []}
        repos[r]["commits"] = commits[:3]

    if not repos:
        return "no recent public contributions found.\n"

    lines = []
    for repo_name, data in repos.items():
        desc = get_repo_description(repo_name)
        short = f" — {desc}" if desc else ""
        lines.append(f"- **[{repo_name}](https://github.com/{repo_name})**{short}")

        for pr in data["merged"]:
            lines.append(f"  - {pr}")
        for pr in data["open"]:
            lines.append(f"  - {pr}")
        for commit in data["commits"]:
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
    merged_prs = get_merged_prs()
    open_prs = get_open_prs()
    commit_repos = get_recent_commits()
    section = build_section(merged_prs, open_prs, commit_repos)
    update_readme(section)
