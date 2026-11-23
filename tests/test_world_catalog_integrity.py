"""Phase 1 catalog reference integrity, historical jurisdiction and save consistency."""
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
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"), wait_until="domcontentloaded")
        page.wait_for_function("STORAGE_READY")
        result = page.evaluate("""() => {
          const out={catalog:validateWorldCatalog()};
          const m=WORLD_MARKETS[0], originalId=m.cities[1].id;
          try{
            m.cities[1].id=m.cities[0].id;
            try{validateWorldCatalog();out.rejectDuplicateCity=false}
            catch{out.rejectDuplicateCity=true}
          }finally{m.cities[1].id=originalId}
          const originalTerritory=m.cities[3].territoryId;
          try{
            m.cities[3].territoryId='TER-05-02';
            try{validateWorldCatalog();out.rejectMismatchedTerritory=false}
            catch{out.rejectMismatchedTerritory=true}
          }finally{m.cities[3].territoryId=originalTerritory}
          const location=WORLD_LOCATIONS.get('LOC-UK-LON');
          const originalCityId=location.cityId;
          try{
            location.cityId='CITY-05-02';
            try{validateWorldCatalog();out.rejectMismatchedLocation=false}
            catch{out.rejectMismatchedLocation=true}
          }finally{location.cityId=originalCityId}
          const state=newWorldGame({country:'JP',name:'Phase1検証'});
          // Grouped legal jurisdictions do not imply a trading engine.
          const incomplete=['CITY-05-03','CITY-05-04','CITY-08-03',
            'CITY-08-04','CITY-13-01','CITY-13-04'];
          const registered=['CITY-05-01','CITY-08-02','CITY-13-02'];
          const compositeClosed=incomplete.every(id=>{
            const city=worldCityLocation(state,id);
            return !city.marketOpen&&!city.economicEngineConnected;
          });
          const compositeLaw=(
            worldCityLocation(state,'CITY-05-03').jurisdictionId==='JUR-PT-KINGDOM'
            &&worldCityLocation(state,'CITY-08-03').jurisdictionId==='JUR-BE'
            &&worldCityLocation(state,'CITY-08-04').jurisdictionId==='JUR-LU'
            &&worldCityLocation(state,'CITY-13-01').jurisdictionId===null
            &&makeWorldExpansion(16).territoryJurisdictions['TER-05-02']===null
            &&makeWorldExpansion(17).territoryJurisdictions['TER-05-02']==='JUR-PT-KINGDOM'
          );
          const compositeOpen=registered.every(id=>{
            const city=worldCityLocation(state,id);
            return city.jurisdictionId!=null&&city.marketOpen;
          });
          const historicMoney=(
            worldHistoricalMonetaryReference('TER-02-01',ym(1900,1)).currencyId==='CUR-FRF-OLD'
            &&worldHistoricalMonetaryReference('TER-02-01',ym(1959,12)).currencyId==='CUR-FRF-OLD'
            &&worldHistoricalMonetaryReference('TER-02-01',ym(1960,1)).currencyId==='CUR-FRF'
            &&worldHistoricalMonetaryReference('TER-02-01',ym(1999,1)).currencyId==='CUR-EUR'
            &&worldHistoricalMonetaryReference('TER-03-01',ym(1900,1)).currencyId==='CUR-GMK'
            &&worldHistoricalMonetaryReference('TER-03-01',ym(1924,10)).currencyId==='CUR-RMK'
            &&worldHistoricalMonetaryReference('TER-03-01',ym(1948,7)).currencyId==='CUR-DEM'
            &&worldHistoricalMonetaryReference('TER-05-02',ym(1900,1)).currencyId==='CUR-PTR'
            &&worldHistoricalMonetaryReference('TER-05-02',ym(1911,6)).currencyId==='CUR-PTE'
            &&worldHistoricalMonetaryReference('TER-08-02',ym(1900,1)).currencyId==='CUR-BEF'
            &&worldHistoricalMonetaryReference('TER-08-03',ym(1900,1)).currencyId==='CUR-LU-MULTI'
            &&worldHistoricalMonetaryReference('TER-08-03',ym(1920,1)).currencyId==='CUR-LUF'
            &&worldHistoricalMonetaryReference('TER-24-01',ym(1900,1)).currencyId==='CUR-GBP'
            &&worldHistoricalMonetaryReference('TER-24-01',ym(1910,1)).currencyId==='CUR-AUP'
            &&worldHistoricalMonetaryReference('TER-24-01',ym(1966,3)).currencyId==='CUR-AUD'
            &&worldHistoricalMonetaryReference('TER-25-01',ym(1967,8)).currencyId==='CUR-NZD'
            &&worldHistoricalMonetaryReference('TER-33-01',ym(1900,1)).currencyId==='CUR-GBP'
            &&worldHistoricalMonetaryReference('TER-33-01',ym(1922,5)).currencyId==='CUR-ZAP'
            &&worldHistoricalMonetaryReference('TER-33-01',ym(1961,3)).currencyId==='CUR-ZAR'
            &&worldHistoricalMonetaryReference('TER-03-01',ym(1960,1)).kind==='PARTIAL_TERRITORY_REFERENCE'
            &&worldHistoricalMonetaryReference('TER-13-01',ym(1900,1))===null
          );
          // This is a sourced historical reference only. Do not retroactively
          // redenominate firms, cash, contracts, journals or FX in saved games.
          const historicalMoneyIsNotLedger=(
            worldCityLocation(state,'CITY-02-01').historicalMoney.currencyId==='CUR-FRF-OLD'
            &&WORLD_ENGINE_CURRENCIES.FR==='CUR-EUR'
            &&WORLD_ENGINE_CURRENCIES.DE==='CUR-EUR'
            &&worldCityLocation(state,'CITY-05-03').historicalMoney.currencyId==='CUR-PTR'
            &&worldCityLocation(state,'CITY-05-03').jurisdictionId==='JUR-PT-KINGDOM'
            &&worldCityLocation(state,'CITY-05-03').marketOpen===false
          );
          const first=worldCityLocation(state,'CITY-01-04');
          const identityBefore=JSON.stringify([
            state.firms.map(f=>[f.id,f.owners,f.loans]),
            state.worldExpansion.companies,
            state.worldExpansion.facilities
          ]);
          const snapshot=makeWorldExpansion();
          const firstHistory=recordWorldEvent(snapshot,WORLD_EVENTS[0]);
          const secondHistory=recordWorldEvent(snapshot,WORLD_EVENTS[0]);
          let rejectsConflict=false;
          try{recordWorldEvent(snapshot,{...WORLD_EVENTS[0],jurisdictionId:'JUR-UK'})}
          catch{rejectsConflict=true}
          state.year=1923;state.month=1;
          applyWorldHistory(state);syncWorldIdentities(state);validateWorldExpansion(state);
          const later=worldCityLocation(state,'CITY-01-04');
          const portugalRepublic=worldCityLocation(state,'CITY-05-03').jurisdictionId
            ==='JUR-PT-REPUBLIC'&&!worldCityLocation(state,'CITY-05-03').marketOpen
            &&state.worldExpansion.appliedEvents.some(e=>e.id==='HIST-PT-1910');
          const identityAfter=JSON.stringify([
            state.firms.map(f=>[f.id,f.owners,f.loans]),
            state.worldExpansion.companies,
            state.worldExpansion.facilities
          ]);
          const restored=parsePayload(savePayload(state));
          // Version 16 saves remain legal inputs. Upgrading must not
          // rewrite firms, cash, ownership or historical pre-1910 events.
          const legacy=structuredClone(state);
          const oldWorld=makeWorldExpansion(16);
          for(const event of worldHistoryThrough(ym(legacy.year,legacy.month),16))
            recordWorldEvent(oldWorld,event);
          Object.assign(legacy.worldExpansion,{
            marketRegistryVersion:16,
            territoryJurisdictions:oldWorld.territoryJurisdictions,
            openMarkets:oldWorld.openMarkets,
            appliedEvents:oldWorld.appliedEvents
          });
          delete legacy.worldExpansion.weightDutyFromSeq;
          syncWorldIdentities(legacy);
          const oldAccepted=check(legacy).length===0;
          const upgraded=parsePayload(savePayload(legacy));
          const upgradePreservesLedger=oldAccepted
            &&upgraded.worldExpansion.marketRegistryVersion===WORLD_MARKET_REGISTRY_VERSION
            &&worldCityLocation(upgraded,'CITY-05-03').jurisdictionId==='JUR-PT-REPUBLIC'
            &&JSON.stringify(upgraded.firms.map(f=>[f.id,f.owners,f.journals,f.stock]))
              ===JSON.stringify(legacy.firms.map(f=>[f.id,f.owners,f.journals,f.stock]))
            &&check(upgraded).length===0;
          return {
            ...out,compositeClosed,compositeOpen,compositeLaw,portugalRepublic,upgradePreservesLedger,
            historicMoney,historicalMoneyIsNotLedger,
            firstHistory,secondHistory:!secondHistory,rejectsConflict,
            irelandBefore:first.territoryId==='TER-01-02'
              &&first.marketId==='MKT-01'&&first.jurisdictionId==='JUR-UK'
              &&!first.marketOpen&&!first.economicEngineConnected,
            irelandAfter:later.jurisdictionId==='JUR-IE'
              &&later.marketId==='MKT-01'&&!later.marketOpen&&!later.economicEngineConnected,
            stableIdentity:identityBefore===identityAfter,
            roundTrip:worldCityLocation(restored,'CITY-01-04').jurisdictionId==='JUR-IE',
            allMarkets:Object.keys(restored.worldExpansion.openMarkets).length===40,
            clean:check(restored).length===0
          };
        }""")
        assert all(result.values()), result
        for country, reference in (("FR", "CUR-FRF-OLD"), ("DE", "CUR-GMK")):
            preserved = page.evaluate("""country => {
              S=newWorldGame({country,name:'会計通貨監査'});
              VIEW_FIRM=S.playerId;VIEW_COUNTRY=country;PAGE='finance';
              const firm=current();
              const balances=()=>JSON.stringify([firm.ledger,firm.stock,firm.journals]);
              const before=balances();
              render();
              return before===balances()&&firmCurrency(firm,S)==='EUR';
            }""", country)
            notice = page.locator("[data-world-currency-audit]")
            assert preserved and notice.count() == 1
            assert f"帳簿通貨 CUR-EUR ／ 年代別の史料参照 {reference}" in notice.inner_text()
        page.evaluate("S.year=1999;applyWorldHistory(S);syncWorldIdentities(S);render();")
        assert notice.count() == 0
        assert not errors, errors
        browser.close()
    print("PASS Phase 1 world catalog unique IDs, territory location, history, ownership and restore")


if __name__ == "__main__":
    main()
