"""Actual browser use of the accordion:
専門部品の製造・自動配送・輸送中在庫
Mode switching -> per-plant quantities -> all routes saved -> monthly utilization,
on-site stock and in-transit inventory. Also test the one-click bulk setup.
"""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
TYPES=("engine","body","components")

def seed(page):
    page.evaluate("""()=>{
      S=newGame({era:1900,country:'JP',difficulty:'easy',history:'historical',
       name:'一括製造方式の操作テスト'});
      VIEW_FIRM=S.playerId;const f=current(),base=f.plants[0];
      for(const m of f.models)f.plans[m.id]=0;
      f.staff.production=160;
      for(const typ of ['steel','rubber']){
        post(f,{materials:14000},{cash:14000},'補充材料仕入','operating',S);
        f.stock[typ].q+=800;f.stock[typ].v+=14000;
      }
      f.plants.push(...['engine','body','components'].map(k=>({
        ...structuredClone(base),id:'BULK-'+k,name:'一括-'+k,kind:k,
        capacity:60,condition:100,paused:false,construction:null,renovation:null,
        lastProduced:0,lastUtilization:0,componentLines:[] })));
      ensureFactoryV21(f);ensureV11Firm(f);
      f.factoryOps.mode='legacy';f.factoryOps.modeExplicit=true;
      for(const k of ['engine','body','components']){
        f.interplant.partPlans['BULK-'+k]=0;
        f.factoryOps.plans['BULK-'+k]=0;
        f.factoryOps.staffAssignments['BULK-'+k]=0;
      }
      PAGE='facilityProduction';render();
    }""")
    assert not page.evaluate("check(S)")

def open_accordion(page):
    page.get_by_text("専門部品の製造・自動配送・輸送中在庫",exact=True).click()

def month(page):
    old=page.evaluate("S.monthCommitted")
    page.evaluate("async()=>await runMonth()")
    assert page.evaluate("S.monthCommitted")==old+1,page.evaluate("LAST_MONTH_DIAGNOSTIC?.message")
    x=page.evaluate("""()=>{
      const f=current(),c=consolidate(S);
      return {error:check(S),errors:c.errors,cf:c.cf.reconciled,
        factory:Object.fromEntries(['engine','body','components'].map(k=>{
          const p=f.plants.find(p=>p.id==='BULK-'+k);
          return [k,{produced:p.lastProduced,utilization:p.lastUtilization,
             assigned:factoryLaborPlanV026(f).byId[p.id]?.assigned,
             onHand:moduleAtV21(f,p.id)[v21ModuleType(p)],
             outbound:f.factoryOps.shipments.filter(x=>x.from===p.id).reduce((n,x)=>n+x.qty,0)}];
        })),
        inTransit:f.factoryOps.shipments.reduce((n,x)=>n+x.qty,0),
        onHandTotal:Object.fromEntries(V21_MODULE_TYPES.map(t=>[t,f.stock[t].q]))
      };}""")
    assert not x["error"] and not x["errors"] and x["cf"],x
    return x

with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
    page=browser.new_page(viewport={"width":1440,"height":900})
    errs=[]
    page.on("pageerror",lambda e:errs.append(str(e)))
    page.on("dialog",lambda dlg:dlg.accept())
    page.set_content(HTML)
    page.evaluate("saveAuto=async()=>true")
    seed(page)
    before=month(page)
    assert all(x["utilization"]==0 for x in before["factory"].values()),before
    # Month-close navigation sends the user to Monthly Report. Return to Factory.
    page.evaluate("PAGE='facilityProduction';render()")
    open_accordion(page)
    assert page.locator("#factoryV21Mode").input_value()=="legacy"
    page.locator("#factoryV21Mode").select_option("detailed")
    page.locator('[data-action="factoryModeV21"]').click()
    open_accordion(page)
    assembly=page.evaluate("current().plants.find(p=>p.kind==='integrated').id")
    for k in TYPES:
        page.locator("#v21Plan_BULK-"+k).fill("25")
        page.locator("#v21Dest_BULK-"+k).select_option(assembly)
        page.locator("#v21Target_BULK-"+k).fill("35")
        page.locator("#v21Limit_BULK-"+k).fill("9")
        page.locator("#v21Auto_BULK-"+k).check()
    page.locator('[data-action="v21RouteSave"]').click()
    state=page.evaluate("""()=>{
      const f=current();
      return {mode:f.factoryOps.mode,
        labs:Object.fromEntries(['engine','body','components'].map(k=>{
         const id='BULK-'+k;
         return [k,{plan:f.factoryOps.plans[id],
           assigned:factoryLaborPlanV026(f).byId[id].assigned,
           route:f.factoryOps.routes[id]}]
        }))};}""")
    assert state["mode"]=="detailed" and all(a["plan"]==25 and a["assigned"]>0 and a["route"]["enabled"] and a["route"]["to"]==assembly for a in state["labs"].values()),state

    run=month(page)
    assert all(q["utilization"]>0 and q["produced"]>0 for q in run["factory"].values()),run
    assert all(q["onHand"]>0 for q in run["factory"].values()),run
    # Automatic shipping may be rejected if delegated automation expressly
    # disabled it, but manual route settings and factory output must work.
    assert run["inTransit"]>0,run
    month2=month(page)
    assert all(q["utilization"]>0 and q["produced"]>0 for q in month2["factory"].values()),month2
    assert page.evaluate("consolidate(S).cf.reconciled")

    # Restart with a zero-plan former save and exercise the distinct "one click
    # bulk setup" button. It must not preserve zero-fixed staffing.
    seed(page)
    page.locator('[data-action="activateSupportV026"]').click()
    bulk=page.evaluate("""()=>{
      const f=current();
      return {mode:f.factoryOps.mode,plans:['engine','body','components'].map(k=>f.factoryOps.plans['BULK-'+k]),
        staff:['engine','body','components'].map(k=>factoryLaborPlanV026(f).byId['BULK-'+k].assigned),
        routes:['engine','body','components'].map(k=>f.factoryOps.routes['BULK-'+k])};}""")
    assert bulk["mode"]=="detailed" and all(n>0 for n in bulk["plans"]) and all(n>0 for n in bulk["staff"]),bulk
    assert all(r["enabled"] for r in bulk["routes"]),bulk
    one=month(page)
    assert all(q["utilization"]>0 and q["produced"]>0 for q in one["factory"].values()),one
    assert not errs,errs
    browser.close()
print("PASS: UI accordion mode-save/route-save, 3 active factories, shipping and stock, one-click setup, monthly accounting")
