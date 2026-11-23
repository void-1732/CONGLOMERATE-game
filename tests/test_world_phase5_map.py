"""Phase 5: offline 155-city map, real route IDs and live hub management."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def test_city_facility_management(page):
    page.evaluate("""() => {
      S=newWorldGame({country:'JP',name:'Phase5 施設検証'});VIEW_FIRM=S.playerId;
      VIEW_COUNTRY='JP';PAGE='worldMap';
      const rival=S.firms.find(f=>!controller(S,f.id)&&f.country==='JP'&&f.plants.length);
      rival.plants[0].siteId='JP-NGO';
      rival.plants[0].siteCountry='JP';
      syncWorldIdentities(S);
      window.phase5RivalPlant=rival.plants[0].id;
      window.phase5BeforeBuild={cash:acc(current(),'cash'),ppe:acc(current(),'ppe'),
        capacity:current().plant.capacity};
      render();
    }""")
    page.locator('[data-world-map-city-select]').select_option('CITY-14-03')
    detail = page.locator('[data-world-map-city-detail="CITY-14-03"]')
    rival_plant = page.evaluate('window.phase5RivalPlant')
    assert detail.locator(f'[data-world-map-maintain="{rival_plant}"]').count() == 0
    assert detail.get_by_text('JP-NGO', exact=True).count() > 0
    detail.locator('[data-world-map-build="JP-NGO"]').click()
    assert page.locator('#factorySite').input_value() == 'JP-NGO'
    page.locator('#factoryName').fill('名古屋物流工場')
    page.locator('[data-action="factoryBuild"]').click()
    plant_id = page.evaluate("""() => {
      const firm=current(),plant=firm.plants.find(p=>p.name==='名古屋物流工場');
      const before=window.phase5BeforeBuild;
      const amount=localFromBase(siteInvestmentQuote('JP-NGO','small','integrated',S),firm.country);
      const restored=parsePayload(savePayload(S));
      if(!plant||plant.siteId!=='JP-NGO'||plant.construction?.monthsLeft!==2
       ||firm.plant.capacity!==before.capacity
       ||acc(firm,'cash')!==before.cash-amount||acc(firm,'ppe')!==before.ppe+amount
       ||restored.worldExpansion.facilities['FAC-'+plant.id]?.locationId!=='LOC-JP-NGO'
       ||check(restored).length||consolidate(restored).errors.length)throw Error('建設・復元が不一致');
      return plant.id;
    }""")
    page.evaluate("PAGE='worldMap';render();")
    assert '建設中（残2か月）' in detail.inner_text()
    manage = detail.locator(f'[data-world-map-maintain="{plant_id}"]')
    manage.click()
    action = page.locator(f'[data-action="factoryManageSelected"][data-plant-id="{plant_id}"]')
    page.locator('#factoryOneAction').select_option('pause')
    action.click()
    assert page.evaluate("(id)=>!current().plants.find(p=>p.id===id).paused", plant_id)

    assert page.evaluate("""async id => {
      saveAuto=async()=>true;
      await runMonth();await runMonth();
      const plant=current().plants.find(p=>p.id===id);
      return S.monthCommitted===ym(1900,2)&&plant.construction===null&&activeFactories(current()).includes(plant);
    }""", plant_id)
    page.evaluate("PAGE='worldMap';render();")
    manage.click()
    page.locator('#factoryOneAction').select_option('pause')
    action.click()
    assert page.evaluate("(id)=>parsePayload(savePayload(S)).firms.find(f=>f.id===S.playerId).plants.find(p=>p.id===id).paused", plant_id)
    page.locator('#factoryOneAction').select_option('resume')
    action.click()
    assert page.evaluate("(id)=>!current().plants.find(p=>p.id===id).paused&&!check(S).length", plant_id)

    page.evaluate("""() => {
      S.year=1970;S.month=1;S.monthCommitted=ym(1970,1)-1;
      applyWorldHistory(S);syncWorldIdentities(S);
      const firm=current();
      if(!firm.research.tree.done.includes('production-1'))firm.research.tree.done.push('production-1');
      post(firm,{materials:900},{cash:900},'検証用の有償倉庫設備','operating',S);
      firm.stock['PRD-E20']={q:1,v:900};
      window.phase5HubPpe=acc(firm,'ppe');
      PAGE='worldMap';render();
    }""")
    page.get_by_role('button', name='物流拠点管理', exact=True).click()
    page.locator('#world-domestic > summary').click()
    warehouse_form = page.locator('form[data-world-domestic="warehouse"]')
    warehouse_form.locator('select[name="installation"]').select_option(f'JP-NAGOYA-SILO|{plant_id}')
    warehouse_form.get_by_role('button', name='倉庫設備を設置').click()
    warehouse_id = page.evaluate("""id => {
      const firm=current(),restored=parsePayload(savePayload(S));
      const hub=Object.values(restored.worldExpansion.domesticWarehouses).find(h=>h.plantId===id);
      if(!hub||hub.ownerCompanyId!==firm.id||hub.assetValue!==900
       ||acc(firm,'ppe')!==window.phase5HubPpe+900||firm.stock['PRD-E20'].q!==0
       ||check(restored).length||consolidate(restored).errors.length)throw Error('倉庫資産・復元が不一致');
      return hub.id;
    }""", plant_id)
    hub = page.locator(f'[data-world-hub-id="{warehouse_id}"]')
    assert '稼働設備' in hub.inner_text() and '6 kg' in hub.inner_text()


def test_historical_air_route(page):
    page.evaluate("""() => {
      S=newWorldGame({country:'UK',name:'航空地図の検証'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='UK';PAGE='worldMap';
      S.year=1920;S.month=1;S.monthCommitted=ym(1920,1)-1;
      applyWorldHistory(S);syncWorldIdentities(S);render();
    }""")
    page.locator('[data-world-map-mode="air"]').click()
    route_id = "UK-FR-HOUNSLOW-LEATHER"
    route = page.locator(f'[data-world-map-route-row="{route_id}"]')
    assert "開通・設備未登録" in route.inner_text()
    route.get_by_role("button").click()
    detail = page.locator(f'[data-world-map-detail="{route_id}"]')
    assert "ハウンズロー・ヒース飛行場 → ル・ブルジェ飛行場" in detail.inner_text()
    assert detail.get_by_text("1919年9月から1920年2月まで", exact=False).count() == 1
    assert page.locator('[data-world-map-site="UK-HOUNSLOW-HEATH"]').count() == 1
    assert page.locator('[data-world-map-site="FR-LE-BOURGET"]').count() == 1
    page.evaluate("""() => {
      S.month=3;S.monthCommitted=ym(1920,3)-1;
      applyWorldHistory(S);syncWorldIdentities(S);render();
    }""")
    assert "登録運行期間終了" in route.inner_text()


def test_antwerp_and_brussels(page):
    page.evaluate("""() => {
      S=newWorldGame({country:'BE',name:'ベルギー地図検証'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='BE';PAGE='worldMap';
      S.year=1910;S.month=6;S.monthCommitted=ym(1910,6)-1;
      applyWorldHistory(S);syncWorldIdentities(S);render();
    }""")
    page.locator('[data-world-map-mode="sea"]').click()
    route_id = "BE-US-ANTWERP-GLASS"
    route = page.locator(f'[data-world-map-route-row="{route_id}"]')
    assert "開通・設備未登録" in route.inner_text()
    route.get_by_role("button").click()
    detail = page.locator(f'[data-world-map-detail="{route_id}"]')
    assert "アントワープ港 → ニューヨーク港" in detail.inner_text()
    assert detail.get_by_text("1910年5月から1910年12月まで", exact=False).count() == 1
    assert page.locator('[data-world-map-site="BE-ANR"]').count() == 1
    assert page.locator('[data-world-map-site="US-NYC"]').count() == 1

    page.locator('[data-world-map-city-select]').select_option('CITY-08-03')
    brussels = page.locator('[data-world-map-city-detail="CITY-08-03"]')
    assert all(text in brussels.inner_text() for text in ("MKT-08", "JUR-BE", "CUR-BEF", "開放済み"))
    brussels.locator('[data-world-map-build="BE-BRU"]').click()
    assert page.locator('#factorySite').input_value() == 'BE-BRU'
    page.locator('#factoryName').fill('ブリュッセル施設')
    page.locator('[data-action="factoryBuild"]').click()

    assert page.evaluate("""() => {
      const reopened=parsePayload(savePayload(S)),firm=company(reopened.playerId,reopened);
      const plant=firm.plants.find(p=>p.name==='ブリュッセル施設');
      const registration=reopened.worldExpansion.companies[firm.id];
      return plant?.siteId==='BE-BRU'&&plant.construction?.monthsLeft>0
        &&registration.territoryId==='TER-08-02'&&registration.currencyId==='CUR-BEF'
        &&reopened.worldExpansion.facilities['FAC-'+plant.id]?.locationId==='LOC-BE-BRU'
        &&!check(reopened).length&&!consolidate(reopened).errors.length;
    }""")
    page.evaluate("""() => {
      S.year=1911;S.month=1;S.monthCommitted=ym(1911,1)-1;
      applyWorldHistory(S);syncWorldIdentities(S);PAGE='worldMap';render();
    }""")
    assert "登録運行期間終了" in route.inner_text()


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
            const transfer=n.routes.find(r=>r.id==='JP-US-YOKOHAMA-TRANSFER');
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
              coastline:document.querySelector('[data-world-map-land]')?.getTotalLength()>0,
              handoff:transfer.via?.id==='JP-YOK'&&document.querySelectorAll(
                '[data-world-map-route="JP-US-YOKOHAMA-TRANSFER"] line').length===3,
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
        assert audit["exactIds"] and audit["endpoints"] and audit["handoff"], audit
        assert audit["svg"] == 1 and audit["coastline"] and audit["cityCircles"] == 155, audit
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

        provisional = page.locator('[data-world-map-route-row="JP-US-AIR-1965"]')
        assert '未接続・運航史料未登録' in provisional.inner_text()
        assert '年代・航路条件待ち' in page.locator('[data-world-map-route-row="FR-UK-CHANNEL-1994"]').inner_text()
        provisional.get_by_role('button').click()
        assert '未接続・運航史料未登録' in page.locator('[data-world-map-detail="JP-US-AIR-1965"]').inner_text()
        provisional.get_by_role('button').click()

        marseille = page.locator('[data-world-map-route-row="FR-UK-SEA-1900"]')
        assert '1904年1月' in marseille.inner_text()
        marseille.get_by_role('button').click()
        assert 'ゲーム内の運行期間 1904年1月から' in page.locator('[data-world-map-detail="FR-UK-SEA-1900"]').inner_text()
        marseille.get_by_role('button').click()
        schedule = page.evaluate("""() => {
          const state=structuredClone(S),route='JP-US-SEATTLE-STEAM';
          state.year=1941;state.month=7;
          const before=worldMapNetwork(state).routes.find(r=>r.id===route);
          state.month=8;
          const after=worldMapNetwork(state).routes.find(r=>r.id===route);
          return before.available&&!after.available
            &&worldMapRouteStatus(after,ym(state.year,state.month))==='登録運行期間終了'
            &&worldMapRouteDetail(state,after).includes('1941年7月まで');
        }""")
        assert schedule
        assert page.locator('[data-world-map-freight-site]').count() == 0

        first_route = page.locator('[data-world-map-select-route]').first
        selected_id = first_route.get_attribute("data-world-map-select-route")
        first_route.click()
        assert page.locator('[data-world-map-detail]').get_attribute("data-world-map-detail") == selected_id
        assert page.locator('[data-world-map-selected-route="true"]').count() == 1
        assert page.locator('[data-world-map-select-route]').first.get_attribute("aria-pressed") == "true"
        assert page.locator('[data-world-map-detail]').locator("text=登録設備なし").count() == 1
        assert page.locator('[data-world-map-detail]').locator("text=出荷履歴なし").count() == 1

        page.locator('[data-world-map-activity="registered"]').click()
        assert page.locator('[data-world-map-route-row]').count() == 0
        assert page.locator('[data-world-map-detail]').count() == 0
        page.locator('[data-world-map-activity="transit"]').click()
        assert page.locator('[data-world-map-route-row]').count() == 0
        page.locator('[data-world-map-activity="all"]').click()
        assert page.locator('[data-world-map-detail]').get_attribute("data-world-map-detail") == selected_id
        page.locator('[data-world-map-select-route]').first.click()
        assert page.locator('[data-world-map-detail]').count() == 0

        page.locator('[data-world-map-city-select]').select_option('CITY-14-01')
        # Port/site symbols share coordinates with city dots.
        assert page.locator('[data-world-map-site]').first.get_attribute("pointer-events") == "none"
        assert page.locator('[data-world-map-city-detail="CITY-14-01"]').count() == 1
        assert page.locator('[data-world-map-city-selected="true"]').count() == 1
        assert "JUR-JP" in page.locator('[data-world-map-city-detail]').inner_text()
        # City-circle selection toggles its corresponding read-only legal panel.
        page.locator('[data-world-map-city="CITY-14-01"]').click()
        assert page.locator('[data-world-map-city-detail]').count() == 0
        tokyo = page.get_by_role('button', name='東京 の都市・管轄情報')
        tokyo.focus()
        page.keyboard.press('Enter')
        expect(tokyo).to_be_focused()
        expect(tokyo).to_have_attribute('aria-pressed', 'true')
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
            &&panel.includes('未開放・未接続')&&!panel.includes('data-world-map-build');
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
        test_city_facility_management(page)
        test_historical_air_route(page)
        test_antwerp_and_brussels(page)
        assert not errors, errors
        browser.close()
    print("PASS Phase 5: 40 markets, 155 city dots, exact routes, "
          "filters, hubs, facility construction and maintenance")


if __name__ == "__main__":
    main()
