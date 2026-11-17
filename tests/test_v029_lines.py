"""Factory line construction, investment review and plant-capacity regressions."""
import os
import shutil
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text(encoding="utf-8")
legacy_html = subprocess.check_output(
    ["git", "show", "e4d52275dac0dd34b2b8007eb157610a2fd50c2f:index.html"],
    cwd=root,
).decode()
setup = """() => {
    saveAuto=async()=>true;
    S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'設備検証'});
    VIEW_FIRM=S.playerId;
    PAGE='factory';
    render();
}"""

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
    )
    old = browser.new_page()
    old.set_content(legacy_html)
    old.evaluate(setup)
    backup = old.evaluate("savePayload(S)")
    legacy_capacity = old.evaluate("factoryCapacity(current(),S).possible")
    old.close()

    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.set_default_timeout(7000)
    js_errors = []
    page.on("pageerror", lambda e: js_errors.append(str(e)))
    page.set_content(html)
    page.evaluate(setup)
    assert page.evaluate("raw=>restore(raw)", backup)
    assert page.evaluate("factoryCapacity(current(),S).possible") == legacy_capacity

    def close_months(count=1):
        for _ in range(count):
            before = page.evaluate("S.monthCommitted")
            page.evaluate("async()=>await runMonth()")
            result = page.evaluate("""() => ({
                month:S.monthCommitted, errors:check(S), group:consolidate(S).errors,
                cf:consolidate(S).cf.reconciled, why:LAST_MONTH_DIAGNOSTIC?.message
            })""")
            assert result["month"] == before + 1 and not result["errors"] and not result["group"] and result["cf"], result

    def factory(firm=None):
        page.evaluate("id=>{VIEW_FIRM=id??S.playerId;PAGE='factory';render()}", firm)
        button = page.get_by_role("button", name="設備・人員設定")
        if button.get_attribute("aria-selected") != "true":
            button.click()
        panel = page.locator("#componentLinesPanel")
        if panel.get_attribute("open") is None:
            panel.get_by_text("部品ライン・設備投資", exact=True).click()

    def action(key, identifier=None):
        selector = f'button[data-action="{key}"]'
        if identifier is not None:
            selector += f'[data-id="{identifier}"]'
        page.locator(selector).click()

    def last_job():
        return page.evaluate("S.partEconomy.aiInvestmentPlans.at(-1)")

    def get_job(plan):
        return page.evaluate("id=>S.partEconomy.aiInvestmentPlans.find(j=>j.planId===id)", plan["planId"])

    # Release the reference part designs using the existing development system.
    page.evaluate("""() => {
        const f=current();
        f.staff.designEngineers=12;
        for(const family of ['engine','transmission','chassis','body','electronics']){
            const values={...PART_FAMILIES[family].defaults};
            if(family==='engine')values.cost=2200;
            submitPartProject(S,f,{family,name:PART_FAMILIES[family].label,values,parent:null,output:null});
            const p=f.partOperations.engineering.projects.at(-1);
            p.status='APPROVED';p.budget=p.estimate;
        }
    }""")
    close_months(2)
    engine = page.evaluate("partKey(S.partEconomy.specs.find(p=>p.family==='engine'))")
    plant_id = page.evaluate("current().plants[0].id")
    page.evaluate("""key=>{
        const f=current(),part=partRecord(S,key);
        submitPartProject(S,f,{family:'engine',name:part.name,values:{...part.values,torque:190},parent:key,output:null});
        const p=f.partOperations.engineering.projects.at(-1);
        p.status='APPROVED';p.budget=p.estimate;
        const lines=Object.fromEntries(S.partEconomy.specs.map(p=>[p.family,partKey(p)]));
        f.partOperations.designBoms=[{id:'BOM-'+S.partEconomy.nextSerial++,name:'試験構成',lines,approvedAt:ym(S.year,S.month)}];
    }""", engine)
    close_months()
    revised = page.evaluate("partKey(S.partEconomy.specs.find(p=>p.family==='engine'&&p.revision===2))")

    assert page.evaluate("""key=>{
        const trial=structuredClone(S), f=company(trial.playerId,trial),p=f.plants[0],spec=partRecord(trial,key);
        trial.month=7;
        const cash=acc(f,'cash');
        const financing=reviewLineInvestment(trial,f,p,spec);
        if(financing.reason)throw Error(financing.reason);
        proposeAIComponentLines(trial,[]);
        const proposal=trial.partEconomy.aiInvestmentPlans[0];
        if(proposal?.source!=='ai'||proposal.state!=='PROPOSED'||acc(f,'cash')!==cash)return false;
        const rival=trial.firms.find(x=>x.id!==f.id);
        trial.playerId=rival.id;
        try{approveLineJob(trial,f,proposal);return false;}catch(e){}
        trial.playerId=f.id;
        approveLineJob(trial,f,proposal);
        return proposal.state==='BUILDING'&&acc(f,'constructionAssets')===proposal.cost;
    }""", engine)
    assert page.evaluate("""key=>{
        const trial=structuredClone(S),f=company(trial.playerId,trial);
        f.staff.production=0;
        return reviewLineInvestment(trial,f,f.plants[0],partRecord(trial,key)).reason.includes('人員');
    }""", engine)

    factory()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    page.locator("#lineSpec").select_option(engine)
    action("lineReview", plant_id)
    assert page.get_by_text("投資審査：", exact=False).is_visible()
    page.locator("#lineSpec").select_option(engine)
    page.locator("#lineDelta").fill("999")
    action("linePropose", plant_id)
    assert page.evaluate("S.partEconomy.aiInvestmentPlans.length") == 0
    page.locator("#lineDelta").fill("10")
    action("linePropose", plant_id)
    add = last_job()
    assert add["state"] == "PROPOSED"
    assert page.evaluate("acc(current(),'constructionAssets')") == 0
    before = page.evaluate("({cash:acc(current(),'cash'),ppe:acc(current(),'ppe'),p:current().plants[0].capacity})")
    action("lineApprove", add["planId"])
    after = page.evaluate("({cash:acc(current(),'cash'),ppe:acc(current(),'ppe'),cip:acc(current(),'constructionAssets')})")
    assert after == {"cash": before["cash"]-add["cost"], "ppe": before["ppe"], "cip": add["cost"]}
    assert page.evaluate("current().plants[0].componentLines===undefined")
    factory()
    assert page.get_by_text("竣工予定", exact=False).is_visible()

    save = page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)", save)
    assert page.evaluate("acc(current(),'constructionAssets')") == add["cost"]
    close_months(3)
    assert get_job(add)["state"] == "BUILDING"
    close_months()
    assert get_job(add)["state"] == "COMPLETE"
    assert page.evaluate("acc(current(),'constructionAssets')") == 0
    assert page.evaluate("current().plants[0].capacity") == before["p"]
    assert page.evaluate("current().plants[0].componentLines[0].capacity") == 10

    def job(kind, key, delta="1"):
        factory()
        pending = page.evaluate("""line=>S.partEconomy.aiInvestmentPlans
            .filter(j=>j.lineId===line&&j.state==='PROPOSED').map(j=>j.planId)""", add["lineId"])
        for identifier in pending:
            action("lineCancel", identifier)
        page.locator("#lineKind").select_option(kind)
        page.locator("#lineTarget").select_option(add["lineId"])
        page.locator("#lineSpec").select_option(key)
        page.locator("#lineDelta").fill(delta)
        action("linePropose", plant_id)
        plan = last_job()
        assert plan["kind"] == kind and plan["state"] == "PROPOSED"
        action("lineApprove", plan["planId"])
        return plan

    retrofit = job("RETROFIT", revised)
    assert page.evaluate("lineOutputPlan(S,current(),current().plants[0])[0].possible") == 0
    close_months(3)
    assert get_job(retrofit)["state"] == "COMPLETE"
    assert page.evaluate("current().plants[0].componentLines[0].specKey") == revised
    expand = job("EXPAND_LINE", revised, "5")
    close_months(3)
    assert page.evaluate("current().plants[0].componentLines[0].capacity") == 15
    assert page.evaluate("current().plants[0].capacity") == before["p"]
    assert get_job(expand)["state"] == "COMPLETE"
    assert page.evaluate("""()=>{
        const bad=structuredClone(S),f=company(bad.playerId,bad);
        f.plants[0].componentLines[0].capacity++;
        const prior=S;
        return !restore(savePayload(bad))&&S===prior;
    }""")
    assert page.evaluate("current().models.every(m=>m.componentMode==='legacy')")

    # Licensed equipment can start, but the inspection must wait if the scope expires during work.
    page.evaluate("PAGE='group';render()")
    page.locator("#subName").fill("ライン協力工場")
    page.locator("#subCountry").select_option("JP")
    page.locator("#subIndustry").select_option("manufacturing")
    page.locator("#subCapital").fill("650000")
    action("createSub")
    child = page.evaluate("current().id")
    assert child != page.evaluate("S.playerId")
    page.evaluate("""([child,key])=>{
        const f=company(child,S),part=partRecord(S,key),month=ym(S.year,S.month);
        S.partEconomy.licenses.push({licenseId:'LIC-'+S.partEconomy.nextSerial++,groupId:S.playerId,
            specKey:key,licensorFirmId:part.ownerFirmId,licenseeFirmId:child,grant:'manufacture',
            plantId:f.plants[0].id,proposedAt:month,approvedAt:month,termMonths:1,endedAt:null,endReason:null});
    }""", [child, engine])
    factory(child)
    page.locator("#lineSpec").select_option(engine)
    page.locator("#lineDelta").fill("4")
    action("linePropose")
    licensed = last_job()
    action("lineApprove", licensed["planId"])
    close_months(4)
    assert get_job(licensed)["state"] == "INSPECTION"
    assert page.evaluate("id=>acc(company(id,S),'constructionAssets')", child) == licensed["cost"]
    factory(child)
    assert page.get_by_text("この工場で製造できる許諾がありません", exact=True).is_visible()
    action("lineCancel", licensed["planId"])
    assert get_job(licensed)["state"] == "CANCELLED"
    assert page.evaluate("id=>acc(company(id,S),'constructionAssets')", child) == 0
    close_months()
    page.set_viewport_size({"width": 1440, "height": 900})
    factory()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    assert not js_errors, js_errors
    browser.close()

print("PASS: factory lines, commissioning, investment approval, cash/PPE/CF, license hold, save and legacy capacity")
