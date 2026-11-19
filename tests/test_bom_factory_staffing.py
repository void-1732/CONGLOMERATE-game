"""Regression: BOM-only support factories receive workers, raw materials and output."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text(encoding="utf-8")

with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
        args=["--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.set_content(html)
    page.evaluate("""() => {
        saveAuto=async()=>true;
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'BOM人員回帰'});
        VIEW_FIRM=S.playerId;
        const f=current();
        f.staff.production=172;
        f.staff.designEngineers=12;
        for(const m of f.models)f.plans[m.id]=0;
        submitPartProject(S,f,{family:'electronics',name:'電子制御',
            values:{...PART_FAMILIES.electronics.defaults},parent:null,output:null});
        const project=f.partOperations.engineering.projects.at(-1);
        project.status='APPROVED';
        project.budget=project.estimate;
        render();
    }""")
    for _ in range(2):
        page.evaluate("async()=>await runMonth()")
        assert not page.evaluate("check(S)")

    fixture = page.evaluate("""() => {
        const f=current(),spec=S.partEconomy.specs.find(x=>x.family==='electronics');
        if(!spec)throw Error('electronics specification not approved');
        const p={...structuredClone(f.plants[0]),id:'P-BOM-ONLY',name:'BOM専用工場',
            kind:'components',capacity:120,condition:100,equipmentTier:1,
            construction:null,renovation:null,paused:false,componentLines:[],assetTracked:0,
            lastProduced:0,lastUtilization:0};
        f.plants.push(p);
        ensureFactoryV21(f);f.factoryOps.mode='detailed';
        f.factoryOps.plans[p.id]=0;
        f.interplant.partPlans[p.id]=0;
        const key=partKey(spec);
        const job=proposeLineJob(S,f,p,'ADD_LINE','',key,10);
        approveLineJob(S,f,job);
        syncPlant(f);
        return {id:p.id,lineId:job.lineId};
    }""")
    # Complete commissioning through real monthly factory investment processing.
    for _ in range(4):
        page.evaluate("async()=>await runMonth()")
        assert not page.evaluate("check(S)"), page.evaluate("check(S)")
    fixture = page.evaluate("""id => {
        const f=current(),p=f.plants.find(x=>x.id===id);
        if(!p.componentLines.length)throw Error('BOM line did not complete commissioning');
        f.partOperations.productionPlans=[{
            plantId:p.id,lineId:p.componentLines[0].lineId,quantity:10,
            destinationId:null,managedByLineAI:false
        }];
        const work=factoryLaborPlanV026(f),record=work.byId[p.id];
        const line=lineOutputPlan(S,f,p)[0];
        if(line.issue)throw Error('BOM line not eligible: '+line.issue);
        return {id:p.id,required:record.required,assigned:record.assigned,
            lineRequired:line.required,lineAssigned:line.assigned,possible:line.possible,
            total:work.records.reduce((sum,r)=>sum+r.assigned,0)};
    }""", fixture["id"])
    assert fixture["required"] == 5, fixture
    assert fixture["assigned"] >= 5, fixture
    assert fixture["lineRequired"] == 5 and fixture["lineAssigned"] == 5, fixture
    assert fixture["possible"] == 10 and fixture["total"] <= 172, fixture

    # Previously a 120-capacity factory with a 10-capacity BOM line received
    # zero workers (or required 60 fixed workers for full line output).
    page.evaluate("""id => {
        const f=current(),p=f.plants.find(x=>x.id===id),spec=partRecord(S,p.componentLines[0].specKey);
        const recipe=bomPartRecipe(spec,partTechnologyProfile(f,spec.family));
        const logistics=ensureWarehouseV038(f);
        logistics.localizedRawTypes=[...new Set([...logistics.localizedRawTypes,...RAW_TYPES_V032])];
        logistics.rawAtPlant[p.id]??={};
        for(const type of RAW_TYPES_V032){
            post(f,{materials:1000},{cash:1000},'BOM 人員テスト用の在庫','operating',S);
            const stock=f.stock[type]??={q:0,v:0};
            stock.q+=100;stock.v+=1000;
            const bin=logistics.rawAtPlant[p.id][type]??={q:0,v:0};
            bin.q+=100;bin.v+=1000;
        }
        const demand=rawFactoryDemandV038(S,f).find(x=>x.p.id===id).monthly;
        for(const [type,amount] of Object.entries(recipe))
            if(amount>0&&!(demand[type]>=10*amount-1e-8))
                throw Error('BOM recipe not allocated to actual site: '+type);
    }""", fixture["id"])
    assert not page.evaluate("check(S)"), page.evaluate("check(S)")
    page.evaluate("async()=>await runMonth()")
    report = page.evaluate("""id=>{
        const f=current(),plan=f.partOperations.productionPlans.find(x=>x.plantId===id);
        const lots=f.partOperations.inventoryLots.filter(x=>x.plantId===id);
        return {last:plan.last,lots:lots.reduce((n,x)=>n+x.quantity,0),
            errors:check(S),group:consolidate(S).errors,month:S.monthCommitted};
    }""", fixture["id"])
    assert report["last"]["good"] > 0 and report["lots"] > 0, report
    assert not report["errors"] and not report["group"], report

    # Two BOM lines share only the actual labor requirement, not idle factory capacity.
    staffing = page.evaluate("""id=>{
        const f=current(),p=f.plants.find(x=>x.id===id);
        p.componentLines.push({...p.componentLines[0],lineId:'LIN-BOM-2',capacity:6});
        f.partOperations.productionPlans.push({
            plantId:id,lineId:'LIN-BOM-2',quantity:6,destinationId:null,managedByLineAI:false
        });
        const full=factoryLaborPlanV026(f).byId[id],lines=lineOutputPlan(S,f,p);
        const before={needed:full.required,workers:lines.map(x=>x.assigned),
            possible:lines.map(x=>x.possible)};
        f.factoryOps.staffAssignments[id]=0;
        const fixed=factoryLaborPlanV026(f).byId[id];
        const blocked=lineOutputPlan(S,f,p);
        delete f.factoryOps.staffAssignments[id];
        // The second line is a temporary demand calculation fixture only.
        // Production/save validation must use the real commissioned line ledger.
        p.componentLines.pop();
        f.partOperations.productionPlans.pop();
        const restored=factoryLaborPlanV026(f).byId[id];
        return {before,fixed:fixed.assigned,blocked:blocked.map(x=>x.possible),
            restored:restored.assigned,corporate:factoryLaborPlanV026(f).records.reduce((n,x)=>n+x.assigned,0)};
    }""", fixture["id"])
    assert staffing["before"]["needed"] == 8, staffing
    assert staffing["before"]["workers"] == [5, 3], staffing
    assert staffing["before"]["possible"] == [10, 6], staffing
    assert staffing["fixed"] == 0 and staffing["blocked"] == [0, 0], staffing
    assert staffing["restored"] >= 8 and staffing["corporate"] <= 172, staffing

    page.evaluate("PAGE='factory';render()")
    # A planned BOM-only factory must not be labeled 'no production plan'.
    panel = page.locator("[data-factory-select='P-BOM-ONLY']")
    panel.click()
    page.locator('[data-factory-view-v026="control"]').click()
    assert "生産計画なし" not in page.locator("#factorySelectedDetail .factory-v026-staff").inner_text()
    backup = page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)", backup)
    assert not page.evaluate("check(S)")
    assert not errors, errors
    browser.close()

print("PASS: BOM-only headcount, two-line staffing, site raw demand, production and save compatibility")
