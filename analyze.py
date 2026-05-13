#!/usr/bin/env python3
"""
VGB Tracker — pulls latest Instagram posts via Apify, analyzes with Claude,
and outputs a music marketing blueprint update as a markdown report.
"""

import os
import sys
from datetime import datetime
from apify_client import ApifyClient
import anthropic
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

ACCOUNTS = ["musicbylukas", "ruffmusicofficial", "omgadrian", "nathanhodgson.ai"]
POSTS_PER_ACCOUNT = 10


def scrape_instagram(apify_token: str) -> list[dict]:
    client = ApifyClient(apify_token)

    run_input = {
        "directUrls": [f"https://www.instagram.com/{u}/" for u in ACCOUNTS],
        "resultsType": "posts",
        "resultsLimit": POSTS_PER_ACCOUNT,
    }

    print(f"Scraping {POSTS_PER_ACCOUNT} posts each from: {', '.join(f'@{a}' for a in ACCOUNTS)}")
    print("Running Apify actor (this may take 1-3 minutes)...")

    run = client.actor("apify/instagram-scraper").call(run_input=run_input)

    posts = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    print(f"Collected {len(posts)} posts total\n")
    return posts


def format_posts_for_analysis(posts: list[dict]) -> str:
    by_account: dict[str, list] = {}
    for post in posts:
        owner = post.get("ownerUsername") or post.get("username") or "unknown"
        by_account.setdefault(owner, []).append(post)

    lines = []
    for account, acct_posts in by_account.items():
        lines.append(f"\n## @{account} ({len(acct_posts)} posts)\n")
        for i, p in enumerate(acct_posts, 1):
            likes = p.get("likesCount") or 0
            comments = p.get("commentsCount") or 0
            views = p.get("videoViewCount") or p.get("videoPlayCount") or 0
            post_type = (p.get("type") or "image").upper()
            timestamp = (p.get("timestamp") or "")[:10]
            caption = (p.get("caption") or "(no caption)").replace("\n", " ")[:250]
            shares = p.get("sharesCount") or 0

            line = (
                f"{i}. [{post_type}] {timestamp} | "
                f"Likes: {likes:,} | Comments: {comments:,}"
            )
            if views:
                line += f" | Views: {views:,}"
            if shares:
                line += f" | Shares: {shares:,}"
            line += f"\n   Caption: {caption}"
            lines.append(line)

    return "\n".join(lines)


def analyze_with_claude(posts_summary: str, anthropic_key: str) -> str:
    client = anthropic.Anthropic(api_key=anthropic_key)

    system = (
        "You are a music marketing strategist specializing in social media performance analysis. "
        "You analyze Instagram data from music creators to extract actionable insights. "
        "Your reports are direct, specific, and grounded in the actual numbers — no filler."
    )

    prompt = f"""Analyze this Instagram post data from music creators and produce a Marketing Blueprint Update.

ACCOUNTS ANALYZED: {', '.join(f'@{a}' for a in ACCOUNTS)}

--- POST DATA ---
{posts_summary}
--- END DATA ---

Write the report with these sections:

## 1. Performance Summary
Overall top posts across all accounts (cite the actual numbers). What engagement levels define "high performance" in this peer group?

## 2. Content Format Winners
Which formats (Reels, carousels, static images, videos) are driving the most engagement? Include averages where you can infer them.

## 3. Caption & Hook Patterns
What do the captions of high-performing posts have in common? Identify hooks, themes, lengths, or call-to-action styles that appear in winners vs. underperformers.

## 4. Posting Timing Insights
Any patterns in when top posts were published? Note if data is too sparse to draw conclusions.

## 5. Account-by-Account Breakdown
For each account: their strongest content angle, what's working, what isn't — 3 bullets max per account.

## 6. Actionable Recommendations for Your Music Marketing
5 specific, immediately actionable tactics derived directly from what's working in this peer group. Reference the data.

Be specific. Reference actual accounts and numbers. Prioritize insight over length."""

    print("Sending to Claude for analysis...")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text


def save_report(analysis: str, post_count: int) -> str:
    timestamp = datetime.now()
    filename = f"report_{timestamp.strftime('%Y-%m-%d_%H%M')}.md"

    header = (
        f"# VGB Music Marketing Blueprint Update\n"
        f"**Generated:** {timestamp.strftime('%B %d, %Y at %H:%M')}  \n"
        f"**Accounts:** {', '.join(f'@{a}' for a in ACCOUNTS)}  \n"
        f"**Posts analyzed:** {post_count} ({POSTS_PER_ACCOUNT} per account)\n\n"
        f"---\n\n"
    )

    path = os.path.join(os.path.dirname(__file__), filename)
    with open(path, "w") as f:
        f.write(header + analysis)

    return path


def send_email(report_content: str, report_path: str, post_count: int, sendgrid_key: str):
    date_str = datetime.now().strftime("%B %d, %Y")
    subject = f"VGB Weekly Instagram Report — {date_str}"

    body = (
        f"VGB Music Marketing Blueprint Update\n"
        f"Generated: {date_str}\n"
        f"Accounts: {', '.join(f'@{a}' for a in ACCOUNTS)}\n"
        f"Posts analyzed: {post_count}\n"
        f"Report saved to: {report_path}\n\n"
        f"{'=' * 60}\n\n"
        f"{report_content}"
    )

    message = Mail(
        from_email="vibralstudio@gmail.com",
        to_emails="vibralstudio@gmail.com",
        subject=subject,
        plain_text_content=body,
    )

    sg = SendGridAPIClient(sendgrid_key)
    response = sg.send(message)
    print(f"Email sent → vibralstudio@gmail.com (status {response.status_code})")


def main():
    apify_token = os.environ.get("APIFY_TOKEN")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    sendgrid_key = os.environ.get("SENDGRID_API_KEY")

    missing = []
    if not apify_token:
        missing.append("APIFY_TOKEN")
    if not anthropic_key:
        missing.append("ANTHROPIC_API_KEY")
    if not sendgrid_key:
        missing.append("SENDGRID_API_KEY")
    if missing:
        print(f"Error: missing environment variable(s): {', '.join(missing)}")
        print("Set them or copy .env.example to .env and export them.")
        sys.exit(1)

    posts = scrape_instagram(apify_token)

    if not posts:
        print("No posts returned. Check your Apify token and that the accounts are public.")
        sys.exit(1)

    posts_summary = format_posts_for_analysis(posts)
    analysis = analyze_with_claude(posts_summary, anthropic_key)
    report_path = save_report(analysis, len(posts))

    print(f"\nReport saved → {report_path}\n")
    send_email(analysis, report_path, len(posts), sendgrid_key)
    print("=" * 60)
    print(analysis[:1000] + ("...\n[truncated — open the report file for the full analysis]" if len(analysis) > 1000 else ""))


if __name__ == "__main__":
    main()
