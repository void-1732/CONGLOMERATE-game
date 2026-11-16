from pathlib import Path
from playwright.sync_api import sync_playwright
import os

html=(Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None)
    page=browser.new_page()
    errors=[]
    page.on('pageerror',lambda err:errors.append(str(err)))
    page.set_content(html,wait_until='load')
    page.evaluate("""()=>{
      window.__db={meta:{},snapshots:{}};
      window.__makeMockDB=()=>({objectStoreNames:['meta','snapshots'],close(){},
       transaction(store,type){const tx={oncomplete:null,onerror:null,onabort:null,
        objectStore(){return{delete(id){delete window.__db[store][id];queueMicrotask(()=>tx.oncomplete?.())}}}};return tx;}});
      idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);
      idbWrite=async(k,o)=>{if(window.__failOnce&&k==='meta'){window.__failOnce=false;throw Error('save pointer failure')}
       window.__db[k][o.key]=structuredClone(o)};
      openDatabase=async()=>window.__makeMockDB();IDB=window.__makeMockDB();
      SAVE_INDEX.backend='IndexedDB';
    }""")
    result=page.evaluate("""async()=>{
      S=newGame({...setup,era:1900});VIEW_FIRM=S.playerId;PAGE='save';render();
      const saved=await saveAuto();
      const metaBefore=structuredClone(window.__db.meta.active),slot=SAVE_INDEX.active;
      await diagnoseStorage();
      const diagnosticResult=saveWarning,keys=Object.keys(window.__db.snapshots);
      const metaSame=window.__db.meta.active.slot===metaBefore.slot;
      window.__failOnce=true;
      const failedSave=await saveAuto(),preservedPointer=window.__db.meta.active.slot===slot;
      await refreshSaveIndex();
      const good=await restoreAuto();
      await runMonth();
      const second=SAVE_INDEX.active;
      window.__db.snapshots['auto:'+second].serialized='CORRUPT';
      await refreshSaveIndex();S=null;
      const recovered=await restoreAuto();
      return {saved,diagnosticResult,metaSame,keys,failedSave,preservedPointer,good,recovered,
       checks:check(S),warnings:saveWarning};
    }""")
    print('STORAGE MOCK',result,'PAGE ERRORS',errors)
    assert result['saved'] and result['metaSame'] and result['preservedPointer']
    assert not result['failedSave'] and result['good'] and result['recovered']
    assert not result['checks'] and not errors
    assert '一致' in result['diagnosticResult']
    assert not any(key.startswith('diagnostic:') for key in result['keys'])
    browser.close()
