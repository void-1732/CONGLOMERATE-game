"""Warehouse migration and per-plant inventory views on legacy saves."""

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
        page = browser.new_page(offline=True, viewport={"width": 390, "height": 840})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(HTML.read_text(encoding="utf-8"), wait_until="domcontentloaded")
        migrated = page.evaluate("""() => {
            saveAuto = async () => true;
            const old = newGame({era:1900, country:'JP', difficulty:'normal',
                history:'historical', name:'倉庫移行の試験'});
            const buyer = company(old.playerId,old);
            const first = buyer.plants[0];
            const second = beginFactoryConstruction(old,buyer,'small','engine','第二工場','JP-OSA');
            second.construction = null;
            ensureFirmGameplay(buyer);

            post(buyer,{materials:10001},{cash:10001},'既存在庫の試験','operating',old);
            buyer.stock.components.q += 5;
            buyer.stock.components.v += 7001;
            buyer.interplant.siteComponents[first.id] = 3;
            buyer.stock.moduleEngine = {q:7,v:3000};
            moduleAtV21(buyer,second.id).moduleEngine = 7;
            const model = buyer.models[0],finished = {q:2,v:42000};
            post(buyer,{goods:42000},{cash:42000},'旧方式の完成品','operating',old);
            buyer.goods[model.id] = finished;
            for (const f of old.firms) delete f.inventoryLogisticsV038;
            const balanceBefore = JSON.stringify(buyer.ledger);
            const stockBefore = JSON.stringify(buyer.stock);
            const goodsBefore = JSON.stringify(buyer.goods);

            S = parsePayload(savePayload(old));
            VIEW_FIRM = S.playerId;
            const f = current(), view = inventoryLocationsV038(S,f);
            const parts = view.locations.get(first.id).items.get('materials:components');
            const modules = view.locations.get(second.id).items.get('materials:moduleEngine');
            const group = [view.warehouse,...view.locations.values()].flatMap(l => Array.from(l.items.values()));
            const entries = account => group.filter(bin => bin.account === account).reduce((sum,bin) => sum + bin.value,0);
            const after = parsePayload(savePayload(S)), roundTrip = company(f.id,after);
            PAGE = 'factory';
            render();
            return {
                warehouse:view.warehouse.siteId, warehouseSteel:view.warehouse.items.get('materials:steel').quantity,
                stockSteel:f.stock.steel.q, parts:parts.quantity, modules:modules.quantity,
                moduleValue:modules.value, materialsMatch:entries('materials')===acc(f,'materials'),
                goodsMatch:entries('goods')===acc(f,'goods'),
                dataMatch:JSON.stringify(f.ledger)===balanceBefore&&JSON.stringify(f.stock)===stockBefore&&
                    JSON.stringify(f.goods)===goodsBefore&&JSON.stringify(roundTrip.stock)===stockBefore,
                second:second.id, errors:check(after)
            };
        }""")
        assert migrated["warehouse"] == "JP-TOK", migrated
        assert migrated["warehouseSteel"] == migrated["stockSteel"] > 0, migrated
        assert migrated["parts"] == 3 and migrated["modules"] == 7 and migrated["moduleValue"] == 3000, migrated
        assert migrated["materialsMatch"] and migrated["goodsMatch"] and migrated["dataMatch"], migrated
        assert not migrated["errors"], migrated
        page.get_by_text("中央倉庫の保管在庫", exact=True).click()
        assert page.get_by_role("heading", name="中央倉庫", exact=True).is_visible()
        page.locator(f'[data-factory-select="{migrated["second"]}"]').click()
        page.get_by_text("この工場の保管在庫", exact=True).click()
        assert page.get_by_role("rowheader", name="エンジンユニット", exact=True).is_visible()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
        assert not errors, errors
        browser.close()
    print("PASS STEP 2: warehouse migration, per-plant parts, inventory value and offline UI")
