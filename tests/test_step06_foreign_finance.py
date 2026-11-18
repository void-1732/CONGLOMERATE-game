"""Settlement currency, foreign cash valuation and consolidated cash-flow evidence."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"


def check_wallets(page):
    opening = page.evaluate("""() => {
        S=newGame({era:1960,country:'JP',difficulty:'normal',history:'historical',name:'通貨別現金の検証'});
        VIEW_FIRM=S.playerId;
        PAGE='finance';render();
        return {cash:acc(current(),'cash'),usd:S.world.US.fx,checks:check(parsePayload(savePayload(S)))};
    }""")
    assert not opening["checks"], opening
    button = page.get_by_role("button", name="現在のレートで両替")
    page.locator("#fxWalletCurrency").select_option("USD")
    page.locator("#fxWalletAmount").fill("1200")
    button.click()
    first = page.evaluate("""() => ({cash:acc(current(),'cash'),book:acc(current(),'foreignCash'),wallet:current().foreignFinanceV042.wallets.USD,
        base:consolidate(S).bs.cash})""")
    assert first["wallet"]["quantity"] == 120000, first
    assert first["wallet"]["bookValue"] == first["book"] == opening["cash"] - first["cash"], first
    assert first["base"] == opening["cash"], first

    page.locator("#fxWalletCurrency").select_option("USD")
    page.locator("#fxWalletAmount").fill("9000000000000")
    button.click()
    assert page.evaluate("acc(current(),'cash')") == first["cash"]
    page.locator("#fxWalletCurrency").select_option("GBP")
    page.locator("#fxWalletAmount").fill("200")
    button.click()
    page.evaluate("S.world.US.fx=185")
    page.locator("#fxWalletCurrency").select_option("USD")
    page.locator("#fxWalletOperation").select_option("sell")
    page.locator("#fxWalletAmount").fill("300")
    button.click()
    result = page.evaluate("""async () => {
        const old=current(),sale=old.journals.find(j=>j.text==='外貨の売却 USD');
        const before=old.foreignFinanceV042.wallets.USD.quantity;
        const cashMoved=cashOfJournal(sale),gain=sale.cr.find(([a])=>a==='otherRevenue')?.[1];
        S=parsePayload(savePayload(S));
        saveAuto=async()=>true;
        const prior=S.monthCommitted;
        await runMonth();
        const f=current(),g=consolidate(S),month=S.monthCommitted;
        const usd=f.foreignFinanceV042.wallets.USD,gbp=f.foreignFinanceV042.wallets.GBP;
        const fxCash=f.journals.filter(j=>j.when===month&&j.kind==='fxCash').reduce((n,j)=>n+cashOfJournal(j),0);
        const broken=structuredClone(S);
        company(f.id,broken).foreignFinanceV042.wallets.USD.bookValue++;
        return {advanced:month===prior+1,diagnostic:LAST_MONTH_DIAGNOSTIC?.message,before,cashMoved,gain,
            cash:f.ledger.cash,book:f.ledger.foreignCash,total:cashBookV042(f),usd,gbp,
            settledUsd:Math.round(usd.quantity*currencyRatioV042(S,f,'USD')),
            settledGbp:Math.round(gbp.quantity*currencyRatioV042(S,f,'GBP')),
            fxCash,translation:g.cf.fxTranslation,reconciled:g.cf.reconciled,spot:g.spot.cash,
            errors:[...check(S),...g.errors],badState:check(broken)};
    }""")
    assert result["advanced"] and result["before"] == 90000, result
    assert result["cashMoved"] == result["gain"] > 0, result
    assert result["usd"]["bookValue"] == result["settledUsd"] and result["gbp"]["bookValue"] == result["settledGbp"], result
    assert result["book"] == result["settledUsd"] + result["settledGbp"], result
    assert result["cash"] + result["book"] == result["total"] == result["spot"], result
    assert result["fxCash"] == result["translation"] and result["reconciled"], result
    assert not result["errors"] and result["badState"], result


def check_foreign_invoices(page):
    page.evaluate("""() => {
        S=newGame({era:1960,country:'JP',difficulty:'easy',history:'historical',name:'外貨建て決済の検証'});
        VIEW_FIRM=S.playerId;
        PAGE='finance';render();
    }""")
    page.locator("#fxKeepReceipts").check()
    page.get_by_role("button", name="外貨受取方針を保存").click()
    observed = page.evaluate("""() => {
        const f=current(),type='steel',m=f.models[0],supplierId=npcIdV033('DE',type);
        for(const t of SUPPLY_TYPES)f.supply.contracts[t].autoOrder=t===type;
        Object.assign(f.supply.contracts[type],{supplierId,autoManage:false,longTermV036:null});
        const used=f.stock[type];
        post(f,{otherExpense:used.v},{materials:used.v},'調達試験の材料払出','operating',S);
        f.stock[type]={q:0,v:0};
        procureNetwork(S,[]);
        post(f,{goods:4000},{cash:4000},'外貨売上の完成車','operating',S);
        f.goods[m.id].q+=4;f.goods[m.id].v+=4000;
        exportShipment(S,f,m.id,4,m.priceBase,'US',[],'mass');
        const due=Math.max(f.supply.inbound.find(x=>x.supplierId===supplierId).due,f.distribution.outbound[0].due);
        while(ym(S.year,S.month)<due)nextMonthDate(S);
        deliverMaterials(S,f,[]);
        Object.assign(S.world.US,{demand:100,cycle:0,war:false});
        f._salesNow=0;f._unitsNow=0;f.marketThisMonth={};
        deliverExports(S,[]);
        const newDebt=f.payables.find(x=>x.currency==='DEM'),sale=f.receivables.find(x=>x.currency==='USD');
        const retained=f.foreignFinanceV042.wallets.USD.quantity;
        const funded=Math.floor(newDebt.foreignMinor/3);
        const bought=exchangeForeignV042(S,f,'DEM',funded,'buy');
        const saved=parsePayload(savePayload(S)),buyer=company(f.id,saved),cash=acc(buyer,'cash');
        post(buyer,{otherExpense:cash},{cash},'決済資金不足の検証','operating',saved);
        saved.world.US.fx=180;
        saved.world.DE.fx=205;
        nextMonthDate(saved);
        settleScheduled(buyer,saved);
        const partial=buyer.payables.find(x=>x.currency==='DEM');
        const debited=buyer.journals.find(j=>j.text.startsWith('外貨建て買掛金決済 DEM'));
        const income=buyer.journals.find(j=>j.text.startsWith('外貨建て売掛金回収 USD'));
        const heldAfter=buyer.foreignFinanceV042.wallets.USD.quantity;
        const walletUsed=debited.cr.find(([a])=>a==='foreignCash')[1];
        const missingBeforeFunding=acc(buyer,'cash')===0&&buyer.distress.stage>=2;
        const recovered=income.dr.find(([account])=>account==='foreignCash')[1];
        const resultAfterPartial=check(saved);
        post(buyer,{cash:300000000},{capital:300000000},'期日後の資金再建','financing',saved);
        nextMonthDate(saved);
        settleScheduled(buyer,saved);
        const retry=buyer.journals.filter(j=>j.text.startsWith('外貨建て買掛金決済 DEM')).at(-1);
        const loss=retry.dr.find(([account])=>account==='fxLoss')?.[1]??0;
        const value=Math.round(sale.foreignMinor*currencyRatioV042(saved,buyer,'USD'));
        return {funded,retained,partial:partial.foreignMinor,debt:newDebt.foreignMinor,sale:sale.foreignMinor,
            missingBeforeFunding,walletUsed,bought,recovered,value,heldAfter,loss,remaining:buyer.payables.some(x=>x.currency==='DEM'),
            errors:[...resultAfterPartial,...check(saved)],receivable:buyer.receivables.some(x=>x.currency==='USD')};
    }""")
    assert observed["funded"] > 0 and observed["partial"] == observed["debt"] - observed["funded"], observed
    assert observed["bought"] == observed["walletUsed"] and observed["missingBeforeFunding"], observed
    assert observed["heldAfter"] == observed["retained"] + observed["sale"] and observed["retained"] > 0, observed
    assert observed["recovered"] == observed["value"] and observed["loss"] > 0, observed
    assert not any(observed[k] for k in ["remaining", "receivable", "errors"]), observed


def check_forwards(page):
    page.evaluate("""() => {
        S=newGame({era:1960,country:'JP',difficulty:'easy',history:'historical',name:'為替予約の検証'});
        VIEW_FIRM=S.playerId;
        exchangeForeignV042(S,current(),'GBP',50000,'buy');
        PAGE='finance';render();
    }""")
    sign = page.get_by_role("button", name="為替予約を締結")
    page.locator("#fxForwardCurrency").select_option("USD")
    page.locator("#fxForwardAmount").fill("750")
    page.locator("#fxForwardMonths").select_option("1")
    sign.click()
    page.locator("#fxForwardCurrency").select_option("GBP")
    page.locator("#fxForwardOperation").select_option("sell")
    page.locator("#fxForwardAmount").fill("700")
    sign.click()
    assert page.evaluate("current().foreignFinanceV042.forwards.length") == 1
    page.locator("#fxForwardAmount").fill("250")
    sign.click()
    result = page.evaluate("""async () => {
        const original=structuredClone(current().foreignFinanceV042.forwards),[purchase,sale]=original;
        const noFunding=parsePayload(savePayload(S)),test=company(S.playerId,noFunding);
        while(ym(noFunding.year,noFunding.month)<purchase.due)nextMonthDate(noFunding);
        const cash=acc(test,'cash');
        post(test,{otherExpense:cash},{cash},'為替予約の資金不足試験','operating',noFunding);
        const warning=[];
        settleForeignForwardsV042(noFunding,test,warning);
        const stillPending=test.foreignFinanceV042.forwards.find(o=>o.id===purchase.id).settledMonth===undefined;
        S=parsePayload(savePayload(S));
        saveAuto=async()=>true;
        const first=S.monthCommitted;
        await runMonth();
        S.world.US.fx=190;
        S.world.UK.fx=155;
        await runMonth();
        const f=current(),consolidated=consolidate(S);
        const orders=f.foreignFinanceV042.forwards,fx=f.foreignFinanceV042.wallets;
        const results=orders.map(o=>({id:o.id,maturity:o.due,settled:o.settledMonth,benefit:o.benefitLocal,amount:o.amount}));
        settleForeignForwardsV042(S,f,[]);
        const booked=f.journals.filter(j=>j.text.startsWith('為替予約の'));
        return {first,closed:S.monthCommitted,results,walletUsd:fx.USD.quantity,walletGbp:fx.GBP.quantity,
            expected:[Math.round(purchase.quantity*190)-purchase.amount,sale.amount-Math.round(sale.quantity*155)],
            original,booked:booked.length,warning,stillPending,cf:consolidated.cf.reconciled,
            errors:[...check(S),...consolidated.errors]};
    }""")
    assert result["closed"] == result["first"] + 2 and result["walletUsd"] == 75000, result
    assert result["walletGbp"] == 25000 and result["booked"] == 2 and result["stillPending"] and result["warning"], result
    assert [x["benefit"] for x in result["results"]] == result["expected"], result
    assert all(x["settled"] == x["maturity"] for x in result["results"]), result
    assert [x["amount"] for x in result["results"]] == [x["amount"] for x in result["original"]], result
    assert result["cf"] and not result["errors"], result


def check_subsidiary_finance(page):
    child = page.evaluate("""() => {
        S=newGame({era:1960,country:'JP',difficulty:'easy',history:'historical',name:'海外子会社の資金検証'});
        VIEW_FIRM=S.playerId;
        PAGE='group';render();
        document.getElementById('subName').value='北米部品会社';
        document.getElementById('subCountry').value='US';
        document.getElementById('subIndustry').value='manufacturing';
        document.getElementById('subCapital').value='1800000';
        createSub();
        PAGE='finance';render();
        return current().id;
    }""")
    page.locator("#borrowBase").fill("125000")
    page.locator('[data-action="borrow"]').click()
    native_loan = page.evaluate("current().loans.at(-1)")
    assert native_loan["outstanding"] == round(125000 / 150 * 100), native_loan

    page.evaluate("() => { VIEW_FIRM=S.playerId; S.world.US.fx=179; PAGE='group';render(); }")
    page.locator("#loanSubs").select_option(child)
    page.locator("#loanAmount").fill("160000")
    page.locator('[data-action="groupLoan"]').click()
    outcome = page.evaluate("""async childId => {
        const buyer=current(),partner=company(childId,S),loan=partner.loans.at(-1),type='components';
        const cashIn=partner.journals.find(j=>j.text==='親会社からの借入');
        const cashOut=buyer.journals.find(j=>j.text==='子会社への貸付');
        const amount=3700;
        post(partner,{materials:amount},{cash:amount},'決済検証の実在部品','operating',S);
        partner.stock[type].q+=20;partner.stock[type].v+=amount;
        const initialCurrency=500000;
        exchangeForeignV042(S,buyer,'USD',initialCurrency,'buy');
        const start=buyer.stock[type];
        post(buyer,{otherExpense:start.v},{materials:start.v},'検証前の部品払出','operating',S);
        buyer.stock[type]={q:0,v:0};buyer.interplant.siteComponents={};
        const supplierId='CORP:'+partner.id+':'+type;
        buyer.supply.contracts[type].supplierId=supplierId;
        const term=contractV036(buyer,type);
        Object.assign(term,{supplierId,quantity:5});
        procureNetwork(S,[]);
        const shipment=buyer.supply.inbound.find(x=>x.supplierId===supplierId&&x.contractV036);
        saveAuto=async()=>true;render=()=>{};
        const end=shipment.due;
        while(ym(S.year,S.month)<=end){
            const previous=S.monthCommitted;
            if(ym(S.year,S.month)===end)S.world.US.fx=193;
            await runMonth();
            if(S.monthCommitted!==previous+1)return {failed:LAST_MONTH_DIAGNOSTIC?.message};
        }
        const f=current(),seller=company(childId,S),g=consolidate(S);
        const paid=f.journals.find(j=>j.text==='法人間資材の検収・決済 '+shipment.id);
        const received=seller.journals.find(j=>j.text==='グループ内資材の簿価決済 '+shipment.id);
        const ledgerPart=paid.cr.find(([account])=>account==='foreignCash')?.[1]??0;
        const domestic=paid.cr.find(([account])=>account==='cash')?.[1]??0;
        const matching=S.intercompanyTx.some(x=>x.kind==='materialsCash'&&x.fromJournal===paid.id&&x.toJournal===received.id);
        const restored=parsePayload(savePayload(S));
        return {loanOut:cashOut.amount,quotedAmount:Math.round(cashOut.amount*cashOut.fxAtPost/cashIn.fxAtPost),
            loanIn:cashIn.amount,localPrincipal:loan.outstanding,paid:ledgerPart,domestic,matching,
            fundsUsed:initialCurrency-f.foreignFinanceV042.wallets.USD.quantity,supplierCredit:received.amount,
            cf:g.cf.reconciled,errors:[...check(restored),...g.errors]};
    }""", child)
    assert outcome["loanOut"] == 16000000 and outcome["loanIn"] == outcome["quotedAmount"] == outcome["localPrincipal"], outcome
    assert outcome["fundsUsed"] >= outcome["supplierCredit"] > 0, outcome
    assert outcome["paid"] > 0 and outcome["domestic"] == 0 and outcome["matching"], outcome
    assert outcome["cf"] and not outcome["errors"], outcome


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
        check_wallets(page)
        check_foreign_invoices(page)
        check_forwards(page)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.get_by_role("heading", name="通貨別の現金・両替").is_visible()
        assert page.get_by_role("button", name="為替予約を締結").is_visible()
        page.set_viewport_size({"width": 1280, "height": 900})
        check_subsidiary_finance(page)
        assert not errors, errors
        browser.close()
    print("PASS STEP 6: cash wallets, invoice settlement, forwards, subsidiary finance, consolidated cash flow and saves")
