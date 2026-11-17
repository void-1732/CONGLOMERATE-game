"""Joint development and part license regression through the v0.28 game UI."""
import os
import shutil
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text(encoding="utf-8")
old_html = subprocess.check_output(
    ["git", "show", "84ae7d68f914827a84e7f0bf29fdf7c3d0bde7b8:index.html"],
    cwd=root,
).decode()
setup = """() => {
    saveAuto=async()=>true;
    S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'開発本社'});
    VIEW_FIRM=S.playerId;
    PAGE='product';
    render();
}"""

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
    )
    old = browser.new_page()
    old.set_content(old_html)
    old.evaluate(setup)
    previous = old.evaluate("savePayload(S)")
    old.close()
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.set_default_timeout(7000)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content(html)
    page.evaluate(setup)
    assert page.evaluate("raw=>restore(raw)", previous)
    parent = page.evaluate("S.playerId")

    def show_company(firm, section="product"):
        page.evaluate("([firm,section])=>{VIEW_FIRM=firm;PAGE=section;render()}", [firm, section])

    def create_company(name):
        show_company(parent, "group")
        page.locator("#subName").fill(name)
        page.locator("#subCountry").select_option("JP")
        page.locator("#subIndustry").select_option("manufacturing")
        page.locator("#subCapital").fill("650000")
        page.locator('[data-action="createSub"]').click()
        return page.evaluate("current().id")

    def finish_month():
        last_month = page.evaluate("S.monthCommitted")
        page.evaluate("async()=>await runMonth()")
        report = page.evaluate("""() => ({
            month:S.monthCommitted,
            errors:check(S),
            consolidated:consolidate(S).errors,
            cf:consolidate(S).cf.reconciled,
            diagnostic:LAST_MONTH_DIAGNOSTIC?.message
        })""")
        assert report["month"] == last_month + 1 and not report["errors"] and not report["consolidated"] and report["cf"], report

    def contracts():
        details = page.locator("#partContracts")
        if details.get_attribute("open") is None:
            details.locator("summary").click()

    def action(key, identifier=None):
        selector = f'[data-action="{key}"]'
        if identifier is not None:
            selector += f'[data-id="{identifier}"]'
        page.locator(selector).click()

    child = create_company("組立子会社")
    partner = create_company("研究協力会社")
    assert len({parent, child, partner}) == 3
    # Prepare the part catalogue through the real monthly release path.
    page.evaluate("""([parent,child]) => {
        for(const [id,families] of [[parent,['engine']],[child,['transmission','chassis','body','electronics']]]){
            const f=company(id,S);
            f.staff.designEngineers=12;
            for(const family of families){
                submitPartProject(S,f,{family,name:PART_FAMILIES[family].label,values:{...PART_FAMILIES[family].defaults},parent:null,output:null});
                const p=f.partOperations.engineering.projects.at(-1);
                p.budget=p.estimate;
                p.status='APPROVED';
            }
        }
    }""", [parent, child])
    finish_month()
    assert page.evaluate("S.partEconomy.specs.length") == 5
    engine = page.evaluate("partKey(S.partEconomy.specs.find(p=>p.family==='engine'))")
    plant = page.evaluate("id=>company(id,S).plants[0].id", child)

    def propose_license(grant, term=12, factory=None):
        show_company(parent)
        contracts()
        page.locator("#partLicenseSpec").select_option(engine)
        page.locator("#partLicenseFirm").select_option(child)
        page.locator("#partLicenseGrant").select_option(grant)
        page.locator("#partLicenseMonths").fill(str(term))
        if factory:
            page.locator("#partLicensePlant").select_option(factory)
        action("partLicensePropose")
        return page.evaluate("S.partEconomy.licenses.at(-1).licenseId")

    read_id = propose_license("read")
    design_id = propose_license("designUse", term=1)
    factory_id = propose_license("manufacture", factory=plant)
    assert page.locator('[data-action="partLicenseApprove"]').count() == 0
    show_company(child)
    contracts()
    action("partLicenseApprove", read_id)
    action("partLicenseApprove", factory_id)
    assert page.evaluate("""([key,plant])=>{
        const f=current(),p=partRecord(S,key);
        return !!matchingPartLicense(S,f,p,'read')&&!!matchingPartLicense(S,f,p,'manufacture',plant)&&
            !matchingPartLicense(S,f,p,'manufacture','unknown')&&!matchingPartLicense(S,f,p,'designUse');
    }""", [engine, plant])
    page.get_by_text("車両構成・適合検査（0件）", exact=True).click()
    page.locator("#partBomName").fill("許諾構成")
    action("partBomCreate")
    assert page.locator(f'#partBom_engine option[value="{engine}"]').count() == 0
    contracts()
    action("partLicenseApprove", design_id)
    bom_id = page.evaluate("current().partOperations.designBoms[0].id")
    page.locator("#partBom_engine").select_option(engine)
    for family in ("transmission", "chassis", "body", "electronics"):
        page.locator(f"#partBom_{family}").select_option(index=1)
    action("partBomSave", bom_id)
    action("partBomApprove", bom_id)
    assert page.evaluate("current().partOperations.designBoms[0].useLicenses.engine") == design_id
    assert page.evaluate("""([key,child])=>{
        const copy=structuredClone(S),f=company(child,copy);
        f.owners=[{id:'PUBLIC',vote:1,econ:1}];
        return !matchingPartLicense(copy,f,partRecord(copy,key),'designUse');
    }""", [engine, child])

    # All participants must approve before shared spending starts.
    show_company(parent)
    page.get_by_text("設計準備案件を申請", exact=True).click()
    page.locator("#engineeringName").fill("共同試作試験")
    page.locator("#engineeringWork").fill("3000")
    page.locator("#engineeringEstimate").fill("90000")
    action("engineeringPropose")
    project = page.evaluate("current().partOperations.engineering.projects.at(-1).id")
    contracts()
    page.locator("#partDevelopmentProject").select_option(project)
    page.locator(f"#partDevelopmentShare_{child}").fill("8000")
    page.locator(f"#partDevelopmentShare_{partner}").fill("3500")
    action("partDevelopmentPropose")
    assert page.evaluate("S.partEconomy.developmentAgreements.length") == 0
    page.locator(f"#partDevelopmentShare_{child}").fill("3500")
    page.locator(f"#partDevelopmentShare_{partner}").fill("2500")
    action("partDevelopmentPropose")
    agreement = page.evaluate("S.partEconomy.developmentAgreements[0].agreementId")
    show_company(child)
    contracts()
    action("partDevelopmentApprove", agreement)
    assert page.evaluate("S.partEconomy.developmentAgreements[0].approvedAt") is None
    show_company(partner)
    contracts()
    action("partDevelopmentApprove", agreement)
    assert page.evaluate("S.partEconomy.developmentAgreements[0].approvedAt") is not None
    show_company(parent)
    page.locator(f"#engineeringFixed_{project}").locator("xpath=ancestor::details").locator("summary").click()
    action("engineeringApprove", project)

    assert page.evaluate("""([child,project])=>{
        const copy=structuredClone(S),delegate=company(child,copy), owner=company(copy.playerId,copy);
        delegate.ledger.cash=0;
        const p=owner.partOperations.engineering.projects.find(p=>p.id===project);
        processEngineering(copy,owner);
        return p.progress===0&&p.actual===0&&copy.partEconomy.developmentAgreements[0].settlements.length===0;
    }""", [child, project])

    finish_month()
    assert page.evaluate("""([child,partner,project])=>{
        const a=S.partEconomy.developmentAgreements[0],x=a.settlements[0];
        const owner=company(S.playerId,S);
        const p=owner.partOperations.engineering.projects.find(p=>p.id===project);
        const expense=owner.journals.find(j=>j.id===x.expenseJournal).amount;
        return a.settlements.length===1&&expense===x.cost&&x.cost===p.actual&&
            x.payments[0].firmId===child&&x.payments[0].amount===Math.floor(x.cost*.35)&&
            x.payments[1].firmId===partner&&x.payments[1].amount===Math.floor(x.cost*.25)&&
            developmentCashPairs(S).length===2&&consolidate(S).cf.internalCashLegs>=2;
    }""", [child, partner, project])
    assert page.evaluate("""([engine,child])=>{
        const f=company(child,S),bom=f.partOperations.designBoms[0];
        return !matchingPartLicense(S,f,partRecord(S,engine),'designUse')&&
            inspectPartBom(S,f,bom.lines).status==='INFEASIBLE'&&
            inspectPartBom(S,f,bom.lines,bom).status==='OK';
    }""", [engine, child])

    assert page.evaluate("""([child,project])=>{
        const copy=structuredClone(S),owner=company(copy.playerId,copy);
        company(child,copy).owners=[{id:'PUBLIC',vote:1,econ:1}];
        refreshPartContracts(copy);
        const a=copy.partEconomy.developmentAgreements[0];
        const p=owner.partOperations.engineering.projects.find(p=>p.id===project);
        return a.endReason==='scope'&&p.status==='ON_HOLD'&&a.settlements.length===1;
    }""", [child, project])
    backup = page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)", backup)
    assert page.evaluate("S.partEconomy.developmentAgreements[0].settlements.length") == 1
    finish_month()
    assert page.evaluate("S.partEconomy.developmentAgreements[0].settlements.length") == 2
    assert page.evaluate("""()=>{
        const bad=structuredClone(S),a=bad.partEconomy.developmentAgreements[0];
        a.settlements.push(structuredClone(a.settlements[0]));
        const prior=S;
        return !restore(savePayload(bad))&&S===prior;
    }""")
    show_company(child)
    page.get_by_text("車両構成・適合検査（1件）", exact=True).click()
    action("partBomOpen", bom_id)
    assert page.get_by_text("承認履歴は保持されています", exact=False).is_visible()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    page.set_viewport_size({"width": 1440, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    contracts()
    action("partLicenseEnd", factory_id)
    assert page.evaluate("""([key,plant])=>!matchingPartLicense(S,current(),partRecord(S,key),'manufacture',plant)""", [engine, plant])
    for _ in range(3):
        finish_month()
    assert page.evaluate("""project=>{
        const a=S.partEconomy.developmentAgreements[0];
        const p=company(S.playerId,S).partOperations.engineering.projects.find(p=>p.id===project);
        return a.endReason==='closed'&&p.status==='COMPLETED'&&
            a.settlements.reduce((n,x)=>n+x.cost,0)===p.estimate;
    }""", project)
    assert not errors, errors
    browser.close()

print("PASS: joint approval, shared costs and CF, separate rights, expiry, scope change, historical BOM and recovery")
