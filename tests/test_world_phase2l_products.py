"""Every catalogued resource can be received and every recipe can produce a physical unit."""

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
        report = page.evaluate("""() => {
          const base=newWorldGame({country:'JP',name:'Phase 2 product audit'});
          const errors=[];
          function put(s,f,id,q,v){
            post(f,{materials:v},{cash:v},'検証用の現物仕入','operating',s);
            const item=f.stock[id]??={q:0,v:0};
            item.q+=q;item.v+=v;
          }
          for(const recipe of WORLD_SUPPLEMENTAL_RECIPES){
            const s=structuredClone(base),f=company(s.playerId,s),plant=f.plants[0];
            try{
              s.year=Math.max(recipe.year,TECH_BY_ID[recipe.tech].year);
              if(recipe.equipment){
                const build=WORLD_SUPPLEMENTAL_BY_ID.get(recipe.equipment);
                s.year=Math.max(s.year,build.year,TECH_BY_ID[build.tech].year);
              }
              s.month=1;
              plant.kind=recipe.plantKind??'integrated';
              plant.lastProduced=0;plant.componentLines=[];plant.wirePlan=0;f.staff.production=300;
              syncPlant(f);
              if(worldRecipeUnlocked(f,recipe,s.year)&&!f.research.tree.done.includes(recipe.tech))
                throw Error('research locked product is available');
              if(!f.research.tree.done.includes(recipe.tech))f.research.tree.done.push(recipe.tech);
              if(!worldRecipeUnlocked(f,recipe,s.year)||worldRecipeUnlocked(f,recipe,recipe.year-1))
                throw Error('release year or research failed');
              for(const [id,qty] of recipe.inputs)put(s,f,id,qty,100*qty);
              worldPlanSave(f,plant,recipe.id,1);
              const noProduction=()=>produceWorldSupplemental(s,[]);
              if(recipe.powerKwh){
                noProduction();
                if(f.stock[recipe.id]?.q)throw Error('production without power');
                s.worldExpansion.powerAllocations[plant.id]={plantId:plant.id,source:'TEST_FIXTURE',
                  receiptId:'TEST-2L',month:ym(s.year,s.month),capacityKwh:recipe.powerKwh,usedKwh:0};
              }
              if(recipe.equipment){
                noProduction();
                if(f.stock[recipe.id]?.q)throw Error('production without installed equipment');
                const tool=WORLD_SUPPLEMENTAL_BY_ID.get(recipe.equipment);
                if(!f.research.tree.done.includes(tool.tech))f.research.tree.done.push(tool.tech);
                put(s,f,tool.id,1,900);
                const ppe=acc(f,'ppe');
                const a=worldInstallManufacturingTool(s,f.id,plant.id,tool.id);
                if(a.assetValue!==900||acc(f,'ppe')!==ppe+900||f.stock[tool.id].q!==0)
                  throw Error('equipment basis did not move');
                worldValidateManufacturingTools(s);
              }
              const before=recipe.inputs.map(([id,qty])=>[id,qty,f.stock[id].q,f.stock[id].v]);
              const expectedCost=recipe.inputs.reduce((sum,[id,qty])=>sum+Math.round(f.stock[id].v*qty/f.stock[id].q),0);
              const conversion=localFromBase(recipe.cost*eraCostFactor(s.year),f.country);
              const cash=acc(f,'cash');
              produceWorldSupplemental(s,[]);
              const result=f.stock[recipe.id];
              if(result?.q!==1||result.v!==expectedCost+conversion||acc(f,'cash')!==cash-conversion)
                throw Error('quantity, cash or cost mismatch');
              if(before.some(([id,qty,q])=>f.stock[id].q!==q-qty))throw Error('inputs not consumed once');
              if(recipe.powerKwh&&s.worldExpansion.powerAllocations[plant.id].usedKwh!==recipe.powerKwh)
                throw Error('power not consumed exactly');
              produceWorldSupplemental(s,[]);
              if(result.q!==1||check(s).length)throw Error('duplicate production or book imbalance');
            }catch(error){errors.push(recipe.id+' '+error.message);}
          }
          const resources=WORLD_PRODUCTS.filter(p=>p.category==='resource');
          for(const product of resources){
            try{
              const pair=Object.entries(WORLD_REGIONAL_SUPPLY).find(([,offer])=>offer.productId===product.id);
              if(!pair)throw Error('missing regional source');
              const [id,offer]=pair,site=findSite(offer.siteId);
              const s=newWorldGame({country:site.country,name:'Physical resource receipt'});
              const f=company(s.playerId,s),plant=f.plants[0];
              s.year=Math.floor(offer.opensAt/12);s.month=offer.opensAt%12+1;
              plant.siteId=site.id;
              applyWorldHistory(s);syncWorldIdentities(s);
              const cash=acc(f,'cash'),entry=worldBuyRegionalSupply(s,f.id,plant.id,id,1);
              if(!offer.source.startsWith('https://')||f.stock[product.id]?.q!==1
               ||f.stock[product.id].v!==entry.amount||acc(f,'cash')!==cash-entry.amount)
                throw Error('quantity, evidence or cash mismatch');
              worldValidateRegionalSupplies(s);
              if(check(s).length)throw Error('books unbalanced');
            }catch(error){errors.push(product.id+' '+error.message);}
          }
          return {recipes:WORLD_SUPPLEMENTAL_RECIPES.length,resources:resources.length,errors,
            units:['PRD-M18','PRD-M26','PRD-M44','PRD-R01'].map(id=>worldProductUnitClass(id))};
        }""")
        assert report == {
            "recipes": 104,
            "resources": 30,
            "errors": [],
            "units": ["volume", "piece", "length", "mass"],
        }, report
        assert not errors, errors
        browser.close()
    print("PASS Phase 2-L catalog: 104 production/cost/constraint cases, 30 finite resource receipts")


if __name__ == "__main__":
    main()
