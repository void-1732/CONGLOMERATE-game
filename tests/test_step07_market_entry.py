"""Overseas manufacturing, local market entry and legal-entity accounting."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"


def check_local_manufacturing(page):
    result = page.evaluate("""() => {
        S=newGame({era:1960,country:'JP',difficulty:'easy',history:'historical',name:'現地工場の検証'});
        VIEW_FIRM=S.playerId;
        const f=current(),model=f.models[0],country='US',home=f.plants[0];
        S.logisticsV041={restrictions:{'JP/DE':{end:ym(S.year,S.month)+3}}};
        const opening=acc(f,'cash');
        let restriction=false;
        try{beginFactoryConstruction(S,f,'small','integrated','建設規制の試験','DE-HAM');}
        catch(error){restriction=error.message.includes('投資規制')&&acc(f,'cash')===opening;}
        const factory=beginFactoryConstruction(S,f,'small','integrated','北米組立','US-LAX');
        factory.construction=null;
        home.paused=true;
        syncPlant(f);
        f.plans[model.id]=3;
        const req=materialRequirement(model.design,f);
        laborAndPlant(S,[],'auto');
        const before=f._produced;
        for(const [type,ratio] of Object.entries(req)){
            if(!ratio||!RAW_TYPES_V032.includes(type))continue;
            const quantity=Math.ceil(3*ratio),bin=f.stock[type];
            if(bin.q<quantity){
                const extra=quantity-bin.q,value=Math.round(extra*10000);
                post(f,{materials:value},{cash:value},'現地製造へ送る追加購入','operating',S);
                bin.q+=extra;bin.v+=value;
            }
            dispatchRawShipmentV038(S,f,'warehouse',factory.id,type,quantity);
        }
        for(let i=0;i<2;i++)nextMonthDate(S);
        deliverRawShipmentsV038(S,[]);
        S.world.US.wage=S.world.JP.wage*1.3;
        const wage=sitePayrollFactor(f,S);
        laborAndPlant(S,[],'auto');
        const produced=f._produced,local=finishedAtCountryV043(f,model.id,country);
        const localBook=ensureWarehouseV038(f).finishedAtPlant[factory.id][model.id].v;
        const modelBin=f.goods[model.id];
        const homeCost=12000;
        post(f,{goods:homeCost},{cash:homeCost},'比較試験用に国内完成車を取得','operating',S);
        modelBin.q+=3;modelBin.v+=homeCost;
        const forecast=structuredClone(S),seller=company(f.id,forecast);
        forecast.logisticsV041.restrictions['JP/US']={end:ym(S.year,S.month)+1};
        const restricted=salesRoomV031(forecast,{f:seller,m:seller.models[0]},country,100);
        bookModelSalesV031(S,{f,m:model},country,'mass',local+2,[]);
        const sent=f.distribution.outbound[0],tax=corporateTaxRateV043(S,f);
        const received=f.marketThisMonth[country]?.units??0;
        const localDebit=f.journals.filter(j=>j.text.startsWith('現地工場からの販売：')).length;
        const customerInvoice=f.receivables.find(x=>x.note==='商品売上'&&x.currency==='USD');
        const after=parsePayload(savePayload(S));
        return {restriction,before,produced,local,restricted,received,wage,localBook,tax,localDebit,invoice:customerInvoice?.foreignMinor,
            sent:sent.qty,sentCost:sent.bookCost,remaining:f.goods[model.id],localLeft:finishedAtCountryV043(f,model.id,country),
            errors:[...check(after),...consolidate(after).errors]};
    }""")
    assert result["restriction"] and result["before"] == 0 < result["produced"], result
    assert result["local"] == result["produced"] == result["restricted"] == result["received"], result
    assert result["localDebit"] == 1 and result["localLeft"] == 0 and result["localBook"] > 0, result
    assert result["sent"] == 2 and result["sentCost"] == 8000 and result["remaining"] == {"q": 1, "v": 4000}, result
    assert result["wage"] > 1 and result["tax"] == 0.18 and result["invoice"] > 0 and not result["errors"], result


if __name__ == "__main__":
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_page(offline=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(HTML.read_text(encoding="utf-8"), wait_until="domcontentloaded")
        check_local_manufacturing(page)
        assert not errors, errors
        browser.close()
    print("PASS STEP 7: foreign factory custody, local sales, wage and tax, FX and saves")
