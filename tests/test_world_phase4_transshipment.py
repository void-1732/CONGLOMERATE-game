"""Offline rail-to-steamship acceptance at Yokohama's Shinko cargo pier."""

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
          const profile='JP-US-YOKOHAMA-TRANSFER';
          S=newWorldGame({country:'JP',name:'Shimbashi paper merchant'});VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';
          const closedEarly=!worldInternationalRouteAvailable(S,profile);
          S.year=1920;S.month=1;S.monthCommitted=ym(1920,1)-1;
          applyWorldHistory(S);syncWorldIdentities(S);
          PAGE='corporateSubsidiaries';render();
          document.querySelector('#subName').value='Seattle paper importer';
          document.querySelector('#subCountry').value='US';
          document.querySelector('#subIndustry').value='manufacturing';
          document.querySelector('#subCapital').value='650000';
          createSub();
          const seller=company(S.playerId),buyer=S.firms.find(f=>f.name==='Seattle paper importer');
          const origin=seller.plants[0],destination=buyer.plants[0];
          destination.siteId='US-SEA';
          const terminal={id:'P'+S.seq++,name:'横浜新港',siteId:'JP-YOK',siteCountry:'JP',capacity:15,
            kind:'assembly',scale:'small',condition:100,focus:'all',construction:null,lastProduced:0,lastUtilization:0};
          const assetCost=localFromBase(siteInvestmentQuote('JP-YOK','small','assembly',S),'JP');
          post(seller,{ppe:assetCost},{cash:assetCost},'検証用の有償荷役拠点','investing',S);
          seller.plants.push(terminal);
          syncPlant(seller);
          syncWorldIdentities(S);
          for(const firm of [buyer,seller]){
            firm.auto=false;firm.research.tree.done=[...new Set([...firm.research.tree.done,'production-1'])];
          }
          for(const [firm,id,q,value] of [[seller,'PRD-E16',1,4200],[seller,'PRD-E17',1,1200],
             [seller,'PRD-E18',1,3600],[seller,'PRD-E20',1,900],[seller,'PRD-M14',10,1000],
             [seller,'PRD-R04',15,1800],[buyer,'PRD-E20',1,700],[buyer,'PRD-E21',1,900]]){
            post(firm,{materials:value},{cash:value},'検証用の有償現物調達','operating',S);
            firm.stock[id]={q,v:value};
          }
          const blocked=rejects(()=>worldInternationalRegisterRoute(S,seller.id,profile));
          const depot=worldInstallDomesticWarehouse(S,seller.id,terminal.id,'JP-YOKOHAMA-SHINKO');
          const route=worldInternationalRegisterRoute(S,seller.id,profile);
          const warehouse=worldInternationalInstallWarehouse(S,buyer.id,destination.id,profile);
          const registered=route.plantId===origin.id&&route.transferWarehouseId===depot.id
            &&route.assetValue===9000&&route.capacityKg===10;
          const options={routeId:route.id,warehouseId:warehouse.id,productId:'PRD-M14',
            quantity:9,cargoLitres:36,unitPriceSeller:1200,maxPaymentBuyer:100000,paymentDays:60};
          const first=worldInternationalPlaceOrder(S,buyer.id,options);
          const second=worldInternationalPlaceOrder(S,buyer.id,{...options,quantity:1,cargoLitres:2});
          for(const o of [first,second])worldInternationalActOrder(S,seller.id,o.id,'approve');
          S.month=2;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
          const [cargo]=S.worldExpansion.internationalShipments;
          const loaded=first.acceptedQty===4&&second.result==='NO_ALLOCATION'&&cargo?.loadKg===8
            &&cargo.transfer.fuelRail===1&&cargo.transfer.fuelSea===4&&seller.stock['PRD-R04'].q===10
            &&worldDomesticWarehouseReservations(S.worldExpansion,depot.id)===8
            &&rejects(()=>worldRetireDomesticAsset(S,seller.id,'warehouse',depot.id))
            &&!buyer.stock['PRD-M14']?.q&&acc(seller,'worldShipmentStock')===cargo.bookCost;
          terminal.paused=true;syncPlant(seller);
          S.month=3;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
          const waits=cargo.transfer.arrivedAt===null&&cargo.transfer.boardedAt===null
            &&cargo.credit.dueDate==='1920-04-01'&&cargo.credit.paidAt===null;
          terminal.paused=false;syncPlant(seller);
          S.month=4;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
          const savedInPort=parsePayload(savePayload(S));
          const held=cargo.transfer.arrivedAt===ym(1920,4)&&cargo.transfer.boardedAt===null
            &&cargo.credit.paidAt===ym(1920,4)&&!acc(seller,'sales')
            &&savedInPort.worldExpansion.internationalShipments[0].transfer.arrivedAt===ym(1920,4)
            &&worldInternationalTradePanel(seller,true).includes('横浜新港で積替え待ち');
          const forged=structuredClone(S);forged.worldExpansion.internationalShipments[0].transfer.railDueAt--;
          const audit=rejects(()=>parsePayload(savePayload(forged)));
          S.month=5;worldInternationalReceiveShipments(S);
          const boarded=cargo.transfer.boardedAt===ym(1920,5)&&cargo.dueAt===ym(1920,8)
            &&worldDomesticWarehouseReservations(S.worldExpansion,depot.id)===0&&!buyer.stock['PRD-M14']?.q;
          S.month=7;worldInternationalReceiveShipments(S);
          const stillOwned=cargo.status==='IN_TRANSIT'&&acc(seller,'worldShipmentStock')===cargo.bookCost;
          S.month=8;worldInternationalReceiveShipments(S);
          const reopened=parsePayload(savePayload(S));
          const settled=cargo.status==='DELIVERED'&&buyer.stock['PRD-M14'].q===4
            &&buyer.stock['PRD-M14'].v===cargo.totalBuyer&&!acc(seller,'worldShipmentStock')
            &&-acc(seller,'sales')===cargo.goodsSeller&&!check(reopened).length&&!consolidate(reopened).errors.length;
          return {closedEarly,blocked,registered,loaded,waits,held,audit,boarded,stillOwned,settled};
        }""")
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS Phase 4 Tokyo–Yokohama–Seattle: rail, finite transfer warehouse, steamship, title, journals and save")


if __name__ == "__main__":
    main()
