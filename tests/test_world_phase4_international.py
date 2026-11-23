"""Phase 4: international real freight, foreign exchange, title and journals."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"])
        page=browser.new_page()
        page.on("pageerror",lambda err:print("BROWSER ERROR",err))
        page.set_content((ROOT/"index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result=page.evaluate("""() => {
          S=newWorldGame({country:'UK',name:'Phase 4 Channel freight'});
          S.year=2000;S.month=1;S.monthCommitted=ym(2000,1)-1;
          const buyer=company(S.playerId),bp=buyer.plants[0];
          const seller=initFirm(S,{name:'France exporter',country:'FR',seedBase:5000000});
          const sp=seller.plants[0];
          bp.siteId='UK-LON';sp.siteId='FR-PAR';
          seller.owners=[{id:buyer.id,econ:1,vote:1}];
          buyer.auto=false;seller.auto=false;
          for(const f of [seller,buyer]){
            if(!f.research.tree.done.includes('production-1'))
              f.research.tree.done.push('production-1');
            for(const m of f.models)f.plans[m.id]=0;
          }
          const put=(f,id,q,v)=>{
            post(f,{materials:v},{cash:v},'検証用現物取得','operating',S);
            f.stock[id]={q,v};
          };
          put(seller,'PRD-E15',1,2500);
          put(seller,'PRD-M16',30,300);
          put(seller,'PRD-R19',12,600);
          put(buyer,'PRD-E20',1,200);
          applyWorldHistory(S);syncWorldIdentities(S);
          const route=worldInternationalRegisterRoute(S,seller.id,'FR-UK-CHANNEL-1994');
          const warehouse=worldInternationalInstallWarehouse(S,buyer.id,bp.id,'FR-UK-CHANNEL-1994');
          const assets=route.assetValue===2500&&warehouse.assetValue===200
            &&seller.stock['PRD-E15'].q===0&&buyer.stock['PRD-E20'].q===0
            &&worldDomesticAssetBasis(S,seller.id).gross>=2500
            &&worldDomesticAssetBasis(S,buyer.id).gross>=200;
          const early=structuredClone(S);
          early.year=1993;
          const earlyDenied=(()=>{try{
            worldInternationalPlaceOrder(early,buyer.id,{
              routeId:route.id,warehouseId:warehouse.id,productId:'PRD-R19',
              quantity:1,unitPriceSeller:100,maxPaymentBuyer:10000});return false;
            }catch{return true}})();
          const beforeBuyer=acc(buyer,'cash'),beforeSeller=acc(seller,'cash');
          const order=worldInternationalPlaceOrder(S,buyer.id,{
            routeId:route.id,warehouseId:warehouse.id,productId:'PRD-R19',
            quantity:10,unitPriceSeller:100,maxPaymentBuyer:100000});
          const queued=order.status==='OPEN'&&order.acceptedQty===0
            &&acc(buyer,'cash')===beforeBuyer&&acc(seller,'cash')===beforeSeller
            &&!S.worldExpansion.internationalShipments.length;
          const savedOrder=parsePayload(savePayload(S)).worldExpansion.internationalOrders[0].id===order.id;
          worldInternationalActOrder(S,seller.id,order.id,'approve');
          S.month++;
          worldInternationalResolveOrders(S);
          const cargo=S.worldExpansion.internationalShipments[0];
          const dispatched=order.status==='PARTIAL'&&order.acceptedQty===8
            &&order.result==='REMAINDER_UNFILLED'
            &&cargo?.status==='IN_TRANSIT'&&cargo.quantity===8
            &&cargo.goodsSeller===800&&cargo.bookCost===400
            &&cargo.prepaidSeller===cargo.goodsSeller+cargo.fuelCost
            &&cargo.prepaidBuyer===Math.round(cargo.prepaidSeller*cargo.sellerRate/cargo.buyerRate)
            &&acc(buyer,'worldSupplierAdvances')===cargo.prepaidBuyer
            &&-acc(seller,'worldCustomerAdvances')===cargo.prepaidSeller
            &&seller.stock['PRD-R19'].q===4
            &&!buyer.stock['PRD-R19']
            &&!seller.journals.some(j=>j.text.startsWith('国際貨物の現物検収'));
          const refundDenied=(()=>{try{worldInternationalRefundShipment(S,cargo.id);return false}
            catch{return true}})();
          const inTransitValid=worldValidateInternationalLogistics(S)&&!check(S).length;
          const held=structuredClone(S);
          held.month+=2;
          const refund=worldInternationalRefundShipment(held,cargo.id);
          const refunded=refund.status==='REFUNDED'
            &&acc(company(buyer.id,held),'worldSupplierAdvances')===0
            &&acc(company(seller.id,held),'worldCustomerAdvances')===0
            &&!company(buyer.id,held).stock['PRD-R19']
            &&worldValidateInternationalLogistics(held)&&!check(held).length;
          S.month++;
          S.world.FR.fx*=1.2;
          worldInternationalReceiveShipments(S);
          const delivered=cargo.status==='DELIVERED'&&cargo.receivedAt===ym(2000,3)
            &&buyer.stock['PRD-R19'].q===8
            &&buyer.stock['PRD-R19'].v===cargo.prepaidBuyer
            &&acc(buyer,'worldSupplierAdvances')===0
            &&acc(seller,'worldCustomerAdvances')===0
            &&worldValidateInternationalLogistics(S);
          const payload=parsePayload(savePayload(S));
          const restored=payload.worldExpansion.internationalShipments[0].status==='DELIVERED'
            &&company(buyer.id,payload).stock['PRD-R19'].q===8
            &&!check(payload).length;
          const damaged=structuredClone(payload);
          damaged.worldExpansion.internationalShipments[0].prepaidBuyer++;
          const tamper=(()=>{try{parsePayload(savePayload(damaged));return false}
            catch{return true}})();
          const ui=worldInternationalTradePanel(buyer,true).includes('Phase 4')
            &&worldInternationalTradePanel(buyer,true).includes(order.id);
          return {assets,earlyDenied,queued,savedOrder,dispatched,refundDenied,
            inTransitValid,refunded,delivered,restored,tamper,ui};
        }""")
        assert all(result.values()),result
        browser.close()
    print("PASS Phase 4: cross-border physical assets, partial delivery, FX prepayment, "
          "title, revenue, refund, tamper rejection and restore")

if __name__=="__main__":
    main()
