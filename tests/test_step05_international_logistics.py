"""Physical route capacity, customs, alternate routes and previous transport saves."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"


def check_corporate_shipment(page, is_group):
    setup = page.evaluate("""isGroup => {
        S=newGame({era:1960,country:'JP',difficulty:'easy',history:'historical',name:'国際法人間調達の検証'});
        VIEW_FIRM=S.playerId;
        let seller;
        if(isGroup){
            PAGE='group';render();
            document.getElementById('subName').value='独現地部品子会社';
            document.getElementById('subCountry').value='DE';
            document.getElementById('subIndustry').value='manufacturing';
            document.getElementById('subCapital').value='1800000';
            createSub();seller=current();VIEW_FIRM=S.playerId;
        }else{
            seller=initFirm(S,{name:'独立部品会社',country:'DE',industry:'manufacturing',seedBase:4000000});
        }
        const type='components',buyer=current(),stock=seller.stock[type],amount=3400;
        post(seller,{materials:amount},{cash:amount},'実在部品の入荷','operating',S);
        stock.q+=20;stock.v+=amount;
        ensureSupplyNetwork(S);
        const node=S.supplyNetwork.nodes.find(n=>n.firmId===seller.id&&n.type===type);
        for(const t of SUPPLY_TYPES)buyer.supply.contracts[t].autoOrder=t===type;
        const old=buyer.stock[type];
        post(buyer,{otherExpense:old.v},{materials:old.v},'試験の生産払出','operating',S);
        buyer.stock[type]={q:0,v:0};
        buyer.interplant.siteComponents={};
        PAGE='supply';render();
        return {id:seller.id,node:node.id,type};
    }""", is_group)
    page.locator(".supply-v026-contracts > summary").click()
    page.locator("#supplier_components").select_option(setup["node"])
    page.locator("#ltQty_components").fill("5")
    page.locator('.supply-v24 [data-action="saveSupply"]').click()
    result = page.evaluate("""setup => {
        const buyer=current(),type=setup.type;
        procureNetwork(S,[]);
        const first=buyer.supply.inbound.find(x=>x.supplierId===setup.node&&x.contractV036);
        const q=first.qty,route=first.internationalV041.routeId;
        const saved=parsePayload(savePayload(S)),partner=company(setup.id,saved),f=company(buyer.id,saved);
        const openingTransit=acc(partner,'materialsTransit');
        while(ym(saved.year,saved.month)<first.due)nextMonthDate(saved);
        saved.world.DE.fx=186.25;
        const openingCost=f.stock[type].v;
        deliverMaterials(saved,f,[]);
        const buyerJournal=f.journals.find(j=>j.text==='法人間資材の検収・決済 '+first.id);
        const deals=partner.journals.filter(j=>j.text.endsWith(first.id));
        const sellerJournal=deals.find(j=>j.text.startsWith('法人間資材の売上 ')||j.text.startsWith('グループ内資材の簿価決済 '));
        const additional=f.journals.find(j=>j.text==='法人間資材の国際物流・通関 '+first.id).amount;
        const receipts=f.supply.history.filter(r=>r.firmId===partner.id);
        const newStock=f.stock[type].v-openingCost;
        const converted=Math.round(sellerJournal.amount*sellerJournal.fxAtPost/buyerJournal.fxAtPost);
        const held=acc(partner,'materialsTransit');
        const payments=saved.intercompanyTx.filter(x=>x.kind==='materialsCash'&&x.fromJournal===buyerJournal.id&&x.toJournal===sellerJournal.id);
        const expected=receipts.reduce((n,r)=>n+localFromBase(r.totalBase,f.country),0);
        return {q,route,converted,localAmount:buyerJournal.amount,additional,held,openingTransit,
            sellerAmount:sellerJournal.amount,bookCost:first.corporateTradeV037.bookCost,
            sales:deals.filter(j=>j.text.startsWith('法人間資材の売上 ')).length,pairs:payments.length,
            newStock,expected,errors:[...check(saved),...consolidate(saved).errors]};
    }""", setup)
    assert result["q"] == 5 and result["route"] == "DE/JP/sea", result
    assert result["localAmount"] == result["converted"] and result["additional"] > 0, result
    assert result["newStock"] == result["expected"] and result["held"] < result["openingTransit"], result
    assert result["pairs"] == int(is_group) and result["sales"] == int(not is_group), result
    if is_group:
        assert result["sellerAmount"] == result["bookCost"], result
    assert not result["errors"], result


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

        plant_id = page.evaluate("""() => {
            S=newGame({era:1960,country:'JP',difficulty:'easy',history:'historical',name:'海外倉庫の検証'});
            VIEW_FIRM=S.playerId;
            const f=current(),plant=beginFactoryConstruction(S,f,'small','integrated','北米組立工場','US-LAX');
            plant.construction=null;
            ensureFirmGameplay(f);
            PAGE='factory';
            render();
            return plant.id;
        }""")
        page.on("dialog", lambda dialog: dialog.accept())
        page.get_by_text("中央倉庫の保管在庫", exact=True).click()
        page.get_by_text("海外の物流拠点を取得する", exact=True).click()
        page.locator("#overseasDepotName").fill("北米港湾倉庫")
        page.locator("#overseasDepotSite").select_option("US-LAX")
        page.locator("#overseasDepotCapacity").fill("9")
        page.get_by_role("button", name="海外倉庫を取得").click()
        hub = page.evaluate("current().inventoryLogisticsV038.depots[0].id")
        page.locator("#rawShipmentTo").select_option(hub)
        page.locator("#rawShipmentType").select_option("steel")
        page.locator("#rawShipmentQuantity").fill("6")
        page.get_by_role("button", name="資材を発送").click()
        arrival = page.evaluate("""([hub,plantId]) => {
            const f=current(),pending=ensureWarehouseV038(f).rawShipments[0],opening=acc(f,'materialsTransit');
            const inbound=pending.bookCost,id=pending.id,type=pending.type;
            if(depotV038(f,hub).stock[type])return {earlyReceipt:true};
            S=parsePayload(savePayload(S));
            const buyer=current();
            while(ym(S.year,S.month)<pending.due)nextMonthDate(S);
            deliverRawShipmentsV038(S,[]);
            const warehouse=depotV038(buyer,hub);
            const landedQty=warehouse.stock[type].q,landedValue=warehouse.stock[type].v;
            const journal=buyer.journals.find(j=>j.text==='資材の通関・代替輸送 '+id)?.amount;
            const local=dispatchRawShipmentV038(S,buyer,hub,plantId,type,4);
            while(ym(S.year,S.month)<local.due)nextMonthDate(S);
            deliverRawShipmentsV038(S,[]);
            deliverRawShipmentsV038(S,[]);
            PAGE='distribution';
            render();
            return {opening,inbound,landedQty,landedValue,journal,remaining:warehouse.stock[type].q,
                plant:plantRawStockV038(buyer,plantId,type),transit:acc(buyer,'materialsTransit'),errors:check(S)};
        }""", [hub, plant_id])
        assert arrival["inbound"] == arrival["opening"] == arrival["landedValue"], arrival
        assert arrival["landedQty"] == 6 and arrival["remaining"] == 2 and arrival["plant"]["q"] == 4, arrival
        assert arrival["journal"] > 0 and not arrival["transit"] and not arrival["errors"], arrival
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.get_by_role("heading", name="輸出と現地生産の費用比較").is_visible()
        assert page.get_by_role("columnheader", name="国内生産＋輸出").is_visible()

        page.set_viewport_size({"width": 1280, "height": 900})
        check_corporate_shipment(page, is_group=False)
        check_corporate_shipment(page, is_group=True)
        assert not errors, errors
        browser.close()
    print("PASS STEP 5: route capacity, customs, rerouting, overseas depots, local supply and legacy saves")
