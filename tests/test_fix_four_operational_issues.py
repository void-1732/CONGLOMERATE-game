"""Review-branch integration regression for four operational defects.
No GitHub main writes; local in-memory browser state only.
"""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")

def run_month(page):
    prior=page.evaluate("S.monthCommitted")
    page.evaluate("async()=>await runMonth()")
    result=page.evaluate("""()=>({
        committed:S.monthCommitted,errors:check(S),
        group:consolidate(S).errors,cf:consolidate(S).cf.reconciled,
        diagnostic:LAST_MONTH_DIAGNOSTIC?.message||''
    })""")
    assert result["committed"]==prior+1, result
    assert not result["errors"] and not result["group"] and result["cf"],result
    return result

def supply(page):
    page.evaluate("""()=>{
        const f=current();
        for(const type of ['steel','rubber','aluminum','copper','glass','chemicals']){
            const paid=4000;
            post(f,{materials:paid},{cash:paid},'4項目検証用追加材料の購入','operating',S);
            f.stock[type].q+=400;f.stock[type].v+=paid;
        }
    }""")
    assert not page.evaluate("check(S)")

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
        args=["--no-sandbox"])
    page=browser.new_page(viewport={"width":1440,"height":960})
    errors=[]
    page.on("pageerror",lambda err:errors.append(str(err)))
    page.set_content(HTML,wait_until="domcontentloaded")
    page.evaluate("saveAuto=async()=>true")

    # 1: Upgrade makes a live factory temporarily unavailable, then resumes.
    page.evaluate("""()=>{
        S=newGame({era:1900,country:'JP',difficulty:'normal',
          history:'historical',name:'設備更新検証'});
        VIEW_FIRM=S.playerId;
        const f=current();
        f.staff.production=120;
        f.plans[f.models[0].id]=35;
    }""")
    supply(page)
    state=page.evaluate("""()=>{
        const p=current().plants[0];
        manageFactoryV21(p.id,'upgrade');
        return {id:p.id,renovation:p.renovation,paused:p.paused,plan:current().plans[current().models[0].id]};
    }""")
    assert state["renovation"]["monthsLeft"]==2 and not state["paused"],state
    run_month(page)
    still=page.evaluate("""id=>{
       const p=current().plants.find(x=>x.id===id);
       return {renovation:p.renovation,produced:p.lastProduced};
    }""",state["id"])
    assert still["renovation"]["monthsLeft"]==1 and still["produced"]==0,still
    run_month(page)
    active=page.evaluate("""id=>{
       const f=current(),p=f.plants.find(x=>x.id===id);
       return {renovation:p.renovation,paused:p.paused,tier:p.equipmentTier,
          produced:p.lastProduced,plan:f.plans[f.models[0].id],
          utilization:p.lastUtilization};
    }""",state["id"])
    assert active["renovation"] is None and not active["paused"],active
    assert active["tier"]==2 and active["produced"]>0 and active["utilization"]>0,active
    assert active["plan"]==state["plan"],(active,state)
    # A knowingly paused plant must not be silently upgraded and left idle.
    page.evaluate("""id=>{
        const p=current().plants.find(x=>x.id===id);
        p.paused=true;manageFactoryV21(id,'extend');
    }""",state["id"])
    paused=page.evaluate("""id=>{
        const p=current().plants.find(x=>x.id===id);
        return {paused:p.paused,renovation:p.renovation};
    }""",state["id"])
    assert paused["paused"] and paused["renovation"] is None,paused

    # 2 and 4: UI schedule writes to the active engine; idle parts remain in
    # plant-specific inventory without any explicit or implicit shipping.
    page.evaluate("""()=>{
        S=newGame({era:1900,country:'JP',difficulty:'normal',
          history:'historical',name:'部品工場・部品在庫検証'});
        VIEW_FIRM=S.playerId;
        const f=current(),old=f.plants[0];
        f.staff.production=172;
        for(const m of f.models)f.plans[m.id]=0;
        f.plants.push({...structuredClone(old),id:'REVIEW-PART',
          name:'検証用部品工場',kind:'components',capacity:120,
          condition:100,equipmentTier:1,paused:false,
          construction:null,renovation:null,componentLines:[],
          assetTracked:0,lastProduced:0,lastUtilization:0});
        ensureFactoryV21(f);f.factoryOps.mode='legacy';
        f.factoryOps.plans['REVIEW-PART']=0;
        f.interplant.partPlans['REVIEW-PART']=0;
        PAGE='facilityProduction';render();
        FACTORY_UI.selected='REVIEW-PART';renderFactorySelected();
        document.getElementById('factoryOnePlan').value='80';
        saveFactoryRouteOne('REVIEW-PART');
    }""")
    initial=page.evaluate("""()=>{
        const f=current(),id='REVIEW-PART';
        return {legacy:f.interplant.partPlans[id],detailed:f.factoryOps.plans[id],
            assigned:factoryLaborPlanV026(f).byId[id]?.assigned,
            capacity:supportOutputCapacityV035(f.plants.find(p=>p.id===id))};
    }""")
    assert initial["legacy"]==80 and initial["detailed"]==0,initial
    assert initial["assigned"]>=40 and initial["capacity"]>=80,initial
    supply(page)
    run_month(page)
    built=page.evaluate("""()=>{
        const f=current(),id='REVIEW-PART',p=f.plants.find(x=>x.id===id);
        const stock=f.interplant.siteComponents[id]||0;
        return {output:p.lastProduced,stock,units:f.stock.components.q,
           screen:factoryInventoryAuditV035(S,f,p)};
    }""")
    assert built["output"]>=70 and built["stock"]>=70,built
    assert "共通部品（工場内）" in built["screen"],built
    page.evaluate("""()=>{
        const f=current();f.interplant.partPlans['REVIEW-PART']=0;
    }""")
    run_month(page)
    left=page.evaluate("current().interplant.siteComponents['REVIEW-PART']")
    assert left==built["stock"],(left,built)

    # Switch to detailed specialist manufacturing: its schedule and inventory
    # must now use factoryOps, without altering legacy stock.
    page.evaluate("""()=>{
        const f=current();f.factoryOps.mode='detailed';
        PAGE='facilityProduction';render();FACTORY_UI.selected='REVIEW-PART';renderFactorySelected();
        document.getElementById('factoryOnePlan').value='50';
        saveFactoryRouteOne('REVIEW-PART');
    }""")
    state=page.evaluate("""()=>{
        const f=current(),id='REVIEW-PART';
        return {legacy:f.interplant.partPlans[id],detailed:f.factoryOps.plans[id],
          assigned:factoryLaborPlanV026(f).byId[id].assigned};
    }""")
    assert state["legacy"]==0 and state["detailed"]==50 and state["assigned"]>0,state
    run_month(page)
    stock=page.evaluate("""()=>{
        const f=current(),id='REVIEW-PART',p=f.plants.find(x=>x.id===id);
        return {modules:moduleAtV21(f,id).moduleElectronics,
          legacy:f.interplant.siteComponents[id],produced:p.lastProduced,
          html:factoryDetailMarkup(f,p,true)};
    }""")
    assert stock["modules"]>0 and stock["legacy"]==left,stock
    assert "部品在庫の台帳照合" in stock["html"],stock

    # 3: A legally distinct foreign sales company must handle actual
    # manufacturer sales, receive revenue and survive saves & consolidation.
    page.evaluate("""()=>{
        S=newGame({era:1900,country:'JP',difficulty:'normal',
           history:'historical',name:'海外販売法人検証'});
        VIEW_FIRM=S.playerId;
        const f=current();f.staff.production=150;
        f.plans[f.models[0].id]=60;
        PAGE='marketExport';render();
        document.getElementById('salesCorpCountry').value='US';
        establishSalesCorporation();
    }""")
    founded=page.evaluate("""()=>{
        const f=current(),id=f.distribution.salesCorporations.US,
          agency=company(id);
        return {id,mode:f.distribution.contracts.US.channel,
          dealerId:f.distribution.contracts.US.dealerId,
          industry:agency.industry,share:agency.owners[0]?.econ,
          check:check(S),group:consolidate(S).errors};
    }""")
    assert founded["id"] and founded["mode"]=="subsidiary",founded
    assert founded["dealerId"]==founded["id"] and founded["industry"]=="sales",founded
    assert founded["share"]==1 and not founded["check"] and not founded["group"],founded
    # Backward compatibility: old saves with an already-established agent lacked
    # the dealerId link. The migration must make those agents operational too.
    page.evaluate("delete current().distribution.contracts.US.dealerId")
    old_save=page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)",old_save)
    linked=page.evaluate("""()=>{
        const f=current();
        return {agency:f.distribution.salesCorporations.US, dealer:f.distribution.contracts.US.dealerId};
    }""")
    assert linked["agency"]==linked["dealer"],linked
    supply(page)
    receipts=[]
    for _ in range(8):
        run_month(page)
        rec=page.evaluate("""()=>{
            const maker=current(),agent=company(maker.distribution.salesCorporations.US);
            return {agentUnits:agent.agencyOperations?.units||0,
              agentSales:agent._salesNow,serviceRevenue:acc(agent,'serviceRevenue'),
              makerExports:maker.distribution.history.filter(x=>x.country==='US').length,
              agentMonthly:agent.monthly.sales};
        }""")
        receipts.append(rec)
        if rec["agentUnits"]>0 and rec["agentMonthly"]>0:break
    assert any(r["agentUnits"]>0 and r["agentMonthly"]>0 for r in receipts),receipts
    save=page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)",save)
    assert not page.evaluate("check(S)") and not page.evaluate("consolidate(S).errors")
    assert page.evaluate("consolidate(S).cf.reconciled")
    assert not errors,errors
    browser.close()
print("PASS: upgrade+resume, two specialist engine schedules, persistent inventories, regional sales agency and consolidated accounting")
