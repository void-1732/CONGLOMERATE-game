"""Phase 3: actual demand-driven AI procurement and regional B2B prices."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"])
        page = browser.new_page()
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result = page.evaluate("""() => {
          S=newWorldGame({country:'JP',name:'Phase 3 real orders'});
          S.year=1970;S.month=1;S.monthCommitted=ym(1970,1)-1;
          const seller=company(S.playerId),sp=seller.plants[0];
          const buyer=initFirm(S,{name:'Independent rice producer',country:'JP',seedBase:5000000});
          const bp=buyer.plants[0];
          sp.siteId='JP-TOK';bp.siteId='JP-YOK';
          // PRD-C02 requires an assembly site, not the legacy integrated plant.
          bp.kind='assembly';syncPlant(buyer);
          bp.componentLines=[];bp.lastProduced=0;
          for(const f of [seller,buyer]){
            if(!f.research.tree.done.includes('production-1'))f.research.tree.done.push('production-1');
            for(const m of f.models)f.plans[m.id]=0;
          }
          const put=(f,id,q,v)=>{
            post(f,{materials:v},{cash:v},'検証用現物購入','operating',S);
            f.stock[id]={q,v};
          };
          put(seller,'PRD-E16',1,1200);
          put(seller,'PRD-E17',1,300);
          put(seller,'PRD-R04',10,50);
          put(seller,'PRD-R23',8,80);
          put(buyer,'PRD-E20',1,120);
          applyWorldHistory(S);syncWorldIdentities(S);
          worldRegisterDomesticRoute(S,seller.id,'JP-TOK','JP-YOK',29,'VERIFIED','JP-SHIMBASHI-YOKOHAMA');
          worldInstallDomesticWarehouse(S,buyer.id,bp.id,'JP-YOKOHAMA-SHINKO');
          worldPlanSave(buyer,bp,'PRD-C02',2);
          buyer.auto=true;
          const recipe=WORLD_SUPPLEMENTAL_BY_ID.get('PRD-C02');
          const production=worldPhase3ConsumerProductionLimit(S,buyer,bp,recipe,2);
          const costPrice=worldPhase3RegionalB2BUnitPrice(S,seller,'PRD-R23','JP-YOK');
          const hot=structuredClone(S);
          hot.world.JP.inflation=.18;
          const highPrice=worldPhase3RegionalB2BUnitPrice(hot,company(seller.id,hot),'PRD-R23','JP-YOK');
          const empty=structuredClone(S);
          empty.world.JP.pop=0;
          const noDemand=worldPhase3ConsumerProductionLimit(empty,company(buyer.id,empty),
            company(buyer.id,empty).plants[0],recipe,2)===0;
          worldPlanDomesticPurchases(empty);
          const noPhantom=noDemand&&empty.worldExpansion.domesticOrders.length===0;
          const initialCash=acc(buyer,'cash');
          worldPlanDomesticPurchases(S);
          const order=S.worldExpansion.domesticOrders[0];
          const requested=production===2&&highPrice>costPrice
            &&order?.requestedQty===4&&order.unitPrice===costPrice
            &&order.status==='OPEN'&&order.buyerDecision==='AI'
            &&acc(buyer,'cash')===initialCash&&!S.worldExpansion.domesticShipments.length;
          worldPlanDomesticPurchases(S);
          const once=S.worldExpansion.domesticOrders.length===1;
          const pending=worldPhase3B2BMarketSnapshot(S,'MKT-14',ym(1970,1))
            .find(x=>x.productId==='PRD-R23');
          const observed=pending?.requestedQty===4&&pending.pendingQty===4;
          worldActOnDomesticOrder(S,seller.id,order.id,'approve');
          S.month++;
          worldResolveDomesticOrders(S);
          const cargo=S.worldExpansion.domesticShipments[0];
          const dispatched=cargo?.status==='IN_TRANSIT'&&order.status==='FILLED'
            &&order.acceptedQty===4&&cargo.unitPrice===costPrice
            &&acc(buyer,'worldSupplierAdvances')===cargo.prepaid
            &&!seller.journals.some(j=>j.text.startsWith('国内実物流の到着'));
          S.month++;
          worldReceiveDomesticShipments(S);
          const actual=worldPhase3B2BMarketSnapshot(S,'MKT-14',ym(1970,3))
            .find(x=>x.productId==='PRD-R23');
          const delivered=cargo.status==='DELIVERED'
            &&buyer.stock['PRD-R23'].q===4&&buyer.stock['PRD-R23'].v===cargo.prepaid
            &&!acc(buyer,'worldSupplierAdvances')
            &&actual?.deliveredQty===4&&actual.deliveredAmount===4*costPrice
            &&actual.realizedUnitPrice===costPrice;
          const saved=parsePayload(savePayload(S));
          const restored=JSON.stringify(worldPhase3B2BMarketSnapshot(saved,'MKT-14',ym(1970,3)))
            ===JSON.stringify(worldPhase3B2BMarketSnapshot(S,'MKT-14',ym(1970,3)))
            &&!check(saved).length;
          const corrupted=structuredClone(saved);
          corrupted.worldExpansion.domesticShipments[0].unitPrice++;
          const tamper=(()=>{try{parsePayload(savePayload(corrupted));return false}catch{return true}})();
          return {requested,noPhantom,once,observed,dispatched,delivered,restored,tamper};
        }""")
        assert all(result.values()), result
        browser.close()
    print("PASS Phase 3: demand-aware AI purchase, regional price, real stock, "
          "dispatch, delivery, accounting and validated save")

if __name__ == "__main__":
    main()
