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
          const out={catalog:validateWorldCatalog(),
            legacyHomeSites:Object.entries({"UK":"UK-MID","FR":"FR-PAR","DE":"DE-RUH","NO":"NO-OSL","JP":"JP-TOK","US":"US-DET","CA":"CA-MTL","AU":"AU-SYD","NZ":"NZ-WLG","MX":"MX-VER","BR":"BR-RIO","AR":"AR-BUE","CL":"CL-VAP","CO":"CO-CTG","SE":"SE-GOT","NL":"NL-ROT","IT":"IT-GEN","EG":"EG-ALX","IN":"IN-BOM","ZA":"ZA-CPT","SG":"SG-SIN","TH":"TH-BKK","CN":"CN-HAN","ID":"ID-BAT","NG":"NG-LAG","ES":"ES-BIL","PH":"PH-MNL","RU":"RU-SPB","KR":"KR-BUS","TR":"TR-IZM","MY":"MY-PEN","KE":"KE-MBA","MA":"MA-CAS","CH":"CH-BAS","AT":"AT-VIE","PL":"PL-GDY","GR":"GR-PIR","VN":"VN-SGN","IR":"IR-BND","BE":"BE-ANR","PT":"PT-LIS","IE":"IE-DUB","SA":"SA-JED"}).every(([code,id])=>homeSite(code).id===id)};
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
          const incomplete=['CITY-13-01','CITY-13-04'];
          const registered=['CITY-05-01','CITY-08-02','CITY-08-03','CITY-08-04','CITY-13-02'];
          const compositeClosed=incomplete.every(id=>{
            const city=worldCityLocation(state,id);
            return !city.marketOpen&&city.economicEngineConnected;
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
            ==='JUR-PT-REPUBLIC'&&worldCityLocation(state,'CITY-05-03').marketOpen
            &&state.world.PT?.currency==='EUR'&&state.world.ES?.currency==='EUR'
            &&state.worldExpansion.appliedEvents.some(e=>e.id==='HIST-PT-1910');
          const identityAfter=JSON.stringify([
            state.firms.map(f=>[f.id,f.owners,f.loans]),
            state.worldExpansion.companies,
            state.worldExpansion.facilities
          ]);
          const euroShared=state.worldExpansion.euroFxUnified===true
            &&['FR','DE','IE','LU'].every(code=>state.world[code]?.currency==='EUR'
              &&state.world[code].fx===state.world.FR.fx);
          const euroFixture=structuredClone(state);
          euroFixture.world.FR.fx*=1.1;
          worldMatchLedgerCurrencyRates(euroFixture);
          const euroFollowsMarket=['DE','IE','LU'].every(code=>euroFixture.world[code].fx===euroFixture.world.FR.fx)
            &&euroFixture.world.FR.fx!==state.world.FR.fx;
          const badEuro=structuredClone(euroFixture);badEuro.world.DE.fx+=1;
          let euroTamperRejected=false;
          try{parsePayload(savePayload(badEuro))}catch{euroTamperRejected=true}
          const legacyEuro=structuredClone(state);
          delete legacyEuro.worldExpansion.euroFxUnified;
          delete legacyEuro.worldExpansion.modernCurrencyVersion;
          for(const [code,w] of Object.entries(legacyEuro.world))w.currency=worldLedgerCurrencyId(legacyEuro,code).slice(4);
          syncWorldIdentities(legacyEuro);
          worldMatchLedgerCurrencyRates(legacyEuro);
          legacyEuro.world.DE.fx+=1;legacyEuro.world.DE.currency='DEM';
          const legacyEuroSaved=parsePayload(savePayload(legacyEuro));
          const legacyEuroPreserved=legacyEuroSaved.world.DE.fx===legacyEuro.world.DE.fx
            &&legacyEuroSaved.world.DE.currency==='DEM'
            &&JSON.stringify(legacyEuroSaved.firms)===JSON.stringify(legacyEuro.firms);
          const distanceRefs=['JP-SHIMBASHI-YOKOHAMA','JP-TOMEI-TOKYO-KOMAKI','AL-IT-DURRES-BARI-TIMBER']
            .every(id=>worldRouteDistanceReference(id,state).matched);
          const sea=worldInternationalProfile('JP-US-SEATTLE-STEAM',state);
          const oldDistanceState=structuredClone(state);delete oldDistanceState.worldExpansion.routeDistanceVersion;
          const oldDistance=worldInternationalProfile('JP-US-SEATTLE-STEAM',oldDistanceState);
          const actualDistance=sea.distanceKm===7919
            &&oldDistance.distanceKm===8100
            &&worldInternationalProfile('JP-US-YOKOHAMA-TRANSFER',state).distanceKm===7948
            &&worldFreightCharge(sea,2,'JP')===Math.round(7919*.025*2*100)
            &&worldInternationalFuelRequired(sea,25)===11
            &&worldMapNetwork(state).routes.find(r=>r.id==='JP-US-SEATTLE-STEAM').distanceKm===7919
            &&worldMapDistanceNotice('JP-US-SEATTLE-STEAM',oldDistanceState).includes('LEGACY_MODEL');
          const distanceNotInvented=!worldRouteDistanceReference('UK-FR-HOUNSLOW-LEATHER',state).matched
            &&worldMapDistanceNotice('UK-FR-HOUNSLOW-LEATHER',state).includes('PROVISIONAL');
          const modernExpected={AU:'AUD',MX:'MXN',BR:'BRL',AR:'ARS',CN:'CNY',RU:'RUB',TR:'TRY',MA:'MAD',VN:'VND',IR:'IRR'};
          out.modernIndependentCurrencies=Object.entries(modernExpected).every(([code,id])=>
            state.world[code]?.currency===id&&firmCurrency({country:code},state)===id);
          const modernFx=structuredClone(state);
          modernFx.world.AU.fx*=1.01;
          const independentFx=modernFx.world.AU.fx;
          worldMatchLedgerCurrencyRates(modernFx);
          out.modernIndependentFx=modernFx.world.AU.fx===independentFx
            &&modernFx.world.AU.fx!==state.world.AU.fx;
          const oldCurrency=structuredClone(state);
          delete oldCurrency.worldExpansion.modernIndependentCurrencyVersion;
          delete oldCurrency.worldExpansion.modernCurrencyVersion;
          for(const [code,w] of Object.entries(oldCurrency.world))w.currency=WORLD_ENGINE_CURRENCIES[code].slice(4);
          worldMatchLedgerCurrencyRates(oldCurrency);
          for(const code of Object.keys(modernExpected)){
            oldCurrency.world[code].currency=WORLD_ENGINE_CURRENCIES[code].slice(4);
          }
          syncWorldIdentities(oldCurrency);
          const oldCurrencyLoaded=parsePayload(savePayload(oldCurrency));
          out.oldCurrencyPreserved=Object.keys(modernExpected).every(code=>
            oldCurrencyLoaded.world[code].currency===oldCurrency.world[code].currency)
            &&JSON.stringify(oldCurrencyLoaded.firms)===JSON.stringify(oldCurrency.firms);
          const badCurrency=structuredClone(state);badCurrency.world.AU.currency='AUP';
          try{parsePayload(savePayload(badCurrency));out.rejectModernCurrencyTamper=false}
          catch{out.rejectModernCurrencyTamper=true}
          const modernFull=structuredClone(state);
          modernFull.year=1935;modernFull.month=1;applyWorldHistory(modernFull);syncWorldIdentities(modernFull);
          const expectedCurrency={FR:'EUR',DE:'EUR',NL:'EUR',BE:'EUR',IT:'EUR',ES:'EUR',PT:'EUR',AT:'EUR',GR:'EUR',IE:'EUR',LU:'EUR',NZ:'NZD',ZA:'ZAR',SG:'SGD',MY:'MYR',ID:'IDR',NG:'NGN',KR:'KRW',KE:'KES'};
          out.modernFull=Object.keys(modernFull.world).length===46&&Object.entries(expectedCurrency).every(([code,id])=>modernFull.world[code]?.currency===id)
            &&WORLD_EURO_MEMBERS.every(code=>modernFull.world[code].fx===modernFull.world.FR.fx&&localFromBase(155,code,modernFull)===100)
            &&modernFull.world.SA.fx===modernFull.world.US.fx/3.75;
          const modernFloating=structuredClone(modernFull);
          modernFloating.world.UK.fx*=1.1;modernFloating.world.US.fx*=1.05;
          modernFloating.world.FR.fx*=1.04;modernFloating.world.SG.fx*=1.02;
          worldMatchLedgerCurrencyRates(modernFloating);
          out.modernRegimes=modernFloating.world.NZ.fx===modernFull.world.NZ.fx
            &&modernFloating.world.ZA.fx===modernFull.world.ZA.fx
            &&modernFloating.world.NG.fx===modernFull.world.NG.fx
            &&modernFloating.world.PH.fx===modernFull.world.PH.fx
            &&modernFloating.world.MY.fx===modernFull.world.MY.fx
            &&modernFloating.world.KR.fx===modernFull.world.KR.fx
            &&modernFloating.world.SA.fx===modernFloating.world.US.fx/3.75
            &&WORLD_EURO_MEMBERS.every(code=>modernFloating.world[code].fx===modernFloating.world.FR.fx);
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
          delete legacy.world.BE;
          delete legacy.npcSupplyV033.markets.BE;
          delete legacy.world.PT;
          delete legacy.npcSupplyV033.markets.PT;
          for(const [code,row] of Object.entries(WORLD_MARKET_ONBOARDING))if(row.introducedIn>16){delete legacy.world[code];delete legacy.npcSupplyV033.markets[code];}
          ensureSupplyNetwork(legacy);
          const belgiumLegacy=worldCityLocation(legacy,'CITY-08-03');
          const belgiumBeforeUpgrade=belgiumLegacy.jurisdictionId===null
            &&!belgiumLegacy.economicEngineConnected&&!belgiumLegacy.marketOpen;
          syncWorldIdentities(legacy);
          const oldAccepted=check(legacy).length===0;
          const upgraded=parsePayload(savePayload(legacy));
          const upgradePreservesLedger=oldAccepted
            &&upgraded.worldExpansion.marketRegistryVersion===WORLD_MARKET_REGISTRY_VERSION
            &&worldCityLocation(upgraded,'CITY-05-03').jurisdictionId==='JUR-PT-REPUBLIC'
            &&upgraded.world.PT?.currency==='EUR'
            &&JSON.stringify(upgraded.firms.map(f=>[f.id,f.owners,f.journals,f.stock]))
              ===JSON.stringify(legacy.firms.map(f=>[f.id,f.owners,f.journals,f.stock]))
            &&check(upgraded).length===0;
          return {
            ...out,compositeClosed,compositeOpen,compositeLaw,portugalRepublic,upgradePreservesLedger,
            euroShared,euroFollowsMarket,euroTamperRejected,legacyEuroPreserved,distanceRefs,actualDistance,distanceNotInvented,
            belgiumBeforeUpgrade,
            belgiumAfterUpgrade:worldCityLocation(upgraded,'CITY-08-03').marketOpen
              &&upgraded.world.BE?.code==='BE'&&upgraded.world.NL?.code==='NL'
              &&WORLD_ENGINE_BY_MARKET['MKT-08']==='NL',
            historicMoney,historicalMoneyIsNotLedger,
            firstHistory,secondHistory:!secondHistory,rejectsConflict,
            irelandBefore:first.territoryId==='TER-01-02'
              &&first.marketId==='MKT-01'&&first.jurisdictionId==='JUR-UK'
              &&!first.marketOpen&&first.economicEngineConnected,
            irelandAfter:later.jurisdictionId==='JUR-IE'
              &&later.marketId==='MKT-01'&&later.marketOpen&&later.economicEngineConnected
              &&state.world.IE?.currency==='EUR'&&WORLD_ENGINE_BY_MARKET['MKT-01']==='UK'
              &&upgraded.world.IE?.code==='IE',
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
