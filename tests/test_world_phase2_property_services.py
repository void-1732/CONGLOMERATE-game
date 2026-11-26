"""S12 and S14 use real facility capacity and settle once at month close."""

import os
import shutil
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def run(url):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
            args=["--no-sandbox"],
        )
        context = browser.new_context()
        context.route("**/*", lambda route: route.continue_() if route.request.url == url else route.abort())
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        page.wait_for_function("STORAGE_READY")
        page.evaluate("""() => {
          S=newWorldGame({country:'JP',name:'Property service regression'});
          const parent=company(S.playerId),capital=60000000,payer=S.seq;
          post(parent,{investment:capital},{cash:capital},'検証用の設立','investing',S);
          const provider=initFirm(S,{name:'Property provider',country:'JP',industry:'service',
            seedBase:600000,publicOwnership:false});
          provider.owners=[{id:parent.id,econ:1,vote:1}];
          registerEquityLink(S,{parentId:parent.id,childId:provider.id,ratio:1,kind:'foundation',
            considerationLocal:capital,buyerJournal:payer,
            childJournal:provider.journals.find(j=>j.text==='創業資本').id,
            bookEquityBase:baseFromLocal(capital,'JP'),cashAcquiredBase:baseFromLocal(acc(provider,'cash'),'JP')});
          provider.auto=false;
          VIEW_FIRM=parent.id;PAGE='facilityProduction';render();
          window.providerId=provider.id;
        }""")
        page.locator("#world-domestic > summary").click()
        offer = page.locator('form[data-world-domestic="property-offer"]')
        for product, quantity, unit_fee in [("PRD-S12", "1", "230"), ("PRD-S14", "2", "18")]:
            offer.locator('[name="product"]').select_option(product)
            offer.locator('[name="quantity"]').fill(quantity)
            offer.locator('[name="unitFee"]').fill(unit_fee)
            offer.get_by_role("button", name="利用を申し込む").click()
        assert page.evaluate("""() => {
          const w=S.worldExpansion,p=company(window.providerId),buyer=company(S.playerId);
          if(w.propertyContracts.length!==2||w.propertyContracts.some(t=>t.amount!==0)
           ||acc(p,'serviceRevenue')!==0||worldServiceActivity(S,'PRD-S12').length) return false;
          const plant=p.plants[0],days=new Date(Date.UTC(S.year,S.month,0)).getUTCDate();
          const full=worldOfferPropertyService(S,buyer.id,p.id,plant.id,'PRD-S12',worldPropertyCapacity(S,p,plant)/days,100);
          const unpaid=worldOfferPropertyService(S,buyer.id,p.id,plant.id,'PRD-S14',1,Number.MAX_SAFE_INTEGER);
          worldOfferPropertyService(S,buyer.id,p.id,plant.id,'PRD-S14',1,100);
          const cancelled=worldOfferPropertyService(S,buyer.id,p.id,plant.id,'PRD-S14',1,100);
          worldActOnPropertyService(S,buyer.id,cancelled.id,'cancel');
          window.extraIds=[full.id,unpaid.id];
          VIEW_FIRM=p.id;render();
          return true;
        }""")
        page.locator("#world-domestic > summary").click()
        accept = page.locator('form[data-world-domestic="property-accept"]')
        accept.filter(has_text="不動産賃貸サービス").last.get_by_role("button", name="申込を承諾").click()
        accept.filter(has_text="宿泊観光サービス").last.get_by_role("button", name="申込を承諾").click()
        assert page.evaluate("""() => {
          const p=company(window.providerId),[full,unpaid]=window.extraIds;
          let overCapacity=false;
          try{worldActOnPropertyService(S,p.id,full,'accept');}
          catch(e){overCapacity=e.message.includes('容量');}
          worldActOnPropertyService(S,p.id,unpaid,'accept');
          const restored=parsePayload(savePayload(S));
          return overCapacity&&restored.worldExpansion.propertyContracts.filter(t=>t.status==='ACCEPTED').length===3
            &&!worldServiceActivity(restored,'PRD-S14').length;
        }""")
        assert page.evaluate("""async () => {
          await runMonth();
          if(LAST_MONTH_DIAGNOSTIC)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC));
          const w=S.worldExpansion,provider=company(window.providerId),buyer=company(S.playerId);
          const [rent,stay,overCapacity,unpaid,unaccepted,cancelled]=w.propertyContracts;
          const receipts=rent.status==='FULFILLED'&&rent.amount===23000&&stay.status==='FULFILLED'&&stay.amount===3600
            &&overCapacity.status==='EXPIRED'&&unpaid.status==='UNFULFILLED'&&unaccepted.status==='EXPIRED'
            &&cancelled.status==='CANCELLED'&&[overCapacity,unpaid,unaccepted,cancelled].every(t=>!t.amount&&t.journal===null);
          const posted=[rent,stay].every(t=>buyer.journals.find(j=>j.id===t.journal)?.cr[0][1]===t.amount
            &&provider.journals.find(j=>j.id===t.journal+1)?.dr[0][1]===t.amount);
          const conso=consolidate(S);
          const integrated=!check(S).length&&!conso.errors.length&&conso.cf.reconciled
            &&conso.pl.intercompanySales>=26600&&conso.spot.checkDifference===0;
          const bad=structuredClone(S);
          bad.worldExpansion.propertyContracts[0].quantity++;
          let rejects=false;try{parsePayload(savePayload(bad));}catch(e){rejects=e.message.includes('精算仕訳');}
          const noInventory=S.firms.every(f=>!f.stock['PRD-S12']&&!f.goods['PRD-S12']&&!f.stock['PRD-S14']&&!f.goods['PRD-S14']);
          return receipts&&posted&&integrated&&rejects&&noInventory&&SAVE_INDEX.backend==='IndexedDB';
        }""")
        page.reload()
        page.wait_for_function("STORAGE_READY && S?.worldExpansion?.propertyContracts?.length === 6")
        assert page.evaluate("""() => worldServiceActivity(S,'PRD-S12')[0]?.amount===23000
          &&worldServiceActivity(S,'PRD-S14')[0]?.amount===3600&&check(S).length===0""")
        assert not errors, errors
        browser.close()
    print("PASS S12/S14 offers, shared capacity, monthly cash settlement, consolidation and IndexedDB restore")


def main():
    with ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=ROOT)) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        try:
            run(f"http://127.0.0.1:{server.server_port}/index.html")
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
