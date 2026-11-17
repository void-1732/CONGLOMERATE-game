"""CONGLOMERATE v0.27.1: factory production and treasury-share smoke test.
Run: python tests/test_v0271_smoke.py  (requires playwright and chromium)
"""
import os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
    page=browser.new_page(viewport={"width":1440,"height":900})
    page.set_content(html)
    page.evaluate("S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'Smoke'});VIEW_FIRM=S.playerId;saveAuto=async()=>true")
    assert page.evaluate("TECH_NODES.length")==800
    backup=page.evaluate("savePayload(S)")
    page.evaluate("window.BACKUP=savePayload(S)")
    for mode in ["legacy","detailed"]:
        result=page.evaluate("""mode=>{
          S=parsePayload(window.BACKUP);
          const f=current(),p=f.plants[0];
          f.plants=[{...p,id:'A',capacity:54,condition:100,construction:null,paused:false,renovation:null,kind:'integrated'},
                    {...p,id:'B',capacity:54,condition:100,construction:null,paused:false,renovation:null,kind:'integrated'}];
          ensureFactoryV21(f);f.factoryOps.mode=mode;f.factoryOps.staffAssignments={A:0,B:70};f.staff.production=70;
          for(const m of f.models)if(m.status==='active')f.plans[m.id]=25;
          syncPlant(f);
          const ret=(mode==='detailed'?planFactoryOutputDetailed:planFactoryOutput)(f,factoryCapacity(f).possible,S);
          return {made:ret.produced,plants:f.plants.map(x=>x.lastProduced)};
        }""",mode)
        assert result["made"]>=0 and result["plants"][0]==0, (mode,result)
    page.evaluate("S=parsePayload(window.BACKUP)")
    quote=page.evaluate("shareBuybackQuoteV0271(S,current(),5,1.25)")
    if quote["consent"] and quote["affordable"]:
        actual=page.evaluate("""()=>{
          const f=current(),before=acc(f,'cash');
          executeShareBuybackV0271(S,f.id,5,1.25);
          const paid=before-acc(f,'cash');
          return {paid,shares:f.treasuryShares,errors:check(S),group:consolidate(S).errors};
        }""")
        assert actual["paid"]==quote["costLocal"] and actual["shares"]==quote["qty"] and not actual["errors"] and not actual["group"]
        page.evaluate("cancelTreasurySharesV0271(S,current().id)")
        assert page.evaluate("current().treasuryShares")==0
    page.evaluate("S=parsePayload(window.BACKUP)")
    for month in range(60):
        page.evaluate("async()=>await runMonth()")
        verdict=page.evaluate("({errors:check(S),group:consolidate(S).errors,cf:consolidate(S).cf.reconciled})")
        assert not verdict["errors"] and not verdict["group"] and verdict["cf"],(month,verdict)
    browser.close()
print("PASS: 800 tech, staffed factory allocations, treasury shares and 60 monthly accounting checks")
