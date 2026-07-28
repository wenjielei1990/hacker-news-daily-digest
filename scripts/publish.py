#!/usr/bin/env python3
"""Publish immutable Nanobot Hacker News reports to a GitHub Pages repository.

The script copies only rendered ``hn_news.html`` files. Raw stories, fetched
sources, prompts, and enriched JSON remain in the private Nanobot workspace.
Existing published snapshots are never removed, so a temporary local cleanup
cannot erase public history.
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z$")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)
UPDATED_RE = re.compile(r"<span>更新于\s+(.*?)</span>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class Report:
    timestamp: str
    source: Path
    title: str
    updated: str


def _text_match(pattern: re.Pattern[str], document: str, fallback: str) -> str:
    match = pattern.search(document)
    if not match:
        return fallback
    return html.unescape(re.sub(r"\s+", " ", match.group(1)).strip())


def discover_reports(source_dir: Path) -> list[Report]:
    """Return valid timestamped reports, newest first."""
    reports: list[Report] = []
    if not source_dir.is_dir():
        raise FileNotFoundError(f"Hacker News report directory not found: {source_dir}")

    for directory in source_dir.iterdir():
        if not directory.is_dir() or not TIMESTAMP_RE.fullmatch(directory.name):
            continue
        report_path = directory / "hn_news.html"
        if not report_path.is_file():
            continue
        document = report_path.read_text(encoding="utf-8")
        reports.append(
            Report(
                timestamp=directory.name,
                source=report_path,
                title=_text_match(TITLE_RE, document, "HN 每日精选"),
                updated=_text_match(UPDATED_RE, document, directory.name),
            )
        )
    return sorted(reports, key=lambda report: report.timestamp, reverse=True)


def copy_reports(reports: list[Report], site_dir: Path) -> None:
    """Copy reports and normalize links for their public timestamp directory."""
    site_dir.mkdir(parents=True, exist_ok=True)
    for report in reports:
        destination = site_dir / report.timestamp / "hn_news.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        document = report.source.read_text(encoding="utf-8")
        legacy_initialization = """      let initialCount = 10;
      try {
        initialCount = Number(localStorage.getItem("hnDigestVisibleCount"));
      } catch (_) {
        // Keep the compact default.
      }
      applyVisibleCount(initialCount);"""
        default_twenty_initialization = """      let initialCount = 20;
      try {
        const storedCount = Number(
          localStorage.getItem("hnDigestVisibleCountV3")
        );
        if ([10, 20].includes(storedCount)) initialCount = storedCount;
      } catch (_) {
        // Keep the all-20 default.
      }
      applyVisibleCount(initialCount);"""
        document = document.replace(
            legacy_initialization,
            default_twenty_initialization,
        )
        replacements = {
            'class="archive-link" href="index.html"': (
                'class="archive-link" href="../index.html"'
            ),
            "默认先看前 10，想多看时可切换到前 20。": (
                "默认显示前 20，也可以切换到前 10。"
            ),
            'data-count="10" aria-pressed="true"': (
                'data-count="10" aria-pressed="false"'
            ),
            'data-count="20" aria-pressed="false"': (
                'data-count="20" aria-pressed="true"'
            ),
            "当前显示前 10": "当前显示前 20",
            '<section class="story-list" data-visible-count="10">': (
                '<section class="story-list" data-visible-count="20">'
            ),
            '"hnDigestVisibleCount"': '"hnDigestVisibleCountV3"',
            '"hnDigestVisibleCountV2"': '"hnDigestVisibleCountV3"',
        }
        for old, new in replacements.items():
            document = document.replace(old, new)
        if destination.exists() and destination.read_text(encoding="utf-8") == document:
            continue
        destination.write_text(document, encoding="utf-8")


def render_index(reports: list[Report]) -> str:
    """Build the public archive page from deterministic report metadata."""
    cards = []
    for index, report in enumerate(reports):
        timestamp = html.escape(report.timestamp)
        badge = '<span class="badge">最新</span>' if index == 0 else ""
        cards.append(
            f"""
      <li class="report">
        <a href="./{timestamp}/hn_news.html">
          <span class="report-main">
            <span class="report-title">{html.escape(report.title)}</span>
            <span class="report-time" data-timestamp="{timestamp}">{html.escape(report.updated)}</span>
          </span>
          {badge}
          <span class="arrow" aria-hidden="true">→</span>
        </a>
      </li>"""
        )
    report_list = "\n".join(cards) or (
        '<li class="empty">还没有已发布的 Hacker News 简报。</li>'
    )
    report_count = len(reports)
    newest = reports[0].timestamp if reports else ""

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Hacker News 中文简报历史归档">
  <title>Hacker News 简报</title>
  <script>
    (() => {{
      const hour = new Date().getHours();
      document.documentElement.dataset.theme = hour >= 18 || hour < 7 ? "night" : "day";
    }})();
  </script>
  <style>
    :root {{
      color-scheme: light;
      --paper: #f5f3ed;
      --card: #fffefa;
      --ink: #1d252d;
      --muted: #6c747c;
      --line: #d9d6ce;
      --accent: #e85d2a;
      --shadow: rgba(31, 36, 40, .07);
    }}
    html[data-theme="night"] {{
      color-scheme: dark;
      --paper: #111713;
      --card: #1a221d;
      --ink: #e0e7e1;
      --muted: #9ba79f;
      --line: #303c34;
      --shadow: rgba(0, 0, 0, .28);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    }}
    header {{
      border-top: 5px solid var(--accent);
      border-bottom: 1px solid #343b43;
      background: #18212a;
      color: white;
    }}
    .header-inner, main {{
      width: min(780px, calc(100% - 32px));
      margin-inline: auto;
    }}
    .header-inner {{ padding: 28px 0 30px; }}
    .eyebrow {{
      color: #ffb394;
      font-size: .78rem;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    h1 {{
      margin: 8px 0 7px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(1.8rem, 5vw, 2.65rem);
      font-weight: 650;
    }}
    header p {{ margin: 0; color: #bec8d1; line-height: 1.55; }}
    main {{ padding: 28px 0 48px; }}
    .summary {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 13px;
      color: var(--muted);
      font-size: .88rem;
    }}
    ol {{ margin: 0; padding: 0; list-style: none; }}
    .report {{
      margin-bottom: 10px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--card);
      box-shadow: 0 3px 14px var(--shadow);
    }}
    .report a {{
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 17px 18px;
      color: inherit;
      text-decoration: none;
    }}
    .report a:hover .report-title, .report a:focus-visible .report-title {{
      color: var(--accent);
    }}
    .report-main {{ min-width: 0; flex: 1; }}
    .report-title {{
      display: block;
      font-weight: 700;
      line-height: 1.4;
      transition: color .15s ease;
    }}
    .report-time {{
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: .83rem;
    }}
    .badge {{
      flex: 0 0 auto;
      border-radius: 999px;
      padding: 4px 8px;
      background: #fff0e8;
      color: #b64218;
      font-size: .72rem;
      font-weight: 800;
    }}
    .arrow {{ color: var(--accent); font-size: 1.25rem; }}
    .empty {{
      border: 1px dashed var(--line);
      border-radius: 10px;
      padding: 24px;
      color: var(--muted);
      text-align: center;
    }}
    footer {{
      margin-top: 28px;
      color: var(--muted);
      font-size: .78rem;
      line-height: 1.6;
      text-align: center;
    }}
    @media (max-width: 520px) {{
      .report a {{ padding: 15px; }}
      .badge {{ display: none; }}
      .summary {{ display: block; }}
      .summary span {{ display: block; margin-bottom: 4px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <div class="eyebrow">中文精选 · 每日早晚更新</div>
      <h1>Hacker News 简报</h1>
      <p>通俗摘要、精彩评论和 LLM 锐评。每一份简报都是可分享的历史快照。</p>
    </div>
  </header>
  <main>
    <div class="summary">
      <span>共 {report_count} 份历史简报</span>
      <span>最新快照：<span data-timestamp="{html.escape(newest)}">{html.escape(newest)}</span></span>
    </div>
    <ol>{report_list}
    </ol>
    <footer>
      内容来自公开网页与 Hacker News 讨论。归档页会根据浏览器本地时间自动切换日间或夜间配色。
    </footer>
  </main>
  <script>
    const parseTimestamp = (value) => {{
      const match = /^(\\d{{4}}-\\d{{2}}-\\d{{2}})T(\\d{{2}})-(\\d{{2}})-(\\d{{2}})Z$/.exec(value);
      if (!match) return null;
      return new Date(`${{match[1]}}T${{match[2]}}:${{match[3]}}:${{match[4]}}Z`);
    }};
    const formatter = new Intl.DateTimeFormat("zh-CN", {{
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    }});
    document.querySelectorAll("[data-timestamp]").forEach((element) => {{
      const date = parseTimestamp(element.dataset.timestamp);
      if (date && !Number.isNaN(date.valueOf())) element.textContent = formatter.format(date);
    }});
  </script>
</body>
</html>
"""


