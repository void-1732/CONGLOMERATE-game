from pathlib import Path
from playwright.sync_api import sync_playwright
import os

html = (Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None)
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(html,wait_until='load')
    page.evaluate("""()=>{
      window.__db={meta:{},snapshots:{}};
      idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);
      idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};
      IDB={};SAVE_INDEX.backend='IndexedDB';
    }""")
    result=page.evaluate("""async()=>{
      S=newGame({...setup,era:1900,difficulty:'easy'});
      VIEW_FIRM=S.playerId;PAGE='dashboard';render();
      await runMonth();await runMonth();
      const before=consolidate(S);
      const frozenPL=JSON.stringify(before.periodPL),frozenCF=JSON.stringify(before.cf);
      const uk=S.firms.find(x=>x.country==='UK');acquire(uk.id);
      const acquired=consolidate(S);
      const snapshot=acquired.acquisitionReview[0];
      const pastUnaffected=frozenPL===JSON.stringify(acquired.periodPL)
          &&frozenCF===JSON.stringify(acquired.cf);
      await runMonth();
      const final=consolidate(S);
      const loaded=consolidate(parsePayload(savePayload(S)));
      return {pastUnaffected,snapshot,periodCorrect:final.periodPL.period===S.monthCommitted,
       spotCashMatches:final.spot.cash===final.fxBalance.cash,
       nci:final.spot.nci,goodwill:final.spot.goodwill,
       roundtrip:JSON.stringify(loaded.periodPL)===JSON.stringify(final.periodPL),
       bsBalanced:final.spot.checkDifference===0,
       errors:final.errors,checks:check(S),cfOk:final.cf.reconciled};
    }""")
    print(result, 'pageErrors',errors)
    assert not errors and not result['errors'] and not result['checks']
    assert result['pastUnaffected'] and result['snapshot']['complete']
    assert result['periodCorrect'] and result['spotCashMatches']
    assert result['roundtrip'] and result['bsBalanced'] and result['cfOk']
    assert result['nci']>0 and result['goodwill']>0
    browser.close()
