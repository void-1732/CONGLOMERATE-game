"""Legacy common-component routes: real HTTP Playwright monthly production, transport and reload.
Synthetic test scenario; does not claim to contain the 1907 user's private save.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json, os, shutil
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
URL=f'http://127.0.0.1:{server.server_port}/index.html'

with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':950})
    errors=[]
    page.on('pageerror',lambda err:errors.append(str(err)))
    page.goto(URL);page.wait_for_function('STORAGE_READY')
    # An old save with no legacy routes must remain empty after migration.
    old=page.evaluate("""()=>{
       S=newGame({era:1900,country:'JP',difficulty:'easy',history:'historical',name:'共通部品ルート試験'});
       VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';
       const f=current();f.factoryOps.mode='legacy';
       delete f.interplant.autoRoutes;
       const raw=savePayload(S);
       S=null;
       const restored=parsePayload(raw);
       if(restored.year!==1900||restored.month!==1)throw Error('Old save date changed');
       if(restored.firms.find(x=>x.id===restored.playerId).interplant.autoRoutes.length)throw Error('Legacy routes enabled without user consent');
       S=restored;
       return {gameId:saveIdentityV038(S),id:S.playerId};
    }""")
    page.evaluate("""()=>{
       const f=current(),base=f.plants[0];
       base.name='京浜組立';base.capacity=80;base.focus='all';
       f.plants.push({...structuredClone(base),id:'LEG-US',name:'米国組立',siteId:'US-LAX',kind:'integrated',capacity:65,construction:null,paused:false,renovation:null,lastProduced:0});
       for(const [i,kind] of ['engine','body','components'].entries())
          f.plants.push({...structuredClone(base),id:'LEG-N'+i,name:'名古屋 '+kind,siteId:'JP-NGO',kind,capacity:90,construction:null,paused:false,renovation:null,lastProduced:0});
       syncPlant(f);ensureFactoryV21(f);ensureV11Firm(f);
       f.factoryOps.mode='legacy';
       f.staff.production=Math.max(f.staff.production,60);
       f.factoryOps.staffAssignments={
         [base.id]:16,'LEG-US':12,'LEG-N0':8,'LEG-N1':8,'LEG-N2':8
       };
       for(const p of f.plants.filter(p=>v21ModuleType(p)))f.interplant.partPlans[p.id]=18;
       const available=check(S);if(available.length)throw Error(available.join('/'));
       PAGE='factory';render();
    }""")
    # Confirm UI creates only explicitly selected routes.
    page.evaluate("PAGE='factory';render()")
    assert page.locator('[data-action="legacyRouteSaveV035"]').count()>=1
    page.locator('#legacyEnabled_LEG-N0__P-F1-legacy').check()
    page.locator('#legacyTarget_LEG-N0__P-F1-legacy').fill('45')
    page.locator('#legacyLimit_LEG-N0__P-F1-legacy').fill('18')
    page.locator('#legacyEnabled_LEG-N1__LEG-US').check()
    page.locator('#legacyTarget_LEG-N1__LEG-US').fill('45')
    page.locator('#legacyLimit_LEG-N1__LEG-US').fill('18')
    page.locator('[data-action="legacyRouteSaveV035"]').click()
    assert page.evaluate("current().interplant.autoRoutes.filter(r=>r.enabled).length")==2
    assert page.evaluate("check(S)")==[]
    records=[]
    for i in range(12):
        prev=page.evaluate('S.monthCommitted')
        page.evaluate("async()=>await runMonth()")
        data=page.evaluate("""()=>{
          const f=current(),c=consolidate(S);
          return {year:S.year,month:S.month,committed:S.monthCommitted,
           check:check(S),conso:c.errors,cf:c.cf.reconciled,mode:f.factoryOps.mode,
           shipments:structuredClone(f.interplant.shipments),
           history:f.interplant.history.slice(-60),
           plants:f.plants.map(p=>({id:p.id,produced:p.lastProduced,util:p.lastUtilization})),
           components:f.stock.components.q,assigned:structuredClone(f.interplant.siteComponents),
           transit:acc(f,'materialsTransit'),cash:acc(f,'cash')}
        }""")
        print('LEGACY_AUTO_ROUTE_MONTH',json.dumps(data,ensure_ascii=False),flush=True)
        assert data['committed']==prev+1,(i,data,page.evaluate('LAST_MONTH_DIAGNOSTIC'))
        assert not data['check'] and not data['conso'] and data['cf'],(i,data)
        assert data['mode']=='legacy'
        records.append(data)
    history=records[-1]['history']
    assert any(x['action']=='自動発送' for x in history),history
    assert any(x['action']=='受領' for x in history),history
    assert any(x['to']=='P-F1-legacy' for x in history)
    assert any(x['to']=='LEG-US' for x in history)
    # A recorded destination receipt requires a prior route shipment and costs real money.
    for row in history:
        if row['action']=='受領':assert row['qty']>0 and row['bookCost']>=0
    before=page.evaluate("""()=>{
        const f=current();return {year:S.year,month:S.month,id:S.playerId,
        mode:f.factoryOps.mode,routes:structuredClone(f.interplant.autoRoutes),
        assigned:structuredClone(f.interplant.siteComponents),stock:structuredClone(f.stock),
        history:structuredClone(f.interplant.history),ledger:structuredClone(f.ledger),
        plants:f.plants.map(p=>({id:p.id,lastProduced:p.lastProduced,lastUtilization:p.lastUtilization}))}
    }""")
    assert page.evaluate('async()=>await saveAuto()')
    page.reload();page.wait_for_function('STORAGE_READY')
    after=page.evaluate("""()=>{
        const f=current();return {year:S.year,month:S.month,id:S.playerId,
        mode:f.factoryOps.mode,routes:structuredClone(f.interplant.autoRoutes),
        assigned:structuredClone(f.interplant.siteComponents),stock:structuredClone(f.stock),
        history:structuredClone(f.interplant.history),ledger:structuredClone(f.ledger),
        plants:f.plants.map(p=>({id:p.id,lastProduced:p.lastProduced,lastUtilization:p.lastUtilization}))}
    }""")
    assert before==after,(before,after)
    assert not errors,errors
    browser.close()
server.shutdown()
print('PASS: legacy opt-in routes, auto shipping, arrivals, twelve month accounting, HTTP reload')
