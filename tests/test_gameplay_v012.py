"""v0.12 UI, R&D, independent automation, 7 materials and company dealers."""
from pathlib import Path
from playwright.sync_api import sync_playwright
HTML=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8')
INIT="""()=>{window.__db={meta:{},snapshots:{}};idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};IDB={};SAVE_INDEX.backend='IndexedDB';S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});VIEW_FIRM=S.playerId;PAGE='people';render();}"""

with sync_playwright() as p:
 b=p.chromium.launch(headless=True,args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1500,'height':900});issues=[]
 page.on('pageerror',lambda e:issues.append(str(e)))
 page.set_content(HTML,wait_until='load');page.evaluate(INIT)
 assert page.locator('.tech-node').count()==120
 assert page.locator('.section-tabbar').count()==1
 page.locator('[data-people-view=hr]').click()
 assert page.locator('#hrPremium').count()==1
 page.locator('[data-people-view=research]').click()
 assert page.locator('#techBoard').count()==1
 early=page.evaluate("""()=>({allowed:allowedOption('body','sedan'),penalty:techPenalty(S,TECH_BY_ID['powertrain-11']),slots:techSlotLimit(company(S.playerId)),types:SUPPLY_TYPES.length})""")
 assert not early['allowed'] and early['penalty']>50 and early['slots']==1 and early['types']==7
 page.locator('[data-action=startTech]').click()
 page.evaluate("""()=>{const f=company(S.playerId),x=f.research.tree.active[0];x.progress=TECH_BY_ID[x.id].cost-.001}""")
 page.evaluate("async()=>await runMonth()")
 assert page.evaluate("()=>company(S.playerId).research.tree.done.includes('powertrain-1')")
 page.evaluate("()=>{PAGE='group';render()}")
 page.select_option('#delegateMode','delegated')
 page.uncheck('#delegateProductionAuto');page.check('#delegateResearchAuto')
 page.fill('#delegateRndCap','25000');page.click('[data-action=saveDelegate]')
 page.evaluate("()=>{const f=company(S.playerId);f.plans[f.models[0].id]=7;f.rnd.budgetBase=9000;}")
 page.evaluate("async()=>await runMonth()")
 assert page.evaluate("()=>company(S.playerId).plans[company(S.playerId).models[0].id]")==7
 assert page.evaluate("()=>company(S.playerId).rnd.budgetBase")!=9000
 page.evaluate("()=>{PAGE='supply';render()}")
 assert page.locator('select[id^=supplier_]').count()==7
 page.evaluate("()=>{PAGE='distribution';render()}")
 assert page.locator('select[id^=dealer_]').count()==5
 result=page.evaluate("()=>({errors:check(S),conso:consolidate(S).errors,cf:consolidate(S).cf.reconciled})")
 assert not issues and not result['errors'] and not result['conso'] and result['cf'],result
 print('PASS v0.12: 120 technologies, 7 materials, independent AI, dealer contracts and consolidated CF')
 b.close()
