"""G6/G7: released parts, compatibility, repairs and saved design revisions."""
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
labels = {
    "engine": "試験エンジン",
    "transmission": "試験変速機",
    "chassis": "試験車台",
    "body": "試験車体",
    "electronics": "試験電子装備",
    "battery": "試験電池",
}

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
    )
    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content(html)
    page.evaluate("""() => {
        saveAuto=async()=>true;
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'部品検証'});
        VIEW_FIRM=S.playerId;
        PAGE='product';
        render();
    }""")
    slots = page.evaluate("techSlotLimit(current(),S)")

    def action(key, identifier=None):
        selector = f'button[data-action="{key}"]'
        if identifier is not None:
            selector += f'[data-id="{identifier}"]'
        page.locator(selector).click()

    def product():
        page.evaluate("PAGE='product';render()")

    def propose(family, **values):
        family_button = page.locator(f'[data-action="partFamily"][data-id="{family}"]')
        if not family_button.is_visible():
            page.get_by_text("部品を設計・改訂する", exact=True).click()
        action("partFamily", family)
        page.locator("#partName").fill(labels[family])
        for key, value in values.items():
            field = page.locator(f"#partValue_{key}")
            if field.evaluate("(el)=>el.tagName") == "SELECT":
                field.select_option(str(value))
            else:
                field.fill(str(value))
        action("partSubmit")

    def approve_all():
        ids = page.evaluate("""current().partOperations.engineering.projects
            .filter(p=>p.status==='PROPOSED').map(p=>p.id)""")
        for project_id in ids:
            page.locator(f"#engineeringFixed_{project_id}").locator(
                "xpath=ancestor::details"
            ).locator("summary").click()
            action("engineeringApprove", project_id)

    def finish(count):
        for _ in range(count):
            page.evaluate("async()=>await runMonth()")
            assert page.evaluate("check(S).length===0 && consolidate(S).errors.length===0 && consolidate(S).cf.reconciled"), page.evaluate(
                "({errors:check(S),consolidated:consolidate(S).errors,diagnostic:LAST_MONTH_DIAGNOSTIC?.message})"
            )

    # Research gating applies even when the firm could fund development.
    propose("battery", voltage=400)
    assert page.evaluate("current().partOperations.engineering.projects.length") == 0
    assert page.get_by_text("必要な年代・研究条件", exact=False).is_visible()
    page.evaluate("current().staff.designEngineers=12")
    for family in ("engine", "transmission", "chassis", "body", "electronics"):
        propose(family, **({"torque": 250} if family == "engine" else {}))
    assert page.evaluate("S.partEconomy.specs.length") == 0
    assert page.evaluate("techSlotLimit(current(),S)") == slots
    approve_all()
    finish(2)
    assert page.evaluate("S.partEconomy.specs.length") == 5
    original = page.evaluate("structuredClone(S.partEconomy.specs)")
    keys = {row["family"]: f'{row["specId"]}@1' for row in original}

    product()
    page.get_by_text("車両構成・適合検査（0件）", exact=True).click()
    page.locator("#partBomName").fill("試験車・初版")
    action("partBomCreate")
    bom = page.evaluate("current().partOperations.designBoms[0].id")
    for family, key in keys.items():
        page.locator(f"#partBom_{family}").select_option(key)
    action("partBomSave", bom)
    assert page.get_by_text("修正開発可能", exact=True).count() >= 1
    assert page.get_by_text("200 → 250", exact=False).count() == 1
    assert page.locator('[data-action="partBomApprove"]').count() == 0
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    action("partRepair", bom)
    approve_all()
    finish(1)
    assert page.evaluate("S.partEconomy.specs.slice(0,5)") == original
    revised = page.evaluate("partKey(S.partEconomy.specs.at(-1))")
    assert revised == keys["transmission"].replace("@1", "@2")
    assert page.evaluate("current().partOperations.designBoms[0].lines.transmission") == keys["transmission"]

    product()
    page.locator("#partBom_transmission").select_option(revised)
    action("partBomSave", bom)
    action("partBomApprove", bom)
    assert not page.locator("#partBom_transmission").is_enabled()
    saved = page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)", saved)
    assert page.evaluate("current().partOperations.designBoms[0].lines.transmission") == revised
    assert page.evaluate("""() => {
        const bad=structuredClone(S);
        company(bad.playerId,bad).partOperations.designBoms[0].lines.transmission='PART-999999@1';
        const prior=S;
        return !restore(savePayload(bad))&&S===prior;
    }""")
    assert page.evaluate("current().models.every(m=>m.componentMode==='legacy')")

    assert page.evaluate("""() => {
        const trial=structuredClone(S), f=company(trial.playerId,trial);
        const lines=f.partOperations.designBoms[0].lines;
        const gear=partRecord(trial,lines.transmission).values;
        gear.drive='fwd';
        const researchLock=inspectPartBom(trial,f,lines).status==='RESEARCH_LOCK';
        f.research.tree.done.push(...techPathOrder('chassis-5').filter(id=>!f.research.tree.done.includes(id)));
        trial.year=2020;
        const hardMismatch=inspectPartBom(trial,f,lines).status==='INFEASIBLE';
        gear.drive='rwd';
        partRecord(trial,lines.body).values.length=4700;
        partRecord(trial,lines.electronics).values.durability=45;
        const repair=inspectPartBom(trial,f,lines);
        return researchLock&&hardMismatch&&repair.status==='MODIFIABLE'&&
            repair.issues.some(x=>x.repair?.field==='clearance')&&
            repair.issues.some(x=>x.repair?.field==='durability');
    }""")

    # Manual revision and common reuse leave the approved composition pinned.
    product()
    page.get_by_text("自社の部品台帳（6版）", exact=True).click()
    action("partRevise", keys["body"])
    page.locator("#partValue_length").fill("4300")
    action("partSubmit")
    approve_all()
    finish(1)
    assert page.evaluate("S.partEconomy.specs.at(-1).revision") == 2
    assert page.evaluate("current().partOperations.designBoms[0].lines.body") == keys["body"]
    product()
    page.get_by_text("車両構成・適合検査（1件）", exact=True).click()
    page.locator("#partBomName").fill("試験車・共通部品")
    action("partBomCreate")
    other = page.evaluate("current().partOperations.designBoms[1].id")
    for family, key in {**keys, "transmission": revised}.items():
        page.locator(f"#partBom_{family}").select_option(key)
    action("partBomSave", other)
    action("partBomApprove", other)
    assert page.evaluate("""current().partOperations.designBoms.every(
        b=>b.approvedAt!==null&&b.lines.transmission===S.partEconomy.specs[5].specId+'@2')""")

    # Validate approved designs and remaining monetary effects over normal month transitions.
    finish(12)
    page.set_viewport_size({"width": 1440, "height": 900})
    product()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")

    # The electrical family completes once the era and research requirements are met.
    page.evaluate("""() => {
        S=newGame({era:2020,country:'JP',difficulty:'normal',history:'historical',name:'電池検証'});
        VIEW_FIRM=S.playerId;
        PART_FORM=null;
        current().staff.designEngineers=2;
        current().research.tree.done.push(...techPathOrder('energy-11').filter(
            id=>!current().research.tree.done.includes(id)));
    }""")
    product()
    propose("battery", voltage=400)
    approve_all()
    finish(1)
    assert page.evaluate("S.partEconomy.specs[0].family==='battery'")
    assert page.evaluate("S.partEconomy.specs[0].values.voltage===400")
    assert not errors, errors
    browser.close()

print("PASS: six part families, research gating, repairs, release, reuse, pinned revisions, saves and monthly accounting")
