"""Two sourced domestic corridors, receiving buffers and historical equipment title."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result = page.evaluate("""async () => {
          saveAuto=async()=>true;
          S=newWorldGame({country:'JP',name:'Phase 2-G'});
          const seller=company(S.playerId),origin=seller.plants.find(p=>p.kind==='integrated');
          const capital=60000000;
          post(seller,{investment:capital},{cash:capital},'検証用子会社の設立','investing',S);
          const parentJournal=seller.journals.at(-1).id;
          const buyer=initFirm(S,{name:'Phase 2-G buyer',country:'JP',industry:'manufacturing',
            seedBase:capital*COUNTRIES.JP.fx/100,size:.7,strategy:'balanced',publicOwnership:false});
          buyer.owners=[{id:seller.id,econ:1,vote:1}];
          registerEquityLink(S,{parentId:seller.id,childId:buyer.id,ratio:1,kind:'foundation',
            considerationLocal:capital,buyerJournal:parentJournal,
            childJournal:buyer.journals.find(j=>j.text==='創業資本').id,
            bookEquityBase:baseFromLocal(capital,'JP'),cashAcquiredBase:baseFromLocal(acc(buyer,'cash'),'JP')});
          const buyerOrigin=buyer.plants[0];
          const place=(firm,site,id)=>{
            const p={...structuredClone(firm.plants[0]),id,siteId:site,siteCountry:'JP',
              name:id,construction:null,paused:false,renovation:null};
            firm.plants.push(p);
            syncPlant(firm);
            return p;
          };
          origin.siteId=buyerOrigin.siteId='JP-TOK';
          const railReceiver=place(buyer,'JP-YOK','P-G-RAIL');
          const roadReceiver=place(buyer,'JP-NGO','P-G-ROAD');
          const warehouseBuyer=place(seller,'JP-YOK','P-G-XFER');
          for(const firm of [seller,buyer]){
            firm.auto=false;
            firm.delegate.mode='manual';
            for(const model of firm.models)firm.plans[model.id]=0;
            for(const tech of ['production-1','materials-6','energy-1']){
              if(!firm.research.tree.done.includes(tech))firm.research.tree.done.push(tech);
            }
          }
          const date=(year,month)=>{
            S.year=year; S.month=month;
            S.monthCommitted=ym(year,month)-1;
            applyWorldHistory(S);
            syncWorldIdentities(S);
          };
          const buy=(f,id,q,v)=>{
            post(f,{materials:v},{cash:v},'検証用現物購入','operating',S);
            const stock=f.stock[id]??={q:0,v:0};
            stock.q+=q; stock.v+=v;
          };
          const refuses=(action,expected)=>{
            try{action();return false}
            catch(error){return error.message.includes(expected)}
          };
          const railId='JP-SHIMBASHI-YOKOHAMA',roadId='JP-TOMEI-TOKYO-KOMAKI';
          const railWarehouseId='JP-YOKOHAMA-SHINKO',roadWarehouseId='JP-NAGOYA-SILO';
          const register=(id,from='JP-TOK',to='JP-NGO',km=347)=>
            worldRegisterDomesticRoute(S,seller.id,from,to,km,'VERIFIED',id);
          date(1969,5);
          const opens=refuses(()=>register(roadId),'開通月');
          date(1970,1);
          origin.componentLines=[];origin.wirePlan=0;
          const rejectsFiction=refuses(()=>register('made-up-source'),'史料')
            &&refuses(()=>register(roadId,'JP-TOK','JP-OSA',347),'端点');
          buy(seller,'PRD-E16',1,1200);
          const needsWagon=refuses(()=>register(railId,'JP-TOK','JP-YOK',29),'現物設備')
            &&seller.stock['PRD-E16'].q===1;
          buy(seller,'PRD-E17',1,360);
          buy(seller,'PRD-E15',1,720);
          buy(seller,'PRD-R19',16,160);
          buy(seller,'PRD-R04',6,30);
          buy(seller,'PRD-R22',8,64);
          buy(seller,'PRD-R05',9,90);
          buy(seller,'PRD-M16',8,48);
          const recipeIds=['PRD-M15','PRD-M16','PRD-M17'];
          const refineries=recipeIds.every(id=>{
            const r=WORLD_SUPPLEMENTAL_BY_ID.get(id);
            return r.unit==='L'&&r.inputs[0][0]==='PRD-R05'&&r.powerKwh>0
              &&worldRecipeUnlocked(seller,r,1970)&&!worldRecipeUnlocked(seller,r,1900);
          });
          seller.staff.production=500;
          origin.lastProduced=0;
          worldPlanSave(seller,origin,'PRD-M15',1);
          produceWorldSupplemental(S,[]);
          const noFreeFuel=!seller.stock['PRD-M15']&&seller.stock['PRD-R05'].q===9;
          buy(seller,'PRD-E04',1,500);
          buy(seller,'PRD-R04',1,5);
          worldInstallGenerator(S,seller.id,origin.id);
          worldGeneratePower(S,seller.id,origin.id,1);
          const beforeProcessing=acc(seller,'cash');
          produceWorldSupplemental(S,[]);
          const refining=noFreeFuel&&seller.stock['PRD-M15']?.q===1
            &&seller.stock['PRD-R05'].q===6&&seller.stock['PRD-R04'].q===6
            &&seller.stock['PRD-M15'].v>30+beforeProcessing-acc(seller,'cash');
          buy(buyer,'PRD-E20',2,240);
          const rail=register(railId,'JP-TOK','JP-YOK',29);
          const road=register(roadId);
          const railDepot=worldInstallDomesticWarehouse(S,buyer.id,railReceiver.id,railWarehouseId);
          const roadDepot=worldInstallDomesticWarehouse(S,buyer.id,roadReceiver.id,roadWarehouseId);
          const transfer=(kind,assetId,fromCompanyId,toCompanyId,toPlantId)=>
            worldTransferDomesticAsset(S,{kind,assetId,fromCompanyId,toCompanyId,toPlantId});
          const dispatch=(route,p,product,quantity)=>worldDispatchDomesticShipment(
            S,route.id,seller.id,origin.id,buyer.id,p.id,product,quantity,16);
          const refusesCargo=refuses(()=>dispatch(road,roadReceiver,'PRD-R19',1),'荷種')
            &&refuses(()=>dispatch(road,roadReceiver,'PRD-S01',1),'現物重量品');
          railDepot.condition=50;
          const damagedCapacity=refuses(()=>dispatch(rail,railReceiver,'PRD-R19',5),'引当済み容量');
          railDepot.condition=100;
          const railLoad=dispatch(rail,railReceiver,'PRD-R19',7);
          // Existing reservations survive later deterioration and a save/load.
          railDepot.condition=50;
          const roadLoad=dispatch(road,roadReceiver,'PRD-R22',5);
          const capacity=refuses(()=>dispatch(rail,railReceiver,'PRD-R19',2),'引当済み容量')
            &&refuses(()=>dispatch(road,roadReceiver,'PRD-R22',2),'引当済み容量');
          const freight=railLoad.fuelId==='PRD-R04'&&railLoad.fuelQuantity===1&&railLoad.freightCost===5
            &&roadLoad.fuelId==='PRD-M16'&&roadLoad.fuelQuantity===3&&roadLoad.freightCost===18
            &&seller.stock['PRD-R19'].q===9&&seller.stock['PRD-M16'].q===5;
          const pay=railLoad.prepaid+roadLoad.prepaid;
          const escrow=acc(seller,'sales')===0&&-acc(seller,'worldCustomerAdvances')===pay
            &&acc(buyer,'worldSupplierAdvances')===pay
            &&acc(seller,'worldShipmentStock')===railLoad.bookCost+roadLoad.bookCost;
          const stays=refuses(()=>transfer('route',rail.id,seller.id,buyer.id,buyerOrigin.id),'未検収')
            &&refuses(()=>transfer('warehouse',railDepot.id,buyer.id,seller.id,warehouseBuyer.id),'未検収')
            &&refuses(()=>worldRetireDomesticAsset(S,buyer.id,'warehouse',railDepot.id),'未検収')
            &&worldDomesticBlocksReorganization(S,seller.id,origin);
          const saved=parsePayload(savePayload(S));
          const savedTransit=saved.worldExpansion.domesticShipments.every(t=>t.status==='IN_TRANSIT')
            &&worldDomesticWarehouseReservations(saved.worldExpansion,railDepot.id)===7;
          roadReceiver.paused=true;
          syncPlant(buyer);
          date(1970,2);
          worldDepreciateInfrastructure(S);
          worldReceiveDomesticShipments(S);
          const receipt=railLoad.status==='DELIVERED'&&roadLoad.status==='IN_TRANSIT'
            &&-acc(seller,'sales')===railLoad.amount&&buyer.stock['PRD-R19'].v===railLoad.prepaid
            &&worldDomesticWarehouseReservations(S.worldExpansion,railDepot.id)===0;
          const routeGross=rail.assetValue,routeDep=rail.accumulatedDepreciation;
          const buyerPpe=acc(buyer,'ppe'),sellerPpe=acc(seller,'ppe'),sellerAccDep=acc(seller,'accdep');
          const sellerCash=acc(seller,'cash'),buyerCash=acc(buyer,'cash');
          const groupBefore=consolidate(S);
          const routeSale=transfer('route',rail.id,seller.id,buyer.id,buyerOrigin.id);
          const title=routeDep>0&&routeSale.net===routeGross-routeDep
            &&rail.ownerCompanyId===buyer.id&&rail.accumulatedDepreciation===0
            &&acc(seller,'ppe')===sellerPpe-routeGross&&acc(seller,'accdep')===sellerAccDep+routeDep
            &&acc(buyer,'ppe')===buyerPpe+routeSale.net&&acc(buyer,'cash')===buyerCash-routeSale.net
            &&acc(seller,'cash')===sellerCash+routeSale.net&&rail.monthlyDepreciation===routeDep;
          const warehouseSale=transfer('warehouse',railDepot.id,buyer.id,seller.id,warehouseBuyer.id);
          const groupAfter=consolidate(S);
          const groupTitle=groupAfter.errors.length===0&&groupBefore.bs.assets===groupAfter.bs.assets
            &&groupBefore.bs.liab===groupAfter.bs.liab&&groupBefore.bs.cash===groupAfter.bs.cash
            &&groupBefore.pl.profit===groupAfter.pl.profit;
          worldDepreciateInfrastructure(S);
          const once=rail.accumulatedDepreciation===0&&railDepot.accumulatedDepreciation===0
            &&railDepot.plantId===warehouseBuyer.id&&warehouseSale.net>0;
          date(1970,3);
          worldDepreciateInfrastructure(S);
          worldReceiveDomesticShipments(S);
          const beforeRefund=acc(buyer,'cash');
          worldRefundDomesticShipment(S,roadLoad.id);
          const refund=roadLoad.status==='REFUNDED'&&acc(buyer,'cash')===beforeRefund+roadLoad.prepaid
            &&acc(buyer,'worldSupplierAdvances')===0&&acc(seller,'worldCustomerAdvances')===0
            &&acc(seller,'worldShipmentStock')===0&&rail.accumulatedDepreciation===routeDep
            &&!buyer.stock['PRD-R22']&&worldDomesticWarehouseReservations(S.worldExpansion,roadDepot.id)===0;
          const restored=parsePayload(savePayload(S));
          const closure=check(S).length===0&&check(restored).length===0
            &&restored.worldExpansion.domesticAssetTransfers.length===2
            &&restored.worldExpansion.domesticShipments.map(t=>t.status).join()==='DELIVERED,REFUNDED'
            &&worldValidateDomesticLogistics(restored);
          const altered=structuredClone(restored);
          altered.worldExpansion.domesticAssetTransfers[0].net+=1;
          const tamper=refuses(()=>worldValidateDomesticLogistics(altered),'履歴');
          VIEW_FIRM=seller.id;
          requestOperationSaveV037=()=>true;
          render();
          document.getElementById('content').innerHTML=worldDomesticLogisticsPanel(seller,true);
          const element=document.querySelector('#world-domestic');
          element.open=true;
          const showPanel=element.textContent.includes('国内B2B物流')
            &&element.textContent.includes('東名高速道路')
            &&element.textContent.includes('REFUNDED')
            &&element.querySelector('form[data-world-domestic="retire"]')!==null;
          return {opens,rejectsFiction,needsWagon,refineries,refining,refusesCargo,damagedCapacity,capacity,freight,escrow,
            stays,savedTransit,receipt,title,groupTitle,once,refund,closure,tamper,showPanel};
        }""")
        assert result and all(result.values()), result
        panel = page.locator("#world-domestic")
        warehouse_id = page.evaluate(
            "() => Object.values(S.worldExpansion.domesticWarehouses).find(h => h.ownerCompanyId === S.playerId).id"
        )
        panel.locator('form[data-world-domestic="retire"] select').select_option(label=warehouse_id)
        panel.get_by_role("button", name="設備を廃止").click()
        assert page.evaluate("""() => {
          const h=Object.values(S.worldExpansion.domesticWarehouses).find(x=>x.ownerCompanyId===S.playerId);
          return h.retiredAt===ym(S.year,S.month) && !check(S).length
            && worldValidateDomesticLogistics(parsePayload(savePayload(S)));
        }""")
        assert not errors, errors
        browser.close()
    print("PASS Phase 2-G: evidenced rail/road, refinery goods, warehouse reservation, receipt/refund, asset title and save")


if __name__ == "__main__":
    main()
