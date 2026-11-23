"""Phase 2-D physical mining, site delivery, fuel-to-energy metering and constraints."""
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
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.set_content((ROOT/"index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result=page.evaluate("""async()=>{
          saveAuto=async()=>true;
          S=newWorldGame({country:'JP',name:'Phase2-D 有限資源・発電・検収'});
          const firm=company(S.playerId,S),plant=firm.plants.find(canPlanWireProduction);
          const mine=S.firms.find(f=>f.industry==='resource'&&f.plants.some(p=>factoryLaborPlanV026(f).byId[p.id]?.assigned>0));
          const mp=mine.plants.find(p=>factoryLaborPlanV026(mine).byId[p.id]?.assigned>0);
          if(!plant||!mp)return {error:'plant missing'};
          firm.auto=false;firm.delegate.mode='manual';
          for(const model of firm.models)firm.plans[model.id]=0;
          plant.componentLines=[];plant.wirePlan=0;plant.lastProduced=0;
          const id='DEP-2D-FIXTURE';
          S.worldExpansion.resourceDeposits[id]={
            id,productId:'PRD-R04',status:'TEST_FIXTURE',ownerCompanyId:mine.id,plantId:mp.id,
            locationId:'LOC-'+mp.siteId,initialReserve:12,remaining:12,extracted:0,
            availableFromYear:1900,requiredTech:null,lastExtractedAt:null
          };
          worldSetMiningPlan(S,mine.id,mp.id,id,5,19);
          const beforeLegacy=mine.reserveUnits;
          const beforeMonth=S.monthCommitted;
          await runMonth();
          const mf=company(mine.id,S),pf=company(firm.id,S),pm=mf.plants.find(p=>p.id===mp.id);
          const monthlyMined=S.monthCommitted===beforeMonth+1
            &&S.worldExpansion.resourceDeposits[id].extracted>0
            &&S.worldExpansion.resourceDeposits[id].remaining<12
            &&mf.reserveUnits===beforeLegacy;
          // Validate a same-location physical handoff; no international shipment is claimed.
          pf.plants.find(p=>p.id===plant.id).siteId=pm.siteId;
          syncWorldIdentities(S);
          const currentStock=mf.stock['PRD-R04']?.q||0;
          const take=Math.min(2,currentStock);
          const sellerValue=mf.stock['PRD-R04'].v,materialsBefore=acc(mf,'materials');
          const cashBefore=acc(pf,'cash');
          const receipt=worldLocalPhysicalDelivery(S,mf.id,pm.id,pf.id,plant.id,'PRD-R04',take,31);
          const accepted=receipt.quantity===take&&take>0&&receipt.siteId===pm.siteId
            &&acc(pf,'cash')===cashBefore-take*31
            &&acc(mf,'materials')<materialsBefore&&mf.stock['PRD-R04'].v<sellerValue
            &&pf.stock['PRD-R04']?.q===take;
          let rejectsPhantom=false,rejectsService=false,rejectsWrongSite=false;
          try{worldLocalPhysicalDelivery(S,mf.id,pm.id,pf.id,plant.id,'PRD-R04',100,31)}catch{rejectsPhantom=true}
          try{worldLocalPhysicalDelivery(S,mf.id,pm.id,pf.id,plant.id,'PRD-S01',1,31)}catch{rejectsService=true}
          const buyerPlant=pf.plants.find(p=>p.id===plant.id);
          const location=buyerPlant.siteId;
          buyerPlant.siteId='NO-SITE';
          try{worldLocalPhysicalDelivery(S,mf.id,pm.id,pf.id,plant.id,'PRD-R04',1,31)}catch{rejectsWrongSite=true}
          buyerPlant.siteId=location;syncWorldIdentities(S);
          const noExtraReserves=Object.keys(S.worldExpansion.resourceDeposits).length===1;
          const coalPlanSaved=parsePayload(savePayload(S)).worldExpansion.resourceDeposits[id].remaining
            ===S.worldExpansion.resourceDeposits[id].remaining;
          // Generator must be a physical, paid piece of company equipment.
          S.year=1925;S.month=4;applyWorldHistory(S);syncWorldIdentities(S);
          if(!pf.research.tree.done.includes('energy-1'))pf.research.tree.done.push('energy-1');
          if(!pf.research.tree.done.includes('materials-1'))pf.research.tree.done.push('materials-1');
          if(!pf.research.tree.done.includes('production-1'))pf.research.tree.done.push('production-1');
          const generatingBefore=worldPowerAvailable(S,buyerPlant.id)===0;
          let rejectsNoGenerator=false;try{worldGeneratePower(S,pf.id,buyerPlant.id,1)}catch{rejectsNoGenerator=true}
          post(pf,{materials:900},{cash:900},'TEST_FIXTURE 実機入庫','operating',S);
          pf.stock['PRD-E04']={q:1,v:900};
          const ppe=acc(pf,'ppe');
          const generator=worldInstallGenerator(S,pf.id,buyerPlant.id);
          const installed=generator.assetValue===900&&acc(pf,'ppe')===ppe+900
            &&pf.stock['PRD-E04'].q===0;
          let rejectsEmptyFuel=false;try{worldGeneratePower(S,pf.id,buyerPlant.id,3)}catch{rejectsEmptyFuel=true}
          const power=worldGeneratePower(S,pf.id,buyerPlant.id,1);
          const fuelConserved=power.fuelQty===1&&power.deliveredKwh===9
             &&power.lossKwh===1&&pf.stock['PRD-R04'].q===take-1;
          let rejectsRepeat=false;
          try{worldGeneratePower(S,pf.id,buyerPlant.id,1)}catch{rejectsRepeat=true}
          // Real kWh enables an otherwise locked powered material recipe.
          post(pf,{materials:210},{cash:210},'TEST_FIXTURE bauxite inventory','operating',S);
          pf.stock['PRD-R03']={q:6,v:210};
          worldPlanSave(pf,buyerPlant.id===plant.id?buyerPlant:pf.plants[0],'PRD-M07',2);
          const events=[];
          produceWorldSupplemental(S,events);
          const consumedKwh=S.worldExpansion.powerAllocations[buyerPlant.id].usedKwh;
          const powered=pf.stock['PRD-M07']?.q===1&&consumedKwh===5
            &&worldPowerAvailable(S,buyerPlant.id)===4;
          const snapshot=parsePayload(savePayload(S));
          const saved=snapshot.worldExpansion.energyReceipts.length===1
           &&snapshot.worldExpansion.powerGenerators[buyerPlant.id].assetValue===900
           &&snapshot.worldExpansion.physicalDeliveries.length===1
           &&snapshot.worldExpansion.powerAllocations[buyerPlant.id].usedKwh===5;
          const bad=structuredClone(S);
          bad.worldExpansion.energyReceipts[0].grossKwh+=10;
          let rejectTamper=false;try{validateWorldExpansion(bad)}catch{rejectTamper=true}
          const clean=check(S).length===0&&consolidate(S).errors.length===0;
          const count=WORLD_SUPPLEMENTAL_RECIPES.length===104
            &&WORLD_PRODUCTS.filter(p=>worldProductImplementation(p.id).implementation==='DATA_CANDIDATE').length===4;
          const noServiceRevenue=WORLD_PRODUCTS.filter(p=>p.category==='service')
             .every(p=>!worldServiceTerms(p.id).physicalInventory&&!pf.stock[p.id]);
          return {monthlyMined,accepted,rejectsPhantom,rejectsService,rejectsWrongSite,
            noExtraReserves,coalPlanSaved,generatingBefore,rejectsNoGenerator,
            installed,rejectsEmptyFuel,fuelConserved,rejectsRepeat,powered,saved,
            rejectTamper,clean,count,noServiceRevenue};
        }""")
        assert all(result.values()),result
        assert not errors,errors
        browser.close()
    print("PASS Phase 2-D: auto finite mining, local physical receipt, generator asset, fuel, loss, kWh, save")
if __name__=="__main__":
    main()
