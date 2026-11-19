"""STEP 9 / step 04: emerging-market real shipments, customs and FX books.

International import/export must use existing finite physical NPC supply,
route bookings, tariffs and receivable/payable ledgers. No new local firms.
"""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

HTML = Path(__file__).resolve().parents[1] / "index.html"
MARKETS = {"CN": ("CNY",1980), "IN": ("INR",1950), "BR": ("BRL",1920)}


def closed_trade_and_unlicensed_investment(page):
    result=page.evaluate("""() => {
        const output={};
        for(const [code,profile] of Object.entries(EMERGING_MARKET_PROFILES_V047)){
            const year=profile.opening.export-1;
            const s=newGame({era:year,country:'JP',difficulty:'easy',
                history:'historical',name:'貿易開始前テスト',marketExpansionV047:true});
            const f=company(s.playerId,s),original=acc(f,'cash');
            const quote=internationalQuoteV041(s,code,'JP','bulk',100);
            const vehicle=internationalQuoteV041(s,'JP',code,'vehicle',100);
            let rejected=false,denied=false;
            try{changeForeignMarketV043(s,f,code,'enter','direct');}
            catch(e){rejected=true;}
            try{changeForeignMarketV043(s,f,code,'enter','factory');}
            catch(e){denied=true;}
            output[code]={year,quote:!!quote,vehicle:!!vehicle,rejected,denied,
                sameCash:acc(f,'cash')===original,
                legalMarket:marketInvestmentAllowedV043(s,f,code),
                errors:check(s)};
        }
        return output;
    }""")
    for code,item in result.items():
        assert not item["quote"] and not item["vehicle"],(code,item)
        assert item["rejected"] and item["denied"] and item["sameCash"],(code,item)
        assert not item["legalMarket"] and not item["errors"],(code,item)


def import_materials(page, code, currency):
    outcome=page.evaluate("""({code,currency}) => {
        const s=newGame({era:2010,country:'JP',difficulty:'easy',
            history:'historical',name:'国際輸入と実物決済',marketExpansionV047:true});
        const buyer=company(s.playerId,s),type='steel',source=npcIdV033(code,type);
        for(const material of SUPPLY_TYPES)
            buyer.supply.contracts[material].autoOrder=material===type;
        Object.assign(buyer.supply.contracts[type],{
            supplierId:source,backupId:'',autoManage:false,longTermV036:null});
        const opening=buyer.stock[type];
        post(buyer,{otherExpense:opening.v},{materials:opening.v},
            '輸入市場検証の材料払出','operating',s);
        buyer.stock[type]={q:0,v:0};
        const market=npcMarketV033(s,code,type);
        const before={stock:market.stock,produced:market.producedTotal,dispatched:market.dispatchedTotal};
        procureNetwork(s,[]);
        const shipment=buyer.supply.inbound.find(x=>x.supplierId===source);
        if(!shipment)return {error:'No physical shipment',before,attempt:buyer.supply.lastAttempt[type]};
        const reserved=structuredClone(shipment),route=shipment.internationalV041.routeId;
        const physical={stock:market.stock,produced:market.producedTotal,
            dispatched:market.dispatchedTotal};
        const sent=before.stock-market.stock;
        const backup=parsePayload(savePayload(s));
        const f=company(buyer.id,backup);
        while(ym(backup.year,backup.month)<reserved.due)nextMonthDate(backup);
        const inTransit=f.supply.inbound.find(x=>x.id===reserved.id);
        const firstValue=acc(f,'materials'),historyStart=f.supply.history.length;
        deliverMaterials(backup,f,[]);
        const invoice=f.payables.find(p=>p.currency===currency);
        const customsPayable=f.payables.find(p=>p.note==='国際調達／輸入関税・迂回輸送費');
        const stock=f.stock[type];
        const debit=acc(f,'materials')-firstValue;
        const importReceipt=f.supply.history.slice(historyStart).find(r=>
            r.origin===code&&r.routeId===route&&r.qty===reserved.qty);
        const importJournal=f.journals.find(j=>j.text.startsWith('調達品受領：鋼材')&&
            j.amount===debit);
        const customs=inTransit.internationalV041;
        const beforeSettle=invoice?structuredClone(invoice):null;
        // Cover the actual foreign invoice in its specified currency.
        const purchased=invoice?exchangeForeignV042(backup,f,currency,invoice.foreignMinor,'buy'):0;
        if(invoice){
            backup.world[code].fx*=1.09;
            nextMonthDate(backup);
            settleScheduled(f,backup);
        }
        const openInvoice=f.payables.find(p=>p.currency===currency);
        const settled=f.journals.filter(j=>j.text.startsWith('外貨建て買掛金決済 '+currency));
        const financial=consolidate(backup);
        return {code,currency,route,shipment:reserved,
            before,physical,sent,qty:reserved.qty,
            importBook:debit,stock,openingInventory:opening.v,
            invoice:beforeSettle,customsPayable:customsPayable?structuredClone(customsPayable):null,
            customs,importReceipt,importJournal:importJournal?.amount,
            purchased,payments:settled.length,remaining:openInvoice?.amount??0,
            errors:check(backup),financialErrors:financial.errors,
            keys:Object.keys(backup.world),wallet:f.foreignFinanceV042?.wallets?.[currency]};
    }""",{"code":code,"currency":currency})
    assert "error" not in outcome, outcome
    assert outcome["route"] == f"{code}/JP/sea", outcome
    assert outcome["qty"] > 0 and outcome["sent"] == outcome["qty"], outcome
    assert outcome["physical"]["stock"]+outcome["physical"]["dispatched"] == outcome["physical"]["produced"], outcome
    assert outcome["physical"]["dispatched"]-outcome["before"]["dispatched"] == outcome["qty"], outcome
    assert outcome["customs"]["clearedMonth"] > outcome["customs"]["dispatched"], outcome
    assert outcome["customs"]["dutyBase"] > 0, outcome
    assert outcome["importReceipt"]["qty"] == outcome["qty"], outcome
    assert outcome["importReceipt"]["routeId"] == outcome["route"], outcome
    assert outcome["importBook"] == outcome["importJournal"], outcome
    assert outcome["customsPayable"]["amount"] > 0, outcome
    assert outcome["invoice"]["amount"] + outcome["customsPayable"]["amount"] == outcome["importBook"], outcome
    assert outcome["customsPayable"].get("currency") is None, outcome
    assert outcome["stock"]["q"] >= outcome["qty"] and outcome["stock"]["v"] >= outcome["importBook"], outcome
    assert outcome["invoice"]["currency"] == currency and outcome["invoice"]["foreignMinor"] > 0, outcome
    assert outcome["purchased"] > 0 and outcome["payments"] > 0, outcome
    assert outcome["remaining"] == 0, outcome
    assert len(outcome["keys"]) == 8 and not outcome["errors"] and not outcome["financialErrors"], outcome


