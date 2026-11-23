"""Market onboarding, measured freight, calendar settlement, and V2 save upgrade."""
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
          const rejects=action=>{try{action();return false;}catch{return true;}};
          const legacy=newGame({country:'UK',era:1900,difficulty:'normal',history:'historical',name:'Legacy world'});
          const originalPlayer=company(legacy.playerId,legacy);
          legacy.config.scenario='world';
          legacy.worldExpansion=makeWorldExpansion(0);
          delete legacy.worldExpansion.marketRegistryVersion;
          syncWorldIdentities(legacy);
          const legacyRaw=savePayload(legacy);
          const upgraded=parsePayload(legacyRaw);
          const registryUpgrade=upgraded.worldExpansion.marketRegistryVersion===1
            &&upgraded.worldExpansion.openMarkets['MKT-27']===ym(1900,1)&&upgraded.world.CA?.code==='CA'
            &&company(upgraded.playerId,upgraded).id===originalPlayer.id
            &&acc(company(upgraded.playerId,upgraded),'cash')===acc(originalPlayer,'cash')
            &&upgraded.rng===legacy.rng&&JSON.stringify(upgraded.world.UK)===JSON.stringify(legacy.world.UK)
            &&!check(parsePayload(savePayload(upgraded))).length;
          const forged=structuredClone(upgraded);delete forged.worldExpansion.marketRegistryVersion;
          const downgradeRejected=rejects(()=>parsePayload(savePayload(forged)));

          const canadastart=newWorldGame({country:'CA',name:'Canadian start'});
          const canadianIdentity=worldCityLocation(canadastart,'CITY-27-03');
          const player=company(canadastart.playerId,canadastart);
          const selected=canadianIdentity.jurisdictionId==='JUR-CA'&&canadianIdentity.marketOpen
            &&player.plants[0].siteId==='CA-MTL'&&firmCurrency(player,canadastart)==='CAD'
            &&worldPhase3ConsumerQuote(canadastart,'MKT-27','PRD-C01').nationalQuantity>0
            &&canadastart.worldExpansion.facilities['FAC-'+player.plants[0].id].locationId==='LOC-CA-MTL'
            &&!check(canadastart).length;
          S=newWorldGame({country:'UK',name:'Importer Liverpool'});
          const buyer=company(S.playerId),home=buyer.plants[0];
          home.siteId='UK-LIV';
          const capital=localFromBase(750000,buyer.country),payer=S.seq;
          post(buyer,{investment:capital},{cash:capital},'輸出取引検証用の払込','investing',S);
          const seller=initFirm(S,{name:'Montreal grain exporter',country:'CA',seedBase:750000,publicOwnership:false});
          seller.owners=[{id:buyer.id,econ:1,vote:1}];
          registerEquityLink(S,{parentId:buyer.id,childId:seller.id,ratio:1,kind:'foundation',considerationLocal:capital,
            buyerJournal:payer,childJournal:seller.journals.find(j=>j.text==='創業資本').id,
            bookEquityBase:baseFromLocal(financials(seller).equity,seller.country),
            cashAcquiredBase:baseFromLocal(acc(seller,'cash'),seller.country)});
          const profile='CA-UK-MONTREAL-GRAIN',closedAtStart=!worldInternationalRouteAvailable(S,profile);
          const plant=seller.plants[0];
          S.year=1909;S.month=5;S.monthCommitted=ym(1909,5)-1;
          applyWorldHistory(S);syncWorldIdentities(S);
          for(const f of [buyer,seller]){
            f.auto=false;f.research.tree.done=[...new Set([...f.research.tree.done,'production-1'])];
          }
          for(const [f,id,q,amount] of [[seller,'PRD-E18',1,2500],[buyer,'PRD-E20',1,600],[buyer,'PRD-E21',1,900]]){
            post(f,{materials:amount},{cash:amount},'検証用の有償現物設備','operating',S);
            f.stock[id]={q,v:amount};
          }
          const purchase=worldBuyRegionalSupply(S,seller.id,plant.id,'CA-MTL-WHEAT',20);
          worldBuyRegionalSupply(S,seller.id,plant.id,'CA-MTL-COAL',30);
          const route=worldInternationalRegisterRoute(S,seller.id,profile);
          const warehouse=worldInternationalInstallWarehouse(S,buyer.id,home.id,profile);
          const base={routeId:route.id,warehouseId:warehouse.id,productId:'PRD-R22',
            quantity:10,cargoLitres:85,unitPriceSeller:localFromBase(400,seller.country),
            maxPaymentBuyer:10000000,paymentDays:60};
          const invalid=rejects(()=>worldInternationalPlaceOrder(S,buyer.id,{...base,cargoLitres:-1}))
            &&rejects(()=>worldInternationalPlaceOrder(S,buyer.id,{...base,productId:'PRD-R04'}));
          const first=worldInternationalPlaceOrder(S,buyer.id,base);
          const second=worldInternationalPlaceOrder(S,buyer.id,{...base,quantity:2,cargoLitres:8});
          for(const o of [first,second])worldInternationalActOrder(S,seller.id,o.id,'approve');
          S.month=6;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
          const [a,b]=S.worldExpansion.internationalShipments;
          const loading=a?.quantity===6&&a.cargoLitres===51&&a.loadKg===26&&a.fuelRequired===8
            &&b?.quantity===1&&b.cargoLitres===4&&b.loadKg===2&&b.fuelRequired===1
            &&first.acceptedQty===6&&second.acceptedQty===1;
          const ownership=purchase.quantity===20&&a?.status==='IN_TRANSIT'&&a.credit.paidAt===null
            &&acc(seller,'worldShipmentStock')===a.bookCost+b.bookCost
            &&!buyer.stock['PRD-R22']?.q&&seller.stock['PRD-R22'].q===13&&!check(S).length;
          const altered=structuredClone(S);altered.worldExpansion.internationalShipments[0].loadKg--;
          const audit=rejects(()=>parsePayload(savePayload(altered)));
          S.month=7;
          worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
          const prepaid=a?.credit.paidAt===ym(1909,7)&&a.status==='IN_TRANSIT'
            &&acc(buyer,'worldSupplierAdvances')===a.prepaidBuyer+b.prepaidBuyer
            &&acc(buyer,'worldImportDutyPrepaid')===a.dutyBuyer+b.dutyBuyer;
          S.month=8;worldInternationalReceiveShipments(S);
          const restored=parsePayload(savePayload(S));
          const shipment=restored.worldExpansion.internationalShipments[0];
          const settlement=a?.status==='DELIVERED'&&b?.status==='DELIVERED'
            &&shipment.cargoLitres===51&&shipment.credit.paidAt===ym(1909,7)
            &&buyer.stock['PRD-R22'].q===7&&buyer.stock['PRD-R22'].v===a.totalBuyer+b.totalBuyer
            &&!acc(seller,'worldShipmentStock')&&!acc(buyer,'worldSupplierAdvances')
            &&!check(restored).length&&!consolidate(restored).errors.length;
          S.month=11;
          const seasonal=closedAtStart&&!worldInternationalRouteAvailable(S,profile)
            &&rejects(()=>worldInternationalPlaceOrder(S,buyer.id,base));
          return {registryUpgrade,downgradeRejected,selected,invalid,loading,ownership,audit,prepaid,settlement,seasonal};
        }""")
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS Phase 4 Canada: CAD, ports, measured capacity, real wheat purchase, shipment, settlement, migration")


if __name__ == "__main__":
    main()
