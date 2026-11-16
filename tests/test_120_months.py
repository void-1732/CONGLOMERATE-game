from playwright.sync_api import sync_playwright
from pathlib import Path
import time, json, os

html = (Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None)
    page = browser.new_page(viewport={'width': 1420, 'height': 850})
    errors = []
    page.on('pageerror', lambda err: errors.append(str(err)))
    page.set_content(html, wait_until='load')
    page.evaluate("""()=>{
      window.__db={meta:{},snapshots:{}};
      idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);
      idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};
      IDB={}; SAVE_INDEX.backend='IndexedDB';
    }""")
    start = time.monotonic()
    result = page.evaluate("""async()=>{
      S=newGame({...setup,era:1900,difficulty:'easy'});
      VIEW_FIRM=S.playerId;PAGE='group';render();
      const target=S.firms.find(f=>f.country==='UK');
      acquire(target.id);
      const nciStart=consolidate(S).bs.nci;
      await saveAuto();
      const failures=[],cashflowFailures=[];let months=0;
      for(let i=0;i<120;i++){
        const previous=ym(S.year,S.month);
        await runMonth();
        if(ym(S.year,S.month)<=previous){failures.push('no monthly advancement: '+i);break}
        const consolidated=consolidate(S),checks=check(S);
        months++;
        if(consolidated.errors.length||checks.length){failures.push({month:i,errors:consolidated.errors,checks});break}
        if(!consolidated.cf.reconciled){cashflowFailures.push({month:i,diff:consolidated.cf.unreconciled})}
      }
      const payload=savePayload(S),restored=parsePayload(payload);
      const actual=consolidate(S),reloaded=consolidate(restored);
      return {months,failures,cashflowFailures,nciStart,nciEnd:actual.bs.nci,
       roundtrip:JSON.stringify(actual.bs)===JSON.stringify(reloaded.bs) &&
                 JSON.stringify(actual.cf)===JSON.stringify(reloaded.cf),
       serializedBytes:payload.length};
    }""")
    print('elapsed',round(time.monotonic()-start,2),'seconds',json.dumps(result,ensure_ascii=False))
    print('browserErrors',errors)
    assert not errors and not result['failures'] and not result['cashflowFailures']
    assert result['months']==120 and result['roundtrip']
    browser.close()
