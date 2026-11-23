"""Phase 1 world catalog, history, offline start, and versioned save regression."""
import json
import os
import shutil
from collections import Counter
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def test_catalog_and_history(page):
    catalog = json.loads(page.locator("#world-market-catalog").text_content())
    assert len(catalog) == 40
    assert len({market["id"] for market in catalog}) == 40
    assert Counter(market["region"] for market in catalog) == {
        "欧州": 13, "アジア太平洋": 12, "米州": 7, "アフリカ": 5, "中東": 3
    }
    assert sorted(tuple(market["id"] for market in catalog
                        if len(market["territories"]) > 1)) == [
        "MKT-01", "MKT-05", "MKT-08", "MKT-13"
    ]
    cities = [city["id"] for market in catalog for city in market["cities"]]
    assert len(cities) == len(set(cities)) == 155
    for market in catalog:
        assert 3 <= len(market["cities"]) <= 5
        assert {city["territoryId"] for city in market["cities"]} <= {
            territory["id"] for territory in market["territories"]
        }

    result = page.evaluate("""() => {
      const trial = structuredClone(S);
      const identityBefore = JSON.stringify([
        trial.firms.map(f=>[f.id,f.owners,f.loans]),trial.worldExpansion.companies,trial.worldExpansion.facilities
      ]);
      trial.year=1905; trial.month=10; applyWorldHistory(trial);
      const closed=trial.worldExpansion.openMarkets['MKT-11']===null;
      trial.month=11; applyWorldHistory(trial); applyWorldHistory(trial);
      const opened=trial.worldExpansion.openMarkets['MKT-11']===ym(1905,11);
      trial.year=1923; trial.month=1; applyWorldHistory(trial);
      syncWorldIdentities(trial); validateWorldExpansion(trial);
      return {
        closed,opened, events:trial.worldExpansion.appliedEvents.length,
        oldTerritory:trial.worldExpansion.territoryJurisdictions['TER-01-01'],
        newTerritory:trial.worldExpansion.territoryJurisdictions['TER-01-02'],
        unchanged:identityBefore===JSON.stringify([
          trial.firms.map(f=>[f.id,f.owners,f.loans]),trial.worldExpansion.companies,trial.worldExpansion.facilities
        ]),
        stillForty:Object.keys(trial.worldExpansion.openMarkets).length===40
      };
    }""")
    assert result == {
        "closed": True, "opened": True, "events": 3, "oldTerritory": "JUR-UK",
        "newTerritory": "JUR-IE", "unchanged": True, "stillForty": True,
    }


def test_market_opening(page):
    result = page.evaluate("""async () => {
      const original=S,persist=saveAuto,view=VIEW_FIRM,country=VIEW_COUNTRY,oldPage=PAGE;
      try {
        S=structuredClone(original);
        S.year=1905; S.month=10; S.monthCommitted=ym(1905,10)-1;
        saveAuto=async()=>true;
        await runMonth();
        if(S.month!==11||!S.world.NO)return {failure:LAST_MONTH_DIAGNOSTIC};
        const seller=company(S.playerId,S);
        const contract=exportChannel(seller,'NO',S);
        PAGE='worldMap';render();
        const hasLink=!!document.querySelector('[data-market-id="MKT-11"] [data-mk-region="NO"]');
        PAGE='corporateSubsidiaries';render();
        document.querySelector('#subName').value='ノルウェー試験子会社';
        document.querySelector('#subCountry').value='NO';
        document.querySelector('#subIndustry').value='manufacturing';
        document.querySelector('#subCapital').value='750000';
        createSub();
        const child=S.firms.find(f=>f.name==='ノルウェー試験子会社');
        await runMonth();
        const replay=parsePayload(savePayload(S));
        const registration=replay.worldExpansion.companies[child?.id];
        return {
           opened:S.month===12 && S.worldExpansion.openMarkets['MKT-11']===ym(1905,11),
           market:S.world.NO.demand>0,
           resourcePool:npcMarketV033(S,'NO','steel').producedTotal>0,
           subsidiary:child?.country==='NO'&&registration?.jurisdictionId==='JUR-NO'&&
             registration?.currencyId==='CUR-NOK',
           contract:contract.capacity>0,
           events:S.worldExpansion.appliedEvents.filter(e=>e.id==='HIST-NO-1905').length===1,
           restored:replay.world.NO.demand===S.world.NO.demand,
           hasLink, clean:check(S).length===0 && consolidate(S).errors.length===0
        };
      } finally {
        S=original;saveAuto=persist;VIEW_FIRM=view;VIEW_COUNTRY=country;PAGE=oldPage;
        LAST_MONTH_DIAGNOSTIC=null;MONTH_DIAGNOSTIC_OPEN=false;render();
      }
    }""")
    assert all(value is True for value in result.values()), result


