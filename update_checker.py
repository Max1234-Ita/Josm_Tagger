import json
import re
import urllib.error
import urllib.parse
import urllib.request

from app_metadata import (
    APP_REPOSITORY_URL,
    GITHUB_REPOSITORY_NAME,
    GITHUB_REPOSITORY_OWNER,
)


GITHUB_API_BASE = "https://api.github.com"
GITHUB_REPO_API = f"{GITHUB_API_BASE}/repos/{GITHUB_REPOSITORY_OWNER}/{GITHUB_REPOSITORY_NAME}"
GITHUB_RELEASES_URL = f"{APP_REPOSITORY_URL}/releases"


def _fetch_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "JOSM-Tagger-Update-Checker",
        },
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def _version_key(version):
    if not isinstance(version, str):
        return ()
    cleaned = version.strip().lstrip("vV")
    numbers = re.findall(r"\d+", cleaned)
    return tuple(int(part) for part in numbers)


def get_latest_published_version():
    try:
        payload = _fetch_json(f"{GITHUB_REPO_API}/releases/latest")
        return _extract_release_payload(payload)
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
    tags = _fetch_json(f"{GITHUB_REPO_API}/tags?per_page=1")
    if tags:
        return _extract_tag_payload(tags[0])
    return None


def _extract_release_payload(payload):
    tag_name = payload.get("tag_name") or payload.get("name") or ""
    return {
        "source": "release",
        "version": tag_name,
        "url": payload.get("html_url") or GITHUB_RELEASES_URL,
        "title": payload.get("name") or tag_name,
        "notes": payload.get("body") or "",
        "published_at": payload.get("published_at") or payload.get("created_at") or "",
    }


def _extract_tag_payload(payload):
    tag_name = payload.get("name") or ""
    encoded_tag = urllib.parse.quote(tag_name, safe="")
    return {
        "source": "tag",
        "version": tag_name,
        "url": f"{APP_REPOSITORY_URL}/tree/{encoded_tag}",
        "title": tag_name,
        "notes": "",
        "published_at": "",
    }


def check_for_updates(current_version):
    try:
        published = get_latest_published_version()
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
            "current_version": current_version,
        }

    if not published:
        return {
            "status": "no_published_versions",
            "message": "No GitHub releases or tags were found for this repository.",
            "current_version": current_version,
            "releases_url": GITHUB_RELEASES_URL,
        }

    remote_version = published["version"]
    current_key = _version_key(current_version)
    remote_key = _version_key(remote_version)

    if not current_key or not remote_key:
        # If version keys can't be parsed, treat as up-to-date to avoid false positives
        # or errors, though _version_key should handle most cases gracefully.
        return {
            "status": "up_to_date",
            "current_version": current_version,
            "latest_version": remote_version,
            "url": published["url"],
            "source": published["source"],
            "message": "Version comparison failed, assuming up-to-date."
        }

    if remote_key > current_key:
        return {
            "status": "update_available",
            "current_version": current_version,
            "latest_version": remote_version,
            "url": published["url"],
            "title": published["title"],
            "notes": published["notes"],
            "source": published["source"],
            "published_at": published["published_at"],
        }
    elif current_key > remote_key:
        return {
            "status": "newer_than_available",
            "current_version": current_version,
            "latest_version": remote_version,
            "url": published["url"],
            "source": published["source"],
            "message": "Your installed version is newer than the latest available in the repository."
        }
    else: # current_key == remote_key
        return {
            "status": "up_to_date",
            "current_version": current_version,
            "latest_version": remote_version,
            "url": published["url"],
            "source": published["source"],
        }