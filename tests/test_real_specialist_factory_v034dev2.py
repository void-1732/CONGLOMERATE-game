"""Browser regression: no fictitious factory injections, real user build/hire UI.
Proves that engines, bodies and electronic modules reach physical and financial
inventories, old saves migrate at unchanged book value, and an explicit legacy
choice remains respected.
"""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
BUILD="v0.34-dev.2"

def verify(p, label):
    report=p.evaluate("""()=>{const f=current(), c=consolidate(S);return {
      check:check(S), group:c.errors, cf:c.cf.reconciled,
      mode:f.factoryOps.mode, committed:S.monthCommitted,
      stock:Object.fromEntries(['moduleEngine','moduleBody','moduleElectronics'].map(t=>[t,f.stock[t]])),
      factories:f.plants.filter(p=>['engine','body','components'].includes(p.kind)).map(p=>({
        id:p.id,kind:p.kind,status:factoryStatus(p),done:p.lastProduced,util:p.lastUtilization,
        plan:f.factoryOps.plans[p.id],assigned:factoryLaborPlanV026(f).byId[p.id]?.assigned||0
      }))};}""")
    assert not report["check"] and not report["group"] and report["cf"],(label,report)
    return report

def month(p):
    old=p.evaluate("S.monthCommitted")
    p.evaluate("async()=>await runMonth()")
    assert p.evaluate("S.monthCommitted")==old+1, p.evaluate("LAST_MONTH_DIAGNOSTIC?.message")
    return verify(p,"monthly progression")

