"""Normal-world external procurement supplies physically booked rail and road cargo."""

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
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        page.evaluate("""() => {
          S=newWorldGame({country:'JP',name:'Phase 2-K supplies'});
          VIEW_FIRM=S.playerId;PAGE='facilityProduction';
          requestOperationSaveV037=()=>true;
          window.openingCash=acc(company(S.playerId),'cash');
          render();
        }""")
        page.locator("#world-domestic > summary").click()
        supply = page.locator('form[data-world-domestic="supply"]:has(input[value^="JP-KIBA-TIMBER|"])')
        assert supply.count() == 1
        supply.locator('[name="quantity"]').fill("6")
        supply.get_by_role("button", name="現物を仕入れる").click()
        result = page.evaluate("""() => {
          const seller=company(S.playerId),origin=seller.plants[0];
          const wood=S.worldExpansion.regionalSupplyPurchases[0];
          const uiPurchase=wood.supplyId==='JP-KIBA-TIMBER'&&wood.quantity===6
            &&seller.stock['PRD-R19'].q===6&&seller.stock['PRD-R19'].v===wood.amount
            &&acc(seller,'cash')===openingCash-wood.amount&&acc(seller,'sales')===0;
          const subsidiary=(name,site)=>{
            const capital=60000000,parentJournal=S.seq;
            post(seller,{investment:capital},{cash:capital},'検証用設立','investing',S);
            const firm=initFirm(S,{name,country:'JP',seedBase:600000,publicOwnership:false});
            firm.owners=[{id:seller.id,econ:1,vote:1}];
            registerEquityLink(S,{parentId:seller.id,childId:firm.id,ratio:1,kind:'foundation',
              considerationLocal:capital,buyerJournal:parentJournal,
              childJournal:firm.journals.find(j=>j.text==='創業資本').id,
              bookEquityBase:baseFromLocal(capital,'JP'),cashAcquiredBase:baseFromLocal(acc(firm,'cash'),'JP')});
            firm.plants[0].siteId=site;
            return firm;
          };
          const railBuyer=subsidiary('Rail receiver','JP-YOK'),roadBuyer=subsidiary('Road receiver','JP-NGO');
          const jpTokyo=subsidiary('Another Tokyo buyer','JP-TOK');
          const railPlant=railBuyer.plants[0],roadPlant=roadBuyer.plants[0];
          const now=(year,month)=>{
            S.year=year;S.month=month;S.monthCommitted=ym(year,month)-1;
            applyWorldHistory(S);syncWorldIdentities(S);
          };
          const buy=(supplyId,qty,firm=seller,plant=origin)=>
            worldBuyRegionalSupply(S,firm.id,plant.id,supplyId,qty);
          const rejects=(fn,part)=>{try{fn();return false;}catch(e){return e.message.includes(part);}};
          const noEarlyCoal=rejects(()=>buy('JP-TOKYO-COAL-1910',1),'取扱期間');
          const wrongSite=rejects(()=>buy('JP-KIBA-TIMBER',1,railBuyer,railPlant),'所有施設');
          now(1910,4);
          const coal=buy('JP-TOKYO-COAL-1910',4);
          now(1911,4);
          const noExpired=rejects(()=>buy('JP-TOKYO-COAL-1910',1),'取扱期間');
          now(1912,1);
          const equipment=(firm,id,value)=>{
            post(firm,{materials:value},{cash:value},'検証用現物設備','operating',S);
            firm.stock[id]={q:1,v:value};
          };
          for(const f of [seller,railBuyer,roadBuyer]){
            if(!f.research.tree.done.includes('production-1'))f.research.tree.done.push('production-1');
          }
          for(const [id,v] of [['PRD-E16',1200],['PRD-E17',300],['PRD-E15',650]])equipment(seller,id,v);
          equipment(railBuyer,'PRD-E20',120);equipment(roadBuyer,'PRD-E20',120);
          const rail=worldRegisterDomesticRoute(S,seller.id,'JP-TOK','JP-YOK',29,'VERIFIED','JP-SHIMBASHI-YOKOHAMA');
          const railDepot=worldInstallDomesticWarehouse(S,railBuyer.id,railPlant.id,'JP-YOKOHAMA-SHINKO');
          const order=(route,depot,buyer,productId,quantity,unitPrice,maxFreight)=>{
            const o=worldPlaceDomesticOrder(S,buyer.id,{routeId:route.id,warehouseId:depot.id,productId,
              quantity,unitPrice,maxFreight});
            worldActOnDomesticOrder(S,seller.id,o.id,'approve');
            return o;
          };
          const shipment=o=>S.worldExpansion.domesticShipments.find(t=>t.orderId===o.id);
          const railOrder=order(rail,railDepot,railBuyer,'PRD-R19',6,wood.unitPrice,coal.unitPrice);
          now(1912,2);worldResolveDomesticOrders(S);
          const dispatch=shipment(railOrder);
          const railFreight=dispatch?.status==='IN_TRANSIT'&&dispatch.bookCost===wood.amount
            &&dispatch.freightCost===coal.unitPrice&&seller.stock['PRD-R04'].q===3;
          now(1912,3);worldReceiveDomesticShipments(S);
          const railArrival=dispatch.status==='DELIVERED'
            &&railBuyer.stock['PRD-R19'].v===wood.amount+coal.unitPrice;
          buy('JP-KIBA-TIMBER',174,jpTokyo,jpTokyo.plants[0]);
          now(1912,4);
          const exhausted=rejects(()=>buy('JP-KIBA-TIMBER',1),'残量')
            &&worldRegionalSupplyUsage(S.worldExpansion).get('JP-KIBA-TIMBER')===180;
          now(1950,12);
          const earlyToyosu=rejects(()=>buy('JP-TOYOSU-COAL',1),'取扱期間');
          now(1951,1);
          const toyosu=buy('JP-TOYOSU-COAL',2);
          const laterCoal=earlyToyosu&&toyosu.quantity===2&&seller.stock['PRD-R04'].q===5;
          now(1993,12);
          const dieselBefore=rejects(()=>buy('JP-KEIHIN-DIESEL',1),'取扱期間');
          now(1994,1);
          const rice=buy('JP-TOKYO-RICE',4),diesel=buy('JP-KEIHIN-DIESEL',6);
          const empty=structuredClone(S),emptyBuyer=company(seller.id,empty),cash=acc(emptyBuyer,'cash');
          post(emptyBuyer,{otherExpense:cash},{cash},'検証用現金支出','operating',empty);
          const noCredit=rejects(()=>worldBuyRegionalSupply(empty,seller.id,origin.id,'JP-KEIHIN-DIESEL',1),'現預金')
            &&empty.worldExpansion.regionalSupplyPurchases.length===S.worldExpansion.regionalSupplyPurchases.length;
          const road=worldRegisterDomesticRoute(S,seller.id,'JP-TOK','JP-NGO',347,'VERIFIED','JP-TOMEI-TOKYO-KOMAKI');
          const roadDepot=worldInstallDomesticWarehouse(S,roadBuyer.id,roadPlant.id,'JP-NAGOYA-SILO');
          const roadOrder=order(road,roadDepot,roadBuyer,'PRD-R23',4,rice.unitPrice,diesel.unitPrice*3);
          now(1994,2);worldResolveDomesticOrders(S);
          const roadTransit=shipment(roadOrder);
          const roadFuel=roadTransit?.status==='IN_TRANSIT'&&roadTransit.fuelQuantity===3
            &&roadTransit.freightCost===diesel.unitPrice*3&&seller.stock['PRD-M16'].q===3;
          now(1994,3);worldReceiveDomesticShipments(S);
          const restored=parsePayload(savePayload(S));
          const persistence=roadTransit.status==='DELIVERED'&&roadBuyer.stock['PRD-R23'].q===4
            &&restored.worldExpansion.regionalSupplyPurchases.length===6
            &&worldRegionalSupplyUsage(restored.worldExpansion).get('JP-KIBA-TIMBER')===180
            &&!check(restored).length&&Object.keys(restored.worldExpansion.resourceDeposits).length===0;
          const tamper=structuredClone(restored);
          const entry=tamper.worldExpansion.regionalSupplyPurchases[0];
          const journal=company(entry.buyerId,tamper).journals.find(j=>j.id===entry.journal);
          journal.cr[0][1]++;
          const rejectsSpoof=rejects(()=>worldValidateRegionalSupplies(tamper),'現金仕訳');
          return {uiPurchase,noEarlyCoal,wrongSite,noExpired,railFreight,railArrival,exhausted,
            laterCoal,dieselBefore,noCredit,roadFuel,persistence,rejectsSpoof};
        }""")
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS Phase 2-K supply: normal UI purchases, finite shared stock, real rail/road cargo and fuel, save")


if __name__ == "__main__":
    main()
