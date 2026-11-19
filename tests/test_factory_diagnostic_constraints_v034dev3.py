"""Factory diagnostic regression: legacy is valid, local inventory is binding,
and two model plans must never reserve the same common components twice.
Run with Playwright Chromium, using real game JS and an accounting-consistent seed.
"""
import os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
    page=browser.new_page()
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.set_content(HTML)
    page.evaluate("saveAuto=async()=>true")
    page.evaluate("""()=>{
      S=newGame({era:1900,country:'JP',difficulty:'easy',history:'historical',name:'工場診断修正テスト'});
      VIEW_FIRM=S.playerId;const f=current();
      const base=f.plants[0];
      f.staff.production=130;
      f.plants.push({...structuredClone(base),id:'LEGACY-COMPONENTS',kind:'components',
        name:'共通部品工場',capacity:50,condition:100,paused:false,
        construction:null,renovation:null,lastProduced:0,lastUtilization:0});
      ensureFactoryV21(f);ensureV11Firm(f);
      f.factoryOps.mode='legacy';f.factoryOps.modeExplicit=true;
      f.interplant.partPlans['LEGACY-COMPONENTS']=20;
      delete f.factoryOps.staffAssignments['LEGACY-COMPONENTS'];
      for(const t of ['steel','rubber']){
        post(f,{materials:5000},{cash:5000},'工場検証の実材料調達','operating',S);
        f.stock[t].q+=100;f.stock[t].v+=5000;
      }
      PAGE='factory';render();
    }""")
    check=page.evaluate("""()=>{
      const f=current(),p=f.plants.find(x=>x.id==='LEGACY-COMPONENTS');
      const o=factoryInsightV023(f,p);return {reasons:o.reasons,estimate:o.estimate,assigned:o.staff.assigned};
    }""")
    assert check["assigned"]>0,check
    assert check["estimate"]["value"]>0,check
    assert not any("共通部品方式では3種類の専門モジュールは増えません" in r["state"] for r in check["reasons"]),check
    page.evaluate("""()=>{
      const f=current();f.stock.steel.q=0;f.stock.steel.v=0;
      // Zeroing a material in this UI-only fixture is not used for book entry assertions.
    }""")
    missing=page.evaluate("""()=>{
      const f=current(),p=f.plants.find(x=>x.id==='LEGACY-COMPONENTS');
      return factoryInsightV023(f,p);
    }""")
    assert missing["estimate"]["value"]==0,missing
    assert any("不足" in r["detail"] and "鋼材" in r["detail"] for r in missing["reasons"]),missing
    # Restore a consistent stock ledger and actual monthly production.
    page.evaluate("""()=>{
      const f=current();f.stock.steel.q=100;f.stock.steel.v=5000;
    }""")
    prev=page.evaluate("S.monthCommitted")
    page.evaluate("async()=>await runMonth()")
    state=page.evaluate("""()=>{
      const f=current(),p=f.plants.find(x=>x.id==='LEGACY-COMPONENTS'),c=consolidate(S);
      return {committed:S.monthCommitted,produced:p.lastProduced,util:p.lastUtilization,
        parts:f.stock.components.q,mode:f.factoryOps.mode,
        errors:check(S),group:c.errors,cf:c.cf.reconciled};
    }""")
    assert state["committed"]==prev+1,state
    assert state["mode"]=="legacy" and state["produced"]>0 and state["util"]>0 and state["parts"]>0,state
    assert not state["errors"] and not state["group"] and state["cf"],state
    assert not errors,errors
    browser.close()
print("PASS factory diagnostics: no false legacy stop, material deficit, legacy production, month-end reconciliation")
