"""Real five-factory end-to-end reproduction, no mocked monthly engine/save.
One company with Tokyo integrated, Los Angeles assembly, Nagoya's 3 module works.
This is a synthetic fixture reproducing visible symptoms, NOT the user's save.
"""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright
import os, shutil, json

ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
URL=f'http://127.0.0.1:{server.server_port}/index.html'
LOG=[]
def snapshot(p, stage):
    r=p.evaluate("""()=>{
      const f=current(),c=consolidate(S),month=S.monthCommitted;
      return {
        date:S.year+'-'+S.month,committed:month,mode:f.factoryOps.mode,cash:acc(f,'cash'),debt:acc(f,'debt'),
        errors:check(S),group:c.errors,cf:c.cf.reconciled,
        materials:{steel:structuredClone(f.stock.steel),rubber:structuredClone(f.stock.rubber),
          ledger:acc(f,'materials'),transit:acc(f,'materialsTransit')},
        plants:f.plants.map(p=>({id:p.id,name:p.name,kind:p.kind,country:p.siteCountry,
          status:factoryStatus(p),capacity:p.capacity,condition:p.condition,
          staff:factoryLaborPlanV026(f).byId[p.id]?.assigned||0,
          produced:p.lastProduced||0,util:p.lastUtilization||0,
          local:moduleAtV21(f,p.id)[v21ModuleType(p)]||0,
          incoming:f.factoryOps.shipments.filter(x=>x.to===p.id).map(x=>({from:x.from,typ:x.typ,qty:x.qty,due:x.due}))})),
        shipments:f.factoryOps.shipments.map(x=>({from:x.from,to:x.to,typ:x.typ,qty:x.qty,due:x.due,bookCost:x.bookCost})),
        history:f.factoryOps.history.slice(-25).map(x=>({action:x.action,month:x.month,from:x.from,to:x.to,qty:x.qty,typ:x.typ})),
        completed: f._produced||0,productStock:Object.values(f.goods).reduce((n,x)=>n+(x.q||0),0)
      };
    }""")
    assert not r['errors'] and not r['group'] and r['cf'],(stage,r)
    LOG.append({'stage':stage,'result':r})
    print('FIVE_PLANT_MONTH',json.dumps(LOG[-1],ensure_ascii=False),flush=True)
    return r

def month(p,name):
    before=p.evaluate('S.monthCommitted')
    p.evaluate('async()=>await runMonth()')
    after=p.evaluate('S.monthCommitted')
    assert after==before+1,(name,'month did not commit',p.evaluate('LAST_MONTH_DIAGNOSTIC'))
    return snapshot(p,name)

