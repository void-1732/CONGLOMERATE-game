"""Physical route capacity, customs, alternate routes and previous transport saves."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"


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
        raw = page.evaluate("""() => {
            S=newGame({era:1960,country:'DE',difficulty:'normal',history:'historical',name:'国際調達の検証'});
            VIEW_FIRM=S.playerId;
            const f=current(),type='steel',source=npcIdV033('FR',type),events=[];
            for(const t of SUPPLY_TYPES)f.supply.contracts[t].autoOrder=t===type;
            Object.assign(f.supply.contracts[type],{supplierId:source,autoManage:false,longTermV036:null});
            const opening=f.stock[type];
            post(f,{otherExpense:opening.v},{materials:opening.v},'輸入試験の原材料消費','operating',S);
            f.stock[type]={q:0,v:0};
            const priorMarket=npcMarketV033(S,'FR',type).stock;
            procureNetwork(S,events);
            const sent=f.supply.inbound.find(x=>x.supplierId===source);
            const opened=sent.internationalV041.routeId,openingDuty=sent.internationalV041.dutyBase;
            const marketSent=priorMarket-npcMarketV033(S,'FR',type).stock;
            const saved=parsePayload(savePayload(S)),buyer=company(f.id,saved),shipment=buyer.supply.inbound.find(x=>x.id===sent.id);
            while(ym(saved.year,saved.month)<sent.due)nextMonthDate(saved);
            const month=ym(saved.year,saved.month);
            const originalValue=acc(buyer,'materials'),originalStock=buyer.stock[type].q;
            saved.logisticsV041.disruptions={[opened]:{end:month+3,capacityFactor:0}};
            deliverMaterials(saved,buyer,events);
            const rerouted=shipment.internationalV041.routeId,afterRoute=shipment.due;
            const delayedInventory=acc(buyer,'materials');
            nextMonthDate(saved);
            saved.logisticsV041.restrictions={'FR/DE':{end:month+2}};
            deliverMaterials(saved,buyer,events);
            const afterCustoms=shipment.due,restrictedStock=buyer.stock[type].q;
            nextMonthDate(saved);
            const priorPayables=acc(buyer,'payable');
            deliverMaterials(saved,buyer,events);
            const purchase=buyer.supply.history.find(x=>x.routeId===rerouted);
            const expected=localFromBase(sent.totalBase+purchase.rerouteBase+purchase.dutyBase,'DE');
            const corrupt=structuredClone(S);
            company(f.id,corrupt).supply.inbound.find(x=>x.id===sent.id).internationalV041.routeId='unexpected';
            return {opened,openingDuty,rerouted,times:[month,afterRoute,afterCustoms],originalValue,delayedInventory,
                marketSent,originalStock,restrictedStock,purchase,expected,qty:sent.qty,received:buyer.stock[type].q-originalStock,
                duty:Math.round(sent.qty*sent.internationalV041.unitBase*tariffRateV041(saved,'FR','DE','bulk')),
                debit:acc(buyer,'materials')-originalValue,payable:acc(buyer,'payable')-priorPayables,
                legacyErrors:check(S),errors:check(saved),badState:check(corrupt)};
        }""")
        assert raw["opened"] == "FR/DE/rail" and raw["rerouted"] == "FR/DE/sea", raw
        assert raw["openingDuty"] is None and raw["purchase"]["dutyBase"] == raw["duty"] > 0, raw
        assert raw["marketSent"] >= raw["qty"] > 0 and raw["received"] == raw["qty"], raw
        assert raw["times"] == list(range(raw["times"][0], raw["times"][0] + 3)), raw
        assert raw["originalValue"] == raw["delayedInventory"] and raw["restrictedStock"] == raw["originalStock"], raw
        assert raw["debit"] == -raw["payable"] == raw["expected"], raw
        assert not raw["legacyErrors"] and not raw["errors"] and raw["badState"], raw

        vehicles = page.evaluate("""() => {
            S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'海上輸送の検証'});
            VIEW_FIRM=S.playerId;
            const f=current(),m=f.models[0],cost=8000,month=ym(S.year,S.month),dest='US';
            post(f,{goods:cost},{cash:cost},'輸出試験の完成車','operating',S);
            f.goods[m.id].q+=8;f.goods[m.id].v+=cost;
            const route=internationalRoutesV041(S,f.country,dest)[0];
            S.logisticsV041={month,used:{[route.id]:route.capacity-18},restrictions:{'JP/US':{end:month+1}}};
            exportShipment(S,f,m.id,8,m.priceBase,dest,[],'mass');
            const blocked=f.distribution.outbound.length===0&&f.goods[m.id].q>=8;
            delete S.logisticsV041.restrictions['JP/US'];
            exportShipment(S,f,m.id,8,m.priceBase,dest,[],'mass');
            const bookings=f.distribution.outbound.map(x=>[x.id,x.qty,x.internationalV041.routeId,x.due]);
            const used=S.logisticsV041.used[route.id],initial=acc(f,'goodsTransit');
            const legacy=structuredClone(S),older=company(f.id,legacy);
            delete legacy.logisticsV041;
            for(const x of older.distribution.outbound)delete x.internationalV041;
            const priorSave=check(parsePayload(savePayload(legacy)));
            const monthErrors=[],confirmed=[];
            for(const [lead,demand] of [[2,1],[3,28]]){
                while(ym(S.year,S.month)<month+lead)nextMonthDate(S);
                Object.assign(S.world[dest],{demand,cycle:0,war:false});
                f._salesNow=0;f._unitsNow=0;f.marketThisMonth={};
                deliverExports(S,[]);
                confirmed.push(f.marketThisMonth[dest].units);
                monthErrors.push(...check(S));
            }
            const duty=f.journals.filter(j=>j.text.startsWith('輸出品の通関・代替輸送 '));
            const restored=parsePayload(savePayload(S));
            return {blocked,bookings,used,max:route.capacity,initial,rest:acc(f,'goodsTransit'),confirmed,
                dutyIds:duty.map(j=>j.text.split(' ').at(-1)),priorSave,monthErrors,errors:check(restored),
                postUnion:tariffRateV041({...S,year:2010},'DE','FR','vehicle')};
        }""")
        assert vehicles["blocked"] and vehicles["used"] == vehicles["max"], vehicles
        assert [(row[1], row[2]) for row in vehicles["bookings"]] == [(3, "JP/US/sea"), (5, "JP/US/alternateSea")], vehicles
        assert vehicles["confirmed"] == [1, 7] and vehicles["initial"] > 0 and vehicles["rest"] == 0, vehicles
        assert vehicles["dutyIds"] == [row[0] for row in vehicles["bookings"]], vehicles
        assert vehicles["postUnion"] == 0 and not any(vehicles[k] for k in ["priorSave", "monthErrors", "errors"]), vehicles
        assert not errors, errors
        browser.close()
    print("PASS STEP 5: route capacity, rail and sea, customs, rerouting, inventory and legacy saves")
