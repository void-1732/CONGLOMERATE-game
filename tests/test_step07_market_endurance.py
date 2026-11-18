"""Exercise foreign factories and market strategy over 24 to 240 monthly closes."""

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
    setup = page.evaluate("""([era,country,market,difficulty])=>{
        S=newGame({era,country,difficulty,history:'historical',name:'海外進出の長期検証'});
        VIEW_FIRM=S.playerId;saveAuto=async()=>true;render=()=>{};
        const f=current(),site=TRADE_GEOGRAPHY_V041[market].ports[0];
        changeForeignMarketV043(S,f,market,'enter','direct','');
        const plant=beginFactoryConstruction(S,f,'small','integrated','現地組立拠点',site);
        if(f.models[0])f.plans[f.models[0].id]=12;
        return {id:plant.id,site};
    }""", [era, country, market, difficulty])
    total = dict(localSaleMonths=0, factoryReceipts=0, closedMonths=0, closedLocalSales=0, taxMonths=0)
    start = perf_counter()
    last = 0
    for checkpoint in checkpoints:
        for first in range(last, checkpoint, 12):
            outcome = page.evaluate("""async ({first,months,setup,market})=>{
                const totals={localSaleMonths:0,factoryReceipts:0,closedMonths:0,closedLocalSales:0,taxMonths:0};
                for(let i=first;i<first+months;i++){
                    const f=current(),date=ym(S.year,S.month),p=f.plants.find(x=>x.id===setup.id);
                    if(!p.construction&&!p.paused){
                        if(f.foreignMarketsV043[market].mode!=='factory'&&i<14){
                            changeForeignMarketV043(S,f,market,'enter','factory','');
                            f.plants[0].paused=true;syncPlant(f);
                        }
                        if(i%6===0&&p.condition<82){
                            const cost=localFromBase((2000+p.capacity*95)*eraCostFactor(S.year),f.country);
                            if(acc(f,'cash')>=cost){
                                post(f,{maintenance:cost},{cash:cost},'海外工場の設備保全','operating',S);
                                p.condition=Math.min(100,p.condition+18);syncPlant(f);
                            }
                        }
                        const req=materialRequirement(f.models[0].design,f),logistics=ensureWarehouseV038(f);
                        for(const type of RAW_TYPES_V032){
                            if(!req[type])continue;
                            const observed=plantRawStockV038(f,p.id,type).q;
                            const promised=logistics.rawShipments.filter(x=>x.type===type&&x.to===p.id).reduce((n,x)=>n+x.quantity,0);
                            const central=centralRawStockV038(f,type);
                            const need=Math.max(0,Math.ceil(36*req[type]-observed-promised));
                            const qty=Math.floor(Math.min(need,central.q,rawSpaceForTransferV038(f,p.id),rawTransportRoomV038(S,f,'warehouse',p.id)));
                            if(!qty)continue;
                            const declared=baseFromLocal(Math.round(central.v/central.q),f.country)/100||1;
                            const route=internationalQuoteV041(S,f.country,market,'bulk',declared,qty);
                            if(route&&acc(f,'cash')>=localFromBase(qty*route.freightUnitBase,f.country))
                                dispatchRawShipmentV038(S,f,'warehouse',p.id,type,qty);
                        }
                    }
                    if(i===12)changeForeignMarketV043(S,f,market,'reduce','','');
                    if(i===14)changeForeignMarketV043(S,f,market,'withdraw','','');
                    if(i===16)changeForeignMarketV043(S,f,market,'enter','factory','');
                    const previous=S.monthCommitted,open=f.marketPresence.includes(market);
                    if(p.paused===open)return {date,open,paused:p.paused};
                    await runMonth();
                    if(S.monthCommitted!==previous+1)return {failedAt:previous+1,diagnostic:LAST_MONTH_DIAGNOSTIC?.message};
                    const after=current(),journals=after.journals.filter(j=>j.when===date);
                    const local=journals.some(j=>j.text.startsWith('現地工場からの販売：'));
                    totals.localSaleMonths+=Number(local);
                    totals.factoryReceipts+=journals.filter(j=>j.text.startsWith('資材の海外検収')).length;
                    totals.closedMonths+=Number(!open);
                    totals.closedLocalSales+=Number(!open&&local);
                    totals.taxMonths+=Number(journals.some(j=>j.text==='当月法人税見込計上'));
                }
                S=parsePayload(savePayload(S));const g=consolidate(S),errors=[...check(S),...g.errors];
                return errors.length||!g.cf.reconciled?{errors,cf:g.cf}:{totals,firms:S.firms.length};
            }""", {"first": first, "months": min(12, checkpoint - first), "setup": setup, "market": market})
            assert 'totals' in outcome, (era, country, first + 1, outcome)
            for name, value in outcome['totals'].items(): total[name] += value
        assert total['localSaleMonths'] > 0 and total['factoryReceipts'] > 0, (era, country, checkpoint, total)
        assert total['closedMonths'] == 2 and not total['closedLocalSales'], total
        assert total['taxMonths'] > 0, total
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
