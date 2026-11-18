"""Physical component trading, usage-based royalties and internal elimination."""
from pathlib import Path
import os
import shutil
import subprocess

from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text()
prior_html = subprocess.check_output(
    ["git", "show", "4f6b15b83ed4df281d70dcd025249b43a5af056d:index.html"], cwd=root, text=True
)
setup = """() => {
    saveAuto=async()=>true;
    S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'部品供給本社'});
    VIEW_FIRM=S.playerId;
    PAGE='group';
    render();
}"""

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
    )
    prior = browser.new_page()
    prior.set_content(prior_html)
    prior.evaluate(setup)
    old_save = prior.evaluate("savePayload(S)")
    prior.close()
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.set_default_timeout(8000)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_content(html)
    page.evaluate(setup)
    assert page.evaluate("raw=>restore(raw)", old_save)
    page.evaluate("PAGE='group';render()")
    page.locator("#subName").fill("部品購入子会社")
    page.locator("#subCountry").select_option("JP")
    page.locator("#subIndustry").select_option("manufacturing")
    page.locator("#subCapital").fill("700000")
    page.locator('[data-action="createSub"]').click()
    buyer = page.evaluate("current().id")
    seller = page.evaluate("S.playerId")
    assert buyer != seller

    def firm(identifier, section="product"):
        page.evaluate("([id,section])=>{VIEW_FIRM=id;PAGE=section;PRODUCT_VIEW='design';render()}", [identifier, section])

    def action(name, identifier=None):
        selector = f'button[data-action="{name}"]'
        if identifier:
            selector += f'[data-id="{identifier}"]'
        page.locator(selector).click()

    def open_section(summary):
        text = page.get_by_text(summary, exact=True)
        if text.locator("xpath=..").get_attribute("open") is None:
            text.click()

    def month():
        previous = page.evaluate("S.monthCommitted")
        page.evaluate("async()=>await runMonth()")
        result = page.evaluate("""()=>{
            const g=consolidate(S);
            return {month:S.monthCommitted,err:check(S),group:g.errors,cf:g.cf.reconciled,
                diagnostic:LAST_MONTH_DIAGNOSTIC?.message};
        }""")
        assert result["month"] == previous + 1 and not result["err"] and not result["group"] and result["cf"], result

    page.evaluate("""([seller,buyer])=>{
        for(const [id,families] of [[seller,['engine']],[buyer,['transmission','chassis','body','electronics']]]){
            const f=company(id,S);
            f.staff.designEngineers=12;
            f.staff.production=100;
            f.auto=false;
            for(const model of f.models)f.plans[model.id]=0;
            for(const family of families){
                submitPartProject(S,f,{family,name:PART_FAMILIES[family].label,values:{...PART_FAMILIES[family].defaults},
                  parent:null,output:null});
                const p=f.partOperations.engineering.projects.at(-1);
                p.status='APPROVED';p.budget=p.estimate;
            }
        }
    }""", [seller, buyer])
    month()
    month()
    assert page.evaluate("S.partEconomy.specs.length") == 5
    data = page.evaluate("""([seller,buyer])=>{
        const a=company(seller,S),b=company(buyer,S);
        b.plants[0].capacity=60;syncPlant(b);
        for(const f of [a,b])for(const spec of S.partEconomy.specs.filter(x=>x.ownerFirmId===f.id)){
            const job=proposeLineJob(S,f,f.plants[0],'ADD_LINE','',partKey(spec),8);
            approveLineJob(S,f,job);
        }
        return {key:partKey(S.partEconomy.specs.find(x=>x.family==='engine')),destination:b.plants[0].id,model:b.models[0].id};
    }""", [seller, buyer])
    for _ in range(4):
        month()
    page.evaluate("""([seller,buyer])=>{
        for(const id of [seller,buyer]){
            const f=company(id,S),plant=f.plants[0];
            for(const line of plant.componentLines)f.partOperations.productionPlans.push({
                plantId:plant.id,lineId:line.lineId,quantity:8,destinationId:null
            });
            for(const type of SUPPLY_TYPES){
                post(f,{materials:2000},{cash:2000},'検証用資材','operating',S);
                const stock=f.stock[type]??={q:0,v:0};stock.q+=200;stock.v+=2000;
            }
        }
    }""", [seller, buyer])
    month()

    def order(quantity):
        firm(buyer)
        open_section("法人間の部品売買・使用料")
        page.locator("#partOrderQty").fill(str(quantity))
        page.locator("#partOrderPrice").fill("2000")
        action("partOrderPlace")
        return page.evaluate("S.partEconomy.orders.at(-1).orderId")

    first = order(1)
    assert page.evaluate("S.partEconomy.tradeEvents.length") == 0
    action("partOrderCancel", first)
    assert page.evaluate("S.partEconomy.orders[0].state==='CANCELLED'")
    assert page.evaluate("check(S).length") == 0
    ordered = order(5)
    assert page.evaluate("S.partEconomy.orders.at(-1).state==='ORDERED'")
    assert page.evaluate("""() => {
        const order = S.partEconomy.orders.at(-1), seller = company(order.seller,S);
        const view = inventoryLocationsV038(S,seller).locations.get(order.from);
        const reserved = view.items.get('componentStock:'+order.specKey+':reserved');
        return reserved.quantity === order.quantity && reserved.value === order.bookCost;
    }""")
    page.locator("#partOrderQty").fill("999")
    action("partOrderPlace")
    assert page.evaluate("S.partEconomy.orders.length") == 2
    assert page.evaluate("acc(current(),'partPayable')") == 0
    firm(seller)
    open_section("法人間の部品売買・使用料")
    action("partOrderDispatch", ordered)
    transit = page.evaluate("S.partEconomy.orders.at(-1)")
    assert transit["state"] == "IN_TRANSIT"
    assert page.evaluate("acc(current(),'componentTransit')") == transit["bookCost"] + transit["freight"]
    assert page.evaluate("S.partEconomy.tradeEvents.length") == 0

    # Stock purchased with no licence cannot enter the buyer's approved composition.
    assert page.evaluate("""([buyer,key])=>{
        const f=company(buyer,S);
        return !matchingPartLicense(S,f,partRecord(S,key),'designUse');
    }""", [buyer, data["key"]])
    firm(seller)
    open_section("共同開発・部品ライセンス")
    page.locator("#partLicenseSpec").select_option(data["key"])
    page.locator("#partLicenseFirm").select_option(buyer)
    page.locator("#partLicenseGrant").select_option("designUse")
    page.locator("#partLicenseRate").fill("120")
    action("partLicensePropose")
    license_id = page.evaluate("S.partEconomy.licenses.at(-1).licenseId")
    firm(buyer)
    open_section("共同開発・部品ライセンス")
    action("partLicenseApprove", license_id)
    assert page.evaluate("S.partEconomy.tradeEvents.length") == 0

    for _ in range(transit["lead"] + 1):
        month()
    sale = page.evaluate("S.partEconomy.tradeEvents[0]")
    assert sale["kind"] == "component" and sale["amount"] == 1_000_000 and not sale["settlement"]
    margin = sale["amount"] - sale["cost"]
    assert margin > 0
    assert page.evaluate("consolidate(S).spot.partClaimsEliminated") == sale["amount"]
    assert page.evaluate("consolidate(S).pl.unrealizedProfit") == margin
    assert page.evaluate("consolidate(S).periodPL.partInternalSalesEliminated") == sale["amount"]
    firm(seller, "consolidated")
    assert page.get_by_text("部品・使用料の内部売掛買掛消去", exact=True).is_visible()
    assert page.get_by_text("うち部品売買・使用料", exact=True).is_visible()
    assert page.evaluate("""([seller,buyer,amount])=>acc(company(seller,S),'partReceivable')===amount&&
        -acc(company(buyer,S),'partPayable')===amount""", [seller, buyer, sale["amount"]])
    assert page.evaluate("""([seller,buyer,expected])=>{
        const members=[company(seller,S),company(buyer,S)];
        const a=partConsolidation(S,members,[],{},S.monthCommitted,{[seller]:0.8,[buyer]:1});
        return Math.round(a.nci)===Math.round(expected*0.2);
    }""", [seller, buyer, margin])
    snapshot = page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)", snapshot)

    # Keep the finished units on hand for one month to check continued deferral.
    page.evaluate("""([buyer,data,licenseId])=>{
        const f=company(buyer,S);
        const lines=Object.fromEntries(S.partEconomy.specs.map(p=>[p.family,partKey(p)]));
        const bom={id:'BOM-'+S.partEconomy.nextSerial++,name:'使用料検証',lines,
            approvedAt:ym(S.year,S.month),useLicenses:{engine:licenseId}};
        f.partOperations.designBoms=[bom];
        f.partOperations.approvedModels=[{modelId:data.model,plantId:data.destination,bomId:bom.id}];
        // Changing a model to detailed BOM production requires its old-style
        // finished goods to be cleared first. Increased raw-material supply
        // can make previous legacy production accumulate on this fixture.
        const legacy=f.goods[data.model]||{q:0,v:0};
        if(legacy.q||legacy.v){
            const carryingValue=legacy.v;
            legacy.q=0;legacy.v=0;
            if(carryingValue)post(f,{otherExpense:carryingValue},{goods:carryingValue},
                'BOM方式切替前の旧車在庫処分（検証用）','operating',S);
        }
        f.models[0].componentMode='detailed';
        f.plans[data.model]=5;
        sellMonthly=()=>{};
    }""", [buyer, data, license_id])
    month()
    royalty = page.evaluate("S.partEconomy.tradeEvents.find(x=>x.kind==='royalty')")
    batch = page.evaluate("id=>company(id,S).partOperations.vehicleLots[0]", buyer)
    assert royalty["quantity"] == batch["initialQty"] == 5
    assert royalty["amount"] == 5 * 12000 and royalty["batchId"] == batch["batchId"]
    assert batch["initialCost"] >= royalty["amount"] + sum(x["cost"] for x in batch["inputs"])
    assert page.evaluate("""({buyer,batch}) => {
        const f = company(buyer,S), view = inventoryLocationsV038(S,f);
        const item = view.locations.get(batch.plantId).items.get('goods:'+batch.modelId);
        return item.quantity === batch.quantity && item.value === batch.cost &&
            !view.warehouse.items.has('goods:'+batch.modelId);
    }""", {"buyer": buyer, "batch": batch})
    assert page.evaluate("S.partEconomy.tradeEvents[0].settlement.settlementId").endswith("-PAY")
    assert page.evaluate("consolidate(S).cf.internalCashLegs") >= 1
    assert page.evaluate("consolidate(S).pl.unrealizedProfit") == margin + royalty["amount"]

    # Insufficient cash preserves the debt and can be retried with the same event.
    assert page.evaluate("""buyer=>{
        const trial=structuredClone(S),f=company(buyer,trial),e=trial.partEconomy.tradeEvents[1];
        f.ledger.cash=0;nextMonthDate(trial);settlePartClaims(trial);
        return e.settlement===null&&-acc(f,'partPayable')===e.amount;
    }""", buyer)
    export_due = page.evaluate("""([buyer,model])=>{
        const f=company(buyer,S);
        f.plans[model]=0;
        const quantity=f.goods[model].q;
        exportShipment(S,f,model,quantity,6000,'UK',[]);
        return f.distribution.outbound.at(-1).due;
    }""", [buyer, data["model"]])
    assert page.evaluate("consolidate(S).pl.unrealizedProfit") == margin + royalty["amount"]
    while page.evaluate("ym(S.year,S.month)") < export_due:
        month()
        assert page.evaluate("consolidate(S).pl.unrealizedProfit") == margin + royalty["amount"]
    month()
    assert page.evaluate("consolidate(S).pl.unrealizedProfit") == 0
    assert page.evaluate("S.partEconomy.tradeEvents.length") == 2
    assert page.evaluate("S.partEconomy.tradeEvents.every(e=>e.settlement)")
    assert page.evaluate("""()=>{
        const bad=structuredClone(S);
        bad.partEconomy.tradeEvents.push(structuredClone(bad.partEconomy.tradeEvents[1]));
        const prior=S;
        return !restore(savePayload(bad))&&S===prior;
    }""")
    # An independent seller dispatches a real priced order, and a recall restores lots.
    assert page.evaluate("""([seller,buyer,data])=>{
        const trial=structuredClone(S),a=company(seller,trial),b=company(buyer,trial);
        trial.playerId=buyer;
        a.auto=true;
        const quantity=()=>bomPlantLots(a,a.plants[0].id,data.key).reduce((n,l)=>n+l.quantity,0);
        const original=quantity(),cash=acc(a,'cash'),count=trial.partEconomy.tradeEvents.length;
        const order=placePartOrder(trial,b,a,a.plants[0],b.plants[0],data.key,1,200000);
        if(!order.external||quantity()!==original-1)return false;
        dispatchExternalPartOrders(trial);
        if(order.state!=='IN_TRANSIT'||acc(a,'componentTransit')!==order.bookCost+order.freight)return false;
        cancelPartOrder(trial,order);
        return quantity()===original&&acc(a,'cash')===cash-order.freight&&
            acc(a,'componentTransit')===0&&trial.partEconomy.tradeEvents.length===count&&!check(trial).length;
    }""", [seller, buyer, data])
    firm(buyer)
    open_section("法人間の部品売買・使用料")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    page.set_viewport_size({"width": 1440, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    assert not errors, errors
    browser.close()

print("PASS: reservation, receipt, settlement, usage royalties, inventory and export elimination, NCI and saves")
