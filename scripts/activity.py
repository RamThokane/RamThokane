"""Write the user's latest public GitHub events into README.md between the activity markers."""
import json, os, re, urllib.request
from datetime import datetime, timezone

USER = os.environ["USERNAME"]
MAX = int(os.environ.get("MAX_LINES", "6"))
req = urllib.request.Request(
    f"https://api.github.com/users/{USER}/events/public?per_page=60",
    headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"},
)
events = json.load(urllib.request.urlopen(req))
events = [e for e in events if e["repo"]["name"].lower() != f"{USER}/{USER}".lower()]  # skip profile-repo noise
events.sort(key=lambda e: e["created_at"], reverse=True)

def repo(e):
    n = e["repo"]["name"]
    return f"[{n}](https://github.com/{n})"

def ago(ts):
    d = datetime.now(timezone.utc) - datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if d.days >= 1: return f"{d.days}d ago"
    h = d.seconds // 3600
    return f"{h}h ago" if h else f"{max(1, d.seconds // 60)}m ago"

def line(e):
    t, p = e["type"], e.get("payload", {})
    if t == "PushEvent":
        n = p.get("size") or len(p.get("commits", [])) or 1
        return f"🔨 Pushed {n} commit{'s' if n > 1 else ''} to {repo(e)}"
    if t == "CreateEvent" and p.get("ref_type") == "repository":
        return f"🆕 Created repository {repo(e)}"
    if t == "CreateEvent" and p.get("ref_type") == "branch":
        return f"🌿 Created branch `{p.get('ref')}` in {repo(e)}"
    if t == "PullRequestEvent":
        pr = p["pull_request"]; act = "Merged" if p.get("action") == "closed" and pr.get("merged") else p.get("action", "").capitalize()
        return f"🔀 {act} PR [#{pr['number']}]({pr['html_url']}) in {repo(e)}"
    if t == "IssuesEvent":
        i = p["issue"]; return f"🐛 {p.get('action','').capitalize()} issue [#{i['number']}]({i['html_url']}) in {repo(e)}"
    if t == "IssueCommentEvent":
        i = p["issue"]; return f"💬 Commented on [#{i['number']}]({i['html_url']}) in {repo(e)}"
    if t == "WatchEvent":   return f"⭐ Starred {repo(e)}"
    if t == "ForkEvent":    return f"🍴 Forked {repo(e)}"
    if t == "ReleaseEvent": return f"🚀 Released {p['release'].get('tag_name','')} in {repo(e)}"
    return None

lines, seen = [], set()
for e in events:
    l = line(e)
    if not l or l in seen: continue          # collapse repeated identical entries
    seen.add(l)
    lines.append(f"{len(lines)+1}. {l} <sub>· {ago(e['created_at'])}</sub>")
    if len(lines) == MAX: break
if not lines:
    lines = ["_Quiet on the public timeline right now. Probably heads-down in a private repo._"]

readme = open("README.md", encoding="utf-8").read()
new = re.sub(r"(<!--START_SECTION:activity-->).*?(<!--END_SECTION:activity-->)",
             lambda m: m.group(1) + "\n" + "\n".join(lines) + "\n" + m.group(2), readme, flags=re.S)
open("README.md", "w", encoding="utf-8").write(new)
print("\n".join(lines))
