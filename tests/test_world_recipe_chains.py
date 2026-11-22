"""Additional world-economy recipes: product, technology, inventory and accounting gates."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
            args=["--no-sandbox"],
        )
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content(HTML, wait_until="domcontentloaded")
        page.wait_for_function("STORAGE_READY")
        result = page.evaluate("""() => {
          saveAuto=async()=>true;
          S=newWorldGame({country:'JP',name:'追加生産検証'});
          const f=company(S.playerId,S), p=f.plants.find(x=>canPlanWireProduction(x));
          if(!p)return {error:'eligible factory missing'};
          f.delegate.mode='manual';
          f.auto=false;
          for(const model of f.models)f.plans[model.id]=0;
          p.componentLines=[];p.wirePlan=0;p.lastProduced=0;
          const g=f.research.tree.done;
          if(!g.includes('materials-1'))g.push('materials-1');
          post(f,{materials:600},{cash:600},'鉄鋼材料の検証用購入','operating',S);
          f.stock.steel.q+=30;f.stock.steel.v+=600;
          worldPlanSave(f,p,'PRD-M03',10);
          const before={q:f.stock.steel.q,v:f.stock.steel.v,cash:acc(f,'cash')};
          const expectedInputCost=Math.round(before.v*20/before.q);
          const events=[];
          produceWorldSupplemental(S,events);
          produceWorldSupplemental(S,events);
          const out=f.stock['PRD-M03'];
          const after={q:f.stock.steel.q,v:f.stock.steel.v,cash:acc(f,'cash')};
          const recipe=WORLD_SUPPLEMENTAL_BY_ID.get('PRD-M03');
          const future=WORLD_SUPPLEMENTAL_BY_ID.get('PRD-M21');
          const copied=parsePayload(savePayload(S)), copyFirm=company(f.id,copied);
          let invalidPlan=false;
          try{worldPlanSave(f,p,'INVALID-PRODUCT',10)}catch{invalidPlan=true}
          return {
            count:WORLD_SUPPLEMENTAL_RECIPES.length,
            produced:out?.q===10,
            material:before.q-after.q===20,
            materialValue:before.v-after.v===expectedInputCost,
            conversion:before.cash-after.cash>0,
            value:out?.v===expectedInputCost+before.cash-after.cash,
            once:events.length===1,
            lockedFuture:!worldRecipeUnlocked(f,future,1900),
            unlockedNow:worldRecipeUnlocked(f,recipe,1900),
            saved:copyFirm.plants.find(x=>x.id===p.id)?.worldPlan?.quantity===10,
            invalidPlan,
            valid:check(S).length===0&&consolidate(S).errors.length===0,
            validCatalog:WORLD_SUPPLEMENTAL_RECIPES.every(r=>WORLD_PRODUCT_BY_ID.has(r.id))
          };
        }""")
        assert result.pop("count") == 35, result
        assert all(result.values()), result
        integration = page.evaluate("""async () => {
          S=newWorldGame({country:'JP',name:'追加世界商品・月次統合試験'});
          const f=company(S.playerId,S);
          const p=f.plants.find(x=>canPlanWireProduction(x));
          f.delegate.mode='manual';f.auto=false;
          for(const model of f.models)f.plans[model.id]=0;
          p.componentLines=[];p.wirePlan=0;p.lastProduced=0;
          if(!f.research.tree.done.includes('materials-1'))f.research.tree.done.push('materials-1');
          post(f,{materials:2000},{cash:2000},'生産試験用の原料','operating',S);
          f.stock.steel.q+=100;f.stock.steel.v+=2000;
          worldPlanSave(f,p,'PRD-M03',8);
          VIEW_FIRM=f.id; PAGE='facilityProduction';render();
          const hasButton=!!document.querySelector('[data-world-production-save]');
          const month=S.monthCommitted;
          await runMonth();
          const now=company(f.id,S);
          const produced=now.stock['PRD-M03']?.q||0;
          const roundTrip=company(f.id,parsePayload(savePayload(S))).stock['PRD-M03']?.q||0;
          return {
            hasButton,advanced:S.monthCommitted===month+1,
            produced:produced>=8,roundTrip:roundTrip===produced,
            clean:check(S).length===0,
            diagnostics:LAST_MONTH_DIAGNOSTIC
          };
        }""")
        assert integration.pop("diagnostics") is None, integration
        assert all(integration.values()), integration
        assert not errors, errors
        browser.close()
    print("PASS: 35 researched world recipes, factory, input, cash, duplicate processing, and save")


if __name__ == "__main__":
    main()
