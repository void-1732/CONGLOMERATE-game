"""Vehicle discontinuation: sell-through, immediate stop, exports, ledgers, AI, UI and saves."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")

def start(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("dialog", lambda dialog: dialog.accept())
    page.set_content(HTML, wait_until="domcontentloaded")
    page.evaluate("""() => {
        saveAuto=async()=>true;
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'車種廃止試験'});
        VIEW_FIRM=S.playerId; PAGE='product'; PRODUCT_VIEW='planning'; render();
    }""")
    assert page.locator("#modelDiscontinuationPanel").count() == 1
    assert page.locator('#modelDiscontinuationPanel [data-action="discontinueModel"]').count() >= 1
    return page, errors

def assert_books(page):
    state = page.evaluate("""() => ({errs:check(S),group:consolidate(S).errors,
        cf:consolidate(S).cf.reconciled})""")
    assert not state["errs"] and not state["group"] and state["cf"], state

def add_stock(page, quantity, cost):
    return page.evaluate("""([qty,cost]) => {
        const f=current(),m=f.models.find(x=>x.status==='active');
        if(!m)throw Error('No active model');
        post(f,{goods:cost},{cash:cost},'廃止テスト用の完成車追加','operating',S);
        f.goods[m.id].q+=qty;f.goods[m.id].v+=cost;
        render();return m.id;
    }""", [quantity,cost])

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
            args=["--no-sandbox"],
        )
        page, errors = start(browser)
        mid = add_stock(page, 12, 1200)
        before = page.evaluate("""id => ({q:current().goods[id].q,v:current().goods[id].v,
            goods:acc(current(),'goods'),cash:acc(current(),'cash')})""",mid)
        page.locator(f"#discontinueMode_{mid}").select_option("sellthrough")
        page.locator(f'[data-action="discontinueModel"][data-model-id="{mid}"]').click()
        state=page.evaluate("""id => {
            const f=current(),m=f.models.find(x=>x.id===id);
            return {status:m.status,mode:m.discontinuation.mode,q:f.goods[id].q,v:f.goods[id].v,
                plan:f.plans[id],goods:acc(f,'goods'),cash:acc(f,'cash'),
                candidate:marketVehicleContendersV031(S,f.country).some(x=>x.f.id===f.id&&x.m.id===id)};
        }""",mid)
        assert state["status"]=="legacy" and state["mode"]=="sellthrough" and state["plan"]==0, state
        assert state["q"]==before["q"] and state["v"]==before["v"], state
        assert state["goods"]==before["goods"] and state["cash"]==before["cash"], state
        assert state["candidate"], state
        assert_books(page)
        assert page.evaluate("""id => {
            const f=current();f.delegate.mode='delegated';f.delegate.productionAuto=true;
            planAI(f,S);return f.plans[id];
        }""",mid)==0
        page.evaluate("""id => {
            const f=current(),qty=f.goods[id].q;
            const {cost,batches}=takeFinishedGoods(f,id,qty);
            postFinishedCost(S,f,cost,'goods','廃止テスト：在庫販売原価',batches);
            modelLifecycleMonth(S,f,[]);
        }""",mid)
        assert page.evaluate("id=>current().models.find(m=>m.id===id).status",mid)=="retired"
        assert_books(page)
        raw=page.evaluate("savePayload(S)")
        assert page.evaluate("raw=>restore(raw)",raw)
        assert page.evaluate("id=>current().models.find(m=>m.id===id).discontinuation.mode",mid)=="sellthrough"
        assert_books(page)
        assert not errors,errors
        page.close()

        page,errors=start(browser)
        mid=add_stock(page,18,1800)
        page.evaluate("""id => {
            const f=current(),m=f.models.find(x=>x.id===id);
            exportShipment(S,f,id,3,m.priceBase,'US',[]);
        }""",mid)
        assert_books(page)
        blocked=page.evaluate("""id => {
            const f=current();
            f.projects.push({status:'developing',fromModel:id,kind:'facelift',left:2});
            let reason='';try{discontinueVehicleModel(S,f,id,'immediate');}
            catch(e){reason=e.message;}f.projects.pop();return reason;
        }""",mid)
        assert "開発" in blocked,blocked
        previous=page.evaluate("""id => {
            const f=current(),ship=modelPendingShipments(f,id);
            return {onHand:f.goods[id].v,transitBook:ship.reduce((n,x)=>n+x.bookCost,0),
                goods:acc(f,'goods'),transit:acc(f,'goodsTransit'),
                sales:financials(f).revenue,profit:financials(f).profit,cash:acc(f,'cash')};
        }""",mid)
        page.evaluate("()=>{PAGE='product';PRODUCT_VIEW='planning';render()}")
        page.locator(f"#discontinueMode_{mid}").select_option("immediate")
        page.locator(f'[data-action="discontinueModel"][data-model-id="{mid}"]').click()
        state=page.evaluate("""id => {
            const f=current(),m=f.models.find(x=>x.id===id);
            return {status:m.status,plan:f.plans[id],q:f.goods[id].q,v:f.goods[id].v,
                shipment:modelPendingShipments(f,id).length,
                goods:acc(f,'goods'),transit:acc(f,'goodsTransit'),
                sales:financials(f).revenue,profit:financials(f).profit,cash:acc(f,'cash'),
                disposal:m.discontinuation.writtenOffBookValue,
                candidate:marketVehicleContendersV031(S,f.country).some(x=>x.f.id===f.id&&x.m.id===id)};
        }""",mid)
        loss=previous["onHand"]+previous["transitBook"]
        assert state["status"]=="retired" and state["plan"]==0 and state["q"]==0 and state["v"]==0,state
        assert state["shipment"]==0 and not state["candidate"],state
        assert state["goods"]==previous["goods"]-previous["onHand"],state
        assert state["transit"]==previous["transit"]-previous["transitBook"],state
        assert state["profit"]==previous["profit"]-loss and state["disposal"]==loss,state
        assert state["sales"]==previous["sales"] and state["cash"]==previous["cash"],state
        assert_books(page)
        raw=page.evaluate("savePayload(S)")
        assert page.evaluate("raw=>restore(raw)",raw)
        assert page.evaluate("id=>current().models.find(m=>m.id===id).status",mid)=="retired"
        assert_books(page)
        page.evaluate("async()=>await runMonth()")
        assert page.evaluate("id=>current().plans[id]",mid)==0
        assert_books(page)
        assert not errors,errors
        page.close()
        browser.close()

if __name__=="__main__":
    run()
    print("PASS: vehicle discontinuation UI, exports, AI, ledger, inventory, save and month")
