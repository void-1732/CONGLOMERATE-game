"""Check the 150-candidate catalog and pilot input/output cost conservation."""
from collections import Counter
from pathlib import Path
import os
import shutil

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
        page.evaluate("""() => {
          saveAuto=async()=>true;
          S=newWorldGame({country:'JP',name:'試作生産試験'});
          VIEW_FIRM=S.playerId;
          const f=current();
          f.auto=false;
          f.delegate.mode='manual';
          for(const model of f.models)f.plans[model.id]=0;
          post(f,{materials:1500},{cash:1500},'試験用銅の購入','operating',S);
          f.stock.copper.q+=15;f.stock.copper.v+=1500;
          PAGE='facilityProduction';render();
        }""")
        items = page.evaluate("WORLD_PRODUCTS")
        assert len(items) == len({item["id"] for item in items}) == 150
        assert Counter(item["category"] for item in items) == {
            "resource": 30, "material": 45, "equipment": 30, "consumer": 30, "service": 15
        }
        assert {item["status"] for item in items} == {"DATA_CANDIDATE"}
        page.locator("#wire-plan-0").fill("12")
        page.get_by_role("button", name="目標を保存").first.click()
        result = page.evaluate("""async () => {
          const recipe=WIRE_RECIPE;
          const shadow=structuredClone(S), shadowFirm=company(shadow.playerId,shadow);
          shadowFirm.plants[0].paused=true;
          produceWorldWire(shadow,[]);
          const blocked=!shadowFirm.stock[recipe.productId];
          shadowFirm.plants[0].paused=false;
          const beforeCopper=shadowFirm.stock.copper.q;
          const beforeMaterials=acc(shadowFirm,'materials');
          const beforeCash=acc(shadowFirm,'cash');
          produceWorldWire(shadow,[]);
          produceWorldWire(shadow,[]);
          const shadowOutput=shadowFirm.stock[recipe.productId];
          const isolated=shadowOutput?.q===12 && shadowFirm.stock.copper.q===beforeCopper-12 &&
            acc(shadowFirm,'materials')-beforeMaterials===beforeCash-acc(shadowFirm,'cash') &&
            shadowOutput.v>=beforeCash-acc(shadowFirm,'cash') && check(shadow).length===0;
          const month=S.monthCommitted;
          await runMonth();
          const f=current();
          const output=f.stock[recipe.productId];
          return {
             blocked,isolated,advanced:S.monthCommitted===month+1,
             produced:output?.q===12,
             lowerCostMatches:f.journals.some(j=>j.text.startsWith('銅線の加工費')&&j.amount>0),
             clean:check(S).length===0&&consolidate(S).errors.length===0,
             restored:company(S.playerId,parsePayload(savePayload(S))).stock[recipe.productId]?.q===12
          };
        }""")
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS: 150 provisional products, copper-wire planning, monthly material/conversion accounting, and save")


if __name__ == "__main__":
    main()
