"""Real-browser save backend classification, multiple games and user-approved module routes."""
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
 context=browser.new_context()
 page=context.new_page()
 errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(URL);page.wait_for_function('STORAGE_READY')
 result=page.evaluate("""async()=>{
   S=newGame({era:1900,country:'JP',history:'historical',difficulty:'normal',name:'大成自動車'});
   VIEW_FIRM=S.playerId;
   if(!await saveAuto()||S.autosaveState!=='保存成功'||!LAST_SAVE_RESULT_V035.indexedDB)
    throw Error('verified IndexedDB save must succeed');
   const idA=saveIdentityV038(S);
   const B=newGame({era:1900,country:'JP',history:'historical',difficulty:'normal',name:'大成自動車'});
   const idB=saveIdentityV038(B);if(idA===idB)throw Error('same-company game identities collided');
   S=B;VIEW_FIRM=S.playerId;
   if(!await saveAuto())throw Error('second game save failed');
   const ok=await restoreAuto();
   if(!ok||saveIdentityV038(S)!==idB)throw Error('last selected game not restored');
   localStorage.removeItem(RECOVERY_SELECTION_KEY_V038);
   const ambiguous=await restoreAuto();
   if(ambiguous||!RECOVERY_BLOCKED_V038||RECOVERY_CHOICES_V038.length<2)
    throw Error('different games should trigger recovery selection');
   RECOVERY_BLOCKED_V038=false;RECOVERY_CHOICES_V038=[];
   S=B;VIEW_FIRM=S.playerId;
   const real=IDB;
   IDB=null;
   const fallback=await saveAuto();
   if(fallback||S.autosaveState!=='簡易バックアップのみ成功'||
      LAST_SAVE_RESULT_V035.indexedDB||!LAST_SAVE_RESULT_V035.safety)
    throw Error('emergency only save was mislabeled');
   const oldWrite=writeSafetySnapshotV037;
   writeSafetySnapshotV037=()=>false;
   const total=await saveAuto();
   if(total||S.autosaveState!=='保存失敗'||LAST_SAVE_RESULT_V035.safety)
    throw Error('total save failure was mislabeled');
   writeSafetySnapshotV037=oldWrite;
   IDB=real;
   if(!await saveAuto()||S.autosaveState!=='保存成功')throw Error('IDB recovery failed');
   const latest=LAST_SAVE_RESULT_V035;
   const p=factoryPlantPlanV039(current(),current().plants[0]);
   if(p.plantTotal>p.companyTotal)throw Error('factory allocation exceeds company plan');
   return {idA,idB,latest,choices:2};
 }""")
 assert result['idA']!=result['idB'],result
 assert result['latest']['status']=='保存成功'
 # Refresh and ensure the second company's ID is retained.
 before=page.evaluate("()=>({id:saveIdentityV038(S),year:S.year,month:S.month})")
 page.reload();page.wait_for_function('STORAGE_READY')
 after=page.evaluate("()=>({id:saveIdentityV038(S),year:S.year,month:S.month})")
 assert before==after,(before,after)
 assert not errors,errors
 browser.close()
server.shutdown()
print('PASS: 3 save statuses, two same-name games, choice guard, IDB recovery and HTTP reload')
