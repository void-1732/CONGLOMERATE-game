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
        render=()=>{};
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
        assert not errors, errors
        browser.close()
    print("PASS STEP 6: currency wallets, exchange limits, FX gains, consolidated cash flow and saves")
