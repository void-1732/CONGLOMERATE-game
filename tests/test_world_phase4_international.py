"""Phase 4: international real freight, foreign exchange, title and journals."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def main(observe_receipts=None):
    with sync_playwright() as pw:
        browser=pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"])
        page=browser.new_page(offline=True)
        page.on("pageerror",lambda err:print("BROWSER ERROR",err))
        page.set_content((ROOT/"index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        if observe_receipts is not None:
            observe_receipts(page)
        result=page.evaluate("""() => {
          S=newWorldGame({country:'UK',name:'Phase 4 Channel freight'});
          // Historical exact-amount fixture; new tariff is covered by the monthly freight audit.
          delete S.worldExpansion.freightRateFromSeq;
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
          const denied=action=>{try{action();return false;}catch{return true;}};
          const retirementBlockedByOrder=denied(()=>worldRetireInternationalAsset(S,seller.id,route.id))
            &&denied(()=>worldRetireInternationalAsset(S,buyer.id,warehouse.id));
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
          const retirementBlockedInTransit=denied(()=>worldRetireInternationalAsset(S,seller.id,route.id))
            &&denied(()=>worldRetireInternationalAsset(S,buyer.id,warehouse.id));
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
          worldMatchLedgerCurrencyRates(S);
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
            &&worldInternationalTradePanel(buyer,true).includes(order.id)
            &&worldInternationalTradePanel(buyer,true).includes('暫定関税 2.5%');
          worldDepreciateInfrastructure(S);
          const retirementBefore=(firm,asset)=>({
            ppe:acc(firm,'ppe'),accdep:acc(firm,'accdep'),expense:acc(firm,'otherExpense'),
            cash:acc(firm,'cash'),assetId:asset.id,gross:asset.assetValue,dep:asset.accumulatedDepreciation
          });
          window.beforeInternationalRetirement=[retirementBefore(buyer,warehouse),retirementBefore(seller,route)];
          const wrongOwnerDenied=denied(()=>worldRetireInternationalAsset(S,buyer.id,route.id));
          const outsideGroup=structuredClone(S);
          company(seller.id,outsideGroup).owners=[{id:'PUBLIC',econ:1,vote:1}];
          const outsideBefore=JSON.stringify(outsideGroup);
          const unauthorizedDenied=!controller(outsideGroup,seller.id)
            &&denied(()=>worldRetireInternationalAsset(outsideGroup,seller.id,route.id))
            &&JSON.stringify(outsideGroup)===outsideBefore;
          VIEW_FIRM=buyer.id;PAGE='logisticsHubs';render();
          return {assets,earlyDenied,queued,savedOrder,dispatched,refundDenied,
            inTransitValid,refunded,delivered,restored,tamper,ui,wrongOwnerDenied,unauthorizedDenied,
            retirementBlockedByOrder,retirementBlockedInTransit};
        }""")
        assert all(result.values()),result
        page.locator('#world-international > summary').click()
        retire = page.locator('form[data-world-international="retire"]')
        retire.get_by_role('button', name='国際物流設備を除却').click()
        page.evaluate("""() => {
          VIEW_FIRM=S.worldExpansion.internationalShipments[0].sellerId;
          render();
        }""")
        page.locator('#world-international > summary').click()
        retire.get_by_role('button', name='国際物流設備を除却').click()
        retirement = page.evaluate("""() => {
          const persisted=parsePayload(savePayload(S)),w=persisted.worldExpansion;
          const originals=[...Object.values(w.internationalWarehouses),...Object.values(w.internationalRoutes)];
          const checks=originals.map((asset,i)=>{
            const before=window.beforeInternationalRetirement[i],f=company(asset.ownerCompanyId,persisted);
            return asset.id===before.assetId&&asset.retiredAt===ym(2000,3)&&before.dep>0
              &&acc(f,'ppe')===before.ppe-before.gross&&acc(f,'accdep')===before.accdep+before.dep
              &&acc(f,'otherExpense')===before.expense+before.gross-before.dep&&acc(f,'cash')===before.cash;
          });
          const depot=worldMapWarehouseLedger(persisted).find(row=>row.id===originals[0].id);
          const route=worldMapNetwork(persisted).routes.find(row=>row.id===originals[1].profileId);
          const damaged=structuredClone(persisted);
          Object.values(damaged.worldExpansion.internationalRoutes)[0].retirementJournal++;
          const rejects=action=>{try{action();return false;}catch{return true;}};
          const tamper=rejects(()=>parsePayload(savePayload(damaged)));
          const [oldWarehouse,oldRoute]=originals;
          const buyer=company(oldWarehouse.ownerCompanyId,persisted),seller=company(oldRoute.ownerCompanyId,persisted);
          for(const [firm,product,price] of [[buyer,'PRD-E20',200],[seller,'PRD-E15',2500]]){
            post(firm,{materials:price},{cash:price},'交換用現物取得','operating',persisted);
            firm.stock[product]={q:1,v:price};
          }
          const newRoute=worldInternationalRegisterRoute(persisted,seller.id,oldRoute.profileId);
          const newWarehouse=worldInternationalInstallWarehouse(persisted,buyer.id,oldWarehouse.plantId,oldWarehouse.profileId);
          const reopened=parsePayload(savePayload(persisted));
          return {accounting:checks.every(Boolean),history:w.internationalShipments[0].status==='DELIVERED',
            map:depot.status==='廃止済み'&&depot.available===0&&route.installed===0,
            tamper,secondRetirement:rejects(()=>worldRetireInternationalAsset(persisted,seller.id,oldRoute.id)),
            replacement:newRoute.id!==oldRoute.id&&newWarehouse.id!==oldWarehouse.id
              &&!check(reopened).length&&!consolidate(reopened).errors.length};
        }""")
        assert all(retirement.values()),retirement
        multimodal=page.evaluate("""() => {
          const profiles=Object.entries(WORLD_INTERNATIONAL_CORRIDORS);
          const modes=new Set(profiles.map(([,p])=>p.mode));
          const documentedAdded=['SE-UK-GOTHENBURG-TIMBER','NL-US-ROTTERDAM-PULP',
            'UK-IT-CARDIFF-GENOA-COAL','EG-UK-ALEXANDRIA-COTTON',
            'IN-UK-BOMBAY-COTTON','ZA-UK-CAPE-WOOL'];
          const paths=profiles.length>=33
            &&documentedAdded.every(id=>WORLD_INTERNATIONAL_CORRIDORS[id]
              &&WORLD_INTERNATIONAL_ROUTE_EVIDENCE[id]?.source?.startsWith('https://'))
            &&['road+rail-shuttle','sea','rail','air','rail+sea'].every(m=>modes.has(m))
            &&profiles.every(([,p])=>findSite(p.from)&&findSite(p.to)
              &&findSite(p.from).country!==findSite(p.to).country
              &&p.capacityKg>0&&p.warehouseCapacityKg>0&&p.distanceKm>0
              &&p.fuel&&p.truck&&p.status==='PROVISIONAL');
          S=newWorldGame({country:'UK',name:'Phase 4 ocean test'});
          // Historical exact-amount fixture; new tariff is covered by the monthly freight audit.
          delete S.worldExpansion.freightRateFromSeq;
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
          const startsAfterEvidence=worldInternationalRouteAvailable(S,'US-UK-SEA-1900')
            &&!worldInternationalRouteAvailable(S,'FR-UK-SEA-1900');
          S.year=2000;S.month=1;S.monthCommitted=ym(2000,1)-1;
          applyWorldHistory(S);syncWorldIdentities(S);
          let unsupportedWarehouse=false;
          try{worldInternationalInstallWarehouse(S,buyer.id,bp.id,'DE-UK-SEA-1900');}
          catch{unsupportedWarehouse=true;}
          const publicProfileIds=profiles.filter(([id])=>worldInternationalRouteAvailable(S,id)).map(([id])=>id);
          const sourceGate=startsAfterEvidence&&unsupportedWarehouse&&publicProfileIds.length===5
            &&publicProfileIds.every(id=>WORLD_INTERNATIONAL_ROUTE_EVIDENCE[id].source.startsWith('https://'))
            &&!worldInternationalTradePanel(seller,true).includes('FR-UK-AIR-1950')
            &&!worldInternationalTradePanel(buyer,true).includes('DE-UK-SEA-1900');
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
          const rejectsSave=(mutate)=>{
            const modified=structuredClone(S),w=modified.worldExpansion,t=w.internationalShipments[0];
            mutate(w,t);
            try{parsePayload(savePayload(modified));return false;}catch{return true;}
          };
          const blocksChangedFx=rejectsSave((w,t)=>{t.sellerRate*=2;t.buyerRate*=2;});
          const blocksChangedFuel=rejectsSave((w,t)=>{t.fuelRequired++;});
          const blocksMissingShipment=rejectsSave(w=>{w.internationalShipments=[];});
          const blocksWrongCloseMonth=rejectsSave(w=>{w.internationalOrders[0].closedAt++;});
          const blocksFutureEquipment=rejectsSave(w=>{w.internationalRoutes[route.id].installedAt=ym(2001,1);});
          const coalBefore=seller.stock['PRD-R04'].q;
          const sharedFuelDenied=Boolean(worldInternationalQuote(
            S,route,'PRD-R04',coalBefore,100,buyer.id).problem);
          const sharedFuelQuoted=!worldInternationalQuote(
            S,route,'PRD-R04',1,100,buyer.id).problem;
          const coalOrder=worldInternationalPlaceOrder(S,buyer.id,{
            routeId:route.id,warehouseId:wh.id,productId:'PRD-R04',
            quantity:1,unitPriceSeller:100,maxPaymentBuyer:100000});
          worldInternationalActOrder(S,seller.id,coalOrder.id,'approve');
          S.month++;
          worldInternationalResolveOrders(S);
          const coal=S.worldExpansion.internationalShipments.at(-1);
          const sharedFuelDispatched=coal?.orderId===coalOrder.id
            &&coal.status==='IN_TRANSIT'&&coal.quantity===1
            &&coal.fuelRequired>0&&coal.fuelCost>0
            &&seller.stock['PRD-R04'].q===coalBefore-1-coal.fuelRequired
            &&acc(seller,'materials')>=0
            &&worldValidateInternationalLogistics(S)&&!check(S).length;
          return {paths,sourceGate,equipment,customs,retain,delivered,retained,provenance,tamper,
            blocksChangedFx,blocksChangedFuel,blocksMissingShipment,blocksWrongCloseMonth,blocksFutureEquipment,
            sharedFuelDenied,sharedFuelQuoted,sharedFuelDispatched};
        }""")
        assert all(multimodal.values()),multimodal
        browser.close()
    print("PASS Phase 4: cross-border physical assets, partial delivery, FX prepayment, "
          "title, customs, revenue, refund, tamper rejection and restore")

if __name__=="__main__":
    main()
