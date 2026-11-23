"""Phase 5: offline 155-city map, real route IDs and live hub management."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
            args=["--no-sandbox"],
        )
        context = browser.new_context(offline=True, viewport={"width": 1366, "height": 900})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"),
                         wait_until="domcontentloaded")
        page.wait_for_function("STORAGE_READY")
        audit = page.evaluate("""() => {
            S=newWorldGame({country:'JP',name:'Phase5 世界地図検証'});
            VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='worldMap';
            const n=worldMapNetwork();
            const actual=new Set([
              ...Object.keys(WORLD_DOMESTIC_CORRIDORS),
              ...Object.keys(WORLD_INTERNATIONAL_CORRIDORS)
            ]);
            const siteIds=new Set(SITE_CATALOG.map(s=>s.id));
            const before=JSON.stringify(S);
            render();
            return {
              markets:WORLD_MARKETS.length,cities:n.cities.length,
              distinctCities:new Set(n.cities.map(c=>c.id)).size,
              profiles:actual.size,routes:n.routes.length,
              exactIds:n.routes.every(r=>actual.has(r.id)),
              endpoints:n.routes.every(r=>siteIds.has(r.fromId)&&siteIds.has(r.toId)
                &&r.from.id===r.fromId&&r.to.id===r.toId
                &&Number.isFinite(r.from.x)&&Number.isFinite(r.to.y)),
              svg:document.querySelectorAll('.phase5-world-svg').length,
              cityCircles:document.querySelectorAll('[data-world-map-city]').length,
              routeGraphics:document.querySelectorAll('[data-world-map-route]').length,
              noMutation:JSON.stringify(S)===before,
              noPhantomWarehouses:worldMapWarehouseLedger(S).length===0,
              noPhantomEquipment:n.routes.every(r=>r.installed===0&&r.shipments===0),
              check:check(S).length
            };
        }""")
        assert audit["markets"] == 40 and audit["cities"] == 155, audit
        assert audit["distinctCities"] == 155, audit
        assert audit["routes"] == audit["profiles"] and audit["routes"] >= 60, audit
        assert audit["exactIds"] and audit["endpoints"], audit
        assert audit["svg"] == 1 and audit["cityCircles"] == 155, audit
        assert audit["routeGraphics"] == audit["routes"], audit
        assert audit["noMutation"] and audit["check"] == 0, audit
        assert audit["noPhantomWarehouses"] and audit["noPhantomEquipment"], audit
        # No network or gameplay mutations are necessary to inspect the live freight ledger.
        page.evaluate("window.__phase5PreUiState=JSON.stringify(S);")

        page.locator('[data-world-map-mode="rail"]').click()
        rail_count = page.evaluate("""() => Object.values(WORLD_INTERNATIONAL_CORRIDORS)
            .filter(p=>p.mode==='rail').length
            +Object.values(WORLD_DOMESTIC_CORRIDORS).filter(p=>p.mode==='rail').length""")
        assert page.locator('[data-world-map-route-row]').count() == rail_count
        assert page.locator('[data-world-map-mode="rail"]').get_attribute("aria-pressed") == "true"

        page.locator('[data-world-map-mode="all"]').click()
        page.locator('[data-world-map-focus="country"]').click()
        country_count = page.evaluate("""() => worldMapNetwork().routes
            .filter(r=>r.from.country==='JP'||r.to.country==='JP').length""")
        assert country_count > 0
        assert page.locator('[data-world-map-route-row]').count() == country_count
        assert page.locator('[data-world-map-focus="country"]').get_attribute("aria-pressed") == "true"

        page.locator('[data-world-map-focus="global"]').click()
        assert page.locator('[data-world-map-route-row]').count() == audit["routes"]

        first_route = page.locator('[data-world-map-select-route]').first()
        selected_id = first_route.get_attribute("data-world-map-select-route")
        first_route.click()
        assert page.locator('[data-world-map-detail]').get_attribute("data-world-map-detail") == selected_id
        assert page.locator('[data-world-map-selected-route="true"]').count() == 1
        assert page.locator('[data-world-map-select-route]').first().get_attribute("aria-pressed") == "true"
        assert page.locator('[data-world-map-detail]').locator("text=登録設備なし").count() == 1
        assert page.locator('[data-world-map-detail]').locator("text=出荷履歴なし").count() == 1

        page.locator('[data-world-map-activity="registered"]').click()
        assert page.locator('[data-world-map-route-row]').count() == 0
        assert page.locator('[data-world-map-detail]').count() == 0
        page.locator('[data-world-map-activity="transit"]').click()
        assert page.locator('[data-world-map-route-row]').count() == 0
        page.locator('[data-world-map-activity="all"]').click()
        assert page.locator('[data-world-map-detail]').get_attribute("data-world-map-detail") == selected_id
        page.locator('[data-world-map-select-route]').first().click()
        assert page.locator('[data-world-map-detail]').count() == 0

        page.locator('[data-world-map-city-select]').select_option('CITY-14-01')
        assert page.locator('[data-world-map-city-detail="CITY-14-01"]').count() == 1
        assert page.locator('[data-world-map-city-selected="true"]').count() == 1
        assert "JUR-JP" in page.locator('[data-world-map-city-detail]').inner_text()
        # City-circle selection toggles its corresponding read-only legal panel.
        page.locator('[data-world-map-city="CITY-14-01"]').click()
        assert page.locator('[data-world-map-city-detail]').count() == 0
        page.locator('[data-world-map-city="CITY-14-01"]').focus()
        page.keyboard.press('Enter')
        assert page.locator('[data-world-map-city-detail="CITY-14-01"]').count() == 1
        assert page.locator('[data-world-map-city-selected="true"]').count() == 1

        # Portugal has a recorded historical jurisdiction, not an approved
        # independent engine or silently redenominated accounting books.
        territory_reference = page.evaluate("""() => {
          const city=worldMapNetwork().cities.find(c=>c.territoryId==='TER-05-02');
          const state=city&&worldCityLocation(S,city.id);
          const panel=city&&worldMapCityDetail(S,city);
          return !!city&&state.jurisdictionId==='JUR-PT-KINGDOM'
            &&!state.marketOpen&&panel.includes('REFERENCE_ONLY')
            &&panel.includes('未開放・未接続');
        }""")
        assert territory_reference
        # Registry views must not report retired infrastructure as installed.
        live_only = page.evaluate("""() => {
          const copy=structuredClone(S),id=Object.keys(WORLD_DOMESTIC_CORRIDORS)[0];
          copy.worldExpansion.domesticRoutes={
            'DR-900':{id:'DR-900',profileId:id,retiredAt:ym(1912,1)},
            'DR-901':{id:'DR-901',profileId:id,retiredAt:null}
          };
          const r=worldMapNetwork(copy).routes.find(x=>x.id===id);
          return r.installed===1&&worldMapNetwork(S).routes.find(x=>x.id===id).installed===0;
        }""")
        assert live_only
        assert page.evaluate("JSON.stringify(S)===window.__phase5PreUiState")

        page.evaluate("PAGE='logisticsHubs';render();")
        assert page.locator('[aria-label="Phase 5 現物物流拠点"]').count() == 1
        assert page.locator("text=国内・国際物流の登録・発注操作").count() >= 1
        assert page.locator('[data-page="worldMap"]').count() >= 1
        assert page.evaluate("JSON.stringify(S)===window.__phase5PreUiState")
        assert not errors, errors
        browser.close()
    print("PASS Phase 5: 40 markets, 155 city dots, exact routes, "
          "filters, hubs and nonmutating map")


if __name__ == "__main__":
    main()
