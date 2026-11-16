from pathlib import Path
from playwright.sync_api import sync_playwright
import os

html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, executable_path=os.getenv("CHROMIUM_EXECUTABLE") or None)
    page=browser.new_page(viewport={"width":1440,"height":900})
    errors=[]
    page.on("pageerror",lambda e: errors.append(str(e)))
    page.set_content(html,wait_until="load")
    page.evaluate("""()=>{window.__db={meta:{},snapshots:{}};
      idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);
      idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};
      IDB={};SAVE_INDEX.backend='IndexedDB';
      S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});
      VIEW_FIRM=S.playerId;PAGE='group';render();}""")

    page.evaluate("async()=>{await runMonth();await runMonth();PAGE='group';render()}")
    target=page.evaluate("()=>S.firms.find(f=>!f.player&&f.country==='JP').id")
    target_cash=page.evaluate(f"""()=>acc(company("{target}"),'cash')""")
    page.select_option("#negTarget",target)
    page.fill("#negPercent","35");page.fill("#negPremium","105")
    page.click("[data-action=buyStake]")
    minority=page.evaluate(f"""()=>({{controlled:controller(S,"{target}"),checks:check(S),ownership:company("{target}").owners.find(o=>o.id===S.playerId)?.econ,targetCash:acc(company("{target}"),'cash')}})""")
    assert not minority["controlled"] and not minority["checks"]
    assert minority["ownership"]==.35 and minority["targetCash"]==target_cash
    page.evaluate("async()=>await runMonth()")
    page.evaluate("()=>{PAGE='group';render()}")
    page.select_option("#negTarget",target)
    page.fill("#negPercent","20");page.fill("#negPremium","105")
    page.click("[data-action=buyStake]")
    majority=page.evaluate(f"""()=>({{controlled:controller(S,"{target}"),members:consolidate(S).members.length,ownership:company("{target}").owners.find(o=>o.id===S.playerId)?.econ}})""")
    assert majority["controlled"] and majority["members"]==2 and majority["ownership"]==.55
    page.evaluate("async()=>await runMonth()")
    assert page.evaluate("()=>consolidate(S).cf.reconciled")
    page.evaluate("()=>{PAGE='group';render()}")
    page.select_option("#negTarget",target)
    page.fill("#negPercent","10");page.fill("#negPremium","120")
    page.click("[data-action=buyStake]")
    page.evaluate("async()=>await runMonth()")
    later=page.evaluate("()=>consolidate(S).cf")
    assert later["reconciled"] and later["scopeAdded"]==0
    page.evaluate("()=>{PAGE='product';render()}")
    page.fill("#renewName","第二世代ツーリング")
    page.fill("#renewPrice","10400")
    page.select_option("#renewKind","full")
    page.click("[data-action=renewModel]")
    page.evaluate("()=>{PAGE='group';render()}")
    page.select_option("#delegateMode","delegated")
    page.select_option("#delegatePriority","tech")
    page.fill("#delegateTarget","25")
    page.fill("#delegateRndCap","4500")
    page.fill("#delegateReserve","100000")
    page.click("[data-action=saveDelegate]")
    for _ in range(6):
        page.evaluate("async()=>await runMonth()")
    final=page.evaluate("""()=>{
      const f=company(S.playerId),c=consolidate(S),reloaded=parsePayload(savePayload(S));
      return {checks:check(S),conso:c.errors,cf:c.cf.reconciled,
      secondGeneration:f.models.some(m=>m.generation>1&&m.status==='active'),
      delegateReports:f.delegate.reports.length,cap:f.delegate.researchMaxBase,
      reloadedChecks:check(reloaded)};
    }""")
    assert not errors and not final["checks"] and not final["conso"]
    assert final["cf"] and final["secondGeneration"] and final["delegateReports"]>0
    assert final["cap"]==4500 and not final["reloadedChecks"]
    print("PASS v0.7 negotiation, control, CF, replacement, delegation, JSON roundtrip")
    browser.close()
