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
          const buyer=company(S.playerId),bp=buyer.plants[0];
          const capital=300000,parentJournal=S.seq;
          post(buyer,{investment:capital},{cash:capital},'検証用海外法人の正式設立','investing',S);
          const seller=initFirm(S,{name:'France exporter',country:'FR',seedBase:570000,publicOwnership:false});
          seller.owners=[{id:buyer.id,econ:1,vote:1}];
          registerEquityLink(S,{parentId:buyer.id,childId:seller.id,ratio:1,kind:'foundation',
            considerationLocal:capital,buyerJournal:parentJournal,
            childJournal:seller.journals.find(j=>j.text==='創業資本').id,
            bookEquityBase:baseFromLocal(capital,'UK'),
            cashAcquiredBase:baseFromLocal(acc(seller,'cash'),'FR')});
          const sp=seller.plants[0];
          bp.siteId='UK-LON';sp.siteId='FR-PAR';
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
          // Found the foreign subsidiary with balanced 1900 books; travel begins after 1994.
          S.year=2000;S.month=1;S.monthCommitted=ym(2000,1)-1;
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
            &&buyer.stock['PRD-R19'].v===cargo.totalBuyer
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
        multimodal=page.evaluate("""() => {
          const profiles=Object.entries(WORLD_INTERNATIONAL_CORRIDORS);
          const modes=new Set(profiles.map(([,p])=>p.mode));
          const paths=profiles.length===18&&['road+rail-shuttle','sea','rail','air'].every(m=>modes.has(m))
            &&profiles.every(([,p])=>findSite(p.from)&&findSite(p.to)
              &&findSite(p.from).country!==findSite(p.to).country
              &&p.capacityKg>0&&p.warehouseCapacityKg>0&&p.distanceKm>0
              &&p.fuel&&p.truck&&p.status==='PROVISIONAL');
          S=newWorldGame({country:'UK',name:'Phase 4 ocean test'});
          const buyer=company(S.playerId),bp=buyer.plants[0];
          const capital=300000,parentJournal=S.seq;
          post(buyer,{investment:capital},{cash:capital},'検証用海外法人の正式設立','investing',S);
          const seller=initFirm(S,{name:'French ocean exporter',country:'FR',seedBase:570000,publicOwnership:false});
          seller.owners=[{id:buyer.id,econ:1,vote:1}];
          registerEquityLink(S,{parentId:buyer.id,childId:seller.id,ratio:1,kind:'foundation',
            considerationLocal:capital,buyerJournal:parentJournal,
            childJournal:seller.journals.find(j=>j.text==='創業資本').id,
            bookEquityBase:baseFromLocal(capital,'UK'),
            cashAcquiredBase:baseFromLocal(acc(seller,'cash'),'FR')});
          bp.siteId='UK-LIV';seller.plants[0].siteId='FR-MAR';
          buyer.auto=false;seller.auto=false;
          for(const f of [seller,buyer]){
            if(!f.research.tree.done.includes('production-1'))f.research.tree.done.push('production-1');
            for(const m of f.models)f.plans[m.id]=0;
          }
          const put=(f,id,q,v)=>{
            post(f,{materials:v},{cash:v},'検証用現物取得','operating',S);
            f.stock[id]={q,v};
          };
          put(seller,'PRD-E18',1,4500);
          put(seller,'PRD-R04',50,500);
          put(seller,'PRD-R19',24,1200);
          put(buyer,'PRD-E20',1,200);
          put(buyer,'PRD-E21',1,300);
          S.year=2000;S.month=1;S.monthCommitted=ym(2000,1)-1;
          applyWorldHistory(S);syncWorldIdentities(S);
          const route=worldInternationalRegisterRoute(S,seller.id,'FR-UK-SEA-1900');
          const wh=worldInternationalInstallWarehouse(S,buyer.id,bp.id,'FR-UK-SEA-1900');
          const equipment=route.assetValue===4500&&wh.assetValue===500
            &&seller.stock['PRD-E18'].q===0&&buyer.stock['PRD-E21'].q===0;
          const placed=worldInternationalPlaceOrder(S,buyer.id,{
            routeId:route.id,warehouseId:wh.id,productId:'PRD-R19',
            quantity:12,unitPriceSeller:100,maxPaymentBuyer:100000});
          worldInternationalActOrder(S,seller.id,placed.id,'approve');
          S.month++;
          worldInternationalResolveOrders(S);
          const cargo=S.worldExpansion.internationalShipments.at(-1);
          const customs=cargo?.status==='IN_TRANSIT'&&cargo.quantity===12
            &&cargo.tariffBps===250&&cargo.dutyBuyer>0
            &&cargo.totalBuyer===cargo.prepaidBuyer+cargo.dutyBuyer
            &&acc(buyer,'worldImportDutyPrepaid')===cargo.dutyBuyer
            &&acc(buyer,'worldSupplierAdvances')===cargo.prepaidBuyer
            &&!check(S).length;
          const saved=parsePayload(savePayload(S));
          const retain=worldValidateInternationalLogistics(saved)
            &&saved.worldExpansion.internationalShipments.at(-1).dutyBuyer===cargo.dutyBuyer;
          S.month+=2;
          worldInternationalReceiveShipments(S);
          const delivered=cargo.status==='DELIVERED'
            &&buyer.stock['PRD-R19'].q===12
            &&buyer.stock['PRD-R19'].v===cargo.totalBuyer
            &&acc(buyer,'worldImportDutyPrepaid')===0
            &&!check(S).length;
          const group=consolidate(S),margin=cargo.goodsSeller-cargo.bookCost;
          const retained=group.adjustments.internationalInventoryProfit===baseFromLocal(margin,'FR')
            &&group.spotDeferredInternational===Math.round(margin*balanceFxRate(S,seller))
            &&group.errors.length===0;
          const spent=consume(buyer,'PRD-R19',6);
          post(buyer,{otherExpense:spent},{materials:spent},'国際在庫の部分消費','operating',S);
          const partially=consolidate(S);
          const provenance=partially.adjustments.internationalInventoryProfit===baseFromLocal(margin/2,'FR')
            &&partially.spotDeferredInternational===Math.round(margin/2*balanceFxRate(S,seller))
            &&worldValidateInternationalLogistics(S)&&!check(S).length;
          const changed=structuredClone(S);
          changed.worldExpansion.internationalShipments.at(-1).tariffBps++;
          const tamper=(()=>{try{parsePayload(savePayload(changed));return false}catch{return true}})();
          return {paths,equipment,customs,retain,delivered,retained,provenance,tamper};
        }""")
        assert all(multimodal.values()),multimodal
        browser.close()
    print("PASS Phase 4: cross-border physical assets, partial delivery, FX prepayment, "
          "title, customs, revenue, refund, tamper rejection and restore")

if __name__=="__main__":
    main()
