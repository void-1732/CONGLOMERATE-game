"""Run company contracts, an alternate market and ledger reconciliation over decades."""

import os
import shutil
from pathlib import Path
from time import perf_counter

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"
SCENARIOS = (
    (1900, "JP", "normal", "fixed", (24, 60, 120, 240)),
    (1960, "DE", "hard", "market", (24, 60)),
    (2010, "US", "easy", "market", (24,)),
)


def run_scenario(page, era, country, difficulty, pricing, checkpoints):
    setup = page.evaluate("""([era,country,difficulty,pricing]) => {
        S=newGame({era,country,difficulty,history:'historical',name:'長期契約の月次検証'});
        VIEW_FIRM=S.playerId;
        const buyer=current(),origin=country==='DE'?'US':'DE';
        const seller=initFirm(S,{name:'長期供給資源会社',country,industry:'resource',seedBase:10000000});
        ensureSupplyNetwork(S);
        const supplierId='CORP:'+seller.id+':steel',node=S.supplyNetwork.nodes.find(n=>n.id===supplierId);
        const capacity=availableContractCapacityV040(S,buyer,node,'steel');
        const quantity=Math.max(1,Math.min(4,capacity)),month=ym(S.year,S.month);
        Object.assign(buyer.supply.contracts.steel,{
            supplierId, backupId:npcIdV033(origin,'steel'),backupShareV040:50,autoManage:false,
            corporateSourcesV037:[supplierId],longTermV036:{enabled:true,supplierId,start:month,end:month+12,
                quantity,months:12,renew:true,priceMode:pricing,unitBase:contractUnitBaseV040(S,node),
                creditBase:0,contractIdV040:S.seq++}
        });
        saveAuto=async()=>true;
        render=()=>{};
        return {capacity,quantity,supplierId,seller:seller.id,firstEnd:month+12};
    }""", [era, country, difficulty, pricing])
    assert 0 < setup["quantity"] <= setup["capacity"], setup
    last = 0
    totals = dict(contractOrders=0, missing=0, alternate=0, paidClaims=0, privateReceipts=0)
    start = perf_counter()
    for checkpoint in checkpoints:
        for first in range(last, checkpoint, 12):
            result = page.evaluate("""async ({first,count,setup}) => {
                const totals={contractOrders:0,missing:0,alternate:0,paidClaims:0,privateReceipts:0};
                for(let i=first;i<first+count;i++){
                    const f=current(),seller=company(setup.seller,S),month=ym(S.year,S.month);
                    if(i%12===8){
                        S.supplyRisk.active[setup.supplierId]={type:'steel',country:seller.country,supplierName:seller.name,
                            reason:'試験の操業停止',capacityFactor:0,pricePct:.12,delay:1,remaining:3,start:month};
                    }
                    const previous=S.monthCommitted;
                    await runMonth();
                    if(S.monthCommitted!==previous+1)return {failedAt:previous+1,diagnostic:LAST_MONTH_DIAGNOSTIC?.message};
                    const buyer=current(),supplier=company(setup.seller,S),term=contractV036(buyer,'steel');
                    const row=buyer.supply.lastAttempt.steel;
                    if(row.longTermOrdered>term.quantity||row.ordered>row.requested||
                       row.requested!==row.ordered+row.shortage)return {month,row,term};
                    totals.contractOrders+=row.longTermOrdered;
                    totals.missing+=row.longTermShortfall??0;
                    totals.alternate+=row.backupOrdered??0;
                    totals.paidClaims+=buyer.supply.history.filter(r=>r.month===month&&r.firmId===supplier.id)
                        .reduce((sum,r)=>sum+(r.creditBase??0),0);
                    const sales=supplier.journals.filter(j=>j.when===month&&j.text.startsWith('法人間資材の売上 '));
                    for(const sale of sales){
                        const id=sale.text.split(' ').at(-1);
                        const receipt=buyer.journals.find(j=>j.text==='法人間資材の検収・決済 '+id);
                        if(!receipt)continue;
                        if(receipt.amount!==sale.amount||receipt.when!==sale.when)return {month,receipt,sale};
                        if(!supplier.journals.some(j=>j.text==='法人間資材の売上原価 '+id))return {month,id,error:'missing seller cost'};
                        totals.privateReceipts++;
                    }
                    if(!f.id||!Number.isSafeInteger(term.contractIdV040))return {month,term};
                }
                S=parsePayload(savePayload(S));
                const errors=[...check(S),...consolidate(S,S.playerId).errors];
                return errors.length?{errors}:{totals,expiry:contractV036(current(),'steel').end,month:S.monthCommitted};
            }""", {"first": first, "count": min(12, checkpoint - first), "setup": setup})
            assert "totals" in result, (era, difficulty, first + 1, result)
            for key, value in result["totals"].items():
                totals[key] += value
        assert result["expiry"] > setup["firstEnd"] and result["month"] < result["expiry"], result
        assert all(amount > 0 for amount in totals.values()), (era, checkpoint, totals)
        print(f"PASS {era} {country} {difficulty} {pricing} {checkpoint} months {totals} "
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
