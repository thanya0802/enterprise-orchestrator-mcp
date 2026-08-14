"""GitHub MCP server for issues, PRs, and commits."""

from __future__ import annotations

import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("github-knowledge")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO = os.environ.get("GITHUB_REPO", "owner/repo")
BASE_URL = "https://api.github.com"


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


@mcp.tool()
async def get_open_issues(label: str = "") -> str:
    """Get open issues from the repository, optionally filtered by label."""
    url = f"{BASE_URL}/repos/{REPO}/issues?state=open&per_page=10"
    if label:
        url += f"&labels={label}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers(), timeout=30.0)
        resp.raise_for_status()
    issues = resp.json()
    results: list[str] = []
    for issue in issues:
        if "pull_request" in issue:
            continue
        results.append(
            f"#{issue['number']} — {issue['title']}\n"
            f"  Author: {issue['user']['login']}\n"
            f"  Labels: {', '.join(l['name'] for l in issue['labels'])}\n"
            f"  Created: {issue['created_at'][:10]}\n"
            f"  Body: {(issue.get('body') or '')[:300]}"
        )
    return "\n\n".join(results) if results else "No open issues found."


@mcp.tool()
async def get_recent_prs(state: str = "open") -> str:
    """Get recent pull requests. State can be 'open', 'closed', or 'all'."""
    url = f"{BASE_URL}/repos/{REPO}/pulls?state={state}&per_page=10"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers(), timeout=30.0)
        resp.raise_for_status()
    prs = resp.json()
    results: list[str] = []
    for pr in prs:
        results.append(
            f"PR #{pr['number']} — {pr['title']}\n"
            f"  Author: {pr['user']['login']}\n"
            f"  Status: {pr['state']} | Merged: {pr.get('merged_at', 'No')}\n"
            f"  Branch: {pr['head']['ref']} → {pr['base']['ref']}\n"
            f"  Body: {(pr.get('body') or '')[:300]}"
        )
    return "\n\n".join(results) if results else "No PRs found."


@mcp.tool()
async def get_recent_commits(branch: str = "main", count: int = 10) -> str:
    """Get recent commits from a branch."""
    url = f"{BASE_URL}/repos/{REPO}/commits?sha={branch}&per_page={count}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_headers(), timeout=30.0)
        resp.raise_for_status()
    commits = resp.json()
    results: list[str] = []
    for commit in commits:
        results.append(
            f"{commit['sha'][:7]} — {commit['commit']['message'].split(chr(10))[0]}\n"
            f"  Author: {commit['commit']['author']['name']}\n"
            f"  Date: {commit['commit']['author']['date'][:10]}"
        )
    return "\n\n".join(results)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
