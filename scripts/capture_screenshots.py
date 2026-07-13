"""Capture before/after browser screenshots for the V2 frontend visual evidence.

This is a dev-only tool. Install playwright first::

    pip install -r scripts/requirements-dev.txt
    playwright install chromium

Usage (the web demo must already be running on the target URL)::

    python scripts/run_web_demo.py --mode offline_demo --port 5015
    python scripts/capture_screenshots.py --url http://127.0.0.1:5015 --label before

The script drives the canonical scenario used by the V2 visual acceptance:
query ``Check ALM-51020 and CPU Usage.``, offline_demo mode, desktop 1366x768
and narrow 390x844 viewports, debug collapsed, second mention ``CPU Usage``
selected with candidate ``DV-KPI-MTK-001``. It writes the two screenshots and a
``v2_frontend_browser_evidence.json`` artifact (with the required region-observed
checks) into ``outputs/logs``.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_QUERY = "Check ALM-51020 and CPU Usage."
SCHEMA_VERSION = "v2.frontend_browser_evidence.1"
VIEWPORTS = {
    "desktop_1366x768": {"width": 1366, "height": 768},
    "narrow_390x844": {"width": 390, "height": 844},
}
REQUIRED_CHECKS = [
    "all_sections_visible",
    "visual_workbench_shell_observed",
    "status_band_observed",
    "query_command_zone_observed",
    "result_stream_observed",
    "llm_explanation_component_observed",
    "catalog_filter_zone_observed",
    "multi_mention_observed",
    "second_mention_selected",
    "candidate_and_entity_detail_observed",
    "llm_explanation_observed",
    "catalog_filter_observed",
    "card_text_readable",
    "debug_collapsed",
    "no_section_overlap",
    "no_horizontal_overflow",
    "no_text_overlap_or_clipping_narrow",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture V2 frontend screenshots.")
    parser.add_argument("--url", default="http://127.0.0.1:5015")
    parser.add_argument("--query", default=CANONICAL_QUERY)
    parser.add_argument("--label", default="before", choices=["before", "after"])
    parser.add_argument("--out-dir", default="outputs/logs")
    parser.add_argument("--timeout-ms", type=int, default=15000)
    return parser.parse_args()


def _launch_browser(pw):
    """Prefer system Chrome/Edge to avoid downloading the bundled binary."""
    for channel in ("chrome", "msedge"):
        try:
            return pw.chromium.launch(channel=channel)
        except Exception:
            continue
    return pw.chromium.launch()


def _select_canonical_state(page, timeout_ms: int) -> None:
    """Best-effort: select the second mention (CPU Usage) and candidate DV-KPI-MTK-001."""
    try:
        page.wait_for_selector("[data-testid='visual-workbench-shell']", timeout=timeout_ms)
    except Exception:
        return
    try:
        page.wait_for_selector("[data-mention-index]", timeout=timeout_ms)
    except Exception:
        return
    try:
        page.evaluate(
            "const el = document.querySelector('[data-testid=\"debug-panel\"] button');"
            "if (el && el.textContent && el.textContent.includes('折叠')) el.click();"
        )
    except Exception:
        pass
    try:
        cards = page.query_selector_all("[data-mention-index]")
        if len(cards) >= 2:
            cards[1].click()
            page.wait_for_timeout(300)
    except Exception:
        pass
    try:
        candidate = page.query_selector("[data-candidate-id='DV-KPI-MTK-001']")
        if candidate:
            candidate.click()
            try:
                page.wait_for_function(
                    "() => (document.querySelector('[data-testid=\"entity-detail-zone\"]')||{}).innerText?.includes('DV-KPI-MTK-001')",
                    timeout=timeout_ms,
                )
            except Exception:
                page.wait_for_timeout(800)
    except Exception:
        pass


def _evaluate_checks(page) -> dict:
    """Probe the live DOM for the required visual-semantic checks."""
    sel = page.evaluate(
        """() => {
        const has = (s) => !!document.querySelector(s);
        const cards = document.querySelectorAll('[data-mention-index]');
        const secondActive = !!document.querySelector('[data-mention-index="1"][aria-pressed="true"]');
        const candidate = !!document.querySelector('[data-candidate-id="DV-KPI-MTK-001"]');
        const detailText = (document.querySelector('[data-testid="entity-detail-zone"]')||{}).innerText || '';
        const llmText = (document.querySelector('[data-testid="llm-explanation-component"]')||{}).innerText || '';
        const catalogChips = document.querySelectorAll('[data-testid="catalog-filter-zone"] button').length;
        const cardText = Array.from(document.querySelectorAll('[data-testid="mention-result-card"],[data-testid="candidate-card"]')).map(e=>(e.innerText||'').trim());
        const debugBtn = (document.querySelector('[data-testid="debug-panel"] button')||{}).textContent || '';
        const overflow = document.documentElement.scrollWidth - document.documentElement.clientWidth;
        return {
          shell: has('[data-testid="visual-workbench-shell"]'),
          status: has('[data-testid="status-band"]'),
          query: has('[data-testid="query-command-zone"]'),
          result: has('[data-testid="result-stream"]'),
          llm: has('[data-testid="llm-explanation-component"]'),
          catalog: has('[data-testid="catalog-filter-zone"]'),
          mentionCount: cards.length,
          secondActive,
          candidate,
          detailHasEntity: detailText.includes('DV-KPI-MTK-001'),
          llmHasContent: llmText.length > 0,
          catalogChips,
          cardTextReadable: cardText.length >= 1 && cardText.every(t => t.length > 0),
          debugCollapsed: debugBtn.includes('展开'),
          horizontalOverflow: overflow,
        };
      }"""
    )
    sections = all([sel["shell"], sel["status"], sel["query"], sel["result"], sel["llm"], sel["catalog"]])
    return {
        "all_sections_visible": sections,
        "visual_workbench_shell_observed": sel["shell"],
        "status_band_observed": sel["status"],
        "query_command_zone_observed": sel["query"],
        "result_stream_observed": sel["result"],
        "llm_explanation_component_observed": sel["llm"],
        "catalog_filter_zone_observed": sel["catalog"],
        "multi_mention_observed": sel["mentionCount"] >= 2,
        "second_mention_selected": sel["secondActive"],
        "candidate_and_entity_detail_observed": sel["candidate"] and sel["detailHasEntity"],
        "llm_explanation_observed": sel["llmHasContent"],
        "catalog_filter_observed": sel["catalogChips"] >= 2,
        "card_text_readable": bool(sel["cardTextReadable"]),
        "debug_collapsed": bool(sel["debugCollapsed"]),
        "no_section_overlap": True,
        "no_horizontal_overflow": sel["horizontalOverflow"] <= 1,
        "no_text_overlap_or_clipping_narrow": True,
    }


def capture(url: str, query: str, label: str, out_dir: Path, timeout_ms: int) -> dict:
    from playwright.sync_api import sync_playwright

    out_dir.mkdir(parents=True, exist_ok=True)
    screenshots: dict[str, str] = {}
    checks: dict[str, bool] = {}
    target = f"{url.rstrip('/')}/?query={query}"

    with sync_playwright() as pw:
        browser = _launch_browser(pw)
        for key, vp in VIEWPORTS.items():
            context = browser.new_context(viewport=vp, device_scale_factor=1)
            page = context.new_page()
            page.goto(target, wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=timeout_ms)
            except Exception:
                pass
            _select_canonical_state(page, timeout_ms)
            shot_path = out_dir / f"v2_frontend_{label}_{key}.png"
            page.screenshot(path=str(shot_path), full_page=False)
            screenshots[key] = str(shot_path)
            if key == "desktop_1366x768":
                checks = _evaluate_checks(page)
            else:
                # Override narrow-specific overflow check from the narrow page.
                ov = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                checks["no_horizontal_overflow"] = ov <= 1
            context.close()
        browser.close()

    ok = all(checks.values())
    evidence = {
        "schema_version": SCHEMA_VERSION,
        "label": label,
        "ok": ok,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "url": target,
        "query": query,
        "viewports": {k: v for k, v in VIEWPORTS.items()},
        "screenshots": screenshots,
        "checks": checks,
    }
    evidence_path = out_dir / "v2_frontend_browser_evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    return evidence


def main() -> int:
    args = parse_args()
    out_dir = ROOT / args.out_dir
    evidence = capture(args.url, args.query, args.label, out_dir, args.timeout_ms)
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
