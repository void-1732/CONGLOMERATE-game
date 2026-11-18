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


def check_market_entry(page):
    page.evaluate("""() => {
        S=newGame({era:1960,country:'JP',difficulty:'easy',history:'historical',name:'海外販路の検証'});
        VIEW_FIRM=S.playerId;PAGE='distribution';render();
    }""")
    page.locator("#marketEntryTarget").select_option("US")
    assert page.get_by_role("rowheader", name="現地企業の買収").is_visible()
    assert page.get_by_role("rowheader", name="合弁企業").is_visible()
    page.locator("#marketEntryMode").select_option("direct")
    page.get_by_role("button", name="参入・再開").click()
    assert page.evaluate("current().marketPresence.join('/')") == "JP/US"
    assert page.evaluate("exportChannel(current(),'US').channel") == "direct"
    agent = page.evaluate("S.firms.find(f=>f.country==='US').id")
    page.locator("#marketEntryMode").select_option("dealer")
    page.locator("#marketEntryAgent").select_option(agent)
    page.get_by_role("button", name="参入・再開").click()
    assert page.evaluate("exportChannel(current(),'US').dealerId") == agent
    capacity = page.evaluate("exportChannel(current(),'US').capacity")
    page.get_by_role("button", name="販売枠を半減").click()
    assert page.evaluate("exportChannel(current(),'US').capacity") == capacity // 2
    sent = page.evaluate("""() => {
        const f=current(),m=f.models[0];
        post(f,{goods:10000},{cash:10000},'販売撤退時の輸送在庫','operating',S);
        f.goods[m.id].q+=2;f.goods[m.id].v+=10000;
        exportShipment(S,f,m.id,2,m.priceBase,'US',[]);
        return f.distribution.outbound[0].id;
    }""")
    page.get_by_role("button", name="市場から撤退").click()
    assert page.evaluate("current().marketPresence.includes('US')") is False
    assert page.evaluate("current().distribution.outbound[0].id") == sent
    page.locator('#channel_UK').select_option('distributor')
    page.get_by_role("button", name="販売網の変更を保存").click()
    assert page.evaluate("current().marketPresence.includes('US')") is False
    page.locator('[data-action="createMarketSalesAgencyV043"]').click()
    result = page.evaluate("""() => {
        const f=current(),child=company(f.distribution.salesCorporations.US,S);
        const test=structuredClone(S),buyer=company(f.id,test);
        const target=test.firms.filter(x=>x.country==='DE'&&x.owners.some(o=>o.id==='PUBLIC'))
            .sort((a,b)=>maValuation(test,a).reference-maValuation(test,b).reference)[0];
        const amount=acc(buyer,'cash'),month=ym(test.year,test.month);
        (test.logisticsV041.restrictions??={})['JP/DE']={end:month+1};
        let blocked=false;
        try{executeMADeal(test,buyer.id,target.id,60,2.5);}catch(error){blocked=error.message.includes('規制')&&acc(buyer,'cash')===amount;}
        delete test.logisticsV041.restrictions['JP/DE'];
        const acquired=executeMADeal(test,buyer.id,target.id,60,2.5);
        return {subsidiary:child.country,controlled:controller(S,child.id),active:f.marketPresence.includes('US'),
            blocked,acquired:acquired.control,errors:[...check(test),...consolidate(test).errors]};
    }""")
    assert result == {"subsidiary": "US", "controlled": True, "active": True, "blocked": True, "acquired": True, "errors": []}, result


def check_joint_company(page):
    partner = page.evaluate("""() => {
        S=newGame({era:1960,country:'JP',difficulty:'easy',history:'historical',name:'合弁投資の検証'});
        VIEW_FIRM=S.playerId;PAGE='group';render();
        return S.firms.filter(f=>f.country==='US').sort((a,b)=>acc(b,'cash')-acc(a,'cash'))[0].id;
    }""")
    for stake in (50, 60):
        page.locator('#jointNameV043').fill(f'北米合弁 {stake}')
        page.locator('#jointPartnerV043').select_option(partner)
        page.locator('#jointStakeV043').select_option(str(stake))
        page.locator('#jointCapitalV043').fill('1800000')
        page.get_by_role("button", name="合弁企業を設立").click()
    result = page.evaluate("""async () => {
        const children=S.firms.filter(f=>f.jointCompanyV043),root=current();
        const details=children.map(f=>({
            ratio:f.owners.find(o=>o.id===root.id).econ,
            controlled:controller(S,f.id),
            capital:-acc(f,'capital'),
            account:f.journals.filter(j=>j.text.startsWith('合弁創業資本')).reduce((n,j)=>n+j.amount,0),
            links:S.equityLinks.filter(x=>x.childId===f.id).length
        }));
        const restored=parsePayload(savePayload(S));
        S=restored;saveAuto=async()=>true;
        const before=S.monthCommitted,scope=consolidate(S).members.length;
        await runMonth();
        const reports=consolidate(S);
        return {details,scope,completed:S.monthCommitted===before+1,cf:reports.cf.reconciled,
            diagnostic:LAST_MONTH_DIAGNOSTIC?.message,errors:[...check(S),...reports.errors]};
    }""")
    assert result["scope"] == 2 and result["completed"] and result["cf"] and not result["errors"], result
    assert [row["ratio"] for row in result["details"]] == [0.5, 0.6], result
    assert [row["controlled"] for row in result["details"]] == [False, True], result
    assert all(row["links"] == 2 and row["capital"] == row["account"] > 0 for row in result["details"]), result


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
        check_market_entry(page)
        check_joint_company(page)
        assert not errors, errors
        browser.close()
    print("PASS STEP 7: foreign factories, agents, subsidiaries, joint ventures, acquisitions, exits, and saves")