def test_saves(page):
    result = page.evaluate("""async () => {
      const state = savePayload(S);
      const payload = JSON.parse(state);
      const restored = parsePayload(state);
      payload.version=1;
      let rejectsOld=false, rejectsBad=false;
      try {parsePayload(JSON.stringify(payload))}catch {rejectsOld=true}
      const inner=JSON.parse(payload.payload);
      const first=Object.values(inner.worldExpansion.facilities)[0];
      first.ownerCompanyId='unknown';
      payload.payload=JSON.stringify(inner);payload.checksum=hash(payload.payload);payload.version=SAVE_FORMAT_VERSION;
      try {parsePayload(JSON.stringify(payload))}catch {rejectsBad=true}
      const persist=saveAuto; saveAuto=async()=>true;
      try {
        await runMonth();
        const firstResult={month:S.monthCommitted,rng:S.rng,firms:S.firms,ledger:S.consoHistory};
        S=parsePayload(state);
        await runMonth();
        const secondResult={month:S.monthCommitted,rng:S.rng,firms:S.firms,ledger:S.consoHistory};
        const difference=(a,b,path)=>{
          if(typeof a!==typeof b||a===null||b===null||typeof a!=='object')
            return Object.is(a,b)?null:{path,a,b};
          if(Array.isArray(a)!==Array.isArray(b))return {path,a,b};
          for(const key of new Set([...Object.keys(a),...Object.keys(b)])){
            const result=difference(a[key],b[key],path+'.'+key);
            if(result)return result;
          }
          return null;
        };
        const detail=difference(firstResult,secondResult,'result');
        const finite=firstResult.firms.every(f=>f.step4OrgV1.scaleHistory
          .every(snapshot=>Number.isFinite(snapshot.complexityPoints)));
        const replay=!detail;
        return {rejectsOld,rejectsBad,replay,detail,finite,advanced:S.month===2,roundTrip:restored.worldExpansion.catalogVersion===1};
      } finally {saveAuto=persist}
    }""")
    assert result["detail"] is None, result
    result.pop("detail")
    assert all(result.values()), result

    assert page.evaluate("""async () => {
      const before=S, advance=applyWorldHistory;
      applyWorldHistory=trial=>{
        trial.worldExpansion.openMarkets['MKT-01']=null;
        throw Error('検証用の月次障害');
      };
      try {
        await runMonth();
        return S===before && S.worldExpansion.openMarkets['MKT-01']!==null &&
          LAST_MONTH_DIAGNOSTIC?.message.includes('月次障害');
      } finally {applyWorldHistory=advance}
    }""")

    assert page.evaluate("saveAuto()") is True
    page.evaluate("runMonth()")
    assert page.evaluate("S.month") == 3
    page.evaluate("""async () => {
      const active = await idbRead('meta','active');
      const row = await idbRead('snapshots','auto:'+active.slot);
      await idbWrite('snapshots',{...row,serialized:'broken'});
      writeSafetySnapshotV037=()=>false;
      localStorage.removeItem(EMERGENCY_KEY);
    }""")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("STORAGE_READY && S !== null")
    assert page.evaluate("S.month") == 2
    assert page.evaluate("check(S)") == []


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=ROOT))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
                args=["--no-sandbox"]
            )
            with browser.new_context() as context:
                page = context.new_page()
                errors, external = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                origin = f"http://127.0.0.1:{server.server_port}"
                def route_request(route):
                    if not route.request.url.startswith(origin + "/"):
                        external.append(route.request.url)
                        route.abort()
                    else:
                        route.continue_()
                context.route("**/*", route_request)
                page.goto(origin + "/index.html")
                page.wait_for_function("STORAGE_READY")
                assert page.locator('input[name="era"]').count() == 1
                for _ in range(4):
                    page.get_by_role("button", name="次へ").or_(
                        page.get_by_role("button", name="この条件で創業する")
                    ).click()
                page.wait_for_function("!SAVE_BUSY && S !== null")
                assert page.evaluate("""() => S.startYear===1900 && S.month===1 &&
                    S.config.difficulty==='normal' && check(S).length===0 && TECH_NODES.length===800""")
                test_catalog_and_history(page)
                test_market_opening(page)
                page.evaluate("() => { PAGE='worldMap'; render(); }")
                assert page.locator("[data-market-id]").count() == 40
                page.locator('[data-market-id="MKT-01"] summary').click()
                assert page.locator('[data-market-id="MKT-01"]').get_by_text("ダブリン").is_visible()
                test_saves(page)
                context.set_offline(True)
                page.evaluate("runMonth()")
                assert page.evaluate("S.month") == 3
                assert not errors and not external, (errors, external)
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    print("PASS world foundation: 40 markets, 155 cities, 1900, 800 technologies, events, v2 replay and recovery, offline")


if __name__ == "__main__":
    main()
