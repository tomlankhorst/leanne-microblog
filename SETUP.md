# Signal Microblog — Setup Guide

## How it works

```
You (Signal) → signal-cli-rest-api → Python bot → Claude AI
                                                        ↓
                                          save_post tool (if needed)
                                                        ↓
                                              GitHub repo (markdown)
                                                        ↓
                                          GitHub Actions → static site
```

You message the bot in natural language. Claude decides whether to save it as a post
or just reply conversationally. Photos are supported and stored alongside posts.

---

## What you'll need

- A dedicated phone number for the bot (SIM card or VoIP, e.g. Google Voice)
- A GitHub account + a new empty repo for the content
- An Anthropic API key (console.anthropic.com)
- Fly.io account (for the bot) — free tier works

---

## Step 1 — Create the content repo

1. Create a new GitHub repo (e.g. `yourname/microblog-content`), **public or private**
2. Create a `posts/` folder with a `.gitkeep` file inside it
3. Create a `posts/images/` folder with a `.gitkeep` file inside it
4. Copy `site/` from this project into the content repo
5. Copy `.github/` from this project into the content repo
6. Enable GitHub Pages: Settings → Pages → Source: `gh-pages` branch

---

## Step 2 — Set up signal-cli-rest-api

Run this locally first to link your Signal number:

```bash
docker run --rm -p 8080:8080 \
  -v $(pwd)/signal-data:/home/.local/share/signal-cli \
  bbernhard/signal-cli-rest-api:latest
```

Then link the bot to a Signal account (like Signal Desktop):

```
http://localhost:8080/v1/qrcodelink?device_name=microblog-bot
```

Scan the QR code from your primary Signal account (Settings → Linked Devices).
The bot is now linked to your number.

Stop the container. The `signal-data/` folder now has the linked state.

---

## Step 3 — Deploy signal-api to Fly.io

signal-api needs a persistent volume so its Signal state is preserved across restarts.

```bash
# Create a new Fly app for signal-api
flyctl launch --image bbernhard/signal-cli-rest-api:latest \
  --name signal-microblog-api --region ams --no-deploy

# Create a persistent volume
flyctl volumes create signal_data --size 1 --region ams

# Set env vars
flyctl secrets set MODE=native AUTO_RECEIVE_SCHEDULE="* * * * *"

# Add volume mount to fly.toml (add this section):
# [[mounts]]
#   source = "signal_data"
#   destination = "/home/.local/share/signal-cli"

# Copy existing signal-data into the volume
flyctl ssh sftp put signal-data/ /home/.local/share/signal-cli/

# Deploy
flyctl deploy
```

Note the signal-api URL: `https://signal-microblog-api.fly.dev`

---

## Step 4 — Deploy the bot to Fly.io

```bash
# From this repo root
flyctl launch --name signal-microblog-bot --region ams --no-deploy

# Set secrets
flyctl secrets set \
  PHONE_NUMBER="+31612345678" \
  ALLOWED_NUMBERS="+31698765432" \
  GITHUB_TOKEN="ghp_..." \
  GITHUB_REPO="yourname/microblog-content" \
  ANTHROPIC_API_KEY="sk-ant-..." \
  SIGNAL_API_URL="https://signal-microblog-api.fly.dev" \
  BOT_URL="https://signal-microblog-bot.fly.dev"

# Deploy
flyctl deploy
```

The bot will automatically register its webhook with signal-api on startup.

---

## Step 5 — Send your first message

Send a Signal message to the linked number. Try:

- `"Note: remember to buy oat milk"` → saved as note
- `"Today was interesting. I walked by the canal..."` → saved as diary
- `"Draft post: Why I switched to Signal"` → saved as blog post
- Just send a photo → Claude will caption and save it
- `"What did I write this week?"` → Claude looks through recent posts and replies

---

## Content repo structure

```
microblog-content/
├── posts/
│   ├── 2026-04-10-142300-a1b2c3.md
│   └── images/
│       └── 2026-04-10-142300-a1b2c3.jpg
├── site/
│   ├── build.py
│   ├── templates/
│   └── static/
└── .github/
    └── workflows/
        └── build-site.yml
```

Each post looks like:

```markdown
---
date: "2026-04-10T14:23:00"
type: diary
---

Today was a good day. Went to the market, bought flowers.
```

---

## Local development

```bash
cp .env.example .env
# fill in .env

docker-compose up
```

The bot runs at `http://localhost:8000`.
signal-api runs at `http://localhost:8080`.

To rebuild the site locally:
```bash
cd microblog-content   # your content repo
pip install markdown jinja2 pyyaml
python site/build.py
# open public/index.html
```
