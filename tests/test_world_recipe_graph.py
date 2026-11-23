"""Phase 2: multi-stage manufacturing, era/research gates and accounting invariants."""
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
          S=newWorldGame({country:'JP',name:'レシピ連鎖検証'});
          const firm=company(S.playerId,S);
          const plant=firm.plants.find(canPlanWireProduction);
          if(!plant)return {error:'factory missing'};
          firm.auto=false;firm.delegate.mode='manual';
          for(const model of firm.models)firm.plans[model.id]=0;
          plant.componentLines=[];plant.wirePlan=0;plant.lastProduced=0;
          for(const tech of ['materials-1','production-1','energy-1','electronics-1']){
            if(!firm.research.tree.done.includes(tech))firm.research.tree.done.push(tech);
          }
          const n=WORLD_SUPPLEMENTAL_RECIPES.length;
          const productCatalog=validateWorldProductCatalog();
          const implementations=WORLD_PRODUCTS.map(p=>worldProductImplementation(p.id));
          const catalogStatus=implementations.filter(x=>x.implementation==='RECIPE_PROTOTYPE').length===71
            &&implementations.filter(x=>x.implementation==='WIRE_PILOT').length===1
            &&implementations.filter(x=>x.implementation==='DATA_CANDIDATE').length===78;
          const services=implementations.filter(x=>!x.physical);
          const serviceMetadata=services.length===15&&services.every(x=>x.unitClass==='service');
          const volumeUnits=worldProductUnitClass('PRD-M15')==='volume';
          let rejectsServiceStock=false;
          const illegalState=structuredClone(S);
          illegalState.firms[0].stock['PRD-S01']={q:1,v:0};
          try{validateWorldSupplemental(illegalState)}
          catch{rejectsServiceStock=true}
          const serviceSafe=WORLD_SUPPLEMENTAL_RECIPES.every(
            r=>WORLD_PRODUCT_BY_ID.get(r.id)?.category!=='service'
          );
          const treeGood=validateWorldRecipeGraph();
          let cycleRejected=false,invalidUnitRejected=false;
          const original=WORLD_SUPPLEMENTAL_BY_ID.get('PRD-M03').inputs;
          try{
            WORLD_SUPPLEMENTAL_BY_ID.get('PRD-M03').inputs=[['PRD-E08',1]];
            try{validateWorldRecipeGraph()}catch{cycleRejected=true}
          }finally{WORLD_SUPPLEMENTAL_BY_ID.get('PRD-M03').inputs=original}
          const recipe=WORLD_SUPPLEMENTAL_BY_ID.get('PRD-C22');
          const radioIn1900=!worldRecipeUnlocked(firm,recipe,1900);
          const radioLater=worldRecipeUnlocked(firm,recipe,Math.max(1920,TECH_BY_ID[recipe.tech].year));
          post(firm,{materials:2000},{cash:2000},'原料鉄鋼投入の検証','operating',S);
          firm.stock.steel.q+=100;firm.stock.steel.v+=2000;
          worldPlanSave(firm,plant,'PRD-M03',6);
          const events=[];
          produceWorldSupplemental(S,events);
          const first=firm.stock['PRD-M03'];
          const firstPass=first?.q===6&&events.length===1;
          // Next month: build a downstream capital good from the steel sheets.
          S.month=2;plant.lastProduced=0;
          post(firm,{materials:300},{cash:300},'試験用軸受ロット調達','operating',S);
          firm.stock['PRD-M32']={q:6,v:300};
          worldPlanSave(firm,plant,'PRD-E08',2);
          produceWorldSupplemental(S,events);
          const second=firm.stock['PRD-E08'];
          const secondPass=second?.q===2&&firm.stock['PRD-M03']?.q===0
            &&firm.stock['PRD-M32']?.q===2&&events.length===2;
          const before=events.length;
          produceWorldSupplemental(S,events);
          const noDuplicate=events.length===before&&firm.stock['PRD-E08']?.q===2;
          const snapshot=parsePayload(savePayload(S));
          const reloaded=company(firm.id,snapshot);
          const saved=reloaded.stock['PRD-E08']?.q===2
            &&reloaded.plants.find(x=>x.id===plant.id)?.worldPlan?.productId==='PRD-E08';
          const goodLedger=check(S).length===0&&consolidate(S).errors.length===0;
          const screen=worldSupplementalPanel(firm,true);
          const uiUpdated=screen.includes('追加'+n+'レシピ')&&screen.includes('商品生産計画を保存');
          const allCandidateProducts=WORLD_PRODUCTS.length===150 &&
            WORLD_PRODUCTS.filter(x=>x.category==='service').length===15;
          return {
            n,productCatalog,catalogStatus,serviceMetadata,volumeUnits,rejectsServiceStock,
            serviceSafe,treeGood,cycleRejected,radioIn1900,radioLater,
            firstPass,secondPass,noDuplicate,saved,goodLedger,uiUpdated,allCandidateProducts
          };
        }""")
        assert result.pop("n") == 71, result
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS Phase 2: 71 recipes, intermediate-to-equipment production, era, cycle, inventory, ledger, and save")


if __name__ == "__main__":
    main()
