"""
AI-HR Reddit digest

Read-only, once-a-day script that collects AI-related discussions from public
HR subreddits and writes a short digest with links back to the original threads.

- Read-only: application-only OAuth (no username/password, no posting, voting or messaging).
- Low volume: one listing request per subreddit plus one request per matching thread.
- No storage of user profiles; authors are not recorded.

Usage:
    python reddit_digest.py                 # writes output/YYYY-MM-DD.md and .json
    python reddit_digest.py --dry-run       # prints the plan without calling Reddit
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

SUBREDDITS = [
    "humanresources",
    "recruiting",
    "AskHR",
    "human_resources",
    "managers",
    "recruitinghell",
    "RecruitmentAI",
]

POSTS_PER_SUBREDDIT = 25      # top posts from the last 24 hours
COMMENTS_PER_POST = 3         # top-level comments kept per matching post
MAX_MATCHED_POSTS = 120       # hard ceiling so a run stays under ~130 requests
COMMENT_CHARS = 400           # trim comment text in the digest

AI_TERMS = [
    r"\bai\b", r"\ba\.i\.\b", r"artificial intelligence", r"chat ?gpt", r"\bgpt\b",
    r"copilot", r"claude", r"gemini", r"\bllm", r"generative", r"gen ?ai",
    r"\bagent(s|ic)?\b", r"automat", r"prompt", r"machine learning", r"chatbot",
]
AI_PATTERN = re.compile("|".join(AI_TERMS), re.IGNORECASE)

HR_FUNCTIONS = {
    "Recruiting & TA": ["recruit", "sourcing", "screen", "resume", "cv", "interview", "candidate", "ats", "hiring", "job description"],
    "Onboarding": ["onboard", "new hire", "orientation"],
    "Learning & Development": ["training", "learning", "l&d", "upskill", "course", "coaching"],
    "Performance": ["performance", "review", "feedback", "appraisal", "goals", "okr"],
    "Compensation & Benefits": ["compensation", "salary", "pay", "benefit", "bonus", "payroll"],
    "Employee Relations": ["investigation", "complaint", "grievance", "termination", "disciplin", "employee relations"],
    "HR Ops & Policy": ["policy", "handbook", "hris", "workday", "ticket", "faq", "self-service", "compliance"],
    "People Analytics": ["analytics", "survey", "engagement", "attrition", "turnover", "data"],
}


def classify(text: str) -> list[str]:
    lower = text.lower()
    tags = [name for name, words in HR_FUNCTIONS.items() if any(w in lower for w in words)]
    return tags or ["General"]


def is_ai_related(*parts: str) -> bool:
    return any(AI_PATTERN.search(p or "") for p in parts)


def make_client():
    try:
        import praw  # noqa: WPS433 (import inside function so --dry-run works without it)
    except ImportError:
        sys.exit("PRAW is not installed. Run: pip install -r requirements.txt")

    missing = [k for k in ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT") if not os.getenv(k)]
    if missing:
        sys.exit(f"Missing environment variables: {', '.join(missing)}. Copy .env.example to .env and fill it in.")

    reddit = praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ["REDDIT_USER_AGENT"],
    )
    reddit.read_only = True
    return reddit


def collect(reddit) -> list[dict]:
    items: list[dict] = []
    for name in SUBREDDITS:
        for post in reddit.subreddit(name).top(time_filter="day", limit=POSTS_PER_SUBREDDIT):
            if len(items) >= MAX_MATCHED_POSTS:
                break
            if post.stickied or post.over_18:
                continue
            if not is_ai_related(post.title, post.selftext):
                continue

            post.comment_sort = "top"
            post.comments.replace_more(limit=0)
            comments = [
                c.body.strip()[:COMMENT_CHARS]
                for c in post.comments[:COMMENTS_PER_POST]
                if getattr(c, "body", None) and c.body not in ("[deleted]", "[removed]")
            ]
            text = f"{post.title}\n{post.selftext}"
            items.append({
                "subreddit": f"r/{name}",
                "title": post.title,
                "url": f"https://www.reddit.com{post.permalink}",
                "score": post.score,
                "num_comments": post.num_comments,
                "created_utc": dt.datetime.fromtimestamp(post.created_utc, dt.timezone.utc).isoformat(),
                "excerpt": (post.selftext or "").strip()[:600],
                "top_comments": comments,
                "hr_functions": classify(text + " " + " ".join(comments)),
            })
    items.sort(key=lambda x: (x["score"] + 2 * x["num_comments"]), reverse=True)
    return items


def write_outputs(items: list[dict], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    json_path = out_dir / f"{today}.json"
    md_path = out_dir / f"{today}.md"

    json_path.write_text(json.dumps({"date": today, "count": len(items), "items": items}, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [f"# AI in HR on Reddit — {today}", "", f"{len(items)} AI-related threads from {len(SUBREDDITS)} HR subreddits (last 24h).", ""]
    for i, it in enumerate(items, 1):
        lines += [
            f"## {i}. {it['title']}",
            f"{it['subreddit']} · {it['score']} points · {it['num_comments']} comments · {', '.join(it['hr_functions'])}",
            f"{it['url']}",
        ]
        if it["excerpt"]:
            lines += ["", "> " + it["excerpt"].replace("\n", " ")[:300]]
        for c in it["top_comments"]:
            lines += [f"- {c.replace(chr(10), ' ')[:200]}"]
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return md_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily read-only digest of AI discussions in HR subreddits.")
    parser.add_argument("--out", default="output", help="Output folder (default: output)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fetched, without calling Reddit")
    args = parser.parse_args()

    if args.dry_run:
        print(f"Would read top {POSTS_PER_SUBREDDIT} posts (last 24h) from: " + ", ".join(f"r/{s}" for s in SUBREDDITS))
        print(f"Max requests per run: ~{len(SUBREDDITS) + MAX_MATCHED_POSTS}")
        return

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    items = collect(make_client())
    md_path, json_path = write_outputs(items, Path(args.out))
    print(f"Saved {len(items)} threads → {md_path} and {json_path}")


if __name__ == "__main__":
    main()
