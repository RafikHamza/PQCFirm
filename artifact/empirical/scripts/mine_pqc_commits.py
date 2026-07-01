#!/usr/bin/env python3
"""
PQCFirm GitHub Mining Script
================================
Mines GitHub repositories for PQC migration-related commits.
Searches for commits containing PQC-related keywords and extracts
metadata for defect taxonomy classification.

Usage:
    python mine_pqc_commits.py --token YOUR_GITHUB_TOKEN --output ../data/

Requirements:
    pip install requests
"""

import argparse
import json
import os
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package required. Install with: pip install requests")
    exit(1)

# =============================================================================
# Configuration
# =============================================================================

# Target repositories known to have PQC migration activity
TARGET_REPOS = [
    "wolfSSL/wolfssl",
    "Mbed-TLS/mbedtls",
    "open-quantum-safe/liboqs",
    "open-quantum-safe/oqs-provider",
    "aws/s2n-tls",
    "openssl/openssl",
    "pqcrypto/pqcrypto",  # Rust crate
    "espressif/esp-idf",
]

# PQC-related search keywords
PQC_KEYWORDS = [
    "kyber", "dilithium", "ml-kem", "ml-dsa",
    "post-quantum", "pqc", "liboqs",
    "FIPS 203", "FIPS 204", "FIPS203", "FIPS204",
    "lattice", "sphincs", "falcon",
    "quantum-safe", "quantum-resistant",
    "kem_encaps", "kem_decaps", "kem_keygen",
    "OQS_KEM", "OQS_SIG",
]

# Defect taxonomy categories for manual labeling
DEFECT_CATEGORIES = {
    "D1": "Buffer/key-size mismatch",
    "D2": "API rigidity (non-crypto-agile)",
    "D3": "Stack overflow / exhaustion",
    "D4": "Timing regression",
    "D5": "Memory fragmentation / OOM",
    "D6": "Side-channel exposure",
    "D7": "Error handling gaps",
    "D8": "Build/toolchain incompatibility",
    "D9": "Other",
}


# =============================================================================
# GitHub API Helpers
# =============================================================================

