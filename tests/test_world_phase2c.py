"""Phase 2-C: mined-material dependencies, plant kind, power conservation, saved state."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
            args=["--no-sandbox"],
        )
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result = page.evaluate("""() => {
          saveAuto=async()=>true;
          S=newWorldGame({country:'JP',name:'Phase2-C 制約検証'});
          const f=company(S.playerId,S);
          const p=f.plants.find(x=>x.kind==='integrated'&&!x.construction);
          if(!p)return {error:'integrated plant missing'};
          f.auto=false;f.delegate.mode='manual';
          for(const model of f.models)f.plans[model.id]=0;
          p.componentLines=[];p.wirePlan=0;p.lastProduced=0;
          const newlyAdded=['PRD-M01','PRD-M02','PRD-M09','PRD-M10','PRD-M12',
            'PRD-M13','PRD-M14','PRD-C17','PRD-C18','PRD-M29','PRD-M30'];
          const count=WORLD_SUPPLEMENTAL_RECIPES.length===80
            &&newlyAdded.every(id=>WORLD_SUPPLEMENTAL_BY_ID.has(id))
            &&WORLD_PRODUCTS.filter(x=>worldProductImplementation(x.id).implementation==='DATA_CANDIDATE').length===69;
          const graph=validateWorldRecipeGraph();
          const locked=!worldRecipeUnlocked(f,WORLD_SUPPLEMENTAL_BY_ID.get('PRD-M12'),1900);
          if(!f.research.tree.done.includes('materials-1'))f.research.tree.done.push('materials-1');
          if(!f.research.tree.done.includes('production-1'))f.research.tree.done.push('production-1');
          const stockBefore=structuredClone(f.stock['PRD-R19']||{q:0,v:0});
          post(f,{materials:400},{cash:400},'試験用の木材在庫','operating',S);
          const timber=f.stock['PRD-R19']??={q:0,v:0};
          timber.q+=10;timber.v+=400;
          worldPlanSave(f,p,'PRD-M12',3);
          const events=[];
          produceWorldSupplemental(S,events);
          const timberProduced=f.stock['PRD-M12']?.q===3&&
            f.stock['PRD-R19']?.q===stockBefore.q+4&&
            events.length===1;
          const noDuplicate=(() => {produceWorldSupplemental(S,events);return events.length===1})();
          S.year=1930;S.month=3;applyWorldHistory(S);syncWorldIdentities(S);
          post(f,{materials:450},{cash:450},'電力製品の資材検証','operating',S);
          for(const [id,q,v] of [['PRD-M09',5,150],['PRD-R16',5,150],['PRD-R18',5,150]]){
            const stock=f.stock[id]??={q:0,v:0};stock.q+=q;stock.v+=v;
          }
          worldPlanSave(f,p,'PRD-M10',5);
          const future=WORLD_SUPPLEMENTAL_BY_ID.get('PRD-M29');
          const futureLocked=!worldRecipeUnlocked(f,future,1930);
          const nonAssembly=(() => {
            worldPlanSave(f,p,'PRD-C17',1);
            produceWorldSupplemental(S,events);
            return !(f.stock['PRD-C17']?.q>0);
          })();
          worldPlanSave(f,p,'PRD-M10',5);
          const beforeElectric=events.length;
          produceWorldSupplemental(S,events);
          const powerFailClosed=events.length===beforeElectric&&!(f.stock['PRD-M10']?.q>0);
          S.worldExpansion.powerAllocations[p.id]={
            plantId:p.id,source:'TEST_FIXTURE',receiptId:'TEST-PHASE2C-POWER',
            month:ym(S.year,S.month),capacityKwh:6,usedKwh:0
          };
          validateWorldPowerAllocations(S);
          produceWorldSupplemental(S,events);
          const budget=S.worldExpansion.powerAllocations[p.id];
          const producedWithPower=f.stock['PRD-M10']?.q===2&&budget.usedKwh===6&&events.length===beforeElectric+1;
          produceWorldSupplemental(S,events);
          const electricityNotDoubleSpent=budget.usedKwh===6&&f.stock['PRD-M10']?.q===2;
          const saved=parsePayload(savePayload(S));
          const persistence=saved.worldExpansion.powerAllocations[p.id]?.usedKwh===6
            &&company(f.id,saved).stock['PRD-M10']?.q===2;
          let rejectsOveruse=false, rejectsRecipe=false;
          const invalid=structuredClone(S);
          invalid.worldExpansion.powerAllocations[p.id].usedKwh=7;
          try{validateWorldPowerAllocations(invalid)}catch{rejectsOveruse=true}
          const r=WORLD_SUPPLEMENTAL_BY_ID.get('PRD-M10');
          const priorPower=r.powerKwh;
          try{r.powerKwh=-1;try{validateWorldRecipeGraph()}catch{rejectsRecipe=true}}
          finally{r.powerKwh=priorPower}
          S.month=4;p.worldProductionMonth=null;
          const freshMonthNoPower=worldPowerAvailable(S,p.id)===0;
          const serviceUnchanged=WORLD_PRODUCTS.filter(x=>x.category==='service')
             .every(x=>worldServiceTerms(x.id).revenueState==='NOT_IMPLEMENTED'&&!f.stock[x.id]);
          const noPhantomDeposit=Object.keys(S.worldExpansion.resourceDeposits).length===0;
          const clean=check(S).length===0&&consolidate(S).errors.length===0;
          return {count,graph,locked,timberProduced,noDuplicate,nonAssembly,
            futureLocked,powerFailClosed,producedWithPower,electricityNotDoubleSpent,
            persistence,rejectsOveruse,rejectsRecipe,freshMonthNoPower,
            serviceUnchanged,noPhantomDeposit,clean};
        }""")
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS Phase 2-C: 11 provisional recipes, facility/research/year locks, finite fixture power, conservation, save")


if __name__ == "__main__":
    main()
