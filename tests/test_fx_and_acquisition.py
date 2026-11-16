from pathlib import Path
from playwright.sync_api import sync_playwright
import os

html=(Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None)
    page=browser.new_page(viewport={'width':1500,'height':980})
    errors=[]
    page.on('pageerror',lambda err:errors.append(str(err)))
    page.set_content(html,wait_until='load')
    page.evaluate("""()=>{
      window.__mockdb={meta:{},snapshots:{}};
      idbRead=async(k,id)=>structuredClone(window.__mockdb[k][id]??null);
      idbWrite=async(k,o)=>{window.__mockdb[k][o.key]=structuredClone(o)};
      IDB={close(){}};
      openDatabase=async()=>({close(){},objectStoreNames:['meta','snapshots']});
      SAVE_INDEX.backend='IndexedDB';
    }""")
    result=page.evaluate("""async()=>{
      S=newGame({...setup,era:1900,country:'JP'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='group';render();
      const target=S.firms.find(f=>f.country==='UK');acquire(target.id);
      const rec=S.equityLinks.find(l=>l.kind==='acquisition');
      const meta={equity:rec.acquisitionSnapshot.equity,rate:rec.targetFxOnAcq,currency:rec.targetCurrency};
      const before=consolidate(S);
      await saveAuto();await runMonth();
      const first=consolidate(S).cf;
      await runMonth();
      const after=consolidate(S),second=after.cf;
      const restored=consolidate(parsePayload(savePayload(S)));
      return {meta,beforeErrors:before.errors,first,second,checks:check(S),errors:after.errors,
       roundtrip:restored.fxBalance.cash===after.fxBalance.cash && restored.cf.net===after.cf.net,
       yenRate:S.world.JP.fx};
    }""")
    print(result,'browserErrors',errors)
    assert not errors and not result['checks'] and not result['errors'] and result['roundtrip']
    assert result['yenRate']==1
    assert result['first']['scopeAdded']>0 and result['first']['reconciled']
    assert result['second']['reconciled']
    browser.close()
