"""Domestic buyer consent, seller decisions, FIFO, partial allocation and persistence."""

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
          S=newWorldGame({country:'JP',name:'Phase 2-H'});
          const buyer=company(S.playerId);
          S.year=1970;S.month=1;S.monthCommitted=ym(1970,1)-1;
          const seller=initFirm(S,{name:'Independent Rail',country:'JP',seedBase:5000000});
          const manual=initFirm(S,{name:'Transferable Rail',country:'JP',seedBase:5000000});
          manual.auto=false;
          buyer.auto=false;
          for(const f of [buyer,seller,manual]){
            if(!f.research.tree.done.includes('production-1'))f.research.tree.done.push('production-1');
            for(const model of f.models)f.plans[model.id]=0;
          }
          const put=(f,id,q,v)=>{
            post(f,{materials:v},{cash:v},'検証用現物購入','operating',S);
            f.stock[id]={q,v};
          };
          for(const f of [seller,manual]){
            f.plants[0].siteId='JP-TOK';
            put(f,'PRD-E16',1,1200);
            put(f,'PRD-E17',1,300);
            put(f,'PRD-R04',10,50);
            put(f,'PRD-R19',8,80);
          }
          const receiver=buyer.plants[0];
          receiver.siteId='JP-YOK';
          const receiver2={...structuredClone(receiver),id:'P-H-2',name:'第二受入倉庫'};
          buyer.plants.push(receiver2);
          syncPlant(buyer);
          put(buyer,'PRD-E20',2,240);
          applyWorldHistory(S);syncWorldIdentities(S);
          const warehouse=plant=>worldInstallDomesticWarehouse(S,buyer.id,plant.id,'JP-YOKOHAMA-SHINKO');
          const route=f=>worldRegisterDomesticRoute(S,f.id,'JP-TOK','JP-YOK',29,'VERIFIED','JP-SHIMBASHI-YOKOHAMA');
          window.fixture={buyerId:buyer.id,sellerId:seller.id,manualId:manual.id,
            warehouse1:warehouse(receiver).id,warehouse2:warehouse(receiver2).id,
            routeId:route(seller).id,manualRouteId:route(manual).id};
          saveAuto=async()=>true;
          requestOperationSaveV037=()=>true;
          VIEW_FIRM=buyer.id;PAGE='product';render();
          document.getElementById('content').innerHTML=worldDomesticLogisticsPanel(buyer,true);
          document.getElementById('world-domestic').open=true;
        }""")
        form = page.locator('form[data-world-domestic="order"]')
        first_choice = page.evaluate(
            "() => [fixture.routeId,fixture.warehouse1,'PRD-R19'].join('|')"
        )
        form.locator('select[name="request"]').select_option(first_choice)
        form.locator('[name="quantity"]').fill("5")
        form.locator('[name="price"]').fill("16")
        form.locator('[name="freight"]').fill("6")
        form.get_by_role("button", name="購入を申し込む").click()
        result = page.evaluate("""async () => {
          const {buyerId,sellerId,manualId,warehouse1,warehouse2,routeId,manualRouteId}=fixture;
          const buyer=company(buyerId),seller=company(sellerId);
          const orders=S.worldExpansion.domesticOrders,first=orders[0];
          const buy=(id,w,qty,price=16,cap=6)=>worldPlaceDomesticOrder(S,buyerId,{
            routeId:id,warehouseId:w,productId:'PRD-R19',quantity:qty,unitPrice:price,maxFreight:cap
          });
          const denied=fn=>{try{fn();return false;}catch{return true;}};
          const badCap=buy(routeId,warehouse1,1,16,1),lowPrice=buy(routeId,warehouse1,1,1,6);
          const second=buy(routeId,warehouse2,5),noConsent=buy(manualRouteId,warehouse1,1),
            cancellation=buy(routeId,warehouse2,2);
          const authority=denied(()=>worldActOnDomesticOrder(S,buyerId,first.id,'approve'))
            &&denied(()=>worldActOnDomesticOrder(S,sellerId,first.id,'approve'))
            &&denied(()=>worldPlaceDomesticOrder(S,sellerId,{
              routeId,warehouseId:warehouse1,productId:'PRD-R19',quantity:1,unitPrice:10,maxFreight:6
            }));
          worldActOnDomesticOrder(S,buyerId,cancellation.id,'cancel');
          const noPrematurePayments=first.requestedQty===5&&first.status==='OPEN'
            &&acc(buyer,'worldSupplierAdvances')===0&&seller.stock['PRD-R19'].q===8
            &&S.worldExpansion.domesticShipments.length===0;
          const initialMarket=worldPhase3B2BMarketSnapshot(S,'MKT-14',ym(1970,1))
            .find(r=>r.productId==='PRD-R19');
          const marketOrders=initialMarket.requestedQty===15&&initialMarket.pendingQty===13
            &&initialMarket.acceptedQty===0&&initialMarket.deliveredQty===0;
          const pendingRoundTrip=parsePayload(savePayload(S)).worldExpansion.domesticOrders[0].id===first.id;
          const reversed=structuredClone(S);reversed.worldExpansion.domesticOrders.reverse();
          const reordered=denied(()=>parsePayload(savePayload(reversed)));
          await runMonth();
          const holdsUntilNext=S.month===2&&S.worldExpansion.domesticShipments.length===0;
          await runMonth();
          const acceptedMarket=worldPhase3B2BMarketSnapshot(S,'MKT-14',ym(1970,2))
            .find(r=>r.productId==='PRD-R19');
          const marketAllocation=acceptedMarket.acceptedQty===8&&acceptedMarket.deliveredQty===0;
          const settled=S.worldExpansion.domesticOrders;
          const by=id=>settled.find(o=>o.id===id);
          const sent=S.worldExpansion.domesticShipments;
          const domesticRevenue=f=>f.journals.filter(j=>j.text.startsWith('国内実物流の到着'))
            .reduce((total,j)=>total+j.cr.filter(([a])=>a==='sales').reduce((sum,[,n])=>sum+n,0),0);
          const fifo=S.month===3&&sent.length===2&&sent.every(t=>t.status==='IN_TRANSIT')
            &&by(first.id).status==='FILLED'&&by(first.id).acceptedQty===5
            &&by(second.id).status==='PARTIAL'&&by(second.id).acceptedQty===3
            &&by(first.id).sellerDecision==='AI'&&by(second.id).sellerDecision==='AI'
            &&sent[0].orderId===first.id&&sent[1].orderId===second.id
            &&company(sellerId).stock['PRD-R19'].q===0&&!domesticRevenue(company(sellerId));
          const rejected=by(noConsent.id).result==='NO_CONSENT'
            &&by(cancellation.id).result==='BUYER_CANCELLED'&&by(badCap.id).result==='NO_ALLOCATION'
            &&by(lowPrice.id).result==='NO_ALLOCATION';
          const total=sent.reduce((v,t)=>v+t.prepaid,0);
          const funds=total===138&&acc(company(buyerId),'worldSupplierAdvances')===total
            &&-acc(company(sellerId),'worldCustomerAdvances')===total;
          const badLink=structuredClone(S);badLink.worldExpansion.domesticOrders[0].shipmentId='DS-0';
          const protectedLink=denied(()=>parsePayload(savePayload(badLink)));
          await runMonth();
          const deliveredMarket=worldPhase3B2BMarketSnapshot(S,'MKT-14',ym(1970,3))
            .find(r=>r.productId==='PRD-R19');
          const marketDelivery=deliveredMarket.deliveredQty===8&&deliveredMarket.deliveredAmount===128
            &&deliveredMarket.realizedUnitPrice===16;
          const restored=parsePayload(savePayload(S));
          const auditIssue=structuredClone(restored),audited=auditIssue.worldExpansion.domesticShipments[0];
          const auditedJournal=company(audited.sellerId,auditIssue).journals.find(j=>j.id===audited.accounting.terminal);
          auditedJournal.cr.find(([name])=>name==='sales')[1]++;
          const alteredPosting=denied(()=>parsePayload(savePayload(auditIssue)));
          const delivered=restored.month===4&&restored.worldExpansion.domesticShipments.every(t=>t.status==='DELIVERED')
            &&company(buyerId,restored).stock['PRD-R19'].q===8
            &&company(buyerId,restored).stock['PRD-R19'].v===138
            &&domesticRevenue(company(sellerId,restored))===128
            &&!acc(company(buyerId,restored),'worldSupplierAdvances')&&!check(restored).length;
          const manualFixture=structuredClone(restored);
          const manualBuyer=company(buyerId,manualFixture),manualSeller=company(manualId,manualFixture);
          manualSeller.owners=[{id:manualBuyer.id,econ:1,vote:1}];
          const m=worldPlaceDomesticOrder(manualFixture,buyerId,{
            routeId:manualRouteId,warehouseId:warehouse1,productId:'PRD-R19',quantity:1,unitPrice:16,maxFreight:6
          });
          worldActOnDomesticOrder(manualFixture,manualId,m.id,'approve');
          manualFixture.month++;
          worldResolveDomesticOrders(manualFixture);
          const manualConsent=m.sellerDecision==='MANUAL'&&m.status==='FILLED'
            &&worldValidateDomesticLogistics(manualFixture);
          const failed=manualFixture.worldExpansion.domesticShipments.find(t=>t.orderId===m.id);
          const buyerBeforeRefund=acc(manualBuyer,'cash');
          manualFixture.month+=2;
          worldRefundDomesticShipment(manualFixture,failed.id);
          const refundProof=failed.status==='REFUNDED'&&failed.accounting.terminal>failed.accounting.dispatch+4
            &&acc(manualBuyer,'cash')===buyerBeforeRefund+failed.prepaid
            &&acc(manualBuyer,'worldSupplierAdvances')===0&&acc(manualSeller,'worldShipmentStock')===0
            &&worldValidateDomesticLogistics(manualFixture);
          const spoofed=structuredClone(manualFixture);
          spoofed.worldExpansion.domesticShipments.find(t=>t.id===failed.id).accounting.terminal++;
          const alteredRefund=denied(()=>worldValidateDomesticLogistics(spoofed));
          return {marketOrders,marketAllocation,marketDelivery,authority,noPrematurePayments,pendingRoundTrip,reordered,holdsUntilNext,fifo,
            rejected,funds,protectedLink,delivered,manualConsent,alteredPosting,refundProof,alteredRefund};
        }""")
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS Phases 2-H/2-J: independent consent, FIFO partial allocation, delivery/refund journal audit and save")


if __name__ == "__main__":
    main()
