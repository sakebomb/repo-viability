"""Minimal GitHub REST client. Stdlib only."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


API = "https://api.github.com"


class GitHubError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class GitHub:
    def __init__(self, token: str | None = None):
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "repo-viability/0.1",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if extra:
            headers.update(extra)
        return headers

    def get(self, path: str, params: dict[str, Any] | None = None, extra_headers: dict[str, str] | None = None) -> Any:
        url = API + path
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        req = urllib.request.Request(url, headers=self._headers(extra_headers), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            raise GitHubError(f"GET {path} failed ({exc.code}): {body}", status=exc.code) from exc

    def repo(self, owner: str, name: str) -> dict:
        return self.get(f"/repos/{owner}/{name}")

    def contributors(self, owner: str, name: str, per_page: int = 30) -> list:
        try:
            data = self.get(
                f"/repos/{owner}/{name}/contributors",
                params={"per_page": per_page, "anon": "true"},
            )
            return data if isinstance(data, list) else []
        except GitHubError as exc:
            if exc.status in {204, 403, 404}:
                return []
            raise

    def stargazers(self, owner: str, name: str, per_page: int = 30) -> list:
        """Most recently starred accounts, including starred_at when GitHub provides it."""
        return self.get(
            f"/repos/{owner}/{name}/stargazers",
            params={"per_page": per_page},
            extra_headers={"Accept": "application/vnd.github.star+json"},
        )

    def user(self, login: str) -> dict:
        return self.get(f"/users/{login}")