def run_git(repo_dir: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        check=check,
        text=True,
        capture_output=True,
    )


def commit_and_push(repo_dir: Path, newest: str, push: bool) -> bool:
    """Commit generated site changes and optionally push them to ``origin``."""
    run_git(repo_dir, "add", "public")
    diff = run_git(repo_dir, "diff", "--cached", "--quiet", check=False)
    if diff.returncode == 0:
        print("No new reports to publish.")
        return False
    if diff.returncode != 1:
        raise RuntimeError(diff.stderr.strip() or "Unable to inspect staged changes")

    message = f"publish: Hacker News digest {newest}" if newest else "publish: site"
    result = run_git(repo_dir, "commit", "-m", message)
    print(result.stdout.strip())
    if push:
        result = run_git(repo_dir, "push", "origin", "HEAD:main")
        print(result.stdout.strip() or result.stderr.strip())
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.home() / ".nanobot" / "workspace" / "hn_data",
        help="Nanobot timestamped report directory",
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Checked-out GitHub Pages repository",
    )
    parser.add_argument("--commit", action="store_true", help="Create a git commit")
    parser.add_argument("--push", action="store_true", help="Commit and push to origin/main")
    args = parser.parse_args()
    if args.push:
        args.commit = True

    reports = discover_reports(args.source.expanduser().resolve())
    repo_dir = args.repo.expanduser().resolve()
    site_dir = repo_dir / "public"
    copy_reports(reports, site_dir)
    (site_dir / "index.html").write_text(render_index(reports), encoding="utf-8")
    (site_dir / ".nojekyll").touch()
    print(f"Prepared {len(reports)} reports in {site_dir}")

    if args.commit:
        commit_and_push(repo_dir, reports[0].timestamp if reports else "", args.push)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
