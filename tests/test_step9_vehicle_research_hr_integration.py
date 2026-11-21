"""STEP 9 actual-browser acceptance smoke for the STEP 2-7 additive UI.

This test intentionally exercises the real UI navigation, native hiring,
the existing 800-node research tree, legacy-save migration, month close,
and consolidated accounting. No private save data or network market feed.
"""
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")


def run_era(browser, era):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.set_content(HTML, wait_until="domcontentloaded")
    page.evaluate(
        """era => {
          saveAuto = async () => true;
          S = newGame({era, country: 'JP', difficulty: 'normal',
                       history: 'historical', name: 'STEP9統合試験' + era});
          VIEW_FIRM = S.playerId;
          PAGE = 'product';
          PRODUCT_VIEW = 'planning';
          render();
        }""",
        era,
    )
    assert page.evaluate("TECH_NODES.length") == 800
    assert page.evaluate("STEP4_CATALOG.length") == 22
    assert page.evaluate("STEP2_PRODUCT_TABS.length") == 4
    assert page.evaluate("STEP2_HR_TABS.length") == 4
    assert page.evaluate("check(S)") == []
    assert page.locator('nav.product-tabs [data-product-view]').count() == 4

    # All four tabs must render independently; existing part designs stay reachable.
    for tab in ("planning", "design", "production", "sales"):
        page.locator(f'nav.product-tabs [data-product-view="{tab}"]').click()
        assert page.evaluate("PRODUCT_VIEW") == tab, tab
        assert page.locator(f'[data-product-pane="{tab}"].current:visible').count() >= 1, tab
    page.locator('nav.product-tabs [data-product-view="design"]').click()
    assert page.get_by_text("部品を設計・改訂する", exact=True).is_visible()

    # Use actual page-switch buttons, not an internal reassignment.
    page.locator('[data-page="research"]').first.click()
    assert page.evaluate("PAGE") == "research"
    assert page.locator("#researchTreePanel").count() == 1
    assert page.evaluate("TECH_NODES.length") == 800
    page.locator('[data-page="hr"]').first.click()
    assert page.evaluate("PAGE") == "hr"
    assert page.locator('[data-step2-hr-tab]').count() == 4
    page.locator('[data-step2-hr-tab="staff"]').click()
    before_hire = page.evaluate("current().staff.production")
    page.locator("#hireArea").select_option("production")
    page.locator("#hireCount").fill("2")
    page.locator('[data-action="hireStaff"]').click()
    assert page.evaluate("current().staff.production") == before_hire + 2

    # Legacy page key should land on HR hiring, not an invisible tab.
    page.evaluate("() => {PEOPLE_VIEW='hr'; PAGE='people'; render();}")
    assert page.evaluate("PAGE") == "hr"
    assert page.locator("#hireArea").is_visible()
    assert page.locator("#hireCount").is_visible()

    # An old save without STEP7 fields must load through native checksums,
    # retain the committed headcount, and install an empty notification baseline.
    old_payload = page.evaluate(
        """() => {
          const legacy = structuredClone(S);
          delete legacy.step7LinksV1;
          return step7NativeSavePayload(legacy);
        }"""
    )
    assert page.evaluate("raw => restore(raw)", old_payload)
    assert page.evaluate("current().staff.production") == before_hire + 2
    assert page.evaluate("S.step7LinksV1.version") == 1
    assert page.evaluate("S.step7LinksV1.entries.length") == 0
    assert page.evaluate("check(S)") == []

    # The native month pipeline, payroll, factory logic and consolidated
    # balance must remain valid after the UI-only and additive changes.
    report = page.evaluate(
        """async () => {
          const first = S.monthCommitted;
          for (let i = 0; i < 12; i++) {
            const previous = S.monthCommitted;
            await runMonth();
            if (S.monthCommitted !== previous + 1)
              throw Error('month did not commit at ' + i);
            const issues = check(S);
            if (issues.length)
              throw Error('ledger check failed: ' + JSON.stringify(issues.slice(0, 6)));
          }
          const consolidated = consolidate(S);
          return {
            months: S.monthCommitted - first,
            errors: consolidated.errors,
            cf: consolidated.cf.reconciled,
            year: S.year, month: S.month,
            staff: current().staff.production
          };
        }"""
    )
    assert report["months"] == 12, report
    assert not report["errors"] and report["cf"], report
    # Native HR turnover can reduce staffing during the following 12 months.
    # Hiring persistence is asserted immediately after legacy save restoration.
    assert isinstance(report["staff"], int) and report["staff"] >= 0, report

    saved = page.evaluate("savePayload(S)")
    assert page.evaluate("raw => restore(raw)", saved)
    assert page.evaluate("check(S)") == []
    assert page.evaluate("S.step7LinksV1.version") == 1
    assert page.evaluate("S.year") == report["year"]
    assert page.evaluate("S.month") == report["month"]
    assert not errors, errors
    page.close()
    return report


with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
        args=["--no-sandbox"],
    )
    for start in (1900, 2020):
        report = run_era(browser, start)
        print("PASS:", start, "start, 3 pages, 8 tabs, 800 nodes, 22 departments, "
              "legacy save, hiring, 12 months, consolidation:", report)
    browser.close()
