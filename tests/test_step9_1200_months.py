"""STEP 9 long-duration regression: 1,200 real month closes per start era.

Each trial executes the existing runMonth() pipeline, including factory,
AI, payroll, research, module inventories, debit/credit, and consolidated
accounting checks. Only DOM rerender and recurring browser autosave are
disabled to isolate simulation throughput; full JSON save/parse roundtrips
are exercised at 300, 600, 900, and 1,200 months.

Usage: python tests/test_step9_1200_months.py --era 1900
       python tests/test_step9_1200_months.py --era 2020
"""
import argparse
import json
import os
import shutil
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
MONTHS = 1200
CHUNK = 10
CHECKPOINT = 100
SAVE_CHECKPOINT = 300


def run(era):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(HTML, wait_until="domcontentloaded")
        started = time.monotonic()
        initial = page.evaluate(
            """era => {
              // Do not replace runMonth(), its CHECK_BEFORE/CHECK_AFTER, or
              // its CONSOLIDATION stage. Avoid DOM and IDB work only.
              saveAuto = async () => true;
              render = () => {};
              S = newGame({
                era, country: 'JP', difficulty: 'normal',
                history: 'historical', name: 'STEP9_1200_' + era
              });
              VIEW_FIRM = S.playerId;
              PAGE = 'dashboard';
              return {
                year: S.year, month: S.month, committed: S.monthCommitted,
                firms: S.firms.length, technologies: TECH_NODES.length,
                departments: STEP4_CATALOG.length,
                notifications: S.step7LinksV1?.entries.length,
                checks: check(S)
              };
            }""",
            era,
        )
        assert initial["year"] == era and initial["month"] == 1, initial
        assert initial["technologies"] == 800 and initial["departments"] == 22, initial
        assert initial["notifications"] == 0 and not initial["checks"], initial
        print("START", json.dumps({"era": era, **initial}, ensure_ascii=False), flush=True)
        count = 0
        try:
            for _ in range(MONTHS // CHUNK):
                batch = page.evaluate(
                    """async batchSize => {
                      const first = S.monthCommitted;
                      let completed = 0;
                      for (let i = 0; i < batchSize; i++) {
                        const previous = S.monthCommitted;
                        await runMonth();
                        if (S.monthCommitted !== previous + 1 ||
                            LAST_MONTH_DIAGNOSTIC || MONTH_DIAGNOSTIC_OPEN) {
                          return {
                            completed, failure: 'monthly close failed',
                            prior: previous, now: S.monthCommitted,
                            stage: LAST_MONTH_DIAGNOSTIC?.stage,
                            why: LAST_MONTH_DIAGNOSTIC?.message
                          };
                        }
                        completed++;
                      }
                      return {
                        completed, advanced: S.monthCommitted - first,
                        now: S.monthCommitted
                      };
                    }""",
                    CHUNK,
                )
                assert batch.get("completed") == CHUNK and batch.get("advanced") == CHUNK, {
                    "era": era, "completed_total": count, **batch
                }
                count += CHUNK
                if count % CHECKPOINT != 0:
                    continue
                checkpoint = page.evaluate(
                    """saveCheck => {
                      const prior = S, issues = check(S);
                      const accounting = consolidate(S);
                      const out = {
                        committed: S.monthCommitted, year: S.year, month: S.month,
                        firmCount: S.firms.length, plantCount: S.firms.reduce(
                          (n, f) => n + (f.plants||[]).length, 0),
                        journalEntries: S.firms.reduce(
                          (n, f) => n + (f.journals||[]).length, 0),
                        stateIssues: issues.slice(0, 10),
                        consoIssues: accounting.errors.slice(0, 10),
                        cfReconciled: accounting.cf.reconciled,
                        cfDifference: accounting.cf.unreconciled || null,
                        noticeCount: S.step7LinksV1?.entries.length ?? null,
                        departmentCount: S.firms.reduce(
                          (n, f) => n + (f.step4SpecialistsV1?.departments||[]).length, 0),
                        saveChecked: false
                      };
                      if (saveCheck) {
                        const raw = savePayload(S);
                        const loaded = parsePayload(raw);
                        const restored = consolidate(loaded);
                        const same =
                          loaded.year === S.year &&
                          loaded.month === S.month &&
                          loaded.monthCommitted === S.monthCommitted &&
                          JSON.stringify(accounting.bs) === JSON.stringify(restored.bs) &&
                          JSON.stringify(accounting.cf) === JSON.stringify(restored.cf) &&
                          JSON.stringify(loaded.step7LinksV1) ===
                            JSON.stringify(S.step7LinksV1) &&
                          check(loaded).length === 0;
                        out.saveBytes = raw.length;
                        out.saveChecked = true;
                        out.saveConsistent = same;
                        // Continue from deserialized state, verifying it is runnable.
                        if (same) S = loaded;
                      }
                      return out;
                    }""",
                    count % SAVE_CHECKPOINT == 0,
                )
                assert not checkpoint["stateIssues"], {"era": era, "month": count, **checkpoint}
                assert not checkpoint["consoIssues"], {"era": era, "month": count, **checkpoint}
                assert checkpoint["cfReconciled"], {"era": era, "month": count, **checkpoint}
                assert checkpoint["year"] == era + count // 12, checkpoint
                assert checkpoint["month"] == 1 + count % 12, checkpoint
                if checkpoint["saveChecked"]:
                    assert checkpoint["saveConsistent"], {"era": era, "month": count, **checkpoint}
                assert not errors, {"era": era, "month": count, "page_errors": errors}
                print(
                    "CHECKPOINT",
                    json.dumps({
                        "era": era,
                        "months": count,
                        "elapsedSeconds": round(time.monotonic() - started, 1),
                        **checkpoint,
                    }, ensure_ascii=False),
                    flush=True,
                )
            assert count == MONTHS, {"era": era, "count": count}
            assert not errors, errors
            print("PASS", json.dumps({
                "era": era, "months": count,
                "endYear": era + 100, "endMonth": 1,
                "elapsedSeconds": round(time.monotonic() - started, 1)
            }, ensure_ascii=False), flush=True)
        finally:
            page.close()
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--era", type=int, choices=(1900, 2020), required=True)
    opts = parser.parse_args()
    run(opts.era)