def direct_vehicle_export(page, code, currency):
    outcome=page.evaluate("""({code,currency}) => {
        const s=newGame({era:2010,country:'JP',difficulty:'easy',
            history:'historical',name:'新市場への直接輸出と外貨売掛',marketExpansionV047:true});
        const f=company(s.playerId,s),m=f.models[0],events=[];
        let blockedIndirect=false;
        try{changeForeignMarketV043(s,f,code,'enter','dealer');}
        catch(e){blockedIndirect=true;}
        const noPresence=marketVehicleContendersV031(s,code).length===0;
        const noCash=acc(f,'cash');
        changeForeignMarketV043(s,f,code,'enter','direct');
        const enterCost=noCash-acc(f,'cash');
        const contenders=marketVehicleContendersV031(s,code).length;
        foreignAccountsV042(f).retainReceipts=true;
        post(f,{goods:6000},{cash:6000},'輸出用の実在完成車を保管','operating',s);
        f.goods[m.id].q+=3;f.goods[m.id].v+=6000;
        const before=acc(f,'goods'),firstCash=acc(f,'cash');
        exportShipment(s,f,m.id,3,m.priceBase,code,events,'mass');
        const sent=f.distribution.outbound.find(x=>x.country===code);
        if(!sent)return {error:'No vehicle shipment',code,contenders,events};
        const transit=acc(f,'goodsTransit'),qty=sent.qty;
        const available=internationalRouteRoomV041(s,internationalRoutesV041(s,'JP',code)[0],'vehicle');
        const saved=parsePayload(savePayload(s)),seller=company(f.id,saved);
        const savedShipment=seller.distribution.outbound.find(x=>x.id===sent.id);
        while(ym(saved.year,saved.month)<sent.due)nextMonthDate(saved);
        seller._salesNow=0;seller._unitsNow=0;seller.marketThisMonth={};
        saved.world[code].demand=Math.max(saved.world[code].demand,200);
        deliverExports(saved,[]);
        const income=seller.receivables.find(x=>x.currency===currency);
        const wallet=seller.foreignFinanceV042?.wallets?.[currency];
        const customs=savedShipment.internationalV041;
        const exportRevenue=seller.journals.filter(x=>x.text.startsWith('輸出品到着・顧客引渡し：'+NAMES[code]));
        const shipmentLeft=seller.distribution.outbound.filter(x=>x.country===code);
        const after=consolidate(saved);
        return {code,currency,blockedIndirect,noPresence,contenders,enterCost,
            qty,available,transit,bookSent:before-acc(f,'goods'),sameGoodsValue:transit===before-acc(f,'goods'),
            finished:acc(seller,'goodsTransit'),shipmentLeft:shipmentLeft.length,
            income:income?structuredClone(income):null,wallet:wallet?structuredClone(wallet):null,
            customs,exportRevenue:exportRevenue.length,cash:acc(seller,'cash'),
            firstCash,marketUse:saved.marketDeliveryV031.markets[code]?.units,
            errors:check(saved),financeErrors:after.errors,
            saved:parsePayload(savePayload(saved)).marketExpansionV047};
    }""",{"code":code,"currency":currency})
    assert "error" not in outcome, outcome
    assert outcome["blockedIndirect"] and outcome["noPresence"] and outcome["contenders"] > 0, outcome
    assert outcome["enterCost"] > 0 and outcome["qty"] == 3, outcome
    assert outcome["transit"] > 0 and outcome["sameGoodsValue"], outcome
    assert outcome["customs"]["dispatched"] < outcome["customs"]["clearedMonth"], outcome
    assert outcome["customs"]["dutyBase"] > 0, outcome
    assert outcome["income"]["currency"] == currency and outcome["income"]["foreignMinor"] > 0, outcome
    assert outcome["wallet"]["quantity"] > 0 and outcome["wallet"]["bookValue"] > 0, outcome
    assert outcome["exportRevenue"] == 1 and outcome["marketUse"] == 3, outcome
    assert outcome["finished"] == 0 and outcome["shipmentLeft"] == 0, outcome
    assert not outcome["errors"] and not outcome["financeErrors"] and outcome["saved"]["enabled"],outcome