class GitHubMiner:
    """Mines GitHub for PQC-related commits and issues."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        })
        self.rate_limit_remaining = 5000

    def _request(self, url: str, params: dict = None) -> dict:
        """Make a rate-limited GitHub API request."""
        if self.rate_limit_remaining < 10:
            print("  [!] Rate limit low, sleeping 60s...")
            time.sleep(60)

        resp = self.session.get(url, params=params)
        self.rate_limit_remaining = int(resp.headers.get("X-RateLimit-Remaining", 5000))

        if resp.status_code == 403:
            reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
            sleep_sec = max(reset_time - int(time.time()), 60)
            print(f"  [!] Rate limited. Sleeping {sleep_sec}s...")
            time.sleep(sleep_sec)
            return self._request(url, params)

        resp.raise_for_status()
        return resp.json()

    def search_commits(self, repo: str, keyword: str, max_pages: int = 5) -> list:
        """Search for commits in a repo matching a keyword."""
        results = []
        for page in range(1, max_pages + 1):
            url = f"{self.BASE_URL}/search/commits"
            params = {
                "q": f"{keyword} repo:{repo}",
                "sort": "committer-date",
                "order": "desc",
                "per_page": 30,
                "page": page,
            }
            try:
                data = self._request(url, params)
                items = data.get("items", [])
                if not items:
                    break
                results.extend(items)
                time.sleep(2)  # Be nice to GitHub API
            except Exception as e:
                print(f"  [!] Error searching {repo} for '{keyword}': {e}")
                break
        return results

    def get_commit_diff(self, repo: str, sha: str) -> dict:
        """Get the diff/patch for a specific commit."""
        url = f"{self.BASE_URL}/repos/{repo}/commits/{sha}"
        try:
            return self._request(url)
        except Exception as e:
            print(f"  [!] Error getting diff for {sha}: {e}")
            return {}

    def search_issues(self, repo: str, keyword: str, max_pages: int = 3) -> list:
        """Search for issues/PRs related to PQC."""
        results = []
        for page in range(1, max_pages + 1):
            url = f"{self.BASE_URL}/search/issues"
            params = {
                "q": f"{keyword} repo:{repo} is:issue",
                "sort": "created",
                "order": "desc",
                "per_page": 30,
                "page": page,
            }
            try:
                data = self._request(url, params)
                items = data.get("items", [])
                if not items:
                    break
                results.extend(items)
                time.sleep(2)
            except Exception as e:
                print(f"  [!] Error searching issues in {repo}: {e}")
                break
        return results


# =============================================================================
# Commit Processing
# =============================================================================

def extract_commit_metadata(commit_item: dict, repo: str) -> dict:
    """Extract relevant metadata from a GitHub commit search result."""
    commit_data = commit_item.get("commit", {})
    return {
        "repo": repo,
        "sha": commit_item.get("sha", ""),
        "message": commit_data.get("message", ""),
        "author": commit_data.get("author", {}).get("name", "unknown"),
        "date": commit_data.get("author", {}).get("date", ""),
        "url": commit_item.get("html_url", ""),
        "files_changed": [],  # Populated later from diff
        "defect_category": "",  # For manual labeling
        "notes": "",  # For manual notes
    }


def deduplicate_commits(commits: list) -> list:
    """Remove duplicate commits by SHA."""
    seen = set()
    unique = []
    for c in commits:
        sha = c.get("sha", "")
        if sha and sha not in seen:
            seen.add(sha)
            unique.append(c)
    return unique


# =============================================================================
# Main Mining Pipeline
# =============================================================================

def mine_all_repos(miner: GitHubMiner, output_dir: str):
    """Run the full mining pipeline across all target repos."""
    os.makedirs(output_dir, exist_ok=True)
    all_commits = []
    all_issues = []

    for repo in TARGET_REPOS:
        print(f"\n{'='*60}")
        print(f"Mining: {repo}")
        print(f"{'='*60}")

        repo_commits = []
        repo_issues = []

        # Search commits for each keyword
        for keyword in PQC_KEYWORDS:
            print(f"  Searching commits for '{keyword}'...")
            commits = miner.search_commits(repo, keyword, max_pages=3)
            for c in commits:
                meta = extract_commit_metadata(c, repo)
                repo_commits.append(meta)

        # Search issues
        for keyword in ["post-quantum", "kyber", "pqc", "ml-kem"]:
            print(f"  Searching issues for '{keyword}'...")
            issues = miner.search_issues(repo, keyword, max_pages=2)
            for issue in issues:
                repo_issues.append({
                    "repo": repo,
                    "number": issue.get("number"),
                    "title": issue.get("title", ""),
                    "state": issue.get("state", ""),
                    "created_at": issue.get("created_at", ""),
                    "url": issue.get("html_url", ""),
                    "labels": [l.get("name", "") for l in issue.get("labels", [])],
                })

        # Deduplicate
        repo_commits = deduplicate_commits(repo_commits)
        print(f"  Found {len(repo_commits)} unique commits, {len(repo_issues)} issues")

        all_commits.extend(repo_commits)
        all_issues.extend(repo_issues)

        # Save per-repo results
        repo_name = repo.replace("/", "_")
        with open(os.path.join(output_dir, f"commits_{repo_name}.json"), "w", encoding="utf-8") as f:
            json.dump(repo_commits, f, indent=2)
        with open(os.path.join(output_dir, f"issues_{repo_name}.json"), "w", encoding="utf-8") as f:
            json.dump(repo_issues, f, indent=2)

    # Save combined results
    all_commits = deduplicate_commits(all_commits)
    print(f"\n{'='*60}")
    print(f"TOTAL: {len(all_commits)} unique commits, {len(all_issues)} issues")
    print(f"{'='*60}")

    with open(os.path.join(output_dir, "all_commits.json"), "w", encoding="utf-8") as f:
        json.dump(all_commits, f, indent=2)
    with open(os.path.join(output_dir, "all_issues.json"), "w", encoding="utf-8") as f:
        json.dump(all_issues, f, indent=2)

    # Generate labeling template (CSV for manual classification)
    with open(os.path.join(output_dir, "labeling_template.csv"), "w", encoding="utf-8", newline="") as f:
        f.write("sha,repo,date,message_first_line,defect_category,severity,notes\n")
        for c in all_commits:
            msg_line = c["message"].split("\n")[0].replace(",", ";").replace('"', "'")
            f.write(f'"{c["sha"][:8]}","{c["repo"]}","{c["date"]}","{msg_line}","","",""\n')

    print(f"\nResults saved to: {output_dir}")
    print(f"Labeling template: {os.path.join(output_dir, 'labeling_template.csv')}")
    print(f"\nDefect categories for labeling:")
    for code, desc in DEFECT_CATEGORIES.items():
        print(f"  {code}: {desc}")


# =============================================================================
# Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Mine GitHub for PQC migration commits")
    parser.add_argument("--token", required=True, help="GitHub personal access token")
    parser.add_argument("--output", default="../data/", help="Output directory for results")
    args = parser.parse_args()

    miner = GitHubMiner(args.token)
    mine_all_repos(miner, args.output)


if __name__ == "__main__":
    main()
