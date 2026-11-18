"""Physical resource inventory and accounting regressions in Chromium."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"


def test_reserved_deliveries(page):
    result = page.evaluate("""() => {
        S = newGame({era:1900, country:'JP', difficulty:'normal',
            history:'historical', name:'企業間資材テスト'});
        const buyer = company(S.playerId, S);
        const seller = initFirm(S, {name:'採掘企業', country:'JP',
            industry:'resource', seedBase:3000000});
        seller.owners = [{id:buyer.id, econ:1, vote:1}];
        seller.shareBlocks = [];
        ensureSupplyNetwork(S);
        const type = 'steel', supplierId = 'CORP:' + seller.id + ':' + type;
        const bin = rawBinV032(seller, type);
        post(seller, {goods:4000}, {cash:4000}, '予約対象の実在庫', 'operating', S);
        bin.q = 4;
        bin.v = 4000;
        const month = ym(S.year, S.month);
        buyer.supply.inbound.push({id:'corp-order', type, origin:'JP',
            supplierId, qty:6, totalBase:600, due:month});
        const initialQty = buyer.stock[type].q;
        const initialValue = buyer.stock[type].v;
        const initialBuyerCash = acc(buyer, 'cash');
        const initialSellerCash = acc(seller, 'cash');
        const initialPayables = buyer.payables.length;
        deliverMaterials(S, buyer, []);
        const partial = {
            received:buyer.stock[type].q - initialQty,
            inventoryCost:buyer.stock[type].v - initialValue,
            sellerStock:bin.q,
            sellerBook:acc(seller, 'goods'),
            buyerPaid:initialBuyerCash - acc(buyer, 'cash'),
            sellerReceived:acc(seller, 'cash') - initialSellerCash,
            remaining:rawCommittedV032(S, supplierId, type)
        };
        ensureV09Firm(seller, S);
        seller.lifecycle.phase = 'withdrawn';
        ensureSupplyNetwork(S);
        const events = [];
        nextMonthDate(S);
        deliverMaterials(S, buyer, events);
        return {
            partial,
            received:buyer.stock[type].q - initialQty,
            payablesAdded:buyer.payables.length - initialPayables,
            remaining:rawCommittedV032(S, supplierId, type),
            event:events.some(e => e.includes('予約解除')),
            errors:check(S)
        };
    }""")
    assert result == {
        "partial": {
            "received": 4, "inventoryCost": 4000, "sellerStock": 0,
            "sellerBook": 0, "buyerPaid": 4000, "sellerReceived": 4000,
            "remaining": 2,
        },
        "received": 4, "payablesAdded": 0, "remaining": 0,
        "event": True, "errors": [],
    }, result


def test_zero_book_delivery(page):
    result = page.evaluate("""() => {
        S = newGame({era:1900, country:'JP', difficulty:'normal',
            history:'historical', name:'丸め検収テスト'});
        const buyer = company(S.playerId, S);
        const type = 'steel', market = npcMarketV033(S, 'JP', type);
        const {q, v} = buyer.stock[type], payables = buyer.payables.length;
        market.stock--;
        market.dispatchedTotal++;
        buyer.supply.inbound.push({id:'rounding-order', type, origin:'JP',
            supplierId:npcIdV033('JP', type), qty:1, totalBase:0.001,
            due:ym(S.year, S.month), npcReserved:true});
        deliverMaterials(S, buyer, []);
        const saved = parsePayload(savePayload(S));
        const restored = company(saved.playerId, saved);
        return {quantity:restored.stock[type].q - q, value:restored.stock[type].v - v,
            payableCount:restored.payables.length - payables, errors:check(saved)};
    }""")
    assert result == {"quantity": 1, "value": 0, "payableCount": 0, "errors": []}, result


def test_resource_production(page):
    result = page.evaluate("""() => {
        S = newGame({era:1900, country:'JP', difficulty:'normal',
            history:'historical', name:'資源生産テスト'});
        const seller = initFirm(S, {name:'銅・鉄の試験鉱山', country:'JP',
            industry:'resource', seedBase:3000000});
        ensureRawV032(seller);
        seller.reserveUnits = 30;
        seller.rawOpsV032.weights = Object.fromEntries(RAW_TYPES_V032.map(
            t => [t, t === 'steel' ? 1 : t === 'copper' ? 3 : 0]));
        seller.plants[0].condition = 100;
        seller.staff.production = 120;
        ensureV09Firm(seller, S);
        seller.hr.skill = 90;
        const id = seller.id;
        const legacy = savePayload(S);
        S = parsePayload(legacy);
        const mine = company(id, S);
        const openingRights = acc(mine, 'resourceRights');
        const oldGoods = JSON.stringify(mine.goods);
        const initial = resourceDepositsV037(mine);
        const migrated = {steel:initial.steel.remaining, copper:initial.copper.remaining,
            total:mine.reserveUnits, untouchedGoods:JSON.stringify(mine.goods) === oldGoods};
        const zeroCashOutput = planResourceProductionV037(S, mine, 45, 0).quantity;
        const fullStock = structuredClone(mine);
        for (const type of RAW_TYPES_V032) rawBinV032(fullStock, type).q = 10000;
        const excessStockOutput = planResourceProductionV037(S, fullStock, 45, acc(mine, 'cash')).quantity;
        laborAndPlant(S, [], 'resource');
        const month = mine.rawOpsV032.lastProduction;
        const bins = RAW_TYPES_V032.map(t => rawBinV032(mine, t));
        const production = {byType:month.byType, feed:month.feed,
            capacity:Object.values(month.capacityByType).reduce((a, b) => a+b, 0),
            stock:bins.reduce((a, b) => a+b.q, 0),
            binsCost:bins.reduce((a, b) => a+b.v, 0),
            zeroQtyCost:bins.filter(x => !x.q).reduce((a, b) => a+b.v, 0),
            goods:acc(mine, 'goods'), wip:acc(mine, 'wip'), rights:acc(mine, 'resourceRights'),
            depreciation:-acc(mine, 'accdep'), openingRights};
        const saved = parsePayload(savePayload(S));
        const restored = company(id, saved);
        nextMonthDate(saved);
        laborAndPlant(saved, [], 'resource');
        const empty = {output:restored._produced, reserve:restored.reserveUnits,
            stock:RAW_TYPES_V032.reduce((n,t) => n+rawBinV032(restored,t).q,0),
            wip:acc(restored, 'wip'), errors:check(saved)};
        VIEW_FIRM = id;
        PAGE = 'factory';
        render();
        return {migrated, production, empty, zeroCashOutput, excessStockOutput};
    }""")
    assert result["migrated"] == {
        "steel": 7, "copper": 23, "total": 30, "untouchedGoods": True
    }, result
    production = result["production"]
    assert production["capacity"] == 45, result
    assert production["byType"] == {
        "steel": 7, "rubber": 0, "aluminum": 0, "copper": 23, "glass": 0, "chemicals": 0
    }, result
    assert production["feed"]["steel"] == 14 and production["feed"]["copper"] == 46, result
    assert production["stock"] == 30, result
    assert production["goods"] == production["binsCost"] and production["zeroQtyCost"] == 0, result
    assert production["rights"] == production["wip"] == 0, result
    assert production["goods"] > production["openingRights"] + production["depreciation"], result
    assert result["zeroCashOutput"] == result["excessStockOutput"] == 0, result
    assert result["empty"] == {"output": 0, "reserve": 0, "stock": 30, "wip": 0, "errors": []}, result
    assert page.get_by_role("heading", name="資源の採取・加工").is_visible()
    assert page.get_by_text("銅鉱石の採掘・選鉱・製錬").is_visible()


def test_resource_investment(page):
    page.evaluate("""async () => {
        saveAuto = async () => true;
        S = newGame({era:1900, country:'JP', difficulty:'easy',
            history:'historical', name:'資源投資のテスト'});
        VIEW_FIRM = S.playerId;
        await runMonth();
        PAGE = 'group';
        render();
        document.getElementById('subName').value = '開発試験鉱山';
        document.getElementById('subCountry').value = 'JP';
        document.getElementById('subIndustry').value = 'resource';
        document.getElementById('subCapital').value = '1600000';
        createSub();
        if (current().industry !== 'resource') throw Error('資源子会社の設立に失敗');
        PAGE = 'factory';
        render();
    }""")
    opening = page.evaluate("""() => ({
        cash:acc(current(), 'cash'), rights:acc(current(), 'resourceRights'),
        reserves:current().reserveUnits, capacity:current().plant.capacity
    })""")
    page.locator("#resourceDevelopmentType").select_option("copper")
    page.locator("#resourceDevelopmentUnits").fill("500")
    page.get_by_role("button", name="資源開発に着工").click()
    started = page.evaluate("""() => {
        const f = current(), job = f.rawOpsV032.developments[0];
        return {cash:acc(f, 'cash'), rights:acc(f, 'resourceRights'), reserves:f.reserveUnits, job};
    }""")
    assert started["job"]["units"] == 500 and started["reserves"] == opening["reserves"], started
    assert opening["cash"] - started["cash"] == started["rights"] - opening["rights"] == started["job"]["cost"]

    page.get_by_text("新工場を建設する", exact=True).click()
    page.locator("#factoryName").fill("第二加工設備")
    page.locator('[data-action="factoryBuild"]:visible').click()
    under_construction = page.evaluate("""() => ({
        live:current().plant.capacity,
        pending:current().plants.find(p => p.name === '第二加工設備').construction.monthsLeft
    })""")
    assert under_construction == {"live": opening["capacity"], "pending": 2}, under_construction

    for i in range(5):
        result = page.evaluate("""async () => {
            const previous = S.monthCommitted;
            await runMonth();
            const f = current(), deposit = f.rawOpsV032.deposits.copper;
            return {committed:S.monthCommitted === previous + 1,
                errors:check(S), consolidation:consolidate(S).errors,
                diagnostic:LAST_MONTH_DIAGNOSTIC?.message,
                development:deposit.developed || 0,
                capacity:f.plant.capacity,
                rights:acc(f,'resourceRights')};
        }""")
        assert result["committed"] and not result["errors"] and not result["consolidation"], (i, result)
        if i < 4:
            assert result["development"] == 0 and result["rights"] >= started["job"]["cost"], (i, result)
        assert result["capacity"] == opening["capacity"] + (0 if i == 0 else 25), (i, result)
    assert result["development"] == 500, result
    assert page.evaluate("""() => {
        const clone = parsePayload(savePayload(S)), f = company(current().id, clone);
        return f.rawOpsV032.developments.length === 0 &&
            f.rawOpsV032.deposits.copper.developed === 500 &&
            f.journals.filter(j => j.text === '資源開発の着工：銅').length === 1;
    }""")


def test_external_supply(page):
    fixture = page.evaluate("""() => {
        S = newGame({era:1900, country:'JP', difficulty:'normal',
            history:'historical', name:'独立企業との仕入テスト'});
        VIEW_FIRM = S.playerId;
        const buyer = current(), type = 'steel';
        const seller = initFirm(S, {name:'独立資源会社', country:'JP',
            industry:'resource', seedBase:3000000});
        post(seller, {goods:50000}, {cash:50000}, '売手の検証用現物在庫', 'operating', S);
        ensureSupplyNetwork(S);
        rawBinV032(seller,type).q = 10;
        rawBinV032(seller,type).v = 50000;
        post(buyer, {otherExpense:buyer.stock[type].v}, {materials:buyer.stock[type].v}, '試験用の開始在庫を消費', 'operating', S);
        buyer.stock[type] = {q:0, v:0};
        const fallback = npcMarketV033(S,'JP',type);
        fallback.dispatchedTotal += fallback.stock;
        fallback.stock = 0;
        PAGE = 'supply';
        render();
        return {seller:seller.id, node:'CORP:' + seller.id + ':' + type};
    }""")
    assert page.get_by_role("heading", name="内製と仕入れの比較").is_visible()
    page.locator(".supply-v026-contracts > summary").click()
    page.locator("#supplier_steel").select_option(fixture["node"])
    page.locator("#ltEnable_steel").uncheck()
    page.locator('.supply-v24 [data-action="saveSupply"]').click()
    shipment = page.evaluate("""fixture => {
        const buyer = current(), seller = company(fixture.seller, S);
        if (!buyer.supply.contracts.steel.corporateSourcesV037.includes(fixture.node)) {
            throw Error('画面から独立企業を選択できなかった');
        }
        procureNetwork(S, []);
        const staged = buyer.supply.inbound.find(x => x.corporateTradeV037);
        procureNetwork(S, []);
        return {id:staged.id, qty:staged.qty, invoice:staged.corporateTradeV037.invoice,
            cost:staged.corporateTradeV037.bookCost, transit:acc(seller,'goodsTransit'),
            sellerQty:rawBinV032(seller,'steel').q, buyerQty:buyer.stock.steel.q,
            duplicates:buyer.supply.inbound.filter(x => x.corporateTradeV037).length,
            errors:check(S)};
    }""", fixture)
    assert shipment["qty"] == 10 and shipment["sellerQty"] == shipment["buyerQty"] == 0, shipment
    assert shipment["cost"] == shipment["transit"] == 50000 and shipment["invoice"] > 50000, shipment
    assert shipment["duplicates"] == 1 and not shipment["errors"], shipment
    settled = page.evaluate("""({fixture,shipment}) => {
        S = parsePayload(savePayload(S));
        const buyer = current(), seller = company(fixture.seller,S);
        const cash = acc(buyer,'cash');
        post(buyer,{otherExpense:cash},{cash},'決済資金の不足を検証','operating',S);
        nextMonthDate(S);
        deliverMaterials(S,buyer,[]);
        const deferred = buyer.supply.inbound.find(x => x.id === shipment.id);
        if (!deferred || buyer.stock.steel.q || acc(seller,'goodsTransit') !== shipment.cost) {
            throw Error('資金不足時に出荷在庫を保存できなかった');
        }
        post(buyer,{cash},{capital:cash},'決済資金の投入','financing',S);
        const sellerCash = acc(seller,'cash');
        nextMonthDate(S);
        deliverMaterials(S,buyer,[]);
        return {received:buyer.stock.steel.q, inventory:buyer.stock.steel.v,
            paid:cash-acc(buyer,'cash'), receivedMoney:acc(seller,'cash')-sellerCash,
            revenue:-acc(seller,'sales'), cogs:acc(seller,'cogs'), transit:acc(seller,'goodsTransit'),
            outstanding:buyer.supply.inbound.some(x => x.id === shipment.id), errors:check(S)};
    }""", {"fixture": fixture, "shipment": shipment})
    assert settled == {
        "received": 10, "inventory": shipment["invoice"], "paid": shipment["invoice"],
        "receivedMoney": shipment["invoice"], "revenue": shipment["invoice"],
        "cogs": 50000, "transit": 0, "outstanding": False, "errors": [],
    }, settled

    returned = page.evaluate("""fixture => {
        const buyer = current(), seller = company(fixture.seller,S), type = 'steel';
        post(seller,{goods:1400},{cash:1400},'売手の返品検証用現物在庫','operating',S);
        const bin = rawBinV032(seller,type);
        bin.q = 2; bin.v = 1400;
        const node = S.supplyNetwork.nodes.find(n => n.id === fixture.node);
        const shipment = dispatchCorporateSupplyV037(S,buyer,seller,node,2,0);
        buyer.supply.inbound.push(shipment);
        buyer.lifecycle.phase = 'withdrawn';
        nextMonthDate(S);
        deliverMaterials(S,buyer,[]);
        return {q:bin.q,v:bin.v,transit:acc(seller,'goodsTransit'),buyerQty:buyer.stock.steel.q,errors:check(S)};
    }""", fixture)
    assert returned == {"q": 2, "v": 1400, "transit": 0, "buyerQty": 10, "errors": []}, returned


def test_competitor_investment(page):
    result = page.evaluate("""() => {
        S = newGame({era:1900, country:'JP', difficulty:'normal',
            history:'historical', name:'競合の資源設備投資'});
        const depleted = initFirm(S,{name:'埋蔵量の少ない鉱山',country:'JP',
            industry:'resource',seedBase:4000000});
        depleted.reserveUnits = 6;
        ensureRawV032(depleted);
        depleted.rawOpsV032.lastProduction = {byType:{steel:4},unitCosts:{steel:10}};
        const cashBefore = acc(depleted,'cash'),rightsBefore = acc(depleted,'resourceRights');
        rivalMonthlyStrategy(S,depleted,[]);
        const project = depleted.rawOpsV032.developments[0];
        const funded = cashBefore-acc(depleted,'cash') === project.cost &&
            acc(depleted,'resourceRights')-rightsBefore === project.cost &&
            depleted.reserveUnits === 6;
        rivalMonthlyStrategy(S,depleted,[]);

        const expanding = initFirm(S,{name:'人員が充足している鉱山',country:'JP',
            industry:'resource',seedBase:8000000});
        ensureRawV032(expanding);
        expanding.staff.production = 100;
        expanding.monthly.units = 45;
        expanding.monthly.profit = 100000;
        expanding.rawOpsV032.lastProduction = {
            byType:Object.fromEntries(RAW_TYPES_V032.map(t => [t,7])),
            unitCosts:Object.fromEntries(RAW_TYPES_V032.map(t => [t,100]))
        };
        const before = acc(expanding,'ppe');
        rivalMonthlyStrategy(S,expanding,[]);
        const plant = expanding.plants.find(p => p.construction);
        return {project:project.type, funded,
            projects:depleted.rawOpsV032.developments.length,
            newCapacity:plant?.capacity, activeCapacity:expanding.plant.capacity,
            invested:acc(expanding,'ppe')>before, errors:check(S)};
    }""")
    assert result == {
        "project": "steel", "funded": True, "projects": 1, "newCapacity": 25,
        "activeCapacity": 45, "invested": True, "errors": [],
    }, result


if __name__ == "__main__":
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_page()
        page.context.set_offline(True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("dialog", lambda dialog: dialog.accept())
        page.set_content(HTML.read_text(encoding="utf-8"), wait_until="domcontentloaded")
        test_reserved_deliveries(page)
        test_zero_book_delivery(page)
        test_resource_production(page)
        test_resource_investment(page)
        test_external_supply(page)
        test_competitor_investment(page)
        assert not errors, errors
        browser.close()
    print("PASS STEP 1: physical delivery, resource production, accounting, saves and offline UI")
