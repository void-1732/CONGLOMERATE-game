"""v0.12 30+ company, 120-month BS/CF and JSON persistence regression."""
from pathlib import Path
from playwright.sync_api import sync_playwright
HTML=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8')
INIT="""()=>{window.__db={meta:{},snapshots:{}};idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};IDB={};SAVE_INDEX.backend='IndexedDB';S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});VIEW_FIRM=S.playerId;PAGE='people';render();}"""

with sync_playwright() as p:
 b=p.chromium.launch(headless=True,args=['--no-sandbox']);page=b.new_page()
 page.set_content(HTML,wait_until='load');page.evaluate(INIT)
 for block in range(12):
  result=page.evaluate("""async()=>{let ok=0;const failures=[];for(let i=0;i<10;i++){const m=S.monthCommitted;await runMonth();const e=check(S),g=consolidate(S);if(m+1!==S.monthCommitted||e.length||g.errors.length||!g.cf.reconciled){failures.push({month:i,checks:e,conso:g.errors});break}ok++}return {ok,failures,month:S.monthCommitted,companies:S.firms.length}}""")
  assert result['ok']==10 and not result['failures'],result
  if block in (5,8,10):
   check=page.evaluate("""()=>{const g=consolidate(S),r=parsePayload(savePayload(S)),h=consolidate(r);S=r;return {same:JSON.stringify(g.bs)===JSON.stringify(h.bs)&&JSON.stringify(g.cf)===JSON.stringify(h.cf),issues:check(S),cf:h.cf.reconciled}}""")
   assert check['same'] and not check['issues'] and check['cf'],check
 final=page.evaluate("()=>({firms:S.firms.length,errors:check(S),group:consolidate(S).errors,cf:consolidate(S).cf.reconciled})")
 assert not final['errors'] and not final['group'] and final['cf'],final
 print('PASS v0.12: 120 months',final)
 b.close()
