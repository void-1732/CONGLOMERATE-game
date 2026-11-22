"""Research effect and discovery of a newly founded resource supplier."""
import os
import shutil
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text(encoding="utf-8")
previous = subprocess.check_output(
    ["git", "show", "5a5db0ca799a0993de1366f5edee3513bacd1c98:index.html"], cwd=root, text=True
)
setup = """()=>{
    saveAuto=async()=>true;
    S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'資材検証本社'});
    VIEW_FIRM=S.playerId;
    PAGE='group';
    render();
}"""

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
    )
    old = browser.new_page()
    old.set_content(previous)
    old.evaluate(setup)
    raw = old.evaluate("savePayload(S)")
    technology_ids = old.evaluate("TECH_NODES.map(n=>n.id)")
    old.close()

    page = browser.new_page(viewport={"width": 390, "height": 844})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_default_timeout(10000)
    page.set_content(html)
    page.evaluate(setup)
    assert not page.evaluate("raw=>restore(raw)", raw)  # SPEC-168: old saves are not imported
    assert page.evaluate("TECH_NODES.map(n=>n.id)") == technology_ids and len(technology_ids) == 800

    def screen(section, firm=None):
        page.evaluate("([section,id])=>{VIEW_FIRM=id??S.playerId;PAGE=section;render()}", [section, firm])

    def month():
        status = page.evaluate("""async()=>{
            const close=S.monthCommitted;
            await runMonth();
            const group=consolidate(S);
            return {advanced:S.monthCommitted===close+1,errors:check(S),group:group.errors,
                cf:group.cf.reconciled,why:LAST_MONTH_DIAGNOSTIC?.message};
        }""")
        assert status["advanced"] and not status["errors"] and not status["group"] and status["cf"], status

    screen("corporateSubsidiaries")
    page.locator("#subName").fill("自社資源開発")
    page.locator("#subCountry").select_option("JP")
    page.locator("#subIndustry").select_option("resource")
    page.locator("#subCapital").fill("600000")
    page.locator('[data-action="createSub"]').click()
    mine = page.evaluate("current().id")
    assert mine != page.evaluate("S.playerId")
    assert page.evaluate("S.supplyNetwork.nodes.filter(n=>n.firmId===current().id).map(n=>n.type)") == [
        "steel", "rubber", "aluminum", "copper", "glass", "chemicals"
    ]

    screen("supplyContracts", mine)
    contracts = page.get_by_text("購入契約を編集（7資材）", exact=True)
    assert page.get_by_text("グループ内の供給元", exact=True).is_visible()
    assert page.get_by_text("選択中の法人自身は仕入先候補から除外されます", exact=False).is_visible()
    contracts.click()
    assert page.locator(f'#supplier_steel option[value="CORP:{mine}:steel"]').count() == 0
    screen("supply")
    page.get_by_role("button", name="調達契約を開く").click()
    selector = f"CORP:{mine}:steel"
    assert page.locator("#supplier_steel option").first.get_attribute("value") == selector
    assert page.locator(f'#supplier_components option[value="CORP:{mine}:components"]').count() == 0
    page.locator("#supplier_steel").select_option(selector)
    page.locator('[data-action="saveSupply"]').click()
    assert page.evaluate("current().supply.contracts.steel.supplierId") == selector
    assert not page.evaluate("current().supply.contracts.steel.autoManage")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    snapshot = page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)", snapshot)
    month()
    assert page.evaluate("current().supply.contracts.steel.supplierId") == selector

    # The powertrain research changes a powertrain quote more than an unrelated electronic design.
    project_quote = page.evaluate("""()=>{
        const f=current(),before=f.research.tree.done;
        f.research.tree.done=[];
        const quote=(family)=>partProjectQuote(S,f,family,PART_FAMILIES[family].defaults,null,false);
        const base=quote('engine'),electronics=quote('electronics');
        f.research.tree.done=TECH_NODES.filter(n=>n.domain==='powertrain').slice(0,40).map(n=>n.id);
        const engine=quote('engine'),other=quote('electronics');
        f.research.tree.done=before;
        return {base,engine,electronics,other};
    }""")
    assert project_quote["engine"]["work"] < project_quote["base"]["work"]
    assert project_quote["engine"]["estimate"] < project_quote["base"]["estimate"]
    assert project_quote["electronics"] == project_quote["other"]
    page.evaluate("""()=>{
        const f=current();
        f.staff.designEngineers=6;f.staff.production=110;
        submitPartProject(S,f,{family:'engine',name:'検証エンジン',values:{...PART_FAMILIES.engine.defaults},
            parent:null,output:null});
        const project=f.partOperations.engineering.projects[0];
        project.status='APPROVED';project.budget=project.estimate;
    }""")
    month()
    fixed_part = page.evaluate("structuredClone(S.partEconomy.specs[0])")
    fixed_work = page.evaluate("current().partOperations.engineering.projects[0].work")
    assert fixed_part["family"] == "engine"
    page.evaluate("""()=>{
        const f=current(),p=f.plants[0],part=S.partEconomy.specs[0];
        const job=proposeLineJob(S,f,p,'ADD_LINE','',partKey(part),10);
        approveLineJob(S,f,job);
    }""")
    for _ in range(4):
        month()

    effect = page.evaluate("""()=>{
        const make=trained=>{
            const trial=structuredClone(S),f=company(trial.playerId,trial),p=f.plants[0],l=p.componentLines[0];
            p.condition=80;
            f.research.tree.done=trained?TECH_NODES.filter(n=>['production','materials','powertrain'].includes(n.domain)).map(n=>n.id):[];
            f.partOperations.productionPlans=[{plantId:p.id,lineId:l.lineId,quantity:4,destinationId:null,defectCarry:98}];
            for(const type of ['steel','rubber']){
                post(f,{materials:4000},{cash:4000},'検証資材','operating',trial);
                f.stock[type].q+=100;f.stock[type].v+=4000;
            }
            const steel=f.stock.steel.q,cash=acc(f,'cash'),capacity=lineOutputPlan(trial,f,p)[0].possible;
            produceBomParts(trial);
            return {steel:steel-f.stock.steel.q,cash:cash-acc(f,'cash'),capacity,
                results:f.partOperations.productionPlans[0].last,errors:check(trial)};
        };
        return {basic:make(false),trained:make(true)};
    }""")
    assert not effect["basic"]["errors"] and not effect["trained"]["errors"], effect
    assert effect["basic"]["results"]["attempted"] == effect["trained"]["results"]["attempted"] == 4, effect
    assert effect["trained"]["results"]["rejected"] < effect["basic"]["results"]["rejected"], effect
    assert effect["trained"]["steel"] < effect["basic"]["steel"] and effect["trained"]["cash"] < effect["basic"]["cash"], effect
    assert effect["trained"]["capacity"] > effect["basic"]["capacity"], effect

    page.evaluate("""()=>{
        const f=current(),p=f.plants[0],line=p.componentLines[0];
        f.research.tree.done=TECH_NODES.filter(n=>['production','materials','powertrain'].includes(n.domain)).map(n=>n.id);
        f.partOperations.productionPlans.push({plantId:p.id,lineId:line.lineId,quantity:4,destinationId:null});
    }""")
    month()
    assert page.evaluate("S.partEconomy.specs[0]") == fixed_part
    assert page.evaluate("current().partOperations.engineering.projects[0].work") == fixed_work
    assert page.evaluate("!!current().partOperations.productionPlans[0].last")
    screen("product")
    # STEP 2 separates vehicle planning from the existing part design editor.
    page.get_by_role("button", name="車両・部品設計", exact=True).click()
    page.get_by_text("部品を設計・改訂する", exact=True).click()
    assert page.get_by_text("完了済み研究の効果", exact=False).is_visible()
    page.set_viewport_size({"width": 1440, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    assert not errors, errors
    browser.close()

print("PASS: immediate resource supplier, buyer filter, saves, 800 IDs and researched production effects")
