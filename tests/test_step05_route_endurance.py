"""Run cross-border procurement, overseas depots and vehicle exports through long saves."""

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


def run_scenario(page, era, country, destination, difficulty, checkpoints):
    page.evaluate("""([era,country,destination,difficulty]) => {
        S=newGame({era,country,difficulty,history:'historical',name:'国際物流の長期検証'});
        VIEW_FIRM=S.playerId;
        const f=current(),term=contractV036(f,'steel'),supplierId=npcIdV033(destination,'steel');
        f.supply.contracts.steel.supplierId=supplierId;
        Object.assign(term,{supplierId,quantity:12});
        f.marketPresence=[destination];
        f.dealers[destination]=75;
        Object.assign(exportChannel(f,destination,S),{channel:'dealer',capacity:24});
        const hub=TRADE_GEOGRAPHY_V041[destination].ports[0];
        const cost=localFromBase(23000*eraCostFactor(era),f.country);
        post(f,{ppe:cost},{cash:cost},'長期検証の海外倉庫','investing',S);
        ensureWarehouseV038(f).depots.push({id:'DEPOT-'+S.seq++,name:'海外物流拠点',siteId:hub,capacity:280,stock:{}});
        openRawStorageV038(f);
        saveAuto=async()=>true;
        render=()=>{};
    }""", [era, country, destination, difficulty])
    last = 0
    totals = dict(imports=0, importDuties=0, exports=0, exportDeliveries=0, depotReceipts=0, reroutes=0)
    start = perf_counter()
    for checkpoint in checkpoints:
        for first in range(last, checkpoint, 12):
            result = page.evaluate("""async ({first,count,destination}) => {
                const totals={imports:0,importDuties:0,exports:0,exportDeliveries:0,depotReceipts:0,reroutes:0};
                for(let i=first;i<first+count;i++){
                    const f=current(),month=ym(S.year,S.month),logistics=ensureWarehouseV038(f),depot=logistics.depots[0];
                    const plant=f.plants[0];
                    if(i%6===0&&plant.condition<86){
                        const cost=localFromBase((2000+plant.capacity*95)*eraCostFactor(S.year),f.country);
                        if(acc(f,'cash')>=cost){
                            post(f,{maintenance:cost},{cash:cost},'国際事業の設備保全','operating',S);
                            plant.condition=Math.min(100,plant.condition+18);
                            syncPlant(f);
                        }
                    }
                    if(i%12===3){
                        const flight=logistics.rawShipments.find(x=>x.originV041===f.country&&x.due===month);
                        if(flight){
                            const disruptions=(S.logisticsV041.disruptions??={});
                            disruptions[flight.internationalV041.routeId]={end:month+2,capacityFactor:0};
                        }
                    }
                    const fromWarehouse=i%6===1,fromDepot=i%6===4;
                    if(fromWarehouse||fromDepot){
                        const from=fromWarehouse?'warehouse':depot.id,to=fromWarehouse?depot.id:'warehouse';
                        const source=fromWarehouse?centralRawStockV038(f,'steel'):depot.stock.steel??{q:0,v:0};
                        const quantity=Math.floor(Math.min(source.q,3,rawTransportRoomV038(S,f,from,to),rawSpaceForTransferV038(f,to)));
                        const origin=fromWarehouse?f.country:destination,target=fromWarehouse?destination:f.country;
                        if(quantity>0){
                            const unit=baseFromLocal(Math.round(source.v/source.q),f.country)/100||1;
                            const route=internationalQuoteV041(S,origin,target,'bulk',unit,quantity);
                            if(route&&acc(f,'cash')>=localFromBase(quantity*route.freightUnitBase,f.country))
                                dispatchRawShipmentV038(S,f,from,to,'steel',quantity);
                        }
                    }
                    const priorRoutes=new Map(logistics.rawShipments.filter(x=>x.internationalV041)
                        .map(x=>[x.id,x.internationalV041.routeId]));
                    const previous=S.monthCommitted;
                    await runMonth();
                    if(S.monthCommitted!==previous+1)return {failedAt:previous+1,diagnostic:LAST_MONTH_DIAGNOSTIC?.message};
                    const buyer=current(),postClose=ensureWarehouseV038(buyer);
                    for(const record of buyer.supply.history.filter(r=>r.month===month&&r.routeId)){
                        totals.imports+=record.qty;
                        totals.importDuties+=record.dutyBase||0;
                    }
                    const journals=buyer.journals.filter(j=>j.when===month);
                    totals.exports+=journals.filter(j=>j.text.startsWith('海外輸送中の完成品へ振替')).length;
                    totals.exportDeliveries+=buyer.distribution.history.filter(r=>r.month===month).reduce((n,r)=>n+r.qty,0);
                    totals.depotReceipts+=journals.filter(j=>j.text.startsWith('資材の海外検収')).length;
                    totals.reroutes+=postClose.rawShipments.filter(x=>priorRoutes.has(x.id)&&priorRoutes.get(x.id)!==x.internationalV041.routeId).length;
                    const transit=buyer.distribution.outbound.reduce((n,x)=>n+x.bookCost,0);
                    if(transit!==acc(buyer,'goodsTransit'))return {month,transit,ledger:acc(buyer,'goodsTransit')};
                }
                S=parsePayload(savePayload(S));
                const failures=[...check(S),...consolidate(S).errors];
                return failures.length?{failures}:{totals,companies:S.firms.length};
            }""", {"first": first, "count": min(12, checkpoint - first), "destination": destination})
            assert "totals" in result, (era, country, first + 1, result)
            for key, value in result["totals"].items():
                totals[key] += value
        for key in ("imports", "exports", "exportDeliveries", "depotReceipts"):
            assert totals[key] > 0, (era, country, checkpoint, key, totals)
        if era == 1900:
            assert totals["importDuties"] > 0 and totals["reroutes"] > 0, totals
        print(f"PASS {era} {country}/{destination} {difficulty} {checkpoint} months "
              f"{result['companies']} companies {totals} {perf_counter()-start:.1f}s", flush=True)
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
