"""Exercise BOM manufacturing, lot transfers, assembly and booked cost."""
import os
import shutil
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text(encoding="utf-8")
previous = subprocess.check_output(
    ["git", "show", "8bea85f25f41061c527e7f33011a887eca405024:index.html"],
    cwd=root,
).decode()
start = """() => {
    saveAuto=async()=>true;
    S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'BOM検証'});
    VIEW_FIRM=S.playerId;
    current().plans[current().models[0].id]=0;
    PAGE='product';
    render();
}"""
families = ("engine", "transmission", "chassis", "body", "electronics")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
    )
    old = browser.new_page()
    old.set_content(previous)
    old.evaluate(start)
    old_save = old.evaluate("savePayload(S)")
    old.close()
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.set_default_timeout(7000)
    js_errors = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    page.set_content(html)
    page.evaluate(start)
    assert not page.evaluate("raw=>restore(raw)", old_save)  # SPEC-168 rejects incompatible saves
    assert page.evaluate("current().models[0].componentMode==='legacy'")

    def months(count=1):
        for _ in range(count):
            previous_month = page.evaluate("S.monthCommitted")
            page.evaluate("async()=>await runMonth()")
            result = page.evaluate("""()=>({
                errors:check(S),group:consolidate(S).errors,cf:consolidate(S).cf.reconciled,
                month:S.monthCommitted,reason:LAST_MONTH_DIAGNOSTIC?.message
            })""")
            assert result["month"] == previous_month + 1 and not result["errors"] and not result["group"] and result["cf"], result

    page.evaluate("""families=>{
        const f=current();
        f.staff.designEngineers=12;
        f.staff.production=120;
        for(const family of families){
            submitPartProject(S,f,{family,name:PART_FAMILIES[family].label,
                values:{...PART_FAMILIES[family].defaults},parent:null,output:null});
            const project=f.partOperations.engineering.projects.at(-1);
            project.status='APPROVED';
            project.budget=project.estimate;
        }
    }""", families)
    months(2)
    assert page.evaluate("S.partEconomy.specs.length") == len(families)
    ids = page.evaluate("""() => {
        const f=current(),source=f.plants[0],model=f.models[0],destination={...structuredClone(source),
            id:'P'+S.seq++,name:'BOM最終組立工場',kind:'assembly',capacity:50,assetTracked:0};
        f.plants.push(destination);
        f.factoryOps.mode='detailed';
        syncPlant(f);
        const lines=Object.fromEntries(S.partEconomy.specs.map(spec=>[spec.family,partKey(spec)]));
        const bom={id:'BOM-'+S.partEconomy.nextSerial++,name:'試験部品表',lines,approvedAt:ym(S.year,S.month)};
        f.partOperations.designBoms=[bom];
        for(const key of Object.values(lines)){
            const job=proposeLineJob(S,f,source,'ADD_LINE','',key,6);
            approveLineJob(S,f,job);
        }
        return {source:source.id,to:destination.id,bom:bom.id,model:model.id,lines};
    }""")
    months(4)
    assert page.evaluate("current().plants[0].componentLines.length") == len(families)
    assert page.evaluate("current().goods[current().models[0].id].q") == 0

    page.evaluate("PAGE='product';PRODUCT_VIEW='design';render()")
    page.get_by_text("BOM車両組立の設定", exact=True).click()
    page.locator("#bomModel").select_option(ids["model"])
    page.locator("#bomDesign").select_option(ids["bom"])
    page.locator("#bomAssemblyPlant").select_option(ids["to"])
    page.locator('[data-action="bomAssemblySave"]').click()
    assert page.evaluate("current().models[0].componentMode==='detailed'")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")

    page.evaluate("PAGE='facilityProduction';render()")
    page.locator('[data-factory-view-v026="production"]').click()
    panel = page.locator("#bomShopPanel")
    panel.get_by_text("BOM部品生産・ロット在庫・物流", exact=True).click()
    lines = page.evaluate("current().plants[0].componentLines")
    for line in lines:
        page.locator("#bomLine").select_option(line["lineId"])
        page.locator("#bomLineQty").fill("6")
        if line["specKey"] != ids["lines"]["engine"]:
            page.locator("#bomLineDest").select_option(ids["to"])
        page.locator('[data-action="bomLineSave"]').click()
    assert page.evaluate("current().partOperations.productionPlans.length") == 5

    # Legacy production continues in parallel and cannot consume the new BOM parts.
    page.evaluate("""ids=>{
        const f=current();
        for(const type of SUPPLY_TYPES){
            const amount=2000;
            post(f,{materials:amount},{cash:amount},'検証用資材','operating',S);
            const stock=f.stock[type]??={q:0,v:0};stock.q+=200;stock.v+=amount;
        }
        // Supply genuine legacy modules in their existing inventory and site ledger.
        for(const type of V21_MODULE_TYPES){
            post(f,{materials:2000},{cash:2000},'検証用従来部品','operating',S);
            f.stock[type].q+=200;f.stock[type].v+=2000;
            moduleAtV21(f,ids.source)[type]+=200;
        }
        const m={...structuredClone(f.models[0]),id:'M'+S.seq++,name:'従来方式',componentMode:'legacy'};
        f.models.push(m);f.goods[m.id]={q:0,v:0};f.plans[m.id]=2;
        f.plans[ids.model]=3;
    }""", ids)
    months()
    assert page.evaluate("current().models[0].bomLast.built") == 0
    assert page.evaluate("current().models[0].bomLast.shortages.length") == 5
    assert page.evaluate("current()._productionByModel[current().models[1].id]") > 0
    assert page.evaluate("S.partEconomy.shipments.length") == 4

    page.evaluate("PAGE='factory';render()")
    page.locator('[data-factory-view-v026="production"]').click()
    if panel.get_attribute("open") is None:
        panel.get_by_text("BOM部品生産・ロット在庫・物流", exact=True).click()
    page.locator("#bomShipmentSpec").select_option(ids["lines"]["engine"])
    page.locator("#bomShipmentDest").select_option(ids["to"])
    page.locator("#bomShipmentQty").fill("100")
    page.locator('[data-action="bomShipment"]').click()
    assert page.evaluate("S.partEconomy.shipments.length") == 4
    page.locator("#bomShipmentQty").fill("3")
    page.locator('[data-action="bomShipment"]').click()
    shipment = page.evaluate("S.partEconomy.shipments.find(x=>x.specKey===current().partOperations.designBoms[0].lines.engine)")
    assert shipment["arrivedAt"] is None and shipment["freight"] > 0
    assert shipment["value"] == shipment["freight"] + sum(x["cost"] for x in shipment["inputs"])
    assert page.evaluate("current().partOperations.inventoryLots.every(x=>x.plantId!==S.partEconomy.shipments[0].to)")

    snapshot = page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)", snapshot)
    assert page.evaluate("acc(current(),'componentTransit')===S.partEconomy.shipments.reduce((n,x)=>n+x.value,0)")
    months(shipment["due"] - shipment["departedAt"] + 1)
    batch = page.evaluate("current().partOperations.vehicleLots[0]")
    assert batch["initialQty"] > 0 and batch["plantId"] == ids["to"]
    assert batch["initialCost"] > sum(x["cost"] for x in batch["inputs"])
    assert len(batch["inputs"]) >= 5
    assert page.evaluate("""()=>current().partOperations.vehicleLots.some(l=>l.inputs.some(x=>
        current().partOperations.inventoryLots.find(p=>p.lotId===x.id).origin.shipId))""")
    months(3)
    assert page.evaluate("""()=>current().journals.some(j=>j.bomSources?.length)||
        current().distribution.outbound.some(x=>x.bomSources?.length)""")
    assert page.evaluate("check(parsePayload(savePayload(S))).length") == 0
    assert page.evaluate("""()=>{
        const bad=structuredClone(S);
        const lot=company(bad.playerId,bad).partOperations.inventoryLots[0];
        lot.initialCost++;
        const prev=S;
        return !restore(savePayload(bad))&&S===prev;
    }""")
    page.set_viewport_size({"width": 1440, "height": 900})
    page.evaluate("PAGE='factory';render()")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    assert not js_errors, js_errors
    browser.close()

print("PASS: mixed legacy/BOM output, line lots, transit, save, assembly and sale cost provenance")
