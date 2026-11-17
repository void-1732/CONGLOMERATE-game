"""G6: product engineering through the UI, monthly accounting and save migration."""
import os
import shutil
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text(encoding="utf-8")
legacy_html = subprocess.check_output(
    ["git", "show", "9577c7dfa431382afd53b94b9b66da8fea91baff:index.html"],
    cwd=root,
).decode()
setup = """() => {
    saveAuto = async () => true;
    S = newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'検証会社'});
    VIEW_FIRM = S.playerId;
}"""

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
    )
    original = browser.new_page()
    original.set_content(legacy_html)
    original.evaluate(setup)
    old_save = original.evaluate("savePayload(S)")
    original.close()

    page = browser.new_page(viewport={"width": 390, "height": 844})
    ui_errors = []
    page.on("pageerror", lambda error: ui_errors.append(str(error)))
    page.set_content(html)
    page.evaluate(setup)
    assert page.evaluate("raw => restore(raw)", old_save)
    assert page.evaluate("engineers(current())") == 0
    staff_before = page.evaluate("current().staff")
    research_slots = page.evaluate("techSlotLimit(current(),S)")

    page.evaluate("PAGE='product';PRODUCT_VIEW='design';render()")
    assert page.get_by_text("設計技術者が0人のため工数・進捗は0です。", exact=False).count() == 1

    def propose(name, work, estimate):
        page.get_by_text("設計準備案件を申請", exact=True).click()
        page.locator("#engineeringName").fill(name)
        page.locator("#engineeringWork").fill(str(work))
        page.locator("#engineeringEstimate").fill(str(estimate))
        page.get_by_role("button", name="案件を申請").click()
        return page.evaluate("current().partOperations.engineering.projects.at(-1).id")

    def open_project(project_id):
        control = page.locator(f"#engineeringFixed_{project_id}")
        if not control.is_visible():
            control.locator("xpath=ancestor::details").locator("summary").click()
        return control

    def action(project_id, key):
        page.locator(f'button[data-id="{project_id}"][data-action="{key}"]').click()

    first = propose("車体試験", 1000, 12000)
    open_project(first)
    action(first, "engineeringApprove")
    assert page.evaluate("current().partOperations.engineering.projects[0].status") == "PROPOSED"

    page.evaluate("PAGE='people';PEOPLE_VIEW='hr';render()")
    page.locator("#hireArea").select_option("designEngineers")
    page.locator("#hireCount").fill("4")
    page.get_by_role("button", name="選択した部門へ採用").click()
    assert page.evaluate("current().staff") == {**staff_before, "designEngineers": 4}
    assert page.evaluate("techSlotLimit(current(),S)") == research_slots
    page.locator("#engineeringTraining").fill("1000")
    page.get_by_role("button", name="設計教育予算を保存").click()

    page.evaluate("PAGE='product';render()")
    second = propose("耐久試験", 150, 6000)
    third = propose("比較試験", 100, 3000)
    open_project(first).fill("2")
    assert page.locator(f"#engineeringBudget_{first}").input_value() == "12000"
    action(first, "engineeringApprove")
    open_project(second).fill("3")
    action(second, "engineeringApprove")
    assert page.evaluate("current().partOperations.engineering.projects[1].status") == "PROPOSED"
    open_project(second).fill("")
    action(second, "engineeringApprove")
    open_project(third)
    action(third, "engineeringApprove")
    assert page.evaluate("current().partOperations.engineering.projects[2].status") == "PROPOSED"
    open_project(third)
    action(third, "engineeringCancel")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
    page.set_viewport_size({"width": 1440, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")

    # Hold cash at zero to verify that a project cannot spend beyond available funds.
    no_cash = page.evaluate("""() => {
        const state = structuredClone(S), firm = company(state.playerId,state);
        firm.ledger.cash = 0;
        processEngineering(state,firm);
        return {cash:acc(firm,'cash'),spent:firm.partOperations.engineering.projects[0].actual};
    }""")
    assert no_cash == {"cash": 0, "spent": 0}

    assert page.evaluate("""() => {
        const state = structuredClone(S), firm = company(state.playerId,state);
        processEngineering(state,firm);
        const same = JSON.stringify(state);
        processEngineering(state,firm);
        return JSON.stringify(state) === same;
    }""")
    page.evaluate("async () => await runMonth()")
    projects = page.evaluate("current().partOperations.engineering.projects")
    assert projects[0]["progress"] > 0 and projects[0]["actual"] > 0
    assert projects[1]["status"] == "COMPLETED"
    assert projects[1]["actual"] == projects[1]["estimate"]
    assert projects[2]["status"] == "CANCELLED" and projects[2]["actual"] == 0
    assert 51 < page.evaluate("engineeringSkill(current())") < 52
    assert page.evaluate("""() => {
        const f = current(), journal = f.journals.filter(j=>j.when===S.monthCommitted);
        return journal.filter(j=>j.text==='製品設計技術者の技能教育').length===1 &&
            journal.filter(j=>j.text.startsWith('製品設計の試作・試験費')).length===2 &&
            journal.filter(j=>j.text==='月次給与・製造労務原価').length===1;
    }""")

    page.evaluate("PAGE='product';render()")
    open_project(first)
    action(first, "engineeringPause")
    page.evaluate("async () => await runMonth()")
    paused = page.evaluate("current().partOperations.engineering.projects[0]")
    assert paused["status"] == "ON_HOLD"
    assert (paused["progress"], paused["actual"]) == (projects[0]["progress"], projects[0]["actual"])
    saved = page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)", saved)
    assert page.evaluate("current().partOperations.engineering.projects[0]") == paused

    page.evaluate("PAGE='product';render()")
    open_project(first)
    action(first, "engineeringApprove")
    page.evaluate("async () => await runMonth()")
    assert page.evaluate("current().partOperations.engineering.projects[0].progress") > paused["progress"]
    assert page.evaluate("check(S).length===0 && consolidate(S).errors.length===0 && consolidate(S).cf.reconciled")
    assert page.evaluate("""() => {
        const bad = structuredClone(S);
        const p = company(bad.playerId,bad).partOperations.engineering.projects[0];
        p.actual += 1;
        const before = S;
        return !restore(savePayload(bad)) && S === before;
    }""")
    for _ in range(12):
        page.evaluate("async () => await runMonth()")
        assert page.evaluate("check(S).length===0 && consolidate(S).errors.length===0 && consolidate(S).cf.reconciled")
    assert page.evaluate("current().partOperations.engineering.projects[0].status") == "COMPLETED"
    assert not ui_errors, ui_errors
    browser.close()

print("PASS G6: hiring, separate slots, allocations, costs, pause/resume, save and accounting")
