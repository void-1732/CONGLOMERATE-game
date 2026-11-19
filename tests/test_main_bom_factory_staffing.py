"""Regression for the main-branch BOM factory zero-worker production defect.

Only uses features already shipped on main. Does not depend on STEP 9.
"""
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
        args=["--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.set_content(HTML)

    page.evaluate("""() => {
        saveAuto = async () => true;
        S = newGame({era:1900,country:'JP',difficulty:'normal',
            history:'historical',name:'BOM工場0人回帰'});
        VIEW_FIRM = S.playerId;
        const f = current();
        f.staff.production = 172;
        f.staff.designEngineers = 12;
        for (const m of f.models) f.plans[m.id] = 0;
        submitPartProject(S,f,{family:'electronics',name:'電子部品',
            values:{...PART_FAMILIES.electronics.defaults},parent:null,output:null});
        const project=f.partOperations.engineering.projects.at(-1);
        project.status='APPROVED';
        project.budget=project.estimate;
    }""")
    for _ in range(2):
        previous = page.evaluate("S.monthCommitted")
        page.evaluate("async()=>await runMonth()")
        assert page.evaluate("S.monthCommitted") == previous + 1
        assert not page.evaluate("check(S)"), page.evaluate("check(S)")

    fixture = page.evaluate("""() => {
        const f = current(),spec=S.partEconomy.specs.find(x=>x.family==='electronics');
        if (!spec)throw Error('The BOM electronics specification was not approved');
        const parent=f.plants[0],p={
            ...structuredClone(parent),id:'MAIN-BOM-120',name:'通常版BOM専用工場',
            kind:'components',capacity:120,condition:100,equipmentTier:1,
            construction:null,renovation:null,paused:false,componentLines:[],
            assetTracked:0,lastProduced:0,lastUtilization:0
        };
        f.plants.push(p);
        ensureFactoryV21(f);
        f.factoryOps.mode='detailed';
        f.factoryOps.plans[p.id]=0;
        f.interplant.partPlans[p.id]=0;
        const job=proposeLineJob(S,f,p,'ADD_LINE','',partKey(spec),10);
        approveLineJob(S,f,job);
        syncPlant(f);
        return {id:p.id};
    }""")
    # Respect the real construction/completion lifecycle and its financial ledger.
    for _ in range(4):
        previous = page.evaluate("S.monthCommitted")
        page.evaluate("async()=>await runMonth()")
        assert page.evaluate("S.monthCommitted") == previous + 1
        assert not page.evaluate("check(S)"), page.evaluate("check(S)")

    idle = page.evaluate("""id=>{
        const f=current(),p=f.plants.find(x=>x.id===id);
        return {labor:factoryLaborPlanV026(f).byId[id],
            reasons:factoryInsightV023(f,p).reasons.map(x=>x.state),
            html:factoryDetailMarkup(f,p,true)};
    }""", fixture["id"])
    assert idle["labor"]["required"] == 0 and idle["labor"]["assigned"] == 0, idle
    assert "部品生産計画が0" in idle["reasons"], idle
    assert "この工場のBOMラインには月間生産計画がありません" in idle["html"], idle

    plan = page.evaluate("""id=>{
        const f=current(),p=f.plants.find(x=>x.id===id);
        if(p.componentLines.length!==1)throw Error('BOM line commissioning not complete');
        const line=p.componentLines[0];
        f.partOperations.productionPlans=[{
            plantId:p.id,lineId:line.lineId,quantity:10,
            destinationId:null,managedByLineAI:false
        }];
        const labor=factoryLaborPlanV026(f);
        const assigned=labor.byId[id],capacity=lineOutputPlan(S,f,p)[0];
        const insight=factoryInsightV023(f,p);
        const source=Object.fromEntries(SUPPLY_TYPES.map(type=>[
            type,factoryResourceTargetV026(f,type,S).demand]));
        return {id,required:assigned.required,assigned:assigned.assigned,
            lineRequired:capacity.required,lineAssigned:capacity.assigned,
            linePossible:capacity.possible,lineIssue:capacity.issue,
            alert:insight.reasons.map(x=>x.state),source,
            corporate: labor.records.reduce((sum,x)=>sum+x.assigned,0)};
    }""", fixture["id"])
    assert plan["required"] == 5, plan
    assert plan["assigned"] >= 5, plan
    assert plan["lineRequired"] == 5 and plan["lineAssigned"] == 5, plan
    assert plan["linePossible"] == 10 and not plan["lineIssue"], plan
    assert plan["corporate"] <= 172, plan
    assert "部品生産計画が0" not in plan["alert"], plan
    assert any(q > 0 for q in plan["source"].values()), plan

    # Existing saves with a fixed-zero assignment block auto staffing even with
    # adequate corporate headcount. The diagnostic must allow restoring it.
    blocked = page.evaluate("""id=>{
        const f=current(),p=f.plants.find(x=>x.id===id);
        f.factoryOps.staffAssignments[id]=0;
        const workers=factoryLaborPlanV026(f).byId[id];
        return {assigned:workers.assigned,
            reasons:factoryInsightV023(f,p).reasons.map(x=>x.state),
            html:factoryDetailMarkup(f,p,true)};
    }""", fixture["id"])
    assert blocked["assigned"] == 0 and "固定配置0人で生産停止" in blocked["reasons"], blocked
    assert "固定0人" in blocked["html"], blocked
    page.evaluate("""id=>{
        PAGE='factory';FACTORY_UI.selected=id;FACTORY_DETAIL_VIEW_V026='diagnostic';render();
    }""", fixture["id"])
    page.locator('[data-factory-auto-restore="MAIN-BOM-120"]').click()
    restored = page.evaluate("""id=>{
        const f=current();
        return {assigned:factoryLaborPlanV026(f).byId[id].assigned,
            fixed:Object.hasOwn(f.factoryOps.staffAssignments,id)};
    }""", fixture["id"])
    assert not restored["fixed"] and restored["assigned"] >= 5, restored

    # Supply existing paid materials without generating fictional free inventory.
    page.evaluate("""()=>{
        const f=current();
        for(const type of SUPPLY_TYPES){
            const money=2000;
            post(f,{materials:money},{cash:money},'BOM回帰用原材料','operating',S);
            const bin=f.stock[type]??={q:0,v:0};
            bin.q+=200;bin.v+=money;
        }
    }""")
    assert not page.evaluate("check(S)"), page.evaluate("check(S)")
    previous = page.evaluate("S.monthCommitted")
    page.evaluate("async()=>await runMonth()")
    produced = page.evaluate("""id=>{
        const f=current(),p=f.plants.find(x=>x.id===id);
        const plan=f.partOperations.productionPlans.find(x=>x.plantId===id);
        return {month:S.monthCommitted,last:plan.last,
            actual:p.lastProduced,utilization:p.lastUtilization,staff:p.lastAssignedStaff,
            lots:f.partOperations.inventoryLots.filter(l=>l.plantId===id)
               .reduce((n,l)=>n+l.quantity,0),
            errors:check(S),group:consolidate(S).errors,cf:consolidate(S).cf.reconciled};
    }""", fixture["id"])
    assert produced["month"] == previous + 1, produced
    assert produced["last"]["good"] > 0 and produced["lots"] > 0, produced
    assert produced["actual"] >= produced["last"]["attempted"] > 0, produced
    assert 0 < produced["utilization"] and produced["staff"] >= 5, produced
    assert not produced["errors"] and not produced["group"] and produced["cf"], produced

    # Simultaneous BOM lines must share real labor, not unassigned site capacity.
    # The second line is an isolated, transient workforce test fixture, not
    # a persisted construction or component ledger.
    allocation = page.evaluate("""id=>{
        const f=current(),p=f.plants.find(x=>x.id===id);
        p.componentLines.push({...p.componentLines[0],lineId:'TEMP-BOM-LINE',capacity:6});
        f.partOperations.productionPlans.push({
            plantId:id,lineId:'TEMP-BOM-LINE',quantity:6,destinationId:null,managedByLineAI:false
        });
        const workers=factoryLaborPlanV026(f).byId[id],lines=lineOutputPlan(S,f,p);
        const normal={needed:workers.required,assigned:lines.map(x=>x.assigned),
            possible:lines.map(x=>x.possible)};
        f.factoryOps.staffAssignments[id]=0;
        const blocked=lineOutputPlan(S,f,p).map(x=>x.possible);
        delete f.factoryOps.staffAssignments[id];
        p.componentLines.pop();f.partOperations.productionPlans.pop();
        return {normal,blocked,staffTotal:factoryLaborPlanV026(f).records
            .reduce((n,x)=>n+x.assigned,0)};
    }""", fixture["id"])
    assert allocation["normal"]["needed"] == 8, allocation
    assert allocation["normal"]["assigned"] == [5, 3], allocation
    assert allocation["normal"]["possible"] == [10, 6], allocation
    assert allocation["blocked"] == [0, 0], allocation
    assert allocation["staffTotal"] <= 172, allocation

    # A factory with no assigned work must not claim to be fully staffed.
    page.evaluate("""id=>{
        const f=current();
        f.partOperations.productionPlans=f.partOperations.productionPlans.filter(x=>x.plantId!==id);
    }""", fixture["id"])
    ui = page.evaluate("""id=>{
        const f=current(),p=f.plants.find(x=>x.id===id);
        return {status:factoryLaborPlanV026(f).byId[id],
            html:factoryDetailMarkup(f,p,true)};
    }""", fixture["id"])
    assert ui["status"]["required"] == 0, ui["status"]
    assert "生産計画なし" in ui["html"], "Idle factory is incorrectly labelled fully staffed"
    assert "この工場のBOMラインには月間生産計画がありません" in ui["html"], ui
    page.evaluate("""id=>{
        PAGE='factory';FACTORY_UI.selected=id;FACTORY_DETAIL_VIEW_V026='diagnostic';render();
    }""", fixture["id"])
    page.locator('[data-factory-bom-plan="MAIN-BOM-120"]').click()
    assert page.evaluate("FACTORY_DETAIL_VIEW_V026") == "production"
    assert page.locator("#bomShopPanel").get_attribute("open") is not None

    raw = page.evaluate("savePayload(S)")
    assert page.evaluate("data=>restore(data)", raw)
    assert not page.evaluate("check(S)"), page.evaluate("check(S)")
    assert not errors, errors
    browser.close()

print("PASS: main BOM-only setup guidance, fixed-zero rescue, real utilization, manufacture, accounts and saves")
