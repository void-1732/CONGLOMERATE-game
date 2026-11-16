"""v0.13: 120 monthly closes, 30+ firms and consolidated BS/CF persistence."""
from pathlib import Path
from playwright.sync_api import sync_playwright
html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=["--no-sandbox"])
    page=b.new_page()
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.set_content(html,wait_until="load")
    page.evaluate("""()=>{window.__db={meta:{},snapshots:{}};idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};IDB={};SAVE_INDEX.backend='IndexedDB';S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});VIEW_FIRM=S.playerId;PAGE='dashboard';render()}""")
    for block in range(12):
        r=page.evaluate("""async()=>{let completed=0;const failures=[];for(let i=0;i<10;i++){const old=S.monthCommitted;await runMonth();const checks=check(S),g=consolidate(S);if(S.monthCommitted!==old+1||checks.length||g.errors.length||!g.cf.reconciled){failures.push({i,checks,conso:g.errors});break;}completed++;}return {completed,failures,companies:S.firms.length}}""")
        assert r["completed"]==10 and not r["failures"],r
        if block in (5,8,10):
            saved=page.evaluate("""()=>{const first=consolidate(S),loaded=parsePayload(savePayload(S)),last=consolidate(loaded);S=loaded;return {books:check(S),same:JSON.stringify(first.bs)===JSON.stringify(last.bs)&&JSON.stringify(first.cf)===JSON.stringify(last.cf),cf:last.cf.reconciled}}""")
            assert not saved["books"] and saved["same"] and saved["cf"],saved
    assert not errors,errors
    print("PASS v0.13: 120 months, consolidated BS/CF, JSON roundtrip")
    b.close()
