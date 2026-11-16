"""v0.12 same-country subsidiary stock transfer at book value, paired cash and inventories."""
from pathlib import Path
from playwright.sync_api import sync_playwright
HTML=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8')
INIT="""()=>{window.__db={meta:{},snapshots:{}};idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};IDB={};SAVE_INDEX.backend='IndexedDB';S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});VIEW_FIRM=S.playerId;PAGE='people';render();}"""

with sync_playwright() as p:
 b=p.chromium.launch(headless=True,args=['--no-sandbox']);page=b.new_page()
 page.set_content(HTML,wait_until='load');page.evaluate(INIT)
 page.evaluate("()=>{PAGE='group';render()}")
 page.fill('#subName','調達検証子会社');page.select_option('#subIndustry','resource')
 page.fill('#subCapital','450000');page.click('[data-action=createSub]')
 out=page.evaluate("""()=>{const buyer=company(S.playerId),seller=S.firms.find(f=>f.name==='調達検証子会社');ensureSupplyNetwork(S);seller.goods.RESOURCE??={q:0,v:0};const stock=seller.goods.RESOURCE,added=localFromBase(20000,seller.country);post(seller,{goods:added},{cash:added},'検証用材料');
 stock.q+=100;stock.v+=added;const id='CORP:'+seller.id+':steel';buyer.supply.contracts.steel.supplierId=id;const before=acc(buyer,'cash'),original=acc(seller,'goods');buyer.supply.inbound.push({id:'TEST-BOOK',supplierId:id,type:'steel',origin:'JP',qty:5,totalBase:2000,due:ym(S.year,S.month)});
 deliverMaterials(S,buyer,[]);return {id,buyerPaid:before-acc(buyer,'cash'),sellerGoodsDecrease:original-acc(seller,'goods'),checks:check(S),errors:consolidate(S).errors,cf:consolidate(S).cf.reconciled}}""")
 assert out['buyerPaid']>0 and out['buyerPaid']==out['sellerGoodsDecrease']
 assert not out['checks'] and not out['errors'] and out['cf'],out
 print('PASS v0.12: group-company book-value sourcing, symmetric journals and CF')
 b.close()
