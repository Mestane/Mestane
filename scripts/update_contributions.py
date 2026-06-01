import os
import re
import requests

TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = "Mestane"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

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
                entry = f"[`{sha}`]({commit_url}) {msg}"
                if entry not in repos[repo_name]["commits"]:
                    repos[repo_name]["commits"].append(entry)

        elif event["type"] == "PullRequestEvent":
            payload = event["payload"]
            pr = payload.get("pull_request", {})
            title = pr.get("title", "")[:72] if pr.get("title") else ""
            number = pr.get("number", "")
            pr_url = pr.get("html_url", "")

            if not title or not number or not pr_url:
                continue

            entry = f"[#{number}]({pr_url}) {title}"
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
            lines.append(f"  - pr: {pr}")

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

