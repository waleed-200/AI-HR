# AI-HR

A once-a-day, read-only script that collects AI-related discussions from public HR subreddits and writes a short digest for HR professionals, with links back to every original thread.

Part of a personal research project on how HR professionals use AI in their daily work (recruiting, onboarding, L&D, performance, rewards, employee relations, HR operations, people analytics).

## What it does

- Reads the top 25 posts of the last 24 hours from 7 public subreddits: r/humanresources, r/recruiting, r/AskHR, r/human_resources, r/managers, r/recruitinghell, r/RecruitmentAI.
- Keeps only posts that mention AI (ChatGPT, Copilot, Claude, agents, automation, prompts…).
- Keeps the top 3 comments of each matching post, trimmed.
- Tags each thread by HR function and writes `output/YYYY-MM-DD.md` and `.json`.

## What it does not do

- No posting, commenting, voting, messaging or any write action. Application-only OAuth in read-only mode.
- No author usernames stored, no user profiling.
- No resale of Reddit data, no model training on Reddit data.
- Runs once a day, under ~130 API requests per run.

## Setup

```bash
git clone https://github.com/<you>/AI-HR.git && cd AI-HR && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env
```

Fill in `.env` with the client ID and secret from a "script" app at https://www.reddit.com/prefs/apps (available after Reddit approves API access), then:

```bash
python reddit_digest.py --dry-run && python reddit_digest.py
```

## License

MIT