def direct_export_distributor_ui(page):
    # An established direct-export corridor must survive edits to the original
    # five-country distribution settings, but must not become a dealer route.
    page.evaluate("""() => {
        S=newGame({era:2010,country:'JP',difficulty:'easy',
            history:'historical',name:'輸出開設後の旧市場販路維持',
            marketExpansionV047:true});
        VIEW_FIRM=S.playerId;PAGE='distribution';render();
    }""")
    page.locator("#marketEntryTarget").select_option("BR")
    page.locator("#marketEntryMode").select_option("direct")
    page.get_by_role("button",name="参入・再開").click()
    before=page.evaluate("""() => {
        const f=current();
        return {capacity:f.distribution.contracts.US.capacity,
            br:structuredClone(f.foreignMarketsV043.BR),
            ledger:acc(f,'cash')};
    }""")
    page.locator("#capacity_US").fill(str(before["capacity"]+1))
    page.locator('[data-action="saveDistribution"]').click()
    after=page.evaluate("""() => {
        const f=current();
        return {us:f.distribution.contracts.US.capacity,
            br:f.foreignMarketsV043.BR,
            present:f.marketPresence.includes('BR'),
            errors:check(S),saved:parsePayload(savePayload(S)).marketExpansionV047};
    }""")
    assert after["us"] == before["capacity"]+1,after
    assert after["br"] == before["br"] and after["present"],after
    assert after["saved"]["enabled"] and not after["errors"],after


if __name__ == "__main__":
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"])
        page=browser.new_page(offline=True)
        page.set_content(HTML.read_text(encoding="utf-8"),wait_until="domcontentloaded")
        closed_trade_and_unlicensed_investment(page)
        for code,(currency,year) in MARKETS.items():
            import_materials(page,code,currency)
            direct_vehicle_export(page,code,currency)
        page.goto("about:blank")
        page.set_content(HTML.read_text(encoding="utf-8"),wait_until="domcontentloaded")
        direct_export_distributor_ui(page)
        browser.close()
    print("PASS STEP 9 trade: 3 emerging markets, real imports, vehicle exports, customs, FX payable/receivable")
