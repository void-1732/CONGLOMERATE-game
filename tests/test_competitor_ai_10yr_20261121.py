"""Independent competitor-AI factory, logistics and supply stress measurement (120 real months).
All figures are actual post-commit game-state readings, not assumed utilization.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os, shutil, sys
HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=["--no-sandbox"])
    page=browser.new_page(viewport={"width":1360,"height":900})
    page.set_default_timeout(0)
    js_errors=[]
    page.on("pageerror", lambda e:js_errors.append(str(e)))
    page.set_content(HTML,wait_until="domcontentloaded")
    init=page.evaluate("""()=>{
        saveAuto=async()=>true;
        S=newGame({era:1900,country:'JP',difficulty:'easy',history:'historical',name:'百年経営実験'});
        VIEW_FIRM=S.playerId;PAGE='dashboard';
        const f=company(S.playerId,S);
        f.delegate.mode='delegated';f.delegate.priority='balanced';
        f.delegate.productionAuto=true;f.delegate.researchAuto=true;
        f.delegate.minCashBase=0;f.delegate.researchMaxBase=11000;
        f.delegate.automation={...f.delegate.automation,price:true,procurement:true,maintenance:true,marketing:false,limitBase:12000};
        ensureAiCenter(f);
        for(const k of ['production','research','price','procurement','maintenance'])f.delegate.aiCenter.modes[k]='routine';
        f.hr.trainingBudgetBase=500;
        window.__rivalAudit={monthly:[],birth:{},first:[]};
        const rivals=S.firms.filter(x=>!x.player&&x.auto&&!controller(S,x.id));
        window.__rivalAudit.first=rivals.map(x=>({id:x.id,name:x.name,industry:x.industry,plantCount:x.plants?.length||0,staff:x.staff.production,models:x.models.length}));
        return {date:[S.year,S.month],rivalCount:rivals.length,autoManufacturers:rivals.filter(x=>['auto','manufacturing'].includes(x.industry)).length,
            gameErrors:check(S)};
    }""")
    print("RIVAL_START "+json.dumps(init,ensure_ascii=False),flush=True)
    fail=None
    for yr in range(10):
        annual=page.evaluate("""async()=>{
            const draw=render;render=()=>{};
            const take=()=>{
                const rivals=S.firms.filter(x=>!x.player&&x.auto&&!controller(S,x.id)&&x.lifecycle?.phase!=='withdrawn');
                const makers=rivals.filter(x=>['auto','manufacturing'].includes(x.industry));
                const activePlants=makers.flatMap(f=>(f.plants||[]).filter(p=>!p.construction&&!p.paused&&!p.renovation&&['integrated','assembly'].includes(p.kind)));
                const allPlants=makers.flatMap(f=>f.plants||[]);
                const planned=makers.reduce((n,f)=>n+Object.values(f.plans||{}).reduce((a,b)=>a+Math.max(0,Number(b)||0),0),0);
                const produced=makers.reduce((n,f)=>n+Math.max(0,f._produced||0),0);
                const materialShortages=makers.map(f=>({f,q:Object.values(f.supply?.lastAttempt||{}).reduce((n,x)=>n+Math.max(0,x.shortage||0),0)}));
                const stockouts=materialShortages.filter(x=>x.q>0);
                const sampleNames=['日本交通機械','North Atlantic Motors','Albion Motor Works','Continental Automobil','Automobiles Lumière'];
                const examples=makers.filter(f=>sampleNames.includes(f.name)).map(f=>({
                    name:f.name,production:f._produced||0,planned:Object.values(f.plans||{}).reduce((n,x)=>n+(x||0),0),
                    plantUtilization:(f.plants||[]).filter(p=>['integrated','assembly'].includes(p.kind)).map(p=>Math.round(1000*(p.lastUtilization||0))/10),
                    plantCapacity:(f.plants||[]).filter(p=>['integrated','assembly'].includes(p.kind)).map(p=>p.capacity),
                    plants:f.plants?.length||0,staff:f.staff.production,
                    models:f.models.length,projects:f.projects.length,
                    shortage:materialShortages.find(x=>x.f.id===f.id)?.q||0,
                    distress:f.distress?.stage||0,monthlySales:f.monthly?.units||0,
                    cash:acc(f,'cash')
                }));
                const supply=S.supplyNetwork?.nodes||[];
                const inv=Object.values(ensureNpcV033(S).markets||{}).flatMap(x=>Object.values(x||{}));
                return {year:S.year,month:S.month,competitors:rivals.length,manufacturers:makers.length,
                    makerFactories:allPlants.length,activeAssemblyPlants:activePlants.length,
                    meanAssemblyUtilization:activePlants.length?Math.round(activePlants.reduce((n,x)=>n+(x.lastUtilization||0),0)/activePlants.length*1000)/10:null,
                    zeroUtilizationPlants:activePlants.filter(x=>!(x.lastUtilization>0)).length,
                    planned,produced,productionOverPlan:planned?Math.round(produced/planned*1000)/10:null,
                    zeroProductionMakers:makers.filter(f=>!(f._produced>0)).length,
                    shortageMakers:stockouts.length,shortageUnits:stockouts.reduce((n,x)=>n+x.q,0),
                    supplyRiskShortagesCumulative:makers.reduce((n,x)=>n+(x.supplyRiskShortages||0),0),
                    distressedMakers:makers.filter(f=>f.distress?.stage>0).length,
                    activeModels:makers.reduce((n,f)=>n+f.models.filter(m=>m.status==='active').length,0),
                    makerTotalModels:makers.reduce((n,f)=>n+f.models.length,0),
                    makerStaff:makers.reduce((n,f)=>n+f.staff.production,0),
                    npcMarketCount:inv.length,npcNegativeStocks:inv.filter(x=>x.stock<0).length,
                    investmentPlans:S.partEconomy?.aiInvestmentPlans?.length||0,
                    exampleFirms:examples};
            };
            try{
                const metrics=[];
                for(let i=0;i<12;i++){
                    const before=S.monthCommitted;
                    await runMonth();
                    if(S.monthCommitted!==before+1) return {ok:false,reason:'NO_ADVANCE',before,after:S.monthCommitted,diag:LAST_MONTH_DIAGNOSTIC};
                    const e=check(S),c=consolidate(S);
                    if(e.length||c.errors.length||!c.cf.reconciled)return {ok:false,reason:'ACCOUNTING',errors:e,group:c.errors,cf:c.cf.reconciled,diag:LAST_MONTH_DIAGNOSTIC};
                    const row=take();
                    window.__rivalAudit.monthly.push(row);
                    metrics.push(row);
                }
                const last=metrics[metrics.length-1];
                return {ok:true,year:last.year,month:last.month,snapshot:last,
                    trailing12:{
                        meanProductionOverPlan:Math.round(metrics.reduce((n,x)=>n+x.produced,0)/Math.max(1,metrics.reduce((n,x)=>n+x.planned,0))*1000)/10,
                        shortageMakerMonths:metrics.reduce((n,x)=>n+x.shortageMakers,0),
                        makerMonths:metrics.reduce((n,x)=>n+x.manufacturers,0),
                        zeroProductionMakerMonths:metrics.reduce((n,x)=>n+x.zeroProductionMakers,0),
                        zeroAssemblyPlantMonths:metrics.reduce((n,x)=>n+x.zeroUtilizationPlants,0),
                        assemblyPlantMonths:metrics.reduce((n,x)=>n+x.activeAssemblyPlants,0),
                        minUtilization:Math.min(...metrics.map(x=>x.meanAssemblyUtilization)),
                        maxUtilization:Math.max(...metrics.map(x=>x.meanAssemblyUtilization))
                    }};
            }finally{render=draw;}
        }""")
        print("RIVAL_YEAR "+json.dumps(annual,ensure_ascii=False),flush=True)
        if not annual.get('ok'):
            fail=annual;break
    final=page.evaluate("""()=>{
        const records=window.__rivalAudit.monthly,first=window.__rivalAudit.first;
        const last=records.at(-1);
        const makerNames=new Set(first.filter(x=>['auto','manufacturing'].includes(x.industry)).map(x=>x.name));
        const initialCount=makerNames.size;
        const initialRivals=first.length;
        const n=records.reduce((o,x)=>{o.makerMonths+=x.manufacturers;o.zeroProductionMakerMonths+=x.zeroProductionMakers;
            o.shortageMakerMonths+=x.shortageMakers;o.shortageUnits+=x.shortageUnits;
            o.planned+=x.planned;o.produced+=x.produced;o.assemblyPlantMonths+=x.activeAssemblyPlants;
            o.zeroUtilPlantMonths+=x.zeroUtilizationPlants;return o},
            {makerMonths:0,zeroProductionMakerMonths:0,shortageMakerMonths:0,shortageUnits:0,
                planned:0,produced:0,assemblyPlantMonths:0,zeroUtilPlantMonths:0});
        return {initialRivals,initialMakers:initialCount,initialList:first,
            completedMonths:records.length,totals:n,final:last,
            errors:check(S),cf:consolidate(S).cf.reconciled,
            aiInvestmentPlans:(S.partEconomy?.aiInvestmentPlans||[]).map(j=>({firmId:j.firmId,state:j.state,approvalMode:j.approvalMode})).slice(0,20),
            diagnosis:LAST_MONTH_DIAGNOSTIC?.message||null};
    }""")
    result={"init":init,"final":final,"failure":fail,"browserErrors":js_errors}
    Path("rival_ai_10year_report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print("RIVAL_FINAL "+json.dumps({k:v for k,v in final.items() if k not in ['initialList']},ensure_ascii=False),flush=True)
    browser.close()
    if fail or js_errors or final['completedMonths']!=120:sys.exit(1)
