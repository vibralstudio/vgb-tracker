# VGB Tracker

Weekly Instagram performance analyzer for music marketing. Scrapes the latest posts from a set of music creator accounts, analyzes what's performing best using Claude AI, and emails a marketing blueprint update via SendGrid.

## What it does

1. Pulls the 10 most recent posts from each tracked account via the Apify Instagram scraper
2. Sends the data to Claude for analysis across 6 dimensions: performance summary, content format winners, caption/hook patterns, timing insights, per-account breakdown, and actionable recommendations
3. Saves a timestamped markdown report locally
4. Emails the full report to your inbox via SendGrid

## Tracked accounts

- @musicbylukas
- @ruffmusicofficial
- @omgadrian
- @nathanhodgson.ai

## Setup

**1. Install dependencies**
```bash
pip3 install -r requirements.txt
```

**2. Configure environment variables**
```bash
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Where to get it |
|----------|----------------|
| `APIFY_TOKEN` | [console.apify.com](https://console.apify.com) → Settings → Integrations |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `SENDGRID_API_KEY` | [app.sendgrid.com](https://app.sendgrid.com) → Settings → API Keys |

Also verify your sending email address in SendGrid under Settings → Sender Authentication before the first run.

**3. Run manually**
```bash
source .env && python3 analyze.py
```

## Automated weekly runs (macOS)

The included launchd plist runs the script every Monday at 9am. To install it:

```bash
# Copy the plist to LaunchAgents (edit API keys inside first)
cp com.vgbtracker.weekly.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.vgbtracker.weekly.plist
```

Unlike cron, launchd will catch up and run after wake if the Mac was asleep at the scheduled time.

**Run manually via launchd:**
```bash
launchctl start com.vgbtracker.weekly
```

**View logs:**
```bash
tail -f ~/vgb-tracker/launchd.log
```

**Disable:**
```bash
launchctl unload ~/Library/LaunchAgents/com.vgbtracker.weekly.plist
```

## Output

Reports are saved as `report_YYYY-MM-DD_HHMM.md` in the project directory and emailed to the configured address. Each report covers:

1. Performance summary — top posts with actual engagement numbers
2. Content format winners — which formats drive the most reach and engagement
3. Caption & hook patterns — what high-performing posts have in common
4. Posting timing insights
5. Account-by-account breakdown
6. 5 actionable recommendations for your own music marketing