with sync_playwright() as pw:
    browser=pw.chromium.launch(
       executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
       args=["--no-sandbox"])
    page=browser.new_page(viewport={"width":1440,"height":900})
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.set_content(HTML)
    page.evaluate("saveAuto=async()=>true")
    assert BUILD in page.title()
    assert BUILD in page.locator(".prototype").inner_text()
    page.evaluate("""()=>{
        S=newGame({era:1900,country:'JP',difficulty:'easy',
          history:'historical',name:'完成した工場が稼働するかの実地回帰'});
        VIEW_FIRM=S.playerId;PAGE='people';PEOPLE_VIEW='hr';render();
    }""")
    # Hire actual manufacturing workers through the user interface.
    page.locator("#hireArea").select_option("production")
    page.locator("#hireCount").fill("80")
    page.locator('[data-action="hireStaff"]').click()
    assert page.evaluate("current().staff.production")>=120

    # Purchase real materials and use matching double-entry postings.
    page.evaluate("""()=>{
        const f=current();for(const t of ['steel','rubber']){
            const val=12000;
            post(f,{materials:val},{cash:val},'生産統合テストの原材料仕入','operating',S);
            f.stock[t].q+=1000;f.stock[t].v+=val;
        }
        for(const m of f.models) f.plans[m.id]=0;
        PAGE='factory';render();
    }""")
    verify(page,"before factory construction")
    factory_ids=[]
    for kind in ("engine","body","components"):
        # The actual production UI keeps new construction in a collapsed details panel.
        page.get_by_text("新工場を建設する", exact=True).click()
        page.locator("#factoryName").fill("実工場-"+kind)
        page.locator("#factoryScale").select_option("small")
        page.locator("#factoryKind").select_option(kind)
        page.locator('[data-action="factoryBuild"]').click()
        state=page.evaluate("""kind=>{
          const f=current(),p=f.plants.find(p=>p.name==='実工場-'+kind);
          if(!p)throw Error('The real factory builder did not create '+kind);
          return {id:p.id,mode:f.factoryOps.mode,plan:f.factoryOps.plans[p.id],
             kind:p.kind,build:p.construction?.monthsLeft,workers:f.staff.production,
             route:f.factoryOps.routes[p.id]};}""",kind)
        factory_ids.append(state["id"])
        assert state["mode"]=="detailed",state
        assert state["plan"]>0 and state["build"]==2,state
        assert not state["route"]["enabled"],state
    assert len(set(factory_ids))==3
    assert not page.evaluate("check(S)"),page.evaluate("check(S)")
    for i in range(4):
        report=month(page)
    report=verify(page,"after real construction and production")
    assert report["mode"]=="detailed",report
    assert all(q["q"]>0 and q["v"]>0 for q in report["stock"].values()),report
    assert all(p["util"]>0 and p["done"]>0 for p in report["factories"]),report
    assert all(p["assigned"]>0 for p in report["factories"]),report
    assert "部品在庫の台帳照合" in page.evaluate("""()=>{
      PAGE='factory';render();const f=current();
      return factoryDetailMarkup(f,f.plants.find(p=>p.kind==='engine'),true);
    }""")
    raw=page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)",raw)
    restored=verify(page,"save reload")
    assert restored["stock"]==report["stock"],(restored,report)
    month(page)

    # Existing post-hotfix save with a completed legacy component plant:
    # auto-recovery reclassifies physical on-site stock without any new money.
    page.evaluate("""()=>{
      S=newGame({era:1900,country:'JP',difficulty:'easy',
          history:'historical',name:'既存の共通部品セーブ移行'});
      VIEW_FIRM=S.playerId;const f=current(),p={
        ...structuredClone(f.plants[0]),id:'OLD-ENGINE',kind:'engine',name:'既設エンジン工場',
        capacity:60,condition:100,paused:false,construction:null,renovation:null
      };f.plants.push(p);ensureFactoryV21(f);
      f.factoryOps.mode='legacy';f.factoryOps.idleRecoveryV0262=1;
      f.factoryOps.plans[p.id]=0;f.interplant.partPlans[p.id]=0;
      f.factoryOps.staffAssignments[p.id]=0;
      f.interplant.siteComponents[p.id]=8;
      const value=800;post(f,{materials:value},{cash:value},'旧部品購入実績','operating',S);
      f.stock.components.q+=8;f.stock.components.v+=value;
      syncPlant(f);
    }""")
    pre=page.evaluate("""()=>{
      const f=current();
      return {count:f.stock.components.q,value:f.stock.components.v,
        allQty:f.stock.components.q+f.stock.moduleEngine.q+f.stock.moduleBody.q+f.stock.moduleElectronics.q,
        allVal:f.stock.components.v+f.stock.moduleEngine.v+f.stock.moduleBody.v+f.stock.moduleElectronics.v};
    }""")
    assert not page.evaluate("check(S)")
    save=page.evaluate("savePayload(S)")
    assert page.evaluate("data=>restore(data)",save)
    after=verify(page,"existing save migration")
    migration=page.evaluate("""()=>{
      const f=current();
      return {legacy:f.stock.components,engine:f.stock.moduleEngine,
        plan:f.factoryOps.plans['OLD-ENGINE'],
        staff:factoryLaborPlanV026(f).byId['OLD-ENGINE'].assigned,
        mode:f.factoryOps.mode,
        recovery:f.factoryOps.specialistRecoveryV036,
        remain:f.interplant.siteComponents['OLD-ENGINE']};
    }""")
    assert migration["mode"]=="detailed" and migration["recovery"]==1,migration
    assert migration["engine"]=={"q":8,"v":800} and migration["remain"]==0,migration
    assert migration["plan"]>0 and migration["staff"]>0,migration
    assert migration["legacy"]["q"]+migration["engine"]["q"]==pre["allQty"]
    assert migration["legacy"]["v"]+migration["engine"]["v"]==pre["allVal"]
    second=page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)",second)
    assert page.evaluate("current().stock.moduleEngine.q")==8
    month(page)

    # Explicitly selected legacy mode must not be overridden on reload.
    page.evaluate("""()=>{
      S=newGame({era:1900,country:'JP',difficulty:'easy',
          history:'historical',name:'明示選択の従来方式を維持'});
      VIEW_FIRM=S.playerId;
      const f=current(),p={...structuredClone(f.plants[0]),id:'LEGACY-ENGINE',
         kind:'engine',capacity:25,condition:100,construction:null,paused:false,renovation:null};
      f.plants.push(p);ensureFactoryV21(f);
      f.factoryOps.mode='legacy';f.factoryOps.modeExplicit=true;
      f.factoryOps.idleRecoveryV0262=1;
      syncPlant(f);
    }""")
    manual=page.evaluate("savePayload(S)")
    assert page.evaluate("data=>restore(data)",manual)
    assert page.evaluate("current().factoryOps.mode")=="legacy"
    assert not errors,errors
    browser.close()
print("PASS: real UI factory build + hire + production for all 3 modules; save recovery and book-value conservation")
