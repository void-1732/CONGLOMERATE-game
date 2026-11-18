"""Exercise disruptions, impact, mitigation, and recovery over long saves."""

import os
import shutil
from pathlib import Path
from time import perf_counter

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / 'index.html'
SCENARIOS = (
    (1900, 'JP', 'US', 'normal', (24, 60, 120, 240)),
    (1960, 'DE', 'FR', 'hard', (24, 60)),
    (2010, 'US', 'JP', 'easy', (24,)),
)


def scenario(page, era, country, market, difficulty, checkpoints):
    page.evaluate("""([era,country,market,difficulty])=>{
        S=newGame({era,country,difficulty,history:'historical',name:'供給危機の長期検証'});
        VIEW_FIRM=S.playerId;saveAuto=async()=>true;render=()=>{};
        const f=current(),c=f.supply.contracts.steel;
        c.backupId=npcIdV033(market,'steel');c.backupShareV040=50;c.safetyMonths=1.5;
        changeForeignMarketV043(S,f,market,'enter','direct','');
        f.marketPresence=[market];f.dealers[market]=75;
    }""", [era, country, market, difficulty])
    total = dict(affected=0, notices=0, alternate=0, shipments=0, recovered=0)
    start = perf_counter()
    last = 0
    for checkpoint in checkpoints:
        for first in range(last, checkpoint, 12):
            result = page.evaluate("""async ({first,months,market})=>{
                const total={affected:0,notices:0,alternate:0,shipments:0,recovered:0};
                for(let i=first;i<first+months;i++){
                    const f=current(),date=ym(S.year,S.month),p=f.plants[0];
                    if(i===3)startEconomicShockV044(S,'financial',[market],{id:'stress-credit'});
                    if(i===7)startEconomicShockV044(S,'energy',[f.country],{id:'stress-energy'});
                    if(i===10)startEconomicShockV044(S,'disaster',[market],{id:'stress-disaster'});
                    if(i===13)startEconomicShockV044(S,'tariff',[f.country,market],{id:'stress-tariff',lane:[f.country,market]});
                    if(i===16)startEconomicShockV044(S,'sanctions',[f.country,market],{id:'stress-sanctions',lane:[f.country,market],months:3});
                    if(i%6===0&&p.condition<85){
                        const cost=localFromBase((2000+p.capacity*95)*eraCostFactor(S.year),f.country);
                        if(acc(f,'cash')>=cost){
                            post(f,{maintenance:cost},{cash:cost},'危機試験の設備保全','operating',S);
                            p.condition=Math.min(100,p.condition+18);syncPlant(f);
                        }
                    }
                    const prior=S.monthCommitted;
                    const approved=internationalTradeAllowedV041(S,f.country,market,'vehicle');
                    await runMonth();
                    if(S.monthCommitted!==prior+1)return {failed:date,error:LAST_MONTH_DIAGNOSTIC?.message};
                    const buyer=current(),history=S.economicShocksV044??[];
                    const starts=history.filter(event=>event.start===date);
                    total.notices+=starts.length;
                    total.affected+=Number(history.some(event=>event.start<=date&&date<event.end));
                    total.alternate+=buyer.supply.lastAttempt.steel.backupOrdered??0;
                    const shipped=buyer.journals.filter(j=>j.when===date&&j.text.startsWith('海外輸送中の完成品へ振替')).length;
                    total.shipments+=shipped;
                    total.recovered+=Number(i>=19&&shipped>0);
                    if(!approved&&shipped)return {date,shipped};
                }
                S=parsePayload(savePayload(S));const g=consolidate(S),errors=[...check(S),...g.errors];
                return errors.length||!g.cf.reconciled?{errors,cf:g.cf}:{total,history:S.economicShocksV044?.map(e=>e.id)??[]};
            }""", {"first": first, "months": min(12, checkpoint - first), "market": market})
            assert 'total' in result, (era, first, result)
            for key, count in result['total'].items(): total[key] += count
        assert all(amount > 0 for amount in total.values()), (era, checkpoint, total)
        assert len(set(result['history'])) == len(result['history']), result['history']
        if era == 1900 and checkpoint >= 120: assert '1907-credit' in result['history'], result
        if era == 1900 and checkpoint >= 240: assert '1914-trade' in result['history'], result
        print(f'PASS {era} {country}/{market} {difficulty} {checkpoint} months {total} {perf_counter()-start:.1f}s', flush=True)
        last = checkpoint


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium'),
                                             args=['--no-sandbox'])
        page = browser.new_page(offline=True)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content(HTML.read_text(encoding='utf-8'), wait_until='domcontentloaded')
        for configuration in SCENARIOS:
            scenario(page, *configuration)
        assert not errors, errors
        browser.close()
