"""Private real-save regression. Does NOT upload or change the input JSON.

Usage:
  CONGLOMERATE_REAL_SAVE_PATH=/absolute/path/conglomerate_1907_2.json \
    python tests/test_real_save_1907_v035.py

Runs local HTTP Chromium, restores S=null, compares untouched original before
and after, simulates 12 months in two separate browser contexts, and logs each
plant's production/utilization, route shipment and receipts, accounting,
reload consistency. Does not send the save to GitHub or any remote server.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json, os, shutil, hashlib
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
source=Path(os.environ['CONGLOMERATE_REAL_SAVE_PATH']).resolve()
data=source.read_text(encoding='utf-8')
original_sha=hashlib.sha256(source.read_bytes()).hexdigest()
payload=json.loads(data)
state=json.loads(payload['payload'])
assert payload['format']=='CONGLOMERATE' and payload['version']==1
assert (state['year'],state['month'])==(1907,2)
firm=next(f for f in state['firms'] if f['id']==state['playerId'])
assert firm['name']=='大成自動車' and firm['factoryOps']['mode']=='legacy'
assert firm['stock']['components']['q']==726
assert sum(firm['interplant']['siteComponents'].values())==618
assert len(firm['plants'])==5
assert not firm['interplant']['shipments']

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/index.html'

def save_state(page):
    return page.evaluate("""()=>{
      const f=current(),c=consolidate(S);
      return {date:S.year+'-'+S.month,monthCommitted:S.monthCommitted,gameId:saveIdentityV038(S),
        id:S.playerId,name:f.name,mode:f.factoryOps.mode,check:check(S),conso:c.errors,
        cf:c.cf.reconciled,stock:structuredClone(f.stock),
        materialTransit:acc(f,'materialsTransit'),componentsAccount:acc(f,'materials'),
        cash:acc(f,'cash'),routes:structuredClone(f.interplant.autoRoutes),
        shipments:structuredClone(f.interplant.shipments),
        history:structuredClone(f.interplant.history),
        plants:f.plants.map(p=>({id:p.id,name:p.name,kind:p.kind,production:p.lastProduced||0,
          util:p.lastUtilization||0,staff:factoryLaborPlanV026(f).byId[p.id]?.assigned||0,
          local:f.interplant.siteComponents[p.id]||0}))}
    }""")

def run(page,label,enable_routes):
    page.goto(url);page.wait_for_function('STORAGE_READY')
    result=page.evaluate("""raw=>{
       S=null;const restored=parsePayload(raw);
       if(restored.year!==1907||restored.month!==2)throw Error('Unexpected date');
       S=restored;VIEW_FIRM=S.playerId;VIEW_COUNTRY=company(S.playerId,S).country;
       PAGE='factory';render();return check(S);
    }""",data)
    assert result==[],result
    start=save_state(page)
    assert start['name']=='大成自動車' and start['mode']=='legacy'
    assert sum(x['local'] for x in start['plants'])==618
    assert start['stock']['components']['q']==726
    print('REAL_SAVE_START',label,json.dumps(start,ensure_ascii=False),flush=True)
    if enable_routes:
        # The test explicitly approves two routes via the same UI a player uses.
        page.locator('details.factory-accordion').filter(
          has=page.locator('[data-action="legacyRouteSaveV035"]')).locator('summary').click()
        f=firm
        source_plants=[p for p in f['plants'] if p['kind'] in ('components','body','engine')]
        targets=[p for p in f['plants'] if p['kind'] in ('integrated','assembly')]
        # Split support factories across the two destinations; no game mode switch.
        assert len(source_plants)==3 and len(targets)==2
        for i,target in enumerate(targets):
            source_plant=source_plants[i]
            key=source_plant['id']+'__'+target['id']
            page.locator('#legacyEnabled_'+key).check()
            page.locator('#legacyTarget_'+key).fill('150')
            page.locator('#legacyLimit_'+key).fill('80')
        page.locator('[data-action="legacyRouteSaveV035"]').click()
        assert page.evaluate("current().interplant.autoRoutes.filter(r=>r.enabled).length")==2
    for index in range(12):
        before=page.evaluate('S.monthCommitted')
        page.evaluate('async()=>await runMonth()')
        current=save_state(page)
        print('REAL_SAVE_MONTH',label,index+1,json.dumps(current,ensure_ascii=False),flush=True)
        assert current['monthCommitted']==before+1,(label,index, page.evaluate('LAST_MONTH_DIAGNOSTIC'),current)
        assert current['check']==[] and current['conso']==[] and current['cf'],(label,index,current)
    before=save_state(page)
    assert page.evaluate('async()=>await saveAuto()')
    page.reload();page.wait_for_function('STORAGE_READY')
    after=save_state(page)
    assert before==after,(label,'reload mismatch')
    return after

try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=['--no-sandbox'])
        baseline=run(browser.new_context().new_page(),'baseline_unconfigured',False)
        enabled=run(browser.new_context().new_page(),'approved_legacy_routes',True)
        assert enabled['mode']=='legacy'
        assert any(h['action']=='自動発送' for h in enabled['history'])
        assert any(h['action']=='受領' for h in enabled['history'])
        print('REAL_SAVE_COMPARISON',json.dumps({
          'baseline_month':baseline['date'],'enabled_month':enabled['date'],
          'baseline_plants':baseline['plants'],'enabled_plants':enabled['plants'],
          'baseline_legacy_shipments':len(baseline['shipments']),
          'enabled_legacy_shipments':len(enabled['shipments'])},ensure_ascii=False),flush=True)
        browser.close()
finally:
    server.shutdown()
assert hashlib.sha256(source.read_bytes()).hexdigest()==original_sha
print('PASS: original real-save source unchanged; browser restoration and two twelve-month progressions')
