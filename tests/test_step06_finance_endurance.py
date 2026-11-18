"""Exercise foreign-currency treasury, settlement, and close across eras."""

import os
import shutil
from pathlib import Path
from time import perf_counter

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"
SCENARIOS = (
    (1900, "JP", "US", "normal", (24, 60, 120, 240)),
    (1960, "DE", "FR", "hard", (24, 60)),
    (2010, "US", "JP", "easy", (24,)),
)


def run_scenario(page, era, country, market, difficulty, checkpoints):
    quote = page.evaluate("""([era,country,market,difficulty]) => {
        S=newGame({era,country,difficulty,history:'historical',name:'国際財務の長期検証'});
        VIEW_FIRM=S.playerId;
        const f=current(),currency=COUNTRIES[market].currency,contract=contractV036(f,'steel');
        const supplierId=npcIdV033(market,'steel');
        f.supply.contracts.steel.supplierId=supplierId;
        Object.assign(contract,{supplierId,quantity:12});
        f.marketPresence=[market];f.dealers[market]=75;
        Object.assign(exportChannel(f,market,S),{channel:'dealer',capacity:24});
        foreignAccountsV042(f).retainReceipts=true;
        const reserve=localFromBase(120000,f.country),quantity=Math.floor(reserve/currencyRatioV042(S,f,currency));
        exchangeForeignV042(S,f,currency,quantity,'buy');
        saveAuto=async()=>true;render=()=>{};
        return {currency,reserve};
    }""", [era, country, market, difficulty])
    last = 0
    totals = dict(receivables=0, payables=0, forwards=0, exchanges=0, revaluations=0)
    start = perf_counter()
    for checkpoint in checkpoints:
        for first in range(last, checkpoint, 12):
            result = page.evaluate("""async ({first,count,quote,market}) => {
                const totals={receivables:0,payables:0,forwards:0,exchanges:0,revaluations:0};
                for(let i=first;i<first+count;i++){
                    const f=current(),month=ym(S.year,S.month),currency=quote.currency;
                    const localRate=currencyRatioV042(S,f,currency);
                    const wallet=f.foreignFinanceV042.wallets[currency]?.quantity??0;
                    if(wallet*localRate>quote.reserve*2){
                        const excess=Math.floor(wallet-quote.reserve/localRate);
                        if(excess>0)exchangeForeignV042(S,f,currency,excess,'sell');
                    }
                    if(i%12===3&&acc(f,'cash')>quote.reserve*5){
                        const quantity=Math.max(1,Math.floor(quote.reserve*.25/localRate));
                        signForeignForwardV042(S,f,currency,quantity,'buy',3);
                    }
                    if(i%18===8){
                        const exposed=market==='JP'?f.country:market;
                        S.world[exposed].fx*=i%36===8?1.12:.90;
                    }
                    const plant=f.plants[0];
                    if(i%6===0&&plant.condition<86){
                        const cost=localFromBase((2000+plant.capacity*95)*eraCostFactor(S.year),f.country);
                        if(acc(f,'cash')>=cost){
                            post(f,{maintenance:cost},{cash:cost},'検証の工場保全','operating',S);
                            plant.condition=Math.min(100,plant.condition+18);syncPlant(f);
                        }
                    }
                    const previous=S.monthCommitted;
                    await runMonth();
                    if(S.monthCommitted!==previous+1)return {failedAt:previous+1,diagnostic:LAST_MONTH_DIAGNOSTIC?.message};
                    const buyer=current(),finance=buyer.foreignFinanceV042,close=S.consoHistory.at(-1);
                    const n=Object.values(finance.wallets).reduce((sum,item)=>sum+item.bookValue,0);
                    if(n!==acc(buyer,'foreignCash')||!close.cf.reconciled)return {month,book:n,ledger:acc(buyer,'foreignCash'),cf:close.cf};
                    for(const journal of buyer.journals.filter(row=>row.when===month)){
                        if(journal.text.startsWith('外貨建て売掛金回収'))totals.receivables++;
                        if(journal.text.startsWith('外貨建て買掛金決済'))totals.payables++;
                        if(journal.text.startsWith('為替予約の'))totals.forwards++;
                        if(journal.text.startsWith('外貨の売却'))totals.exchanges++;
                        if(journal.text.startsWith('外貨現金の期末評価'))totals.revaluations++;
                    }
                }
                S=parsePayload(savePayload(S));
                const group=consolidate(S),errors=[...check(S),...group.errors];
                return errors.length?{errors}:{totals,cash:group.spot.cash};
            }""", {"first": first, "count": min(12, checkpoint - first), "quote": quote, "market": market})
            assert "totals" in result, (era, country, first + 1, result)
            for key, value in result["totals"].items():
                totals[key] += value
        assert all(value > 0 for value in totals.values()), (era, country, checkpoint, totals)
        print(f"PASS {era} {country}/{market} {difficulty} {checkpoint} months {totals} "
              f"{perf_counter()-start:.1f}s", flush=True)
        last = checkpoint


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
        for scenario in SCENARIOS:
            run_scenario(page, *scenario)
        assert not errors, errors
        browser.close()
