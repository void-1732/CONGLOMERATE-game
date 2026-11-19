"""STEP 9 / step 04: real 8-market trade and legacy-5-market endurance.

No fake stock or new money: the actual monthly engine must reconcile all cargo,
import invoices, FX wallets, consolidated cash flow and historical save formats.
"""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

HTML=Path(__file__).resolve().parents[1]/"index.html"


def trade_endurance(page):
    result=page.evaluate("""async () => {
        const s=newGame({era:2010,country:'JP',difficulty:'normal',
            history:'historical',name:'8市場実貿易長期監査',marketExpansionV047:true});
        const f=company(s.playerId,s),events=[];
        for(const country of ['CN','IN','BR'])
            changeForeignMarketV043(s,f,country,'enter','direct');
        for(const type of SUPPLY_TYPES)
            f.supply.contracts[type].autoOrder=type==='steel';
        f.supply.contracts.steel.supplierId=npcIdV033('CN','steel');
        f.supply.contracts.steel.backupId='';
        f.supply.contracts.steel.autoManage=false;
        f.supply.contracts.steel.longTermV036=null;
        // Actual overseas stocks and inbound cargo, not synthetic supply.
        procureNetwork(s,events);
        const initiated=f.supply.inbound.filter(x=>x.origin==='CN').length;
        const old=s.world.US.demand,baseline=Object.fromEntries(
            LEGACY_MARKETS_V047.map(c=>[c,s.world[c].referencePopulation]));
        S=s;VIEW_FIRM=f.id;saveAuto=async()=>true;render=()=>{};
        const monthStart=ym(S.year,S.month);
        let actualImports=0,actualExports=0,settlementMonths=0;
        for(let i=0;i<12;i++){
            const prior=S.monthCommitted;
            await runMonth();
            if(S.monthCommitted!==prior+1)
                return {failed:i,stage:'commit',message:LAST_MONTH_DIAGNOSTIC?.message};
            const who=company(f.id,S),errors=check(S),fin=consolidate(S);
            if(errors.length||fin.errors.length||!fin.cf.reconciled)
                return {failed:i,stage:'accounting',errors,financial:fin.errors,reconciled:fin.cf.reconciled};
            for(const code of EMERGING_MARKETS_V047)
                for(const m of Object.values(S.npcSupplyV033.markets[code]))
                    if(m.stock+m.dispatchedTotal!==m.producedTotal)
                        return {failed:i,stage:'physical '+code};
            if(S.firms.some(x=>EMERGING_MARKETS_V047.includes(x.country)))
                return {failed:i,stage:'premature company'};
            actualImports=who.supply.history.filter(x=>x.origin==='CN').reduce((v,x)=>v+x.qty,0);
            actualExports=who.distribution.history.filter(x=>EMERGING_MARKETS_V047.includes(x.country))
                .reduce((v,x)=>v+x.qty,0);
            settlementMonths+=who.journals.some(x=>x.text.startsWith('外貨建て買掛金決済 CNY'))?1:0;
            if(i===5){
                const restored=parsePayload(savePayload(S));
                if(check(restored).length||restored.marketExpansionV047.enabled!==true)
                    return {failed:i,stage:'save'};
                S=restored;
            }
        }
        const who=company(f.id,S);
        return {months:ym(S.year,S.month)-monthStart,
            initiated,actualImports,actualExports,settlementMonths,
            allKeys:Object.keys(S.world),old,referencePreserved:
              LEGACY_MARKETS_V047.every(c=>S.world[c].referencePopulation===baseline[c]),
            importCurrencies:who.payables.filter(x=>x.currency).map(x=>x.currency),
            errors:check(S),financialErrors:consolidate(S).errors};
    }""")
    assert result.get("months")==12,result
    assert result["initiated"]>0,result
    assert result["actualImports"]>0,result
    assert result["allKeys"]==["JP","US","UK","DE","FR","CN","IN","BR"],result
    assert result["referencePreserved"],result
    assert not result["errors"] and not result["financialErrors"],result


def delayed_customs_and_currency(page):
    result=page.evaluate("""()=>{
        const s=newGame({era:2010,country:'JP',difficulty:'easy',
            history:'historical',name:'新市場関税分離と物流障害',marketExpansionV047:true});
        const f=company(s.playerId,s),type='steel',origin='BR';
        for(const material of SUPPLY_TYPES)
            f.supply.contracts[material].autoOrder=material===type;
        const c=f.supply.contracts[type];
        c.supplierId=npcIdV033(origin,type);c.backupId='';c.autoManage=false;c.longTermV036=null;
        const bin=f.stock[type];
        post(f,{otherExpense:bin.v},{materials:bin.v},'材料原価監査の前払出','operating',s);
        f.stock[type]={q:0,v:0};
        procureNetwork(s,[]);
        const shipment=f.supply.inbound.find(x=>x.origin===origin);
        if(!shipment)return {reason:'no physical shipment'};
        const initial=structuredClone(shipment),originalDue=shipment.due;
        const first=internationalRoutesV041(s,origin,'JP')[0];
        s.logisticsV041.disruptions[first.id]={end:originalDue+8,capacityFactor:0};
        while(ym(s.year,s.month)<originalDue)nextMonthDate(s);
        const events=[];
        const pre=f.stock[type].q;
        deliverMaterials(s,f,events);
        const moved=f.supply.inbound.find(x=>x.id===initial.id);
        if(!moved)return {reason:'shipment unexpectedly delivered despite disrupted route'};
        const alternate=moved.internationalV041.routeId;
        const noReceipt=f.stock[type].q===pre;
        const rerouteCost=moved.internationalV041.rerouteBase;
        while(ym(s.year,s.month)<moved.due)nextMonthDate(s);
        deliverMaterials(s,f,events);
        const landed=acc(f,'materials');
        const foreign=f.payables.find(x=>x.currency==='BRL');
        const local=f.payables.find(x=>x.note==='国際調達／輸入関税・迂回輸送費');
        const journal=f.journals.filter(x=>x.text.startsWith('調達品受領：鋼材')).at(-1);
        const snapshot=parsePayload(savePayload(s));
        return {initial:initial.internationalV041.routeId,alternate,
            rerouteCost,noReceipt,now:f.stock[type].q,qty:initial.qty,
            foreign:foreign?.amount,foreignCurrency:foreign?.currency,
            local:local?.amount,localCurrency:local?.currency??null,
            landed,journal:journal?.amount,events,
            cleared:!f.supply.inbound.some(x=>x.id===initial.id),
            errors:check(s),restored:check(snapshot)};
    }""")
    assert "reason" not in result,result
    assert result["initial"]=="BR/JP/sea" and result["alternate"]=="BR/JP/alternateSea",result
    assert result["noReceipt"] and result["rerouteCost"]>0 and result["cleared"],result
    assert result["now"]>=result["qty"]>0,result
    assert result["foreignCurrency"]=="BRL" and result["localCurrency"] is None,result
    assert result["foreign"]+result["local"]==result["journal"]==result["landed"],result
    assert not result["errors"] and not result["restored"],result


if __name__=="__main__":
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"])
        page=browser.new_page(offline=True)
        page.set_content(HTML.read_text(encoding="utf-8"),wait_until="domcontentloaded")
        delayed_customs_and_currency(page)
        page.goto("about:blank")
        page.set_content(HTML.read_text(encoding="utf-8"),wait_until="domcontentloaded")
        trade_endurance(page)
        browser.close()
    print("PASS STEP 9 trade endurance: 12 months, real emerging imports/exports, customs reroute, FX ledger, save")
