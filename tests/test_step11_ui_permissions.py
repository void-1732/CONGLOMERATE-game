"""STEP 11 real-Chromium integration: navigation, controlled entities, permissions and accounting.

Run from repository root:
    python tests/test_step11_ui_permissions.py

The test follows real click/change UI events for controlled and third-party firms.
No external market data and no modifications to the game engine.
"""
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")


def run(browser, start_year):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.set_default_timeout(12000)
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.set_content(HTML, wait_until="domcontentloaded")
    page.evaluate(
        """year => {
            saveAuto=async()=>true;
            S=newGame({era:year,country:'JP',difficulty:'normal',
                history:'historical',name:'STEP11権限検証'});
            VIEW_FIRM=S.playerId; VIEW_COUNTRY='JP'; PAGE='dashboard';
            render();
        }""",
        start_year,
    )
    parent = page.evaluate("S.playerId")
    independent = page.evaluate(
        "() => S.firms.find(x => !controller(S,x.id) && x.id!==S.playerId).id"
    )
    assert page.evaluate("check(S)") == []

    # Browser-click navigation across all eight top-level categories.
    sections = page.evaluate("Object.entries(SECTIONS).map(([k,v])=>[k,v.pages.map(x=>x[0])])")
    assert len(sections) == 8
    assert sum(len(pages) for _, pages in sections) == 37
    for category, routes in sections:
        page.locator(f'[data-section="{category}"]').first.click()
        assert page.evaluate("PAGE") == routes[0], category
        for key in routes:
            page.locator(f'.section-tabs [data-page="{key}"]').click()
            assert page.evaluate("PAGE") == key
            assert page.locator("#content").inner_text().strip(), key

    # Regression: funding screen must navigate to the relocated group loan form.
    page.evaluate("()=>{PAGE='financeFunding';render();}")
    page.get_by_role("button", name="グループ内貸付へ").click()
    assert page.evaluate("PAGE") == "corporateSubsidiaries"
    assert page.locator("#loanSubs").count() == 1

    # Player-controlled subsidiary setup through the real UI and existing accounting.
    page.locator("#subName").fill("STEP11子会社")
    page.locator("#subCountry").select_option("JP")
    page.locator("#subIndustry").select_option("manufacturing")
    min_capital = page.evaluate("Math.round(450000*eraCostFactor(S.year))")
    page.locator("#subCapital").fill(str(int(min_capital * 1.2)))
    previous = page.evaluate("S.firms.length")
    page.locator('[data-action="createSub"]').click()
    assert page.evaluate("S.firms.length") == previous + 1
    child = page.evaluate("current().id")
    assert page.evaluate("current().owners[0].id") == parent
    assert page.evaluate("check(S)") == []

    # Switch to parent and loan real funds to child via the exact contract panel.
    page.locator("#companySelect").select_option(parent)
    assert page.evaluate("current().id") == parent
    page.locator("#loanSubs").select_option(child)
    page.locator("#loanAmount").fill("10000")
    before = page.evaluate("""child => ({
        parentCash:acc(company(S.playerId),'cash'),
        childCash:acc(company(child),'cash'),
        debt:acc(company(child),'debt')
    })""", child)
    page.locator('[data-action="groupLoan"]').click()
    after = page.evaluate("""child => ({
        parentCash:acc(company(S.playerId),'cash'),
        childCash:acc(company(child),'cash'),
        debt:acc(company(child),'debt')
    })""", child)
    assert after["parentCash"] < before["parentCash"], (before, after)
    assert after["childCash"] > before["childCash"], (before, after)
    assert after["debt"] > before["debt"], (before, after)
    assert page.evaluate("check(S)") == []

    # Current controlled firm may rename a member by ID; the data model keeps ownership.
    page.locator("#renameCompanyId").select_option(child)
    page.locator("#renameCompanyName").fill("STEP11新社名")
    page.locator('[data-action="renameCompany"]').click()
    assert page.evaluate("id => company(id).name", child) == "STEP11新社名"

    # Controlled company switching is a genuine UI navigation event.
    page.evaluate("()=>{PAGE='group';render();}")
    page.locator(f'[data-corp-open="{child}"]').click()
    assert page.evaluate("PAGE") == "corporateSubsidiaries"
    assert page.evaluate("current().id") == child

    # Third-party corporations should remain read-only across moved panels.
    page.locator("#companySelect").select_option(independent)
    assert page.evaluate("!canEdit(current())")
    for key in ("renameCompany", "createSub", "groupLoan", "groupSale"):
        control = page.locator(f'[data-action="{key}"]')
        assert control.count() == 1, key
        assert control.is_disabled(), key
    for key in ("renameCompanyName", "subName", "subCountry", "subCapital",
                "loanSubs", "loanAmount", "internalQuantity"):
        control = page.locator(f"#{key}")
        assert control.count() == 1, key
        assert control.is_disabled(), key

    # Invoking a function outside the UI must be rejected when viewing a foreign firm.
    previous_name = page.evaluate("id => company(id).name", child)
    page.evaluate("""id => {
        document.querySelector('#renameCompanyId').value=id;
        document.querySelector('#renameCompanyName').value='不正な変更';
        renameCompany();
    }""", child)
    assert page.evaluate("id => company(id).name", child) == previous_name
    assert page.evaluate("check(S)") == []

    # Representative write controls in the other categories are disabled.
    for route, action in [
        ("financeFunding", "borrow"),
        ("distribution", "saveDistribution"),
        ("marketExport", "establishSalesCorp"),
        ("supplyContracts", "saveSupply"),
        ("corporateMerger", "mergeSibling"),
    ]:
        page.evaluate("(route)=>{PAGE=route;render();}", route)
        control = page.locator(f'[data-action="{action}"]')
        assert control.count() == 1, (route, action)
        assert control.is_disabled(), (route, action)
    page.evaluate("()=>{PAGE='financeFunding';render();}")
    assert page.locator("#borrowBase").is_disabled()

    # Region controls must update the actual country and return to regional view.
    page.evaluate("()=>{VIEW_FIRM=S.playerId;PAGE='worldMap';render();}")
    region = next(c for c in page.evaluate("Object.keys(S.world)") if c != "JP")
    page.locator(f'[data-world-region="{region}"]').first.click()
    assert page.evaluate("VIEW_COUNTRY") == region
    page.evaluate("()=>{PAGE='worldMap';render();}")
    page.locator(f'[data-mk-region="{region}"]').first.click()
    assert page.evaluate("PAGE") == "marketRegion"

    # Round-trip with controlled group/loan/rename state and no accounting corruption.
    saved = page.evaluate("savePayload(S)")
    assert page.evaluate("raw => restore(raw)", saved)
    assert page.evaluate("id => company(id).name", child) == "STEP11新社名"
    assert page.evaluate("id => company(id).owners[0].id", child) == parent
    assert page.evaluate("check(S)") == []
    consolidated = page.evaluate("consolidate(S)")
    assert consolidated["errors"] == [] and consolidated["cf"]["reconciled"], consolidated
    assert not errors, errors
    page.close()
    print(f"PASS STEP 11: {start_year}; 37 UI tabs, loan, subsidiary, rename, "
          "third-party readonly, region switching, save/restore, consolidated accounting")


with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE")
        or shutil.which("chromium") or None, args=["--no-sandbox"]
    )
    try:
        for year in (1900, 2020):
            run(browser, year)
    finally:
        browser.close()
