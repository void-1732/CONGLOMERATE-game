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
          const identityAfter=JSON.stringify([
            state.firms.map(f=>[f.id,f.owners,f.loans]),
            state.worldExpansion.companies,
            state.worldExpansion.facilities
          ]);
          const restored=parsePayload(savePayload(state));
          return {
            ...out,
            firstHistory,secondHistory:!secondHistory,rejectsConflict,
            irelandBefore:first.territoryId==='TER-01-02'
              &&first.marketId==='MKT-01'&&first.jurisdictionId==='JUR-UK',
            irelandAfter:later.jurisdictionId==='JUR-IE'
              &&later.marketId==='MKT-01',
            stableIdentity:identityBefore===identityAfter,
            roundTrip:worldCityLocation(restored,'CITY-01-04').jurisdictionId==='JUR-IE',
            allMarkets:Object.keys(restored.worldExpansion.openMarkets).length===40,
            clean:check(restored).length===0
          };
        }""")
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS Phase 1 world catalog unique IDs, territory location, history, ownership and restore")


if __name__ == "__main__":
    main()
