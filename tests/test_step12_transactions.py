"""STEP 12 end-to-end transaction, rejection, accounting and saved-state regression.

Run: python tests/test_step12_transactions.py
Chromium tests independent scenarios; no external market data.
"""
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")


def new_page(browser, era):
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.set_default_timeout(12000)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_content(HTML, wait_until="domcontentloaded")
    page.evaluate(
        """era => {
          saveAuto=async()=>true;
          S=newGame({era,country:'JP',difficulty:'easy',history:'historical',name:'STEP12本社'});
          VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='dashboard';render();
        }""", era,
    )
    assert page.evaluate("check(S)") == []
    return page, errors


def show(page, route, company_id=None):
    page.evaluate("""([route,id])=>{
      if(id)VIEW_FIRM=id;PAGE=route;render();
    }""", [route, company_id])
    assert page.evaluate("PAGE") == route


def clean(page):
    report = page.evaluate("""() => {
       const errors=check(S), con=consolidate(S);
       return {errors,conErrors:con.errors,
          bsDifference:con.spot.checkDifference,
          cf:con.cf.reconciled,month:S.monthCommitted};
    }""")
    assert not report["errors"] and not report["conErrors"], report
    assert report["bsDifference"] == 0, report
    return report


def save_roundtrip(page):
    snapshot = page.evaluate("""() => ({
      year:S.year,month:S.month,firmCount:S.firms.length,
      parent:S.playerId,shareDeals:S.maDeals.length,
      reorgPlans:(S.groupMergerPlans||[]).length,
      plantCount:current().plants.length
    })""")
    payload = page.evaluate("savePayload(S)")
    assert len(payload) > 1000
    assert page.evaluate("raw=>restore(raw)", payload)
    now = page.evaluate("""() => ({
      year:S.year,month:S.month,firmCount:S.firms.length,
      parent:S.playerId,shareDeals:S.maDeals.length,
      reorgPlans:(S.groupMergerPlans||[]).length,
      plantCount:current().plants.length
    })""")
    assert now == snapshot, (snapshot, now)
    clean(page)


def close_month(page, count=1):
    for _ in range(count):
        previous = page.evaluate("S.monthCommitted")
        page.evaluate("async()=>await runMonth()")
        assert page.evaluate("S.monthCommitted") == previous+1
        assert page.evaluate("check(S)") == []
        c = page.evaluate("consolidate(S)")
        assert c["errors"] == [] and c["spot"]["checkDifference"] == 0
        assert c["cf"]["reconciled"], c["cf"]


def add_subsidiary(page, parent_id, name, industry="manufacturing"):
    show(page, "corporateSubsidiaries", parent_id)
    page.locator("#subName").fill(name)
    page.locator("#subCountry").select_option("JP")
    page.locator("#subIndustry").select_option(industry)
    min_base = page.evaluate("Math.round(450000*eraCostFactor(S.year))")
    page.locator("#subCapital").fill(str(int(min_base * 1.35)))
    count = page.evaluate("S.firms.length")
    page.locator('[data-action="createSub"]').click()
    assert page.evaluate("S.firms.length") == count + 1
    child = page.evaluate("current().id")
    assert page.evaluate("current().owners[0].id") == parent_id
    clean(page)
    return child