with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=['--no-sandbox'])
    p=browser.new_page(viewport={'width':1450,'height':950})
    errs=[]
    p.on('pageerror',lambda x:errs.append(str(x)))
    p.goto(URL);p.wait_for_function('STORAGE_READY')
    # Use production saveAuto (not a mock), and the real factory UI.
    p.evaluate("""async()=>{
      S=newGame({era:1900,country:'JP',difficulty:'easy',
        history:'historical',name:'大成五工場再現試験'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';const f=current();
      f.plants[0].name='大成 京浜工場';
      for(const m of f.models)f.plans[m.id]=230; // a company-wide model schedule
      PAGE='factory';render();
      if(!await saveAuto())throw Error('initial save failed');
    }""")
    # Paid hiring through the actual user command.
    p.evaluate("PAGE='people';PEOPLE_VIEW='hr';render()")
    p.locator('#hireArea').select_option('production')
    p.locator('#hireCount').fill('240')
    p.locator('[data-action="hireStaff"]').click()
    assert p.evaluate('current().staff.production')>=240
    sites=[
      ('米大成工場','assembly','medium','US-LAX'),
      ('大成部品 名古屋工場（エンジン）','engine','small','JP-NGO'),
      ('大成部品 名古屋工場（車体）','body','small','JP-NGO'),
      ('大成部品 名古屋工場','components','small','JP-NGO')
    ]
    for name,kind,scale,site in sites:
        p.evaluate("PAGE='factory';render()")
        p.get_by_text('新工場を建設する',exact=True).click()
        p.locator('#factoryName').fill(name)
        p.locator('#factoryScale').select_option(scale)
        p.locator('#factoryKind').select_option(kind)
        p.locator('#factorySite').select_option(site)
        p.locator('[data-action="factoryBuild"]').click()
        assert p.evaluate("name=>current().plants.some(x=>x.name===name)",name),name
    # Actual double-entry material acquisitions: balances, amounts and journal entries
    # are changed together; no components, vehicles or employees are granted.
    p.evaluate("""()=>{
      const f=current();
      for(const t of ['steel','rubber']){
        const qty=2400,price=t==='steel'?60:40,val=qty*price;
        if(acc(f,'cash')<val)throw Error('no cash for paid fixture procurement');
        post(f,{materials:val},{cash:val},'五工場検証の有償原料調達 '+t,'operating',S);
        f.stock[t].q+=qty;f.stock[t].v+=val;
      }
      ensureFactoryV21(f);ensureV11Firm(f);
      if(f.factoryOps.mode!=='detailed')throw Error('explicit built specialist mode not detailed');
      // Simulate a player who has kept AI shipping decisions proposal-only.
      ensureAiCenter(f).modes.shipping='proposal';
      f.factoryOps.staffAssignments[f.plants.find(x=>x.name==='米大成工場').id]=58;
      for(const site of f.plants.filter(x=>v21ModuleType(x)))
        f.factoryOps.plans[site.id]=14;
      if(check(S).length)throw Error(check(S).join(' / '));
    }""")
    initial=p.evaluate("""()=>{
      const f=current(),us=f.plants.find(x=>x.name==='米大成工場');
      return {kind:us.kind,site:us.siteId,staff:factoryLaborPlanV026(f).byId[us.id]?.assigned??0,
       plan:f.models.reduce((n,m)=>n+(f.plans[m.id]||0),0),moduleStock:V21_MODULE_TYPES.map(t=>moduleAtV21(f,us.id)[t])};
    }""")
    assert initial['kind']=='assembly' and initial['site']=='US-LAX',initial
    assert initial['plan']==230 and initial['moduleStock']==[0,0,0],initial
    assert not p.evaluate('aiModeAllows(current(),"shipping")'),'Expected non-delegated player mode to be disabled'
    # Construct full five-plant topology using actual runMonth.
    for i in range(5): month(p,'build-'+str(i+1))
    diagnostic=p.evaluate("""()=>{
      const f=current(),la=f.plants.find(x=>x.name==='米大成工場');
      return factoryInsightV023(f,la);
    }""")
    assert diagnostic['plantPlanned']>0,diagnostic
    assert diagnostic['estimate']['value']==0,diagnostic
    assert any('専門部品セットが不足' in x['state'] for x in diagnostic['reasons']),diagnostic
    assert p.evaluate("current().plants.find(x=>x.name==='米大成工場').construction===null")
    ids=p.evaluate("""()=>{
      const f=current();
      return {tokyo:f.plants.find(x=>x.name==='大成 京浜工場').id,
        la:f.plants.find(x=>x.name==='米大成工場').id,
        parts:f.plants.filter(p=>v21ModuleType(p)).map(p=>p.id)};
    }""")
    # Facility expansion is paid and scheduled: 60 -> 78 after 3-month construction.
    p.evaluate("""id=>{
      PAGE='factory';render();manageFactoryV21(id,'extend');
      if(!current().plants.find(p=>p.id===id).renovation)throw Error('expansion did not start');
    }""",ids['la'])
    for i in range(3): month(p,'la-expansion-'+str(i+1))
    p.evaluate("""id=>{
      const la=current().plants.find(p=>p.id===id);
      if(la.capacity!==78||la.renovation)throw Error('not expanded to 78');
      la.condition=86.27; // synthetic worn condition for reported-screen reproduction
      la.lastProduced=0;la.lastUtilization=0;
      // The reproduction's displayed zero is an initial condition, never a patched result.
    }""",ids['la'])
    # Active routes are explicitly configured by the user. They must work
    # even when AI shipping delegation is set to proposal-only.
    p.evaluate("PAGE='factory';render()")
    p.get_by_text("専門部品の製造方式・輸送中在庫・一括管理",exact=True).click()
    for sid in ids['parts']:
        p.locator('#v21Plan_'+sid).fill('14')
        p.locator('#v21Dest_'+sid).select_option(ids['la'])
        p.locator('#v21Target_'+sid).fill('24')
        p.locator('#v21Limit_'+sid).fill('8')
        p.locator('#v21Auto_'+sid).check()
    p.locator('[data-action="v21RouteSave"]').click()
    assert all(p.evaluate("ids=>ids.map(id=>current().factoryOps.routes[id].enabled)",ids['parts']))
    last=month(p,'enabled-routes-first-dispatch')
    la=next(x for x in last['plants'] if x['id']==ids['la'])
    parts=[x for x in last['plants'] if x['id'] in ids['parts']]
    assert all(x['produced']>0 and x['util']>0 for x in parts),last
    assert la['produced']==0,('LA assembled cars before receiving modules',last)
    dispatched=[x for x in last['shipments'] if x['to']==ids['la']]
    assert len(dispatched)==3 and all(x['qty']>0 and x['due']>last['committed'] for x in dispatched),(
       'BUG: explicitly enabled routes blocked by AI delegation or routing',last)
    for i in range(3): last=month(p,'international-transit-'+str(i+1))
    assert any(x['id']==ids['la'] and x['produced']>0 and x['util']>0 for x in last['plants']),(
      'LA still stopped after modules arrived',last)
    # Redirect explicit routes to Tokyo (the UI supports one destination per source).
    p.evaluate("PAGE='factory';render()")
    p.get_by_text("専門部品の製造方式・輸送中在庫・一括管理",exact=True).click()
    for sid in ids['parts']:
        p.locator('#v21Dest_'+sid).select_option(ids['tokyo'])
        p.locator('#v21Target_'+sid).fill('24')
        p.locator('#v21Limit_'+sid).fill('8')
    p.locator('[data-action="v21RouteSave"]').click()
    for i in range(4): last=month(p,'domestic-transit-'+str(i+1))
    assert any(x['id']==ids['tokyo'] and x['produced']>0 for x in last['plants']),last
    assert any(x['action']=='到着' and x['to']==ids['tokyo'] for x in last['history']),last
    # Return the player's explicit replenishment destination to LA for the
    # subsequent 12-month sustained-operation test.
    p.evaluate("PAGE='factory';render()")
    p.get_by_text("専門部品の製造方式・輸送中在庫・一括管理",exact=True).click()
    for sid in ids['parts']:
        p.locator('#v21Dest_'+sid).select_option(ids['la'])
        p.locator('#v21Target_'+sid).fill('24')
        p.locator('#v21Limit_'+sid).fill('8')
    p.locator('[data-action="v21RouteSave"]').click()
    assert all(p.evaluate("ids=>ids.map(id=>current().factoryOps.routes[id].to===current().plants.find(p=>p.name==='米大成工場').id)",ids['parts']))
    # Player takes a real 36-month bank loan to fund uninterrupted salaries,
    # procurement and freight over the long horizon (no unearned cash).
    p.evaluate("PAGE='finance';render()")
    p.locator('#borrowBase').fill('1500000')
    debt_before=p.evaluate("acc(current(),'debt')")
    p.locator('[data-action="borrow"]').click()
    assert p.evaluate("acc(current(),'debt')")>debt_before,'legitimate loan was not executed'
    assert not p.evaluate('check(S)')
    # Persist all factory state with the real IndexedDB save and a real reload.
    before=p.evaluate("""()=>{
      const f=current();return {year:S.year,month:S.month,committed:S.monthCommitted,
        id:S.playerId,name:f.name,mode:f.factoryOps.mode,
        factories:f.plants.map(p=>[p.id,p.kind,p.lastProduced,p.lastUtilization,p.condition]),
        modules:V21_MODULE_TYPES.map(t=>structuredClone(f.stock[t])),
        shipments:structuredClone(f.factoryOps.shipments),plan:structuredClone(f.plans)};
    }""")
    p.reload();p.wait_for_function('STORAGE_READY')
    after=p.evaluate("""()=>{
      const f=current();return {year:S.year,month:S.month,committed:S.monthCommitted,
        id:S.playerId,name:f.name,mode:f.factoryOps.mode,
        factories:f.plants.map(p=>[p.id,p.kind,p.lastProduced,p.lastUtilization,p.condition]),
        modules:V21_MODULE_TYPES.map(t=>structuredClone(f.stock[t])),
        shipments:structuredClone(f.factoryOps.shipments),plan:structuredClone(f.plans)};
    }""")
    assert before==after,(before,after)
    for i in range(12): last=month(p,'long-term-'+str(i+1))
    assert any(any(x['id']==ids['la'] and x['produced']>0 for x in row['result']['plants']) for row in LOG if row['stage'].startswith('long-term-')), 'LA never resumed over twelve more months'
    assert not errs,errs
    browser.close()
server.shutdown()
print('PASS five plants: paid materials -> 3 specialist outputs -> international & domestic transit -> completed cars -> reload -> long-term accounting')
