"""Real old-save recovery regression for factory P80367-style zero staff/output.

The save starts with 172 production employees and a 120-unit active
components plant, but both production plans and its fixed assignment are 0.
No STEP 9 features or new-save schema are involved.
"""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
        args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.set_content(HTML)
    page.evaluate("saveAuto=async()=>true")

    for mode in ("legacy", "detailed"):
        page.evaluate("""mode=>{
            S=newGame({era:1900,country:'JP',difficulty:'normal',
                history:'historical',name:'旧セーブ0人・0%復旧'});
            VIEW_FIRM=S.playerId;
            const f=current();
            f.staff.production=172;
            const p={...structuredClone(f.plants[0]),id:'P80367',
                name:'部品専門（支援）',kind:'components',
                capacity:120,condition:100,paused:false,
                construction:null,renovation:null,componentLines:[],
                lastProduced:0,lastUtilization:0,assetTracked:0};
            f.plants.push(p);
            ensureFactoryV21(f);
            f.factoryOps.mode=mode;
            f.factoryOps.plans[p.id]=0;
            f.interplant.partPlans[p.id]=0;
            f.factoryOps.staffAssignments[p.id]=0;
            delete f.factoryOps.idleRecoveryV0262;
            syncPlant(f);
        }""", mode)
        before = page.evaluate("""()=>{
            const f=current(),p=f.plants.find(x=>x.id==='P80367');
            return {staff:f.staff.production,assigned:staffOfPlantV023(f,p).assigned,
                needed:staffOfPlantV023(f,p).recommended,
                plan:f.factoryOps.mode==='detailed'?f.factoryOps.plans[p.id]:
                    f.interplant.partPlans[p.id]};
        }""")
        assert before == {"staff": 172,"assigned": 0,"needed": 0,"plan": 0}, before
        old_raw = page.evaluate("savePayload(S)")
        assert page.evaluate("raw=>restore(raw)", old_raw)
        recovered = page.evaluate("""()=>{
            const f=current(),p=f.plants.find(x=>x.id==='P80367');
            const target=f.factoryOps.mode==='detailed'?f.factoryOps.plans[p.id]:
                f.interplant.partPlans[p.id];
            return {staff:f.staff.production,mode:f.factoryOps.mode,
                plan:target,needed:staffOfPlantV023(f,p).recommended,
                assigned:staffOfPlantV023(f,p).assigned,
                fixedZero:Object.hasOwn(f.factoryOps.staffAssignments,p.id),
                recovery:f.factoryOps.idleRecoveryV0262,errors:check(S)};
        }""")
        assert recovered["mode"] == mode and recovered["staff"] == 172, recovered
        assert recovered["plan"] > 0 and recovered["needed"] > 0, recovered
        assert recovered["assigned"] > 0 and not recovered["fixedZero"], recovered
        assert recovered["recovery"] == 1 and not recovered["errors"], recovered

        # Confirm that original financial assets, material inventory and
        # employee count were not invented by restore.
        saved = page.evaluate("savePayload(S)")
        assert page.evaluate("raw=>restore(raw)", saved)
        second = page.evaluate("""()=>{
            const f=current(),id='P80367';
            return {plan:f.factoryOps.mode==='detailed'?f.factoryOps.plans[id]:
                f.interplant.partPlans[id],
                assigned:factoryLaborPlanV026(f).byId[id].assigned,
                staff:f.staff.production};
        }""")
        assert second["plan"] == recovered["plan"], (mode,second,recovered)
        assert second["assigned"] > 0 and second["staff"] == 172, second

        # Exercise the actual factory UI, not only the internal allocation helper.
        page.evaluate("""()=>{PAGE='facilityProduction';render();}""")
        page.locator('[data-factory-select="P80367"]').click()
        assert page.evaluate("FACTORY_UI.selected") == "P80367"
        page.locator('[data-factory-view-v026="control"]').click()
        page.locator('#factoryStaffModeV026').select_option("fixed")
        page.locator('#factoryStaffAmountV026').fill("12")
        page.locator('[data-action="saveFactoryStaffV026"]').click()
        page.wait_for_function("""()=>
            current().factoryOps.staffAssignments['P80367']===12
        """)
        clicked = page.evaluate("""()=>{
            const f=current(),p=f.plants.find(x=>x.id==='P80367');
            return {assigned:staffOfPlantV023(f,p).assigned,staff:f.staff.production};
        }""")
        assert clicked == {"assigned":12,"staff":172}, (mode,clicked)
        # Reset to automatic allocation via the same UI controls.
        page.locator('#factoryStaffModeV026').select_option("auto")
        page.locator('[data-action="saveFactoryStaffV026"]').click()
        page.wait_for_function("""()=>
            !Object.hasOwn(current().factoryOps.staffAssignments,'P80367')
        """)
        assert page.evaluate("""()=>
            staffOfPlantV023(current(),current().plants.find(x=>x.id==='P80367')).assigned
        """) > 0

        # Use a fully paid, ledger-balanced raw-material fixture, not free goods.
        page.evaluate("""()=>{
            const f=current();
            for(const type of ['steel','rubber']){
                const cost=2000;
                post(f,{materials:cost},{cash:cost},'回帰テスト原材料仕入','operating',S);
                f.stock[type].q+=200;f.stock[type].v+=cost;
            }
        }""")
        assert not page.evaluate("check(S)")
        prev = page.evaluate("S.monthCommitted")
        page.evaluate("async()=>await runMonth()")
        after = page.evaluate("""()=>{
            const f=current(),p=f.plants.find(x=>x.id==='P80367');
            const c=consolidate(S);
            return {month:S.monthCommitted,produced:p.lastProduced,
                utilization:p.lastUtilization,assigned:p.lastAssignedStaff,
                errors:check(S),group:c.errors,cf:c.cf.reconciled};
        }""")
        assert after["month"] == prev + 1, (mode,after)
        assert after["assigned"] > 0 and after["produced"] > 0, (mode,after)
        assert after["utilization"] > 0, (mode,after)
        assert not after["errors"] and not after["group"] and after["cf"], (mode,after)

        # Later explicit decision to stop the plant must survive reload.
        page.evaluate("""()=>{
            const f=current(),id='P80367';
            f.factoryOps.plans[id]=0;f.interplant.partPlans[id]=0;
            f.factoryOps.staffAssignments[id]=0;
        }""")
        intentional = page.evaluate("savePayload(S)")
        assert page.evaluate("raw=>restore(raw)", intentional)
        kept = page.evaluate("""()=>{
            const f=current(),id='P80367';
            return {plan:f.factoryOps.mode==='detailed'?f.factoryOps.plans[id]:
                f.interplant.partPlans[id],
                assigned:factoryLaborPlanV026(f).byId[id].assigned};
        }""")
        assert kept == {"plan":0,"assigned":0}, (mode,kept)
    assert not errors, errors
    browser.close()
print("PASS: historical 172-worker/120-capacity/zero-plan saves recover and produce in both modes")
