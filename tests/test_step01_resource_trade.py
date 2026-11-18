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


if __name__ == "__main__":
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(HTML.read_text(encoding="utf-8"), wait_until="domcontentloaded")
        test_reserved_deliveries(page)
        test_zero_book_delivery(page)
        assert not errors, errors
        browser.close()
    print("PASS STEP 1: corporate reservations, matched books, zero-cost physical receipt")
