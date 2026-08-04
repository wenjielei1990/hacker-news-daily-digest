from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish.py"
SPEC = importlib.util.spec_from_file_location("hn_pages_publish_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
publish = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = publish
SPEC.loader.exec_module(publish)


def _write_report(root: Path, timestamp: str) -> None:
    directory = root / timestamp
    directory.mkdir(parents=True)
    (directory / "hn_news.html").write_text(
        (
            "<html><head><title>HN 每日精选</title></head>"
            f"<body><span>更新于 {timestamp}</span></body></html>"
        ),
        encoding="utf-8",
    )


def test_targeted_publish_does_not_expose_other_local_reports(tmp_path: Path) -> None:
    source = tmp_path / "source"
    public = tmp_path / "public"
    old_timestamp = "2026-08-01T15-00-00Z"
    selected_timestamp = "2026-08-02T08-00-00-0700"
    unpublished_timestamp = "2026-08-02T11-00-00-0700"
    _write_report(public, old_timestamp)
    _write_report(source, selected_timestamp)
    _write_report(source, unpublished_timestamp)

    local_reports = publish.discover_reports(source)
    selected = publish.select_reports(local_reports, selected_timestamp)
    publish.copy_reports(selected, public)
    published_reports = publish.discover_reports(public)
    index = publish.render_index(published_reports)

    assert [report.timestamp for report in selected] == [selected_timestamp]
    assert (public / selected_timestamp / "hn_news.html").is_file()
    assert not (public / unpublished_timestamp).exists()
    assert f"./{old_timestamp}/hn_news.html" in index
    assert f"./{selected_timestamp}/hn_news.html" in index
    assert unpublished_timestamp not in index
    assert 'match[5] === "Z"' in index
    assert "match[5].slice(3)" in index


def test_cli_timestamp_copies_only_selected_report(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "source"
    repo = tmp_path / "repo"
    selected_timestamp = "2026-08-02T08-00-00-0700"
    unpublished_timestamp = "2026-08-02T11-00-00-0700"
    _write_report(source, selected_timestamp)
    _write_report(source, unpublished_timestamp)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--source",
            str(source),
            "--repo",
            str(repo),
            "--timestamp",
            selected_timestamp,
        ],
    )

    assert publish.main() == 0
    assert (repo / "public" / selected_timestamp / "hn_news.html").is_file()
    assert not (repo / "public" / unpublished_timestamp).exists()
    index = (repo / "public" / "index.html").read_text(encoding="utf-8")
    assert selected_timestamp in index
    assert unpublished_timestamp not in index


def test_discovery_orders_legacy_and_local_timestamps_by_instant(
    tmp_path: Path,
) -> None:
    legacy_utc = "2026-08-02T15-00-00Z"
    newer_local = "2026-08-02T09-00-00-0700"
    _write_report(tmp_path, legacy_utc)
    _write_report(tmp_path, newer_local)

    reports = publish.discover_reports(tmp_path)

    assert [report.timestamp for report in reports] == [newer_local, legacy_utc]
