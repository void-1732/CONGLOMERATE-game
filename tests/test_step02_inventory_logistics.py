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
        opening = page.evaluate("""() => ({
            cash:acc(current(),'cash'), materials:acc(current(),'materials'),
            steel:current().stock.steel.q, transit:acc(current(),'materialsTransit')
        })""")
        page.locator("#rawShipmentTo").select_option(migrated["second"])
        page.locator("#rawShipmentQuantity").fill("99999")
        page.get_by_role("button", name="資材を発送").click()
        assert page.evaluate("current().inventoryLogisticsV038.rawShipments.length") == 0
        page.locator("#rawShipmentQuantity").fill("5")
        page.get_by_role("button", name="資材を発送").click()
        dispatched = page.evaluate("""() => {
            const f = current(), shipment = f.inventoryLogisticsV038.rawShipments[0];
            const point = {leadMonths:2,target:100};
            return {shipment, steel:f.stock.steel.q, cash:acc(f,'cash'),
                materials:acc(f,'materials'), transit:acc(f,'materialsTransit'),
                forecast:resourcePurchaseNeedV034(f, 'steel', S, point).dueByLead,
                errors:check(S)};
        }""")
        shipment = dispatched["shipment"]
        assert shipment["quantity"] == 5 and dispatched["steel"] == opening["steel"] - 5, dispatched
        assert opening["cash"] - dispatched["cash"] == shipment["freight"] > 0, dispatched
        assert opening["materials"] - dispatched["materials"] == shipment["bookCost"] > 0, dispatched
        assert dispatched["transit"] - opening["transit"] == shipment["bookCost"], dispatched
        assert dispatched["forecast"] == 5 and not dispatched["errors"], dispatched
        assert page.evaluate("""id => {
            const f = structuredClone(current()), plant = f.plants.find(p => p.id === id);
            f.plants[0].paused = true;
            plant.kind = 'integrated';
            syncPlant(f);
            return factoryMaterialAvailableV038(f,plant,'steel') === 0 &&
                planFactoryOutput(f,25,S).produced === 0 && f.stock.steel.q > 0;
        }""", migrated["second"])
        completed = page.evaluate("""id => {
            S = parsePayload(savePayload(S));
            nextMonthDate(S);
            deliverRawShipmentsV038(S,[]);
            const waiting = current().inventoryLogisticsV038.rawShipments.length;
            nextMonthDate(S);
            deliverRawShipmentsV038(S,[]);
            deliverRawShipmentsV038(S,[]);
            const f = current(), stock = plantRawStockV038(f,id,'steel');
            return {waiting, outstanding:f.inventoryLogisticsV038.rawShipments.length,
                onSite:stock.q, value:stock.v, total:f.stock.steel.q,
                materials:acc(f,'materials'), remainingTransit:acc(f,'materialsTransit'),
                receipts:f.journals.filter(j => j.text.startsWith('資材の国内検収')).length,
                errors:check(S)};
        }""", migrated["second"])
        assert completed == {
            "waiting": 1, "outstanding": 0, "onSite": 5, "value": shipment["bookCost"],
            "total": opening["steel"], "materials": opening["materials"],
            "remainingTransit": opening["transit"], "receipts": 1, "errors": [],
        }, completed
        used = page.evaluate("""id => {
            const f = current(), onSite = f.plants.find(p=>p.id===id);
            f.plants[0].paused = true;
            onSite.kind = 'integrated';
            syncPlant(f);
            const before = centralRawStockV038(f,'steel').q;
            const required = materialRequirement(f.models[0].design,f).steel;
            laborAndPlant(S,[],'auto');
            return {produced:f._produced, remaining:plantRawStockV038(f,id,'steel').q,
                warehouseUnchanged:centralRawStockV038(f,'steel').q === before,
                required, errors:check(S)};
        }""", migrated["second"])
        assert used["produced"] > 0 and used["warehouseUnchanged"], used
        assert abs(used["remaining"] - (5 - used["produced"] * used["required"])) <= 1e-8, used
        assert not used["errors"], used
        remote = page.evaluate("""() => {
            S = newGame({era:1900, country:'JP', difficulty:'easy',
                history:'historical', name:'国内自動補充の試験'});
            VIEW_FIRM = S.playerId;
            const f = current();
            const plant = beginFactoryConstruction(S,f,'small','integrated','生産拠点','JP-OSA');
            plant.construction = null;
            f.plants[0].paused = true;
            syncPlant(f);
            PAGE = 'factory';
            render();
            return plant.id;
        }""")
        page.get_by_text("中央倉庫の保管在庫", exact=True).click()
        page.locator("#rawWarehouseAuto").check()
        page.get_by_role("button", name="倉庫設定を保存").click()
        automatic = page.evaluate("""async id => {
            let peakShipments=0, advanced=0;
            for (let i=0;i<6;i++) {
                const month=S.monthCommitted;
                await runMonth();
                if (S.monthCommitted !== month+1) return {diagnostic:LAST_MONTH_DIAGNOSTIC?.message};
                advanced++;
                peakShipments = Math.max(peakShipments,current().inventoryLogisticsV038.rawShipments.length);
            }
            const f=current(),storage=f.journals.filter(j=>j.text==='原材料の月次保管費').length;
            const receipts=f.journals.filter(j=>j.text.startsWith('資材の国内検収')).length;
            const auto=f.inventoryLogisticsV038.autoRefill;
            const runs=f.history.some(x=>x.produced>0);
            return {advanced,peakShipments,storage,receipts,auto,runs,errors:check(S),
                targetExists:f.plants.some(p=>p.id===id)};
        }""", remote)
        assert automatic["advanced"] == automatic["storage"] == 6 and automatic["auto"], automatic
        assert automatic["peakShipments"] >= 2 and automatic["receipts"] > 0, automatic
        assert automatic["runs"] and automatic["targetExists"] and not automatic["errors"], automatic
        assert not errors, errors
        browser.close()
    print("PASS STEP 2: warehouse migration, per-plant inventory, domestic shipment and offline UI")
