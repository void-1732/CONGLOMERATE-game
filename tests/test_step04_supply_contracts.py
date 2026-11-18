"""Corporate capacity reservations, call-offs and settled contract prices."""

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
        scenario = page.evaluate("""() => {
            S=newGame({era:1900,country:'JP',difficulty:'easy',history:'historical',name:'法人間契約の試験'});
            VIEW_FIRM=S.playerId;
            PAGE='group';
            render();
            document.getElementById('subName').value='第二買手';
            document.getElementById('subCountry').value='JP';
            document.getElementById('subIndustry').value='manufacturing';
            document.getElementById('subCapital').value='1400000';
            createSub();
            const second=current().id;
            const seller=initFirm(S,{name:'独立製鉄所',country:'JP',industry:'resource',seedBase:3500000});
            ensureSupplyNetwork(S);
            const bin=rawBinV032(seller,'steel');
            bin.q=12;bin.v=480000;
            post(seller,{goods:480000},{cash:480000},'長期契約試験の実在庫','operating',S);
            VIEW_FIRM=S.playerId;
            const first=current(),node=S.supplyNetwork.nodes.find(n=>n.firmId===seller.id&&n.type==='steel');
            const quota=availableContractCapacityV040(S,first,node,'steel');
            PAGE='supply';
            render();
            return {first:first.id,second,seller:seller.id,node:node.id,quota};
        }""")
        assert 1 < scenario["quota"] <= 12, scenario

        def open_contracts():
            page.locator(".supply-v026-contracts > summary").click()

        open_contracts()
        page.locator("#supplier_steel").select_option(scenario["node"])
        page.locator("#ltQty_steel").fill(str(scenario["quota"]))
        page.locator("#ltPricing_steel").select_option("fixed")
        page.locator("#ltRenew_steel").uncheck()
        page.locator('.supply-v24 [data-action="saveSupply"]').click()
        contract = page.evaluate("contractV036(current(),'steel')")
        assert contract["supplierId"] == scenario["node"] and contract["quantity"] == scenario["quota"], contract
        assert contract["priceMode"] == "fixed" and contract["unitBase"] > 0 and not contract["renew"], contract

        page.evaluate("id=>{VIEW_FIRM=id;render()}", scenario["second"])
        open_contracts()
        page.locator("#supplier_steel").select_option(scenario["node"])
        page.locator("#ltEnable_steel").check()
        page.locator("#ltQty_steel").fill("1")
        page.locator('.supply-v24 [data-action="saveSupply"]').click()
        assert page.evaluate("contractV036(current(),'steel')") is None

        settled = page.evaluate("""({scenario,contract}) => {
            VIEW_FIRM=scenario.first;
            const f=current(),seller=company(scenario.seller,S),type='steel';
            const opening=f.stock[type];
            post(f,{otherExpense:opening.v},{materials:opening.v},'検証前に在庫を消費','operating',S);
            f.stock[type]={q:0,v:0};
            S.world.JP.steelPrice*=3;
            procureNetwork(S,[]);
            const first=f.supply.inbound.find(x=>x.contractV036&&x.corporateTradeV037);
            const invoice=first.corporateTradeV037.invoice;
            const bought=f.supply.lastAttempt[type].longTermOrdered;
            const saved=parsePayload(savePayload(S)),buyer=company(f.id,saved),partner=company(seller.id,saved);
            while(ym(saved.year,saved.month)<first.due)nextMonthDate(saved);
            const openingCash=acc(buyer,'cash'),sellerCash=acc(partner,'cash');
            deliverMaterials(saved,buyer,[]);
            const boughtFrom=buyer.journals.find(j=>j.text==='法人間資材の検収・決済 '+first.id).amount;
            const soldBy=partner.journals.find(j=>j.text==='法人間資材の売上 '+first.id).amount;
            nextMonthDate(saved);
            saved.year=Math.floor(contract.end/12);saved.month=contract.end%12+1;
            return {bought,invoice,expected:localFromBase(contract.unitBase,'JP')*bought,
                boughtFrom,soldBy,buyerDebit:openingCash-acc(buyer,'cash'),sellerCredit:acc(partner,'cash')-sellerCash,
                expired:!contractActiveV036(buyer,type,saved),errors:check(saved)};
        }""", {"scenario": scenario, "contract": contract})
        assert settled["bought"] == scenario["quota"], settled
        assert settled["invoice"] == settled["expected"] == settled["boughtFrom"] == settled["soldBy"], settled
        assert settled["buyerDebit"] == settled["sellerCredit"] >= settled["invoice"], settled
        assert settled["expired"] and not settled["errors"] and not errors, settled
        browser.close()
    print("PASS STEP 4: corporate capacity limits, fixed prices, expiry, settlements and saves")
