"""Documented sea, air, and Channel freight with equipment and historical closure."""
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_context(offline=True).new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result = page.evaluate("""() => {
          S=newGame({country:'US',era:1900,name:'Legacy sites',difficulty:'normal',history:'historical'});
          const legacyPortHidden=!factorySiteChoice('US').includes('US-SEA')
            &&siteInvestmentQuote('US-SEA','small','assembly',S)===null;
          const sample=[
            ['JP-US-SEATTLE-STEAM',1941,6],['US-JP-SEATTLE-STEAM',1910,1],
            ['NO-UK-NORTHSHIELDS-STEAM',1910,1],['UK-NO-NORTHSHIELDS-STEAM',1910,1],
            ['NO-DE-HAMBURG-STEAM',1910,1],['DE-NO-HAMBURG-STEAM',1910,1],
            ['UK-FR-SEA-1900',1901,1],['UK-FR-CHANNEL-1994',1994,7],
            ['US-UK-SEA-1900',1900,1],['UK-FR-HOUNSLOW-LEATHER',1920,1]
          ];
          const checks={legacyPortHidden};
          function setMonth(period){
            S.year=Math.floor(period/12);
            S.month=period%12+1;
            applyWorldHistory(S);syncWorldIdentities(S);
          }
          function rejects(action){
            try{action();return false;}catch{return true;}
          }
          for(const [profileId,year,month] of sample){
            const profile=worldInternationalProfile(profileId);
            const from=findSite(profile.from),to=findSite(profile.to);
            const air=profile.mode==='air',productId=air?'PRD-M38':'PRD-R19';
            const home=from.country==='NO'?to.country:from.country;
            S=newWorldGame({country:home,name:'Historic steam freight '+home});
            const root=company(S.playerId);
            const otherCountry=home===from.country?to.country:from.country;
            const beforeOpen=(otherCountry!=='NO'&&!air)||!worldInternationalRouteAvailable(S,profileId);
            const earlyAirfields=air&&(!siteVisibleInGame(from,S)&&!siteVisibleInGame(to,S))
              &&siteInvestmentQuote(from.id,'small','assembly',S)===null;
            if(otherCountry==='NO')setMonth(ym(1910,1));
            const capital=localFromBase(600000,root.country),payer=S.seq;
            post(root,{investment:capital},{cash:capital},'検証用海外法人設立','investing',S);
            const other=initFirm(S,{name:'Historic freight receiver '+otherCountry,country:otherCountry,
              seedBase:600000,publicOwnership:false});
            other.owners=[{id:root.id,econ:1,vote:1}];
            registerEquityLink(S,{parentId:root.id,childId:other.id,ratio:1,kind:'foundation',considerationLocal:capital,
              buyerJournal:payer,childJournal:other.journals.find(j=>j.text==='創業資本').id,
              bookEquityBase:baseFromLocal(financials(other).equity,other.country),
              cashAcquiredBase:baseFromLocal(acc(other,'cash'),other.country)});
            const seller=from.country===home?root:other,buyer=to.country===home?root:other;
            seller.plants[0].siteId=from.id;buyer.plants[0].siteId=to.id;
            for(const f of [seller,buyer])f.research.tree.done=[...new Set([...f.research.tree.done,'production-1'])];
            const vehicles=(profile.vehicles??[profile.truck]).map(id=>[seller,id,1,2500]);
            const terminals=(profile.terminals??['PRD-E20']).map(id=>[buyer,id,1,600]);
            const fixtureStock=air?[]:[[seller,profile.fuel,10,500],[seller,productId,5,200]];
            for(const [f,id,q,value] of [...vehicles,...terminals,...fixtureStock]){
              post(f,{materials:value},{cash:value},'検証用の有償現物調達','operating',S);
              f.stock[id]={q,v:value};
            }
            setMonth(ym(year,month));
            const route=worldInternationalRegisterRoute(S,seller.id,profileId);
            const depot=worldInternationalInstallWarehouse(S,buyer.id,buyer.plants[0].id,profileId);
            const orderInputs={routeId:route.id,warehouseId:depot.id,productId,quantity:2,cargoLitres:air?18:0,
              unitPriceSeller:localFromBase(1000,seller.country),maxPaymentBuyer:10000000};
            let airEquipment=true;
            if(air){
              const map=worldMapNetwork(S),fields=map.routes.find(r=>r.id===profileId);
              const leather=worldBuyRegionalSupply(S,seller.id,seller.plants[0].id,'UK-HOUNSLOW-LEATHER',5);
              const missingFuel=worldInternationalQuote(S,route,productId,2,orderInputs.unitPriceSeller,buyer.id).problem;
              const petrol=worldBuyRegionalSupply(S,seller.id,seller.plants[0].id,'UK-HOUNSLOW-PETROL',10);
              airEquipment=earlyAirfields&&siteVisibleInGame(from,S)&&siteVisibleInGame(to,S)
                &&route.assetValue===2500&&seller.stock['PRD-E19'].q===0&&!!missingFuel
                &&fields.from.id===from.id&&fields.to.id===to.id&&fields.mode==='air'
                &&fields.from.cityId==='CITY-01-01'&&fields.to.cityId==='CITY-02-01'
                &&fields.from.lon!==map.cities.find(c=>c.id===fields.from.cityId).lon
                &&fields.to.lon!==map.cities.find(c=>c.id===fields.to.cityId).lon
                &&leather.quantity===5&&petrol.quantity===10
                &&rejects(()=>worldInternationalPlaceOrder(S,buyer.id,{...orderInputs,productId:'PRD-R19'}));
            }
            const order=worldInternationalPlaceOrder(S,buyer.id,orderInputs);
            worldInternationalActOrder(S,seller.id,order.id,'approve');
            setMonth(ym(year,month)+1);worldInternationalResolveOrders(S);
            const t=S.worldExpansion.internationalShipments[0];
            if(!t)throw Error(profileId+' '+order.result+' '+JSON.stringify(
              {quote:worldInternationalQuote(S,route,order.productId,order.quantity,order.unitPriceSeller,buyer.id),
                cash:acc(buyer,'cash'),materials:acc(seller,'materials'),fx:[S.world[seller.country].fx,S.world[buyer.country].fx],
                stock:[seller.stock[productId],seller.stock[profile.fuel]]}));
            const pending=t?.status==='IN_TRANSIT'&&t.fuelRequired>0&&t.fuelCost>0
              &&t.dutyBuyer>0&&route.fromSiteId===from.id&&route.toSiteId===to.id
              &&seller.stock[profile.fuel].q===10-t.fuelRequired
              &&(!air||t.loadKg===3)&&!check(S).length;
            setMonth(t.dueAt);
            const currentMonth=ym(S.year,S.month),window= WORLD_INTERNATIONAL_ROUTE_EVIDENCE[profileId];
            const expired=currentMonth>=window.untilMonth;
            const respectsClosure=!expired||(!worldInternationalRouteAvailable(S,profileId)
              &&rejects(()=>worldInternationalPlaceOrder(S,buyer.id,orderInputs)));
            worldInternationalReceiveShipments(S);
            const saved=parsePayload(savePayload(S));
            const restored=saved.worldExpansion.internationalShipments[0];
            checks[profileId]=beforeOpen&&pending&&respectsClosure&&airEquipment&&t.status==='DELIVERED'
              &&buyer.stock[productId].q===2&&restored.status==='DELIVERED'&&!check(saved).length
              &&!consolidate(saved).errors.length
              &&(!from.worldOnly||WORLD_LOCATIONS.has('LOC-'+from.id))
              &&(!to.worldOnly||WORLD_LOCATIONS.has('LOC-'+to.id));
          }
          return checks;
        }""")
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS Phase 4: ten documented sea, air, and Channel directions, finite cargo, customs, closure and save")


if __name__ == "__main__":
    main()
