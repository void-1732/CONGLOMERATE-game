"""G10/G11: autonomous investment authorization and a 120-month mixed-fleet run."""
import os
import shutil
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright


root = Path(__file__).resolve().parents[1]
html = (root / "index.html").read_text(encoding="utf-8")
legacy = subprocess.check_output(
    ["git", "show", "cc9d02d4a8a4e81a4a3fa096d86e8395b0c369c3:index.html"], cwd=root, text=True
)
start = """()=> {
    saveAuto=async()=>true;
    S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'長期混在検証'});
    VIEW_FIRM=S.playerId;
    PAGE='dashboard';
    render();
}"""

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
    )
    previous = browser.new_page()
    previous.set_content(legacy)
    previous.evaluate(start)
    raw = previous.evaluate("savePayload(S)")
    previous.close()
    page = browser.new_page(viewport={"width": 390, "height": 844})
    page.set_default_timeout(10000)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.set_content(html)
    page.evaluate(start)
    assert not page.evaluate("old=>restore(old)", raw)  # SPEC-168 excludes incompatible old saves
    ai_id = page.evaluate("""()=>{
        const ai=S.firms.find(f=>f.id!==S.playerId&&f.country==='JP'&&f.industry==='auto');
        for(const f of [current(),ai]){
            f.auto=false;
            f.staff.production=110;
            f.staff.designEngineers=10;
            f.plans[f.models[0].id]=0;
            for(const family of ['engine','transmission','chassis','body','electronics']){
                const values={...PART_FAMILIES[family].defaults};
                if(family==='engine')values.cost=7500;
                submitPartProject(S,f,{family,name:PART_FAMILIES[family].label,values,parent:null,output:null});
                const plan=f.partOperations.engineering.projects.at(-1);
                plan.status='APPROVED';plan.budget=plan.estimate;
            }
        }
        return ai.id;
    }""")

    def month(reduced_ui=False):
        result = page.evaluate("""async lite=>{
            const before=S.monthCommitted;
            // The stress loop exercises the real monthly engine without rebuilding the same report 120 times.
            const draw=render;
            if(lite)render=()=>{};
            try{await runMonth();}finally{render=draw;}
            const g=consolidate(S);
            return {advanced:S.monthCommitted===before+1,at:S.monthCommitted,
                    errors:check(S),consolidated:g.errors,cf:g.cf.reconciled,why:LAST_MONTH_DIAGNOSTIC?.message};
        }""", reduced_ui)
        assert result["advanced"] and not result["errors"] and not result["consolidated"] and result["cf"], result

    month()
    month()
    assert page.evaluate("S.partEconomy.specs.length") == 10
    page.evaluate("""aiId=>{
        const root=current(),ai=company(aiId,S);
        for(const f of [root,ai]){
            const specs=S.partEconomy.specs.filter(x=>x.ownerFirmId===f.id);
            const bom={id:'BOM-'+S.partEconomy.nextSerial++,name:'混在運転のBOM',
                approvedAt:ym(S.year,S.month),lines:Object.fromEntries(specs.map(x=>[x.family,partKey(x)]))};
            f.partOperations.designBoms=[bom];
            f.partOperations.approvedModels=[{modelId:f.models[0].id,bomId:bom.id,plantId:f.plants[0].id}];
            f.models[0].componentMode='detailed';
        }
        for(const spec of S.partEconomy.specs.filter(s=>s.ownerFirmId===root.id)){
            const job=proposeLineJob(S,root,root.plants[0],'ADD_LINE','',partKey(spec),4);
            approveLineJob(S,root,job);
        }
        const legacy={...structuredClone(root.models[0]),id:'M'+S.seq++,name:'従来生産車',componentMode:'legacy'};
        root.models.push(legacy);root.goods[legacy.id]={q:0,v:0};root.plans[legacy.id]=2;
        ai.plans[ai.models[0].id]=18;
        ai.auto=true;
    }""", ai_id)

    # A controlled company may receive a plan, but only a player can start it.
    authority = page.evaluate("""aiId=>{
        const copy=structuredClone(S),ai=company(aiId,copy);
        const owned=company(copy.playerId,copy),plant=ai.plants[0];
        ai.owners=[{id:owned.id,econ:1,vote:1}];
        copy.month=7;
        proposeAIComponentLines(copy,[]);
        const job=copy.partEconomy.aiInvestmentPlans.find(j=>j.firmId===ai.id);
        if(!job||job.state!=='PROPOSED'||acc(ai,'constructionAssets'))return null;
        try{startLineJob(copy,ai,job,'independentAI');return null;}catch(e){}
        if(job.state!=='PROPOSED'||acc(ai,'constructionAssets'))return null;
        approveLineJob(copy,ai,job);
        return [job.approvalMode,job.state,acc(ai,'constructionAssets')===job.cost];
    }""", ai_id)
    assert authority == ["player", "BUILDING", True]

    blocks = page.evaluate("""aiId=>{
        const trial=structuredClone(S),ai=company(aiId,trial),p=ai.plants[0];
        const spec=trial.partEconomy.specs.find(s=>s.ownerFirmId===ai.id&&s.family==='engine');
        const viable=reviewLineInvestment(trial,ai,p,spec,null,true);
        const cash=ai.ledger.cash,staff=ai.staff.production,bindings=ai.partOperations.approvedModels;
        ai.ledger.cash=0;
        const finance=reviewLineInvestment(trial,ai,p,spec,null,true).reason;
        ai.ledger.cash=cash;ai.staff.production=0;
        const labor=reviewLineInvestment(trial,ai,p,spec,null,true).reason;
        ai.staff.production=staff;ai.partOperations.approvedModels=[];
        const demand=reviewLineInvestment(trial,ai,p,spec,null,true).reason;
        ai.partOperations.approvedModels=bindings;
        ai.stock.steel.q=0;ai.stock.rubber.q=0;
        for(const node of trial.supplyNetwork.nodes)if(['steel','rubber'].includes(node.type))node.capacity=0;
        const supply=reviewLineInvestment(trial,ai,p,spec,null,true).reason;
        return {viable,finance,labor,demand,supply};
    }""", ai_id)
    assert not blocks["viable"]["reason"], blocks
    assert "現金" in blocks["finance"] and "人員" in blocks["labor"] and "実受注" in blocks["demand"]
    assert "供給リスク" in blocks["supply"]

    for _ in range(5):
        month()
    job = page.evaluate("id=>S.partEconomy.aiInvestmentPlans.find(j=>j.firmId===id&&j.approvalMode==='independentAI')", ai_id)
    assert job and job["state"] == "BUILDING" and job["review"]["payback"] <= 60, job
    cash_proof = page.evaluate("""([id,job])=>{
        const f=company(id,S),j=f.journals.find(x=>x.id===job.paymentJournal);
        return j.dr[0][0]==='constructionAssets'&&j.cr[0][0]==='cash'&&j.amount===job.cost&&
            acc(f,'constructionAssets')===j.amount&&acc(f,'cash')>=job.review.postApprovalCashFloor;
    }""", [ai_id, job])
    assert cash_proof

    # A save/load preserves an in-flight autonomous job and its one authorization.
    working = page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)", working)
    already = page.evaluate("""([id,plan])=>{
        const trial=structuredClone(S),f=company(id,trial),j=trial.partEconomy.aiInvestmentPlans.find(x=>x.planId===plan);
        const cash=acc(f,'cash');
        try{startLineJob(trial,f,j,'independentAI');return false;}catch(e){}
        return acc(f,'cash')===cash&&f.journals.filter(x=>x.text==='ライン工事着工 '+plan).length===1;
    }""", [ai_id, job["planId"]])
    assert already

    page.evaluate("""()=>{
        const f=current(),plant=f.plants[0];
        for(const line of plant.componentLines)f.partOperations.productionPlans.push({
            plantId:plant.id,lineId:line.lineId,quantity:4,destinationId:null
        });
        const model=f.models.find(m=>m.componentMode==='detailed');
        f.plans[model.id]=2;
        for(const type of SUPPLY_TYPES){
            post(f,{materials:2000},{cash:2000},'試験用生産資材','operating',S);
            const item=f.stock[type]??={q:0,v:0};item.q+=200;item.v+=2000;
        }
        let total=S.firms.reduce((n,f)=>n+f.plants.length,0);
        // Use idle sites to stress selection and ledger references while preserving the active production mix.
        const fleet=[f,...S.firms.filter(x=>x!==f&&engineeringEligible(x))].slice(0,8);
        for(let i=0;total<100;i++,total++){
            const site=fleet[i%fleet.length],base=site.plants[0];
            site.plants.push({...base,id:'P'+S.seq++,name:'検証拠点 '+i,capacity:7,
                construction:null,renovation:null,paused:true,assetTracked:0,componentLines:undefined});
            syncPlant(site);
        }
    }""")
    assert page.evaluate("S.firms.length") >= 20
    assert page.evaluate("S.firms.reduce((n,f)=>n+f.plants.length,0)") >= 100
    mixed_month = False
    for count in range(120):
        month(reduced_ui=True)
        if not mixed_month:
            mixed_month = page.evaluate("""()=>{
                const f=company(S.playerId,S);
                return f.models.some(m=>m.componentMode==='legacy'&&f._productionByModel[m.id]>0)&&
                    f.models.some(m=>m.componentMode==='detailed'&&f._productionByModel[m.id]>0);
            }""")
        if count == 59:
            print("PASS checkpoint: 60 months, 100+ plants, 20+ firms", flush=True)
    assert mixed_month
    assert page.evaluate("""([id,plan])=>{
        const f=company(id,S),j=S.partEconomy.aiInvestmentPlans.find(x=>x.planId===plan);
        return j?.state==='COMPLETE'&&f.plants.some(p=>p.componentLines?.some(l=>l.lineId===j.lineId))&&
            f.partOperations.inventoryLots.some(l=>l.origin.lineId===j.lineId);
    }""", [ai_id, job["planId"]])
    assert page.evaluate("parsePayload(savePayload(S)).monthCommitted===S.monthCommitted")
    page.evaluate("PAGE='factory';VIEW_FIRM=S.playerId;render()")
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    page.set_viewport_size({"width": 1440, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    assert not errors, errors
    browser.close()

print("PASS: autonomous authorization, safe commissioning, mixed manufacturing and 120-month accounting")
