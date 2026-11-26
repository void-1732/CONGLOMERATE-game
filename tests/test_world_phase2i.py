"""Auto-procurement uses existing stock, confirmed routes and real production demand."""

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
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result = page.evaluate("""() => {
          S=newWorldGame({country:'JP',name:'Phase 2-I supplier'});
          // Historical exact-amount fixture; new tariff is covered by the monthly freight audit.
          delete S.worldExpansion.freightRateFromSeq;
          S.year=1970;S.month=1;S.monthCommitted=ym(1970,1)-1;
          const seller=company(S.playerId),plant=seller.plants[0];
          const buyer=initFirm(S,{name:'Independent wood mill',country:'JP',seedBase:5000000});
          const receiver=buyer.plants[0];
          plant.siteId='JP-TOK';receiver.siteId='JP-YOK';
          receiver.componentLines=[];receiver.lastProduced=0;
          for(const f of [seller,buyer]){
            for(const tech of ['production-1','materials-1']){
              if(!f.research.tree.done.includes(tech))f.research.tree.done.push(tech);
            }
          }
          const put=(f,id,q,v)=>{
            post(f,{materials:v},{cash:v},'検証用現物購入','operating',S);
            f.stock[id]={q,v};
          };
          put(seller,'PRD-E16',1,1200);
          put(seller,'PRD-E17',1,300);
          put(seller,'PRD-R04',9,45);
          put(seller,'PRD-R19',8,80);
          put(buyer,'PRD-E20',1,120);
          put(buyer,'PRD-R19',1,10);
          applyWorldHistory(S);syncWorldIdentities(S);
          worldRegisterDomesticRoute(S,seller.id,'JP-TOK','JP-YOK',29,'VERIFIED','JP-SHIMBASHI-YOKOHAMA');
          worldInstallDomesticWarehouse(S,buyer.id,receiver.id,'JP-YOKOHAMA-SHINKO');
          worldPlanDomesticPurchases(S);
          const noPlan=S.worldExpansion.domesticOrders.length===0;
          worldPlanSave(buyer,receiver,'PRD-M12',2);
          buyer.auto=false;
          worldPlanDomesticPurchases(S);
          const off=S.worldExpansion.domesticOrders.length===0;
          buyer.auto=true;
          const initialCash=acc(buyer,'cash');
          worldPlanDomesticPurchases(S);
          const first=S.worldExpansion.domesticOrders[0];
          const planned=first.requestedQty===3&&first.productId==='PRD-R19'&&first.buyerDecision==='AI'
            &&first.sellerDecision===null&&first.unitPrice===11&&first.maxFreight===5
            &&acc(buyer,'cash')===initialCash&&buyer.stock['PRD-R19'].q===1
            &&seller.stock['PRD-R19'].q===8&&!S.worldExpansion.domesticShipments.length;
          worldPlanDomesticPurchases(S);
          const once=S.worldExpansion.domesticOrders.length===1;
          worldActOnDomesticOrder(S,seller.id,first.id,'approve');
          S.month++;
          worldResolveDomesticOrders(S);
          worldPlanDomesticPurchases(S);
          const shipment=S.worldExpansion.domesticShipments[0];
          const inbound=first.status==='FILLED'&&shipment?.quantity===3&&shipment.status==='IN_TRANSIT'
            &&S.worldExpansion.domesticOrders.length===1&&acc(buyer,'cash')===initialCash-38;
          S.month++;
          worldReceiveDomesticShipments(S);
          worldPlanDomesticPurchases(S);
          const restored=parsePayload(savePayload(S));
          const inventory=restored.worldExpansion.domesticOrders.length===1
            &&company(buyer.id,restored).stock['PRD-R19'].q===4
            &&company(buyer.id,restored).stock['PRD-R19'].v===48
            &&restored.worldExpansion.domesticShipments[0].status==='DELIVERED'
            &&!check(restored).length;
          return {noPlan,off,planned,once,inbound,inventory};
        }""")
        assert all(result.values()), result
        browser.close()
    print("PASS Phase 2-I: independent AI procurement from real deficit and stock, budget, no duplicate, save")


if __name__ == "__main__":
    main()
