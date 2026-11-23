"""Phase 2-F: metered asset depreciation/retirement and finite domestic B2B logistics.

Both chains use genuinely paid physical inputs. All rail/site distances and
conversion constants are explicit TEST_FIXTURE/PROVISIONAL pilot values, not
assumed railway infrastructure or automatic economic supply.
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
        page=browser.new_page()
        errors=[]
        page.on("pageerror",lambda err:errors.append(str(err)))
        page.set_content((ROOT/"index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        assets=page.evaluate("""()=>{
          saveAuto=async()=>true;
          S=newWorldGame({country:'JP',name:'Phase2-F physical power asset life'});
          const f=company(S.playerId,S),src=f.plants.find(p=>p.kind==='integrated');
          const target={...structuredClone(src),id:'P-2F-WIRE',name:'受電設備テスト',worldPlan:null,
            lastProduced:0,componentLines:[],wirePlan:0};
          f.plants.push(target);syncPlant(f);syncWorldIdentities(S);
          S.year=1950;S.month=3;applyWorldHistory(S);syncWorldIdentities(S);
          if(!f.research.tree.done.includes('energy-1'))f.research.tree.done.push('energy-1');
          post(f,{materials:1140},{cash:1140},'有償発電機/銅線/実燃料','operating',S);
          f.stock['PRD-E04']={q:1,v:900};f.stock['PRD-M06']={q:2,v:120};f.stock['PRD-R04']={q:2,v:120};
          const oldPpe=acc(f,'ppe'),oldDep=acc(f,'accdep');
          const generator=worldInstallGenerator(S,f.id,src.id),line=worldInstallPowerLine(S,f.id,src.id,target.id);
          const sourcePower=worldGeneratePower(S,f.id,src.id,2);
          const transfer=worldTransferPower(S,f.id,src.id,target.id,12);
          const real=acc(f,'ppe')===oldPpe+1020&&f.stock['PRD-E04'].q===0
            &&f.stock['PRD-M06'].q===0&&sourcePower.deliveredKwh===18
            &&transfer.deliveredKwh===11&&worldPowerAvailable(S,target.id)===11;
          worldDepreciateInfrastructure(S);
          worldDepreciateInfrastructure(S);
          const depreciation=generator.accumulatedDepreciation===8
            &&line.accumulatedDepreciation===1&&generator.condition===99&&line.condition===99
            &&acc(f,'accdep')===oldDep-9;
          let forbidsGeneratorRetireFirst=false;
          try{worldRetireEnergyAsset(S,f.id,src.id,'generator')}catch{forbidsGeneratorRetireFirst=true}
          const retiredLine=worldRetireEnergyAsset(S,f.id,target.id,'line');
          const retiredGenerator=worldRetireEnergyAsset(S,f.id,src.id,'generator');
          const closed=retiredLine.remainingValue===119&&retiredGenerator.remainingValue===892
            &&acc(f,'ppe')===oldPpe&&acc(f,'accdep')===oldDep
            &&worldPowerAvailable(S,src.id)===0&&worldPowerAvailable(S,target.id)===0;
          let refusesRestart=false;
          try{worldGeneratePower(S,f.id,src.id,1)}catch{refusesRestart=true}
          const bad=structuredClone(S);bad.worldExpansion.powerGenerators[src.id].condition=200;
          let rejectTamper=false;try{validateWorldExpansion(bad)}catch{rejectTamper=true}
          const persisted=parsePayload(savePayload(S));
          const saved=persisted.worldExpansion.powerGenerators[src.id].retiredAt===ym(S.year,S.month)
            &&persisted.worldExpansion.powerLines[target.id].accumulatedDepreciation===1;
          const balanced=!check(S).length&&!consolidate(S).errors.length;
          const catalog=WORLD_SUPPLEMENTAL_RECIPES.length===104
            &&WORLD_PRODUCTS.filter(p=>worldProductImplementation(p.id).implementation==='DATA_CANDIDATE').length===4;
          const services=WORLD_PRODUCTS.filter(p=>p.category==='service')
            .every(p=>!worldServiceTerms(p.id).physicalInventory&&!f.stock[p.id]);
          return {real,depreciation,forbidsGeneratorRetireFirst,closed,refusesRestart,
            rejectTamper,saved,balanced,catalog,services};
        }""")
        assert all(assets.values()),assets
        shipping=page.evaluate("""async()=>{
          saveAuto=async()=>true;render=()=>{};
          S=newWorldGame({country:'JP',name:'Phase2-F physical locomotive & domestic B2B'});
          const seller=company(S.playerId,S),
            buyer=S.firms.find(f=>f.id!==seller.id&&f.country==='JP'&&f.plants.length);
          const src=seller.plants.find(p=>p.kind==='integrated'),dst=buyer.plants[0];
          seller.auto=false;seller.delegate.mode='manual';seller.staff.production=200;
          for(const model of seller.models)seller.plans[model.id]=0;
          src.componentLines=[];src.wirePlan=0;src.lastProduced=0;
          dst.siteId='JP-OSA';dst.siteCountry='JP';syncPlant(buyer);syncWorldIdentities(S);
          S.year=1950;S.month=3;S.monthCommitted=ym(1950,2);
          applyWorldHistory(S);syncWorldIdentities(S);
          if(!seller.research.tree.done.includes('production-1'))
            seller.research.tree.done.push('production-1');
          const inputs=[['PRD-E01',2,1200],['PRD-M02',4,400],['PRD-M33',1,100],
            ['PRD-R19',10,100],['PRD-R04',3,150]];
          const value=inputs.reduce((n,x)=>n+x[2],0);
          post(seller,{materials:value},{cash:value},'現物素材と実石炭の有償仕入','operating',S);
          for(const [id,q,v] of inputs)seller.stock[id]={q,v};
          worldPlanSave(seller,src,'PRD-E16',1);
          produceWorldSupplemental(S,[]);
          const manufactured=seller.stock['PRD-E16']?.q===1&&seller.stock['PRD-E16'].v>0;
          let refusesNoEvidence=false;
          try{worldRegisterDomesticRoute(S,seller.id,src.siteId,dst.siteId,500,'VERIFIED','')}
          catch{refusesNoEvidence=true}
          const route=worldRegisterDomesticRoute(S,seller.id,src.siteId,dst.siteId,500,'TEST_FIXTURE');
          const shipment=worldDispatchDomesticShipment(S,route.id,seller.id,src.id,
            buyer.id,dst.id,'PRD-R19',5,30);
          let refusesCapacity=false,refusesService=false;
          try{worldDispatchDomesticShipment(S,route.id,seller.id,src.id,buyer.id,dst.id,'PRD-R19',6,30)}
          catch{refusesCapacity=true}
          try{worldDispatchDomesticShipment(S,route.id,seller.id,src.id,buyer.id,dst.id,'PRD-S01',1,30)}
          catch{refusesService=true}
          const inTransit=shipment.status==='IN_TRANSIT'&&
            -acc(seller,'worldCustomerAdvances')===shipment.prepaid
            &&acc(buyer,'worldSupplierAdvances')===shipment.prepaid
            &&acc(seller,'worldShipmentStock')===shipment.bookCost
            &&acc(seller,'sales')===0&&!(buyer.stock['PRD-R19']?.q>0);
          const savedInTransit=parsePayload(savePayload(S)).worldExpansion.domesticShipments[0].status==='IN_TRANSIT';
          const months=[];
          for(let i=0;i<3;i++){
            const before=S.monthCommitted;
            await runMonth();
            const report=consolidate(S);
            months.push({advanced:S.monthCommitted===before+1,
              checked:!check(S).length&&!report.errors.length,
              status:S.worldExpansion.domesticShipments[0].status,
              cf:report.cf.reconciled});
          }
          const current=company(seller.id,S),receiver=company(buyer.id,S),shipmentNow=S.worldExpansion.domesticShipments[0];
          const received=months.every(x=>x.advanced&&x.checked)
            &&months[0].status==='IN_TRANSIT'&&months[1].status==='IN_TRANSIT'
            &&months[2].status==='DELIVERED'&&months[2].cf
            &&shipmentNow.receivedAt===shipment.dueAt
            &&receiver.stock['PRD-R19']?.q===5&&receiver.stock['PRD-R19'].v===shipment.prepaid
            &&acc(current,'worldShipmentStock')===0
            &&acc(current,'worldCustomerAdvances')===0
            &&acc(receiver,'worldSupplierAdvances')===0;
          const second=worldDispatchDomesticShipment(S,route.id,current.id,src.id,
            receiver.id,dst.id,'PRD-R19',2,35);
          const plant=receiver.plants.find(p=>p.id===dst.id);
          plant.paused=true;syncPlant(receiver);syncWorldIdentities(S);
          S.year=1950;S.month=9;applyWorldHistory(S);syncWorldIdentities(S);
          worldReceiveDomesticShipments(S,[]);
          const suspended=second.status==='IN_TRANSIT';
          const refunded=worldRefundDomesticShipment(S,second.id);
          const refundNoGoods=refunded.status==='REFUNDED'&&
            receiver.stock['PRD-R19']?.q===5&&acc(current,'worldShipmentStock')===0
            &&acc(current,'worldCustomerAdvances')===0&&acc(receiver,'worldSupplierAdvances')===0;
          const routeClosed=worldRetireDomesticRoute(S,current.id,route.id).retiredAt===ym(S.year,S.month);
          const corrupted=structuredClone(S);corrupted.worldExpansion.domesticShipments[0].prepaid+=1;
          let rejectsTampered=false;try{validateWorldExpansion(corrupted)}catch{rejectsTampered=true}
          const persisted=parsePayload(savePayload(S));
          const saved=persisted.worldExpansion.domesticShipments[0].status==='DELIVERED'
            &&persisted.worldExpansion.domesticShipments[1].status==='REFUNDED';
          const clean=!check(S).length&&!consolidate(S).errors.length;
          const noImaginaryResource=!Object.keys(S.worldExpansion.resourceDeposits).length;
          return {manufactured,refusesNoEvidence,refusesCapacity,refusesService,inTransit,
            savedInTransit,received,suspended,refundNoGoods,routeClosed,rejectsTampered,
            saved,clean,noImaginaryResource};
        }""")
        assert all(shipping.values()),shipping
        assert not errors,errors
        browser.close()
    print("PASS Phase 2-F: nine recipes, physical power-asset depreciation/retirement, paid locomotive, freight escrow/arrival/refund, save/CF")

if __name__=="__main__":
    main()
