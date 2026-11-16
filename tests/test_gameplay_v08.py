from pathlib import Path
from playwright.sync_api import sync_playwright
import os

html = (Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=os.getenv('CHROMIUM_EXECUTABLE') or None)
    page = browser.new_page(viewport={'width': 1450, 'height': 950})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.set_content(html, wait_until='load')
    page.evaluate("""()=>{
      window.__db={meta:{},snapshots:{}};
      idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);
      idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};
      IDB={}; SAVE_INDEX.backend='IndexedDB';
      S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});
      VIEW_FIRM=S.playerId; PAGE='product'; render();
    }""")
    design = page.evaluate("""()=>{
      const f=company(S.playerId),d=plannedDesign(),before=productCostQuote(f,d);
      S.world.JP.steelPrice *= 2;
      const after=productCostQuote(f,d);
      S.world.JP.steelPrice /= 2;
      return {fields:document.querySelectorAll('[data-design-field]').length,
        sections:document.querySelectorAll('[data-section]').length,
        increased:after.unitCost>before.unitCost,
        quoteVisible:document.body.textContent.includes('推定製造原価')};
    }""")
    assert design == {'fields':9,'sections':6,'increased':True,'quoteVisible':True}
    page.evaluate("""()=>{PAGE='distribution';render()}""")
    page.fill('#capacity_JP','1')
    page.select_option('#channel_US','dealer')
    page.fill('#capacity_US','35')
    page.click('[data-action=saveDistribution]')
    page.evaluate("""()=>{
      const f=company(S.playerId);f.brand.US=95;f.dealers.US=95;
      f.models[0].priceBase=100;f.plans[f.models[0].id]=38;
    }""")
    snapshots=[]
    for _ in range(4):
        snapshots.append(page.evaluate("""async()=>{
          const last=S.monthCommitted;
          await runMonth();
          const f=company(S.playerId),m=f.models[0],g=consolidate(S);
          const cost=f.distribution.outbound.reduce((sum,x)=>sum+x.bookCost,0);
          return {advanced:S.monthCommitted===last+1,errors:check(S),group:g.errors,
            cashflow:g.cf.reconciled,cost,ledger:acc(f,'goodsTransit'),
            deliveries:f.distribution.history.length,
            shipments:f.distribution.outbound.length,
            grossMargin:f.modelEconomics[m.id]?.sales-f.modelEconomics[m.id]?.cogs};
        }"""))
    assert all(x['advanced'] and not x['errors'] and not x['group'] and x['cashflow'] for x in snapshots)
    assert all(x['cost']==x['ledger'] for x in snapshots)
    assert snapshots[0]['grossMargin'] < 0
    assert any(x['shipments']>0 for x in snapshots)
    assert any(x['deliveries']>0 for x in snapshots)
    restored=page.evaluate("""()=>{
       const restored=parsePayload(savePayload(S)),g=consolidate(restored);
       const f=company(restored.playerId,restored);
       return {errors:check(restored),group:g.errors,cf:g.cf.reconciled,
         transit:acc(f,'goodsTransit'),
         manifest:f.distribution.outbound.reduce((a,x)=>a+x.bookCost,0)};
    }""")
    assert not restored['errors'] and not restored['group'] and restored['cf']
    assert restored['transit']==restored['manifest']
    assert not errors
    print('PASS: v0.8 UI, input price sensitivity, export revenue/COGS, loss making sales, JSON roundtrip')
    browser.close()