def test_operations_and_ma(browser, era):
    page, errors = new_page(browser, era)
    parent = page.evaluate("S.playerId")

    # Factory construction changes cash and the plant register atomically.
    show(page, "facilityExpansion", parent)
    initial = page.evaluate("""()=>({
      cash:acc(current(),'cash'),plants:current().plants.length
    })""")
    page.locator("#factoryName").fill("STEP12検証工場")
    page.locator("#factoryKind").select_option("engine")
    page.locator("#factoryScale").select_option("small")
    page.locator('[data-action="factoryBuild"]').click()
    after = page.evaluate("""()=>({
      cash:acc(current(),'cash'),plants:current().plants.length,
      built:current().plants.find(p=>p.name==='STEP12検証工場')
    })""")
    assert after["cash"] < initial["cash"]
    assert after["plants"] == initial["plants"]+1
    assert after["built"]["construction"]["monthsLeft"] > 0
    clean(page)
    show(page, "facilityExpansion", parent)
    page.locator("#factoryName").fill("STEP12検証工場")
    page.locator("#factoryKind").select_option("engine")
    page.locator("#factoryScale").select_option("small")
    page.locator('[data-action="factoryBuild"]').click()
    assert page.evaluate("current().plants.length") == after["plants"]
    assert page.evaluate("acc(current(),'cash')") == after["cash"]

    # Supply contract: a valid changed safety-stock horizon must persist;
    # an invalid duplicate backup supplier must be rejected without partial writes.
    show(page, "supplyContracts", parent)
    old_contracts = page.evaluate("structuredClone(current().supply.contracts)")
    opts = page.locator("#buffer_steel option").evaluate_all(
        "(els)=>els.map(x=>x.value)"
    )
    assert len(opts) >= 2, opts
    desired = next(x for x in opts if float(x) != float(old_contracts["steel"].get("safetyMonths", 0)))
    page.locator("#buffer_steel").select_option(desired)
    page.locator('[data-action="saveSupply"]').click()
    assert page.evaluate("current().supply.contracts.steel.safetyMonths") == float(desired)
    updated_contracts = page.evaluate("structuredClone(current().supply.contracts)")
    show(page, "supplyContracts", parent)
    main = page.locator("#supplier_steel").input_value()
    page.evaluate("""supplier=>{
       const b=document.getElementById('backup_steel');
       if(![...b.options].some(o=>o.value===supplier)){
         const opt=document.createElement('option');opt.value=supplier;b.appendChild(opt);
       }
       b.value=supplier;
    }""", main)
    page.locator('[data-action="saveSupply"]').click()
    assert page.evaluate("current().supply.contracts") == updated_contracts
    clean(page)

    # Distribution contract increases capacity and charges the cost to the firm.
    show(page, "distribution", parent)
    old_capacity = int(page.locator("#capacity_US").input_value())
    cash_before = page.evaluate("acc(current(),'cash')")
    page.locator("#capacity_US").fill(str(old_capacity+1))
    page.locator('[data-action="saveDistribution"]').click()
    assert page.evaluate("current().distribution.contracts.US.capacity") == old_capacity+1
    assert page.evaluate("acc(current(),'cash')") < cash_before
    clean(page)

    # External-share M&A: invalid price is rejected; accepted trade moves
    # ownership and cash but does not move the target's assets or liabilities.
    target = page.evaluate("""()=> {
      const buyer=current();
      const candidates=S.firms.filter(f=>f.id!==buyer.id&&
       !controller(S,f.id)&&f.owners.some(o=>o.id==='PUBLIC'&&o.econ>=.1));
      const selected=candidates.filter(f=>{
       try{return maQuote(S,buyer,f,5,2.5).accepted}catch{return false}
      }).sort((a,b)=>maValuation(S,a).reference-maValuation(S,b).reference);
      return selected[0]?.id || null;
    }""")
    assert target, "No affordable M&A target for test"
    show(page, "ma", parent)
    page.evaluate("id=>{MA_VIEW.target=id;render()}", target)
    page.locator("#maPercent").fill("5")
    page.locator("#maMultiplier").fill("60")
    pre = page.evaluate("""id=>({
       buyerCash:acc(current(),'cash'),buyerInvestment:acc(current(),'investment'),
       sellerShare:company(id).owners.find(o=>o.id==='PUBLIC')?.econ||0,
       targetCash:acc(company(id),'cash'), deals:S.maDeals.length
    })""", target)
    page.locator('[data-action="maBuy"]').click()
    rejected = page.evaluate("""id=>({
       buyerCash:acc(current(),'cash'),buyerInvestment:acc(current(),'investment'),
       sellerShare:company(id).owners.find(o=>o.id==='PUBLIC')?.econ||0,
       targetCash:acc(company(id),'cash'), deals:S.maDeals.length
    })""", target)
    assert rejected == pre, (pre, rejected)
    page.locator("#maMultiplier").fill("250")
    page.locator('[data-action="maQuote"]').click()
    page.locator('[data-action="maBuy"]').click()
    bought = page.evaluate("""id=>({
       buyerCash:acc(current(),'cash'),buyerInvestment:acc(current(),'investment'),
       sellerShare:company(id).owners.find(o=>o.id==='PUBLIC')?.econ||0,
       ourShare:company(id).owners.find(o=>o.id===S.playerId)?.econ||0,
       targetCash:acc(company(id),'cash'), deals:S.maDeals.length
    })""", target)
    assert bought["deals"] == pre["deals"] + 1
    assert bought["buyerCash"] < pre["buyerCash"]
    assert bought["buyerInvestment"] > pre["buyerInvestment"]
    assert abs(bought["ourShare"]-0.05) < 0.000001
    assert abs(bought["sellerShare"]-(pre["sellerShare"]-0.05)) < 0.000001
    assert bought["targetCash"] == pre["targetCash"]
    clean(page)
    save_roundtrip(page)
    close_month(page, 3)
    assert not errors, errors
    print(f"PASS STEP12 {era}: factory, contract, sales, M&A, rejection, 3 month closes")
    page.close()


