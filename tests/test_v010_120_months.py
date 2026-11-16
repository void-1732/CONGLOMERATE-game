from pathlib import Path
from playwright.sync_api import sync_playwright
import os,shutil

html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),args=["--no-sandbox"])
 page=b.new_page()
 errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
 page.set_content(html,wait_until="load")
 page.evaluate("""()=>{window.__db={meta:{},snapshots:{}};idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};IDB={};SAVE_INDEX.backend='IndexedDB';S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});VIEW_FIRM=S.playerId;PAGE='dashboard';render();}""")
 count=0
 for block in range(12):
  result=page.evaluate("""async()=>{let progress=0;const issues=[];for(let i=0;i<10;i++){const old=S.monthCommitted;await runMonth();const g=consolidate(S),checks=check(S);if(S.monthCommitted!==old+1||checks.length||g.errors.length||!g.cf.reconciled){issues.push({i,checks,group:g.errors,cf:g.cf.unreconciled});break;}progress++;}return {progress,issues,companies:S.firms.length}}""")
  assert result["progress"]==10 and not result["issues"],result
  count+=result["progress"]
 check=page.evaluate("""()=>{const parsed=parsePayload(savePayload(S)),a=consolidate(S),b=consolidate(parsed);return {checks:check(parsed),bs:JSON.stringify(a.bs)===JSON.stringify(b.bs),cf:JSON.stringify(a.cf)===JSON.stringify(b.cf),sites:parsed.firms.every(f=>f.plants.every(p=>!!findSite(p.siteId)))}}""")
 assert count==120 and not errors and not check["checks"] and check["bs"] and check["cf"] and check["sites"]
 print("PASS 120 months; accounting, consolidated CF and JSON roundtrip")
 b.close()
