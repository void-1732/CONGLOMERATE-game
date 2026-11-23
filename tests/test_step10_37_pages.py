"""STEP 10 final regression for eight categories and 37 real pages.

Run: python tests/test_step10_37_pages.py
Uses a real Chromium page; tests the current UI, month close, accounting,
serialized restore and browser IndexedDB/page reload. No market-data network calls.
"""
import os
import shutil
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
CATEGORIES = {
    "management": ["dashboard", "reports", "automation", "managementNotices"],
    "vehicles": ["product", "research", "hr"],
    "facilities": ["facilityBusiness", "factory", "facilityExpansion", "facilityProduction", "facilityMaintenance"],
    "logistics": ["supply", "supplyContracts", "transportNetwork", "logisticsHubs", "logisticsDelivery"],
    "markets": ["marketOverview", "marketRivals", "marketOwn", "distribution", "marketExport"],
    "world": ["worldMap", "marketRegion", "market", "worldPolicy", "worldInfrastructure"],
    "corporate": ["group", "corporateSubsidiaries", "ma", "corporateMerger", "corporateHoldings"],
    "finance": ["finance", "consolidated", "financeFunding", "capital", "save"],
}


def test_browser_era(browser, era):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.set_default_timeout(12000)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_content(HTML, wait_until="domcontentloaded")
    page.evaluate(
        """era => {
            saveAuto=async()=>true;
            S=newGame({era,country:'JP',difficulty:'normal',
                history:'historical',name:'STEP10テスト'});
            VIEW_FIRM=S.playerId; VIEW_COUNTRY='JP'; PAGE='dashboard';
            render();
        }""",
        era,
    )
    assert page.evaluate("check(S)") == []
    sections = page.evaluate("SECTIONS")
    assert set(sections) == set(CATEGORIES)
    assert sum(len(x["pages"]) for x in sections.values()) == 37

    for category, routes in CATEGORIES.items():
        assert [x[0] for x in sections[category]["pages"]] == routes, category
        for route in routes:
            page.evaluate("(p)=>{PAGE=p;render();}", route)
            assert page.evaluate("PAGE") == route
            assert page.locator("#content").inner_text().strip(), route
            assert page.locator(f'.section-tabs [data-page="{route}"].active').count() == 1, route

    # Genuine tab switching, not only direct state assignments.
    page.evaluate("()=>{PAGE='group';render()}")
    page.locator('.section-tabs [data-page="corporateSubsidiaries"]').click()
    assert page.evaluate("PAGE") == "corporateSubsidiaries"
    for selector in ("#subName", "#subCountry", "#subIndustry", "#subCapital",
                     "#renameCompanyId", "#loanSubs", "#internalBuyer"):
        assert page.locator(selector).count() == 1, selector

    # STEP 9: all four original subsidiary actions remain reachable on one page.
    for action in ("renameCompany", "createSub", "groupLoan", "groupSale"):
        assert page.locator(f'[data-action="{action}"]').count() == 1, action

    if era == 1900:
        # Company creation goes through the real button and accounting engine.
        firms_before = page.evaluate("S.firms.length")
        parent = page.evaluate("S.playerId")
        page.locator("#subName").fill("STEP10製造子会社")
        page.locator("#subCountry").select_option("JP")
        page.locator("#subIndustry").select_option("manufacturing")
        minimum = page.evaluate("Math.round(450000*eraCostFactor(S.year))")
        page.locator("#subCapital").fill(str(int(minimum * 1.2)))
        page.locator('[data-action="createSub"]').click()
        assert page.evaluate("S.firms.length") == firms_before + 1
        child = page.evaluate("current().id")
        assert page.evaluate("current().owners[0].id") == parent
        page.evaluate("id=>{VIEW_FIRM=id;PAGE='corporateHoldings';render()}", parent)
        assert page.locator("#content").get_by_text("STEP10製造子会社").count() >= 1
        assert page.evaluate("check(S)") == []
        page.evaluate("()=>{PAGE='corporateMerger';render()}")
        assert page.locator('[data-action="mergeParentSub"]').count() == 1
        assert page.locator('[data-action="reorgTransfer"]').count() == 1

    # STEP 8: export pricing belongs only in export management.
    page.evaluate("()=>{VIEW_FIRM=S.playerId;PAGE='distribution';render()}")
    assert page.locator('[data-action="saveDistribution"]').count() == 1
    assert page.locator("#mkSimPrice").count() == 0
    page.locator('.section-tabs [data-page="marketExport"]').click()
    assert page.evaluate("PAGE") == "marketExport"
    assert page.locator("#mkSimPrice").count() == 1
    assert page.locator('[data-action="establishSalesCorp"]').count() == 1
    old = page.locator("#mkSimUnit").inner_text()
    page.locator("#mkSimPrice").fill("100000")
    new = page.locator("#mkSimUnit").inner_text()
    assert new != old, (old, new)

    # STEP 7: purchasing and freight settings use distinct real pages.
    page.evaluate("()=>{PAGE='supplyContracts';render()}")
    assert page.locator('[data-action="saveSupply"]').count() == 1
    assert page.locator("#supplier_steel").count() == 1
    page.evaluate("()=>{PAGE='logisticsDelivery';render()}")
    assert page.locator('[data-action="shipParts"]').count() == 1
    assert page.locator('[data-action="moduleShipV21"]').count() == 1
    page.evaluate("()=>{PAGE='transportNetwork';render()}")
    assert page.locator('[data-action="v21RouteSave"]').count() == 1

    # STEP 10: full monthly pipeline and native accounting checks.
    result = page.evaluate(
        """async () => {
            PAGE='dashboard';render();
            let months=0;
            for(let i=0;i<12;i++){
                const before=S.monthCommitted;
                await runMonth();
                if(S.monthCommitted!==before+1)throw Error('month not advanced: '+i);
                const errors=check(S),c=consolidate(S);
                if(errors.length||c.errors.length||!c.cf.reconciled)
                    throw Error('accounting check: '+JSON.stringify({errors,c:c.errors,cf:c.cf.reconciled}));
                months++;
            }
            const prior={year:S.year,month:S.month,corporations:S.firms.length};
            const payload=savePayload(S);
            const restored=parsePayload(payload);
            if(check(restored).length)throw Error('serialized copy has invalid accounting');
            if(!restore(payload))throw Error('restore() rejected valid data');
            const next={year:S.year,month:S.month,corporations:S.firms.length};
            if(JSON.stringify(prior)!==JSON.stringify(next))
                throw Error('round-trip changed world state');
            return {months,prior,bytes:payload.length};
        }"""
    )
    assert result["months"] == 12 and result["bytes"] > 1000, result
    assert not errors, errors
    print(f"PASS real-browser {era}: 37 pages, subsidiary/export/logistics, "
          f"12 months, consolidation, serialization: {result}")
    page.close()


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def test_real_reload(browser):
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT))
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        page = browser.new_page(viewport={"width": 1365, "height": 850})
        errors = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
        page.wait_for_function("STORAGE_READY", timeout=20000)
        assert page.evaluate("S===null"), "Expected a fresh browser context"
        for _ in range(4):
            page.locator('[data-action="wizardNext"]').click()
        page.wait_for_function("S?.playerId && S.autosaveState==='保存成功'", timeout=20000)
        assert page.evaluate("SAVE_INDEX.backend") == "IndexedDB"
        page.wait_for_function("!SAVE_BUSY")
        page.evaluate("""() => {
          const refresh=refreshSaveIndex;
          refreshSaveIndex=async()=>{
            await refresh();
            await new Promise(resolve=>{window.releaseOldAutosave=resolve;});
            refreshSaveIndex=refresh;
          };
          window.oldAutosave=saveAuto();
        }""")
        page.wait_for_function("typeof window.releaseOldAutosave==='function'")
        page.evaluate("()=>{PAGE='corporateSubsidiaries';render()}")
        page.locator("#renameCompanyName").fill("STEP10保存復元企業")
        page.locator('[data-action="renameCompany"]').click()
        assert page.evaluate("company(S.playerId).name") == "STEP10保存復元企業"
        assert page.evaluate("readSafetySnapshotV037()?.s.config.name") == "STEP10保存復元企業"
        assert page.evaluate("async()=>{window.releaseOldAutosave();return await window.oldAutosave}")
        assert page.evaluate("readSafetySnapshotV037()?.s.config.name") == "STEP10保存復元企業"
        page.reload()
        page.wait_for_function("STORAGE_READY", timeout=20000)
        assert page.evaluate("S!==null")
        assert page.evaluate("company(S.playerId).name") == "STEP10保存復元企業"
        assert page.evaluate("check(S)") == []
        assert not errors, errors
        print("PASS HTTP-origin IndexedDB + immediate rename/reload recovery")
        page.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE")
            or shutil.which("chromium") or None,
            args=["--no-sandbox"],
        )
        try:
            for start_year in (1900, 2020):
                test_browser_era(browser, start_year)
            test_real_reload(browser)
        finally:
            browser.close()
    print("PASS STEP 10 final regression")
