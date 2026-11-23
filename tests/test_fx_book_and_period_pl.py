from pathlib import Path
from playwright.sync_api import sync_playwright
import os

html = (Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None)
    page = browser.new_page(viewport={'width':1520,'height':960})
    errors = []
    page.on('pageerror', lambda err: errors.append(str(err)))
    page.set_content(html, wait_until='load')
    page.evaluate("""()=>{
      window.__db={meta:{},snapshots:{}};
      idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);
      idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};
      IDB={};SAVE_INDEX.backend='IndexedDB';
    }""")
    result = page.evaluate("""async()=>{
      S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='group';render();
      const trade=S.firms.find(f=>f.industry==='trade');acquire(trade.id);
      const uk=S.firms.find(f=>f.country==='UK');acquire(uk.id);
      await runMonth();
      const first=consolidate(S);
      const root=company(S.playerId),buyer=company(trade.id);
      PAGE='corporateSubsidiaries';VIEW_FIRM=root.id;render();
      const qty=10,cost=30000;
      post(root,{goods:cost},{cash:cost},'TEST fixture purchase','operating');
      root.goods.TEST={q:qty,v:cost};
      buyer.marketPresence=[];
      render();
      document.getElementById('internalBuyer').value=buyer.id;
      document.getElementById('internalProduct').value='TEST';
      document.getElementById('internalQuantity').value='10';
      groupSale();
      const transactions=(S.intercompanyTx||[]).filter(x=>x.kind==='goods').length;
      await runMonth();
      const held=consolidate(S),frozen=JSON.stringify(held.periodPL),saved=savePayload(S);
      company(trade.id).marketPresence=['JP'];S.world.JP.demand=10000;
      await runMonth();
      const sold=consolidate(S),loaded=consolidate(parsePayload(savePayload(S)));
      PAGE='consolidated';render();
      return {firstCashMatches:first.spot.cash===first.fxBalance.cash,
       firstBsBalanced:first.spot.checkDifference===0,transactions,
       heldDeferred:held.spotDeferredInventory,heldAdjustment:held.periodPL.inventoryDeferralChange,
       heldSalesEliminated:held.periodPL.internalSalesEliminated,
       releasedDeferred:sold.spotDeferredInventory,releasedAdjustment:sold.periodPL.inventoryDeferralChange,
       finalBsBalanced:sold.spot.checkDifference===0,
       frozenMonth:frozen===JSON.stringify(consolidate(parsePayload(saved)).periodPL),
       roundtrip:JSON.stringify(sold.spot)===JSON.stringify(loaded.spot)
           &&JSON.stringify(sold.periodPL)===JSON.stringify(loaded.periodPL),
       screenVisible:document.body.textContent.includes('全科目・期末為替換算BS'),
       errors:sold.errors,checks:check(S),cfOk:sold.cf.reconciled};
    }""")
    print(result, "pageErrors", errors)
    assert not errors and not result['errors'] and not result['checks']
    assert result['firstCashMatches'] and result['firstBsBalanced']
    assert result['transactions']==1 and result['heldDeferred']>0
    assert result['heldAdjustment']>0 and result['heldSalesEliminated']>0
    assert result['releasedDeferred']==0 and result['releasedAdjustment']<0
    assert result['finalBsBalanced'] and result['frozenMonth']
    assert result['roundtrip'] and result['screenVisible'] and result['cfOk']
    browser.close()
