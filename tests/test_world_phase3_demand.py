"""Phase 3: fixed-city market demand without phantom sales or inventory."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"])
        page=browser.new_page()
        errors=[]
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((ROOT/"index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result=page.evaluate("""() => {
          S=newWorldGame({country:'JP',name:'Phase 3 market acceptance'});
          const before=JSON.stringify(S);
          const consumer=WORLD_PRODUCTS.filter(p=>p.category==='consumer');
          const opened=WORLD_MARKETS.filter(m=>S.worldExpansion.openMarkets[m.id]!==null
            &&WORLD_ENGINE_BY_MARKET[m.id]&&S.world[WORLD_ENGINE_BY_MARKET[m.id]]);
          const quotes=opened.flatMap(m=>consumer.map(p=>worldPhase3ConsumerQuote(S,m.id,p.id)));
          const fixed=WORLD_MARKETS.every(m=>{
            const shares=worldPhase3CityShares(m);
            return shares.length===m.cities.length
              &&shares.reduce((n,c)=>n+c.shareBps,0)===10000
              &&shares.every((c,i)=>c.cityId===m.cities[i].id&&c.shareBps>0);
          });
          const conserved=quotes.every(q=>q.cities.reduce((n,c)=>n+c.quantity,0)===q.nationalQuantity
            &&q.cities.reduce((n,c)=>n+c.shareBps,0)===10000
            &&q.cities.every(c=>Number.isSafeInteger(c.quantity)&&c.quantity>=0
              &&Number.isSafeInteger(c.referencePrice)&&c.referencePrice>=0));
          const stable=quotes.every(q=>JSON.stringify(q)===
            JSON.stringify(worldPhase3ConsumerQuote(S,q.marketId,q.productId)));
          const japan=worldPhase3ConsumerQuote(S,'MKT-14','PRD-C01');
          const years=worldPhase3ConsumerQuote(S,'MKT-14','PRD-C29');
          const tiny=worldPhase3AllocateQuantity(7,WORLD_MARKET_BY_ID.get('MKT-14'));
          const closed=(()=>{try{worldPhase3ConsumerQuote(S,'MKT-11','PRD-C01');return false}
            catch(e){return e.message.includes('未開放')}})();
          const service=(()=>{try{worldPhase3ConsumerQuote(S,'MKT-14','PRD-S08');return false}
            catch(e){return e.message.includes('商品ID')}})();
          const panel=worldMarketPanel(S);
          const preview=panel.includes('data-phase3-market="MKT-14"')
            &&panel.includes('国別消費需要')&&!panel.includes('data-phase3-market="MKT-11"');
          const untouched=JSON.stringify(S)===before;
          const saved=parsePayload(savePayload(S));
          const restored=JSON.stringify(worldPhase3ConsumerQuote(saved,'MKT-14','PRD-C01'))
            ===JSON.stringify(japan)&&!check(saved).length;
          const copy=structuredClone(S);
          copy.world.JP.wealth*=1.2;
          const wealth=worldPhase3ConsumerQuote(copy,'MKT-14','PRD-C01').nationalQuantity>japan.nationalQuantity;
          copy.world.JP.inflation=.15;
          const prices=worldPhase3ConsumerQuote(copy,'MKT-14','PRD-C01').referencePrice>japan.referencePrice;
          return {markets:WORLD_MARKETS.length===40&&opened.some(m=>m.id==='MKT-27')
                    &&opened.some(m=>m.id==='MKT-28')&&opened.some(m=>m.id==='MKT-29')
                    &&opened.some(m=>m.id==='MKT-30')&&opened.some(m=>m.id==='MKT-31')
                    &&opened.some(m=>m.id==='MKT-32')&&opened.length===11,
            products:consumer.length===30,fixed,conserved,stable,
            available:japan.nationalQuantity>0&&japan.referencePrice>0,
            era:!years.available&&years.nationalQuantity===0&&years.referencePrice===0,
            tiny:tiny.map(c=>c.quantity).join(',')==='3,2,1,1',
            closed,service,preview,untouched,restored,wealth,prices};
        }""")
        assert all(result.values()),result
        assert not errors,errors
        browser.close()
    print("PASS Phase 3 demand: 40 fixed city shares, 30 consumer goods, "
          "era locks, conservation, prices, save, no phantom revenue or inventory")

if __name__=="__main__":
    main()
