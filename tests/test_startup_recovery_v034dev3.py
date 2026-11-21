"""Real HTTP browser: exact scenario selection, reload, corruption fallback, and scroll."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import os, shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
URL=f'http://127.0.0.1:{server.server_port}/index.html'
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(URL)
    page.wait_for_function('STORAGE_READY')
    assert page.evaluate('S===null')
    for year in (1900,1920,1950,1980,2020):
        result=page.evaluate("""year=>{
          const s=newGame({era:year,country:'JP',difficulty:'normal',history:'historical',name:'開始テスト'});
          const f=company(s.playerId,s);
          return {year:s.year,month:s.month,committed:s.monthCommitted,gameId:s.gameIdV038,
             name:f.name,country:f.country,difficulty:s.config.difficulty};
        }""",year)
        assert result['year']==year and result['month']==1 and result['committed']==year*12-1,result
        assert result['name']=='開始テスト' and result['country']=='JP' and result['difficulty']=='normal',result
        assert result['gameId'],result
    # Start through the normal UI and commit real storage, not a saveAuto mock.
    for _ in range(4):
        page.locator('[data-action="wizardNext"]').click()
    page.wait_for_function("S?.playerId && S.autosaveState==='保存成功'")
    page.evaluate("PAGE='people';PEOPLE_VIEW='hr';render()")
    page.locator('#hireArea').select_option('production')
    page.locator('#hireCount').fill('7')
    page.locator('[data-action="hireStaff"]').click()
    page.wait_for_function("()=>S&&check(S).length===0")
    # Scroll down and reload before the debounced IDB save finishes.
    page.evaluate('window.scrollTo(0,document.body.scrollHeight)')
    before=page.evaluate("""()=>{const f=current();return {
      id:S.playerId,gameId:S.gameIdV038,year:S.year,month:S.month,
      name:f.name,country:f.country,employees:f.staff.production,
      cash:acc(f,'cash'),materials:f.stock.steel,version:VERSION,db:DB_NAME
    }}""")
    page.reload();page.wait_for_function('STORAGE_READY')
    after=page.evaluate("""()=>{const f=current();return {
      id:S.playerId,gameId:S.gameIdV038,year:S.year,month:S.month,
      name:f.name,country:f.country,employees:f.staff.production,
      cash:acc(f,'cash'),materials:f.stock.steel,version:VERSION,db:DB_NAME
    }}""")
    assert after==before,(before,after)
    assert page.evaluate("PAGE")=="dashboard"
    assert page.evaluate("window.scrollY")==0
    assert page.evaluate("check(S)")==[]
    # Multiple different game identities must not be selected by savedAt.
    page.evaluate("""async()=>{
      const prior=savePayload(S),original=structuredClone(S);
      const next=newGame({era:2020,country:'US',difficulty:'normal',history:'historical',name:'別の創業'});
      writeSafetySnapshotV037(savePayload(next));
      localStorage.removeItem(RECOVERY_SELECTION_KEY_V038); // simulate unknown player choice
      await refreshSaveIndex();
      const ok=await restoreAuto();
      if(ok||!RECOVERY_BLOCKED_V038||RECOVERY_CHOICES_V038.length<2)
        throw Error('different games incorrectly auto-selected');
      S=original;writeSafetySnapshotV037(prior);
      localStorage.setItem(RECOVERY_SELECTION_KEY_V038,saveIdentityV038(S));
      RECOVERY_BLOCKED_V038=false;RECOVERY_CHOICES_V038=[];
    }""")
    # Corrupt only the current IDB generation; previous generation must remain intact.
    expected_previous=page.evaluate("""async()=>{
      await saveAuto();
      const rec=SAVE_INDEX.auto[SAVE_INDEX.previous];
      if(!rec)throw Error('missing previous generation');
      const prior=parsePayload(rec.serialized);
      const active=SAVE_INDEX.auto[SAVE_INDEX.active];
      await idbWrite('snapshots',{...active,serialized:'corrupted-active'});
      localStorage.removeItem(EMERGENCY_KEY);
      return {id:prior.playerId,year:prior.year,month:prior.month,
        name:company(prior.playerId,prior).name};
    }""")
    page.reload();page.wait_for_function('STORAGE_READY')
    actual_previous=page.evaluate("""()=>{
      const f=current();return {id:S.playerId,year:S.year,month:S.month,name:f.name};
    }""")
    assert actual_previous==expected_previous,(expected_previous,actual_previous)
    assert page.evaluate('check(S)')==[]
    earlier_manual=page.evaluate('savePayload(S)')
    # Twelve real month commits with accounting reconciliation, then hard reload.
    for i in range(12):
        prev=page.evaluate('S.monthCommitted')
        page.evaluate('async()=>await runMonth()')
        state=page.evaluate("""()=>{
          const c=consolidate(S),f=current();return {
           committed:S.monthCommitted,errors:check(S),conso:c.errors,cf:c.cf.reconciled,
           inventories:Object.fromEntries(['steel','rubber','components','moduleEngine',
             'moduleBody','moduleElectronics'].map(t=>[t,structuredClone(f.stock[t])])),
           produced:f._produced||0,validYear:S.year,validMonth:S.month
          };
        }""")
        assert state["committed"]==prev+1,(i,state,page.evaluate('LAST_MONTH_DIAGNOSTIC?.message'))
        assert not state["errors"] and not state["conso"] and state["cf"],(i,state)
        assert all(v["q"]>=0 and v["v"]>=0 for v in state["inventories"].values()),(i,state)
    pre_reload=page.evaluate("""()=>({
      id:S.playerId,year:S.year,month:S.month,committed:S.monthCommitted,
      cash:acc(current(),'cash'),staff:current().staff.production,history:S.history.length,
      inventory:structuredClone(current().stock)
    })""")
    page.reload();page.wait_for_function('STORAGE_READY')
    post_reload=page.evaluate("""()=>({
      id:S.playerId,year:S.year,month:S.month,committed:S.monthCommitted,
      cash:acc(current(),'cash'),staff:current().staff.production,history:S.history.length,
      inventory:structuredClone(current().stock)
    })""")
    assert pre_reload==post_reload,(pre_reload,post_reload)
    # An intentional manual restore to an older period must not be undone by
    # a newer IDB generation during an immediate page refresh.
    assert page.evaluate('raw=>restore(raw)',earlier_manual)
    expected_rollback=page.evaluate("()=>({year:S.year,month:S.month,id:S.playerId})")
    assert (expected_rollback['year'],expected_rollback['month'])!=(pre_reload['year'],pre_reload['month'])
    page.reload();page.wait_for_function('STORAGE_READY')
    actual_rollback=page.evaluate("()=>({year:S.year,month:S.month,id:S.playerId})")
    assert actual_rollback==expected_rollback,(expected_rollback,actual_rollback)
    assert page.evaluate('check(S)')==[]
    assert not errors,errors
    browser.close()
server.shutdown()
print("PASS: 5 start eras, persisted immediate edits, scroll reset, different game recovery guard")
