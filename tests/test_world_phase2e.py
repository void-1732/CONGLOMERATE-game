"""Phase 2-E: physical on-site power lines, fuel cost attribution and mined-site receipts."""
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
        page.on("pageerror",lambda error: errors.append(str(error)))
        page.set_content((ROOT/"index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        wired=page.evaluate("""()=>{
          saveAuto=async()=>true;
          S=newWorldGame({country:'JP',name:'Phase2-E fuel allocation'});
          const f=company(S.playerId,S),p=f.plants.find(x=>x.kind==='integrated');
          f.staff.production=160;f.auto=false;f.delegate.mode='manual';
          for(const model of f.models)f.plans[model.id]=0;
          const target={...structuredClone(p),id:'P-PHASE2E',name:'受電先工場',lastProduced:0,
            componentLines:[],worldPlan:null,worldProductionMonth:null,wireProductionMonth:null};
          f.plants.push(target);syncPlant(f);syncWorldIdentities(S);
          S.year=1950;S.month=3;applyWorldHistory(S);syncWorldIdentities(S);
          f.factoryOps.staffAssignments[target.id]=20;
          for(const name of ['energy-1','materials-1','production-1'])
            if(!f.research.tree.done.includes(name))f.research.tree.done.push(name);
          post(f,{materials:1160},{cash:1160},'試験用・実在庫の有償取得','operating',S);
          f.stock['PRD-E04']={q:1,v:900};f.stock['PRD-M06']={q:2,v:120};
          f.stock['PRD-R04']={q:2,v:120};f.stock['PRD-R30']={q:4,v:20};
          let noFreeTransfer=false;try{worldTransferPower(S,f.id,p.id,target.id,12)}catch{noFreeTransfer=true}
          const ppe=acc(f,'ppe');
          const machine=worldInstallGenerator(S,f.id,p.id);
          const line=worldInstallPowerLine(S,f.id,p.id,target.id);
          const paidEquipment=acc(f,'ppe')===ppe+1020&&f.stock['PRD-M06'].q===0
            &&f.stock['PRD-E04'].q===0&&line.ownerCompanyId===f.id&&machine.assetValue===900;
          const generation=worldGeneratePower(S,f.id,p.id,2);
          const transfer=worldTransferPower(S,f.id,p.id,target.id,12);
          const conservation=generation.grossKwh===20&&generation.lossKwh===2
            &&generation.deliveredKwh===18&&transfer.sentKwh===12
            &&transfer.lossKwh===1&&transfer.deliveredKwh===11
            &&transfer.fuelBookCost===80&&worldPowerAvailable(S,p.id)===6
            &&worldPowerAvailable(S,target.id)===11;
          let rejectsDuplicate=false,rejectsOffsite=false;
          try{worldTransferPower(S,f.id,p.id,target.id,2)}catch{rejectsDuplicate=true}
          target.siteId='OFFSITE-INVALID';
          try{worldTransferPower(S,f.id,p.id,target.id,2)}catch{rejectsOffsite=true}
          target.siteId=p.siteId;syncWorldIdentities(S);
          const priorExpense=acc(f,'otherExpense');
          worldPlanSave(f,target,'PRD-M43',2);
          const events=[];produceWorldSupplemental(S,events);
          const b=S.worldExpansion.powerAllocations[target.id],output=f.stock['PRD-M43'];
          const conversion=Math.max(1,localFromBase(15*eraCostFactor(S.year),f.country));
          const allocated=output?.q===2&&b.capitalizedFuelCost===72
            &&output.v===20+2*conversion+72&&acc(f,'otherExpense')===priorExpense-72
            &&b.usedKwh===10&&worldPowerAvailable(S,target.id)===1;
          const saved=parsePayload(savePayload(S));
          const persistent=saved.worldExpansion.powerTransfers.length===1
            &&saved.worldExpansion.powerAllocations[target.id].capitalizedFuelCost===72;
          const corrupt=structuredClone(S);
          corrupt.worldExpansion.powerTransfers[0].sentKwh++;
          let rejectsTampering=false;try{validateWorldExpansion(corrupt)}catch{rejectsTampering=true}
          const catalog=WORLD_SUPPLEMENTAL_RECIPES.length===104&&
            WORLD_PRODUCTS.filter(x=>worldProductImplementation(x.id).implementation==='DATA_CANDIDATE').length===7;
          const noService=WORLD_PRODUCTS.filter(x=>x.category==='service')
            .every(x=>!worldServiceTerms(x.id).physicalInventory&&!f.stock[x.id]);
          const ledger=check(S).length===0&&consolidate(S).errors.length===0;
          return {noFreeTransfer,paidEquipment,conservation,rejectsDuplicate,rejectsOffsite,
            allocated,persistent,rejectsTampering,catalog,noService,ledger};
        }""")
        assert all(wired.values()),wired
        mined=page.evaluate("""async()=>{
          saveAuto=async()=>true;
          S=newWorldGame({country:'JP',name:'Phase2-E mined-to-market'});
          const buyer=company(S.playerId,S),bp=buyer.plants.find(p=>p.kind==='integrated');
          const seller=S.firms.find(f=>f.industry==='resource'&&
            f.plants.some(p=>factoryLaborPlanV026(f).byId[p.id]?.assigned>0));
          const mp=seller.plants.find(p=>factoryLaborPlanV026(seller).byId[p.id]?.assigned>0);
          buyer.auto=false;buyer.delegate.mode='manual';
          for(const model of buyer.models)buyer.plans[model.id]=0;
          bp.lastProduced=0;bp.componentLines=[];bp.wirePlan=0;
          bp.siteId=mp.siteId;bp.siteCountry=mp.siteCountry;
          syncPlant(buyer);syncWorldIdentities(S);
          if(!buyer.research.tree.done.includes('materials-1'))buyer.research.tree.done.push('materials-1');
          const id='DEP-PHASE2E-TEST',month=S.monthCommitted;
          S.worldExpansion.resourceDeposits[id]={id,productId:'PRD-R19',status:'TEST_FIXTURE',
            ownerCompanyId:seller.id,plantId:mp.id,locationId:'LOC-'+mp.siteId,
            initialReserve:10,remaining:10,extracted:0,
            availableFromYear:1900,requiredTech:null,lastExtractedAt:null};
          worldSetMiningPlan(S,seller.id,mp.id,id,5,14);
          worldSetLocalSupplyPlan(S,id,buyer.id,bp.id,4,31);
          worldPlanSave(buyer,bp,'PRD-M12',2);
          await runMonth();
          const d=S.worldExpansion.resourceDeposits[id],plan=S.worldExpansion.localSupplyPlans[id],
            receipt=S.worldExpansion.physicalDeliveries.find(r=>r.id===plan.receiptId),
            stock=company(buyer.id,S).stock['PRD-M12'],group=consolidate(S);
          const resource=d.remaining===5&&d.extracted===5&&d.lastExtractedQuantity===5;
          const physical=receipt?.quantity===4&&receipt.amount===124&&receipt.month===month+1
            &&plan.lastDeliveredAt===month+1;
          const manufacturing=stock?.q===2&&stock.v>124;
          const save=parsePayload(savePayload(S));
          const persistent=save.worldExpansion.localSupplyPlans[id].receiptId===receipt.id;
          const books=!check(S).length&&!group.errors.length&&group.cf.reconciled
            &&S.monthCommitted===month+1;
          const prior=S.worldExpansion.physicalDeliveries.length;
          worldFulfillLocalSupplyPlans(S,[]);
          const noDuplicate=S.worldExpansion.physicalDeliveries.length===prior;
          return {resource,physical,manufacturing,persistent,books,noDuplicate};
        }""")
        assert all(mined.values()),mined
        assert not errors,errors
        browser.close()
    print("PASS Phase 2-E: finite mining, local acceptance, wired fuel cost and saving")

if __name__=="__main__":
    main()