def test_corporate_transfer_and_merger(browser):
    page, errors = new_page(browser, 1900)
    parent = page.evaluate("S.playerId")
    seller = add_subsidiary(page, parent, "STEP12株式売り手")
    # A newly incorporated subsidiary spends its seed capital on equipment;
    # fund the second-tier incorporation with an actual intercompany loan.
    show(page, "corporateSubsidiaries", parent)
    page.locator("#loanSubs").select_option(seller)
    page.locator("#loanAmount").fill("1000000")
    cash_before = page.evaluate("id=>acc(company(id),'cash')", seller)
    page.locator('[data-action="groupLoan"]').click()
    assert page.evaluate("id=>acc(company(id),'cash')",seller) > cash_before
    clean(page)
    grandson = add_subsidiary(page, seller, "STEP12孫会社")
    # Parent is direct 100% owner of seller, qualifying for 100%-valuation
    # transfer under the game's 70%-direct-ownership rule.
    show(page, "ma", parent)
    page.evaluate("id=>{MA_VIEW.target=id;render()}", grandson)
    page.locator("#maCorpSeller").select_option(seller)
    page.locator("#maCorpPercent").fill("25")
    page.locator("#maCorpMode").select_option("group")
    page.locator("#maCorpFactor").fill("100")
    quote = page.evaluate("""([seller,target])=>
       corporateShareQuote(S,S.playerId,target,seller,25,'group',1)
    """, [seller, grandson])
    assert quote["accepted"], {
        k: quote[k] for k in ("consent","affordable","reserve","total")
    }
    before = page.evaluate("""([seller,target])=>({
      buyerCash:acc(company(S.playerId),'cash'),
      sellerCash:acc(company(seller),'cash'),
      owner:company(target).owners.find(x=>x.id===seller).econ,
      deals:S.maDeals.length
    })""", [seller, grandson])
    page.locator('[data-action="maCorpBuy"]').click()
    after = page.evaluate("""([seller,target])=>({
      buyerCash:acc(company(S.playerId),'cash'),
      sellerCash:acc(company(seller),'cash'),
      owner:company(target).owners.find(x=>x.id===seller).econ,
      buyerOwner:company(target).owners.find(x=>x.id===S.playerId)?.econ||0,
      deals:S.maDeals.length
    })""", [seller, grandson])
    assert after["buyerCash"] < before["buyerCash"]
    assert after["sellerCash"] > before["sellerCash"]
    assert abs(after["owner"] - (before["owner"]-.25)) < 1e-6
    assert abs(after["buyerOwner"]-.25) < 1e-6
    assert after["deals"] == before["deals"]+1
    clean(page)
    save_roundtrip(page)

    # Negative share-quote: a group transfer under 100% valuation must be
    # rejected when the buyer does not directly own 70% of the seller.
    rejection = page.evaluate("""([seller,target])=>{
       const trial=structuredClone(S),buyer=company(S.playerId,trial),
             holding=company(seller,trial).owners.find(o=>o.id===buyer.id);
       holding.econ=.69;holding.vote=.69;
       try{corporateShareQuote(trial,buyer.id,target,seller,1,'group',1);return false}
       catch{return true}
    }""", [seller, grandson])
    assert rejection, "Invalid 69%-owned seller was allowed the group discount"

    # Two direct, wholly owned same-industry subsidiaries can start a
    # multi-month merger, with progress committed only through runMonth().
    sibling = add_subsidiary(page, parent, "STEP12統合先")
    other = add_subsidiary(page, parent, "STEP12統合元")
    show(page, "corporateMerger", parent)
    page.locator("#mergeGroupParent").select_option(parent)
    page.locator("#mergeSiblingSource").select_option(other)
    page.locator("#mergeSiblingTarget").select_option(sibling)
    page.locator('[data-action="mergeSibling"]').click()
    plan = page.evaluate("""([a,b])=>{
       const p=S.groupMergerPlans.at(-1);
       return {from:p.fromId,to:p.toId,status:p.status,duration:p.duration,
         progress:p.progress,id:p.id}
    }""", [other, sibling])
    assert plan["from"] == other and plan["to"] == sibling
    assert plan["status"] == "pending" and plan["duration"] in (2, 5, 12)
    duplicate_rejected = page.evaluate("""([from,to])=>{
       try{startGroupMerger(structuredClone(S),S.playerId,from,to);return false}
       catch{return true}
    }""", [other,sibling])
    assert duplicate_rejected, "Overlapping merger was accepted"
    clean(page)
    for _ in range(plan["duration"]+1):
        close_month(page)
        state = page.evaluate("id=>S.groupMergerPlans.find(x=>x.id===id).status",plan["id"])
        if state == "completed":
            break
    state = page.evaluate("""([id,from,to])=>({
      status:S.groupMergerPlans.find(p=>p.id===id)?.status,
      source:company(from)?.reorgStatus,
      sourceExists:!!company(from),
      targetExists:!!company(to)
    })""", [plan["id"],other,sibling])
    assert state["status"] == "completed", state
    assert state["sourceExists"] and state["targetExists"], state
    clean(page)
    save_roundtrip(page)
    assert not errors, errors
    print(f"PASS STEP12: corporate 70% rule, seller cash, 25% sale, merger {plan['duration']} months, save")
    page.close()


if __name__ == "__main__":
    with sync_playwright() as pw:
        browser=pw.chromium.launch(
          executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
          args=["--no-sandbox"]
        )
        try:
            for era in (1900,2020):
                test_operations_and_ma(browser,era)
            test_corporate_transfer_and_merger(browser)
        finally:
            browser.close()
    print("PASS STEP12 transaction regression")
