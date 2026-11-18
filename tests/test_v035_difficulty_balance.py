"""v0.35 STEP 4: BOM-based start inventory and balanced difficulty scenarios.

Checks real stock / GL reconciliation, finite NPC purchases by later entrants,
difficulty risk settings, cross-era monthly operation, and old save migration.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"index.html").read_text(encoding="utf-8")
OLD_HTML=subprocess.check_output(
    ["git","show","be11e80cfe53bb75b7ea4f54306b009e7cf0d1dc:index.html"],
    cwd=ROOT,text=True)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
        args=["--no-sandbox"])
    page=browser.new_page()
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.set_content(HTML,wait_until="domcontentloaded")
    scenarios=[]
    for difficulty,era,country,months in [
        ("easy",1900,"JP",24),
        ("normal",1960,"US",24),
        ("hard",2010,"DE",24)]:
        start=page.evaluate("""({difficulty,era,country})=>{
            saveAuto=async()=>true;
            S=newGame({era,country,difficulty,history:'historical',name:'STEP4 難易度と創業'});
            const f=company(S.playerId,S),setting=supplyDifficultyV035(S);
            const inventory=SUPPLY_TYPES.map(type=>{
                const expected=Math.ceil(factoryResourceTargetV026(f,type,S).demand*setting.startupMonths);
                const observed=f.stock[type]?.q||0;
                return {type,expected,observed,demand:factoryResourceTargetV026(f,type,S).demand};
            });
            const supply=ensureNpcV033(S),initialStock=Object.values(supply.markets)
                .reduce((n,region)=>n+Object.values(region).reduce((v,market)=>v+market.stock,0),0);
            return {difficulty,era,country,months:setting.startupMonths,
                spare:acc(f,'cash'),credit:f.startupMaterialsV035.tradeCredit,
                charged:f.startupMaterialsV035.cost,
                supplyMultiplier:setting.npcSupplyMultiplier,
                inventory,initialStock,firmCount:S.firms.length,
                source:f.startupMaterialsV035.source,stockBook:acc(f,'materials'),
                stockValues:Object.values(f.stock).reduce((v,x)=>v+x.v,0),errors:check(S)};
        }""",{"difficulty":difficulty,"era":era,"country":country})
        assert not start["errors"],start
        assert start["inventory"] and all(x["expected"]==x["observed"] for x in start["inventory"]),start
        assert start["source"]=="開始前の仕入" and start["stockValues"]==start["stockBook"],start
        assert start["initialStock"]>0 and start["firmCount"]>=5 and start["spare"]>=0,start
        assert start["charged"]>=start["credit"]>=0,start
        assert start["months"]=={"easy":2,"normal":1.5,"hard":1}[difficulty],start

        # New companies founded after game start must buy only real NPC stock.
        late=page.evaluate("""()=> {
            // A synthetic new firm changes the consolidation population, so
            // isolate its entry on a clone of the committed scenario.
            const scenario=structuredClone(S);
            const before=Object.fromEntries(SUPPLY_TYPES.map(t=>[t,npcMarketV033(scenario,'JP',t).stock]));
            const firm=initFirm(scenario,{name:'市場調達・新設法人',country:'JP',
                industry:'manufacturing',size:.4,seedBase:800000,strategy:'balanced'});
            const after=Object.fromEntries(SUPPLY_TYPES.map(t=>[t,npcMarketV033(scenario,'JP',t).stock]));
            const consumed=Object.fromEntries(SUPPLY_TYPES.map(t=>[t,before[t]-after[t]]));
            const received=Object.fromEntries(SUPPLY_TYPES.map(t=>[t,firm.startupMaterialsV035.quantities[t]?.units||0]));
            return {consumed,received,errors:check(scenario),source:firm.startupMaterialsV035.source};
        }""")
        assert late["consumed"]==late["received"] and not late["errors"],late
        assert late["source"]=="地域NPC市場からの開業仕入",late

        # Stronger difficulty does not bypass normal physical inventory limits.
        risk=page.evaluate("""()=>{
            const s=structuredClone(S),region='JP',type='steel';
            const m=npcMarketV033(s,region,type),month=ym(s.year,s.month);
            s.supplyRisk.active[npcIdV033(region,type)]={
                type,country:region,capacityFactor:.4,reason:'テスト供給障害',
                supplierName:'市場',remaining:3,delay:1,pricePct:.08,start:month};
            nextMonthDate(s);produceNpcV033(s,[]);
            return {produced:m.lastProduced,limit:Math.floor(m.capacity*.4),
                conserved:m.stock+m.dispatchedTotal===m.producedTotal,errors:check(s)};
        }""")
        assert risk["produced"]<=risk["limit"] and risk["conserved"] and not risk["errors"],risk

        completed=0
        output=0
        planned=0
        months_with_raw_shortage=0
        for i in range(24):
            result=page.evaluate("""async()=>{
                const f=company(S.playerId,S),plan=Object.values(f.plans).reduce((a,x)=>a+x,0);
                const old=S.monthCommitted;
                await runMonth();
                const p=company(S.playerId,S),g=consolidate(S);
                return {advanced:S.monthCommitted===old+1,errors:check(S),group:g.errors,cf:g.cf.reconciled,
                    plan,actual:p._produced||0,
                    shortages:Object.values(p.supply.lastAttempt||{}).reduce((n,x)=>n+(x.shortage||0),0),
                    problem:LAST_MONTH_DIAGNOSTIC?.message};
            }""")
            assert result["advanced"] and not result["errors"] and not result["group"] and result["cf"],(difficulty,era,i,result)
            completed+=1;planned+=result["plan"];output+=result["actual"]
            months_with_raw_shortage+=bool(result["shortages"])
        scenarios.append({"difficulty":difficulty,"era":era,"country":country,
            "months":completed,"productionFraction":round(output/max(1,planned),3),
            "shortageMonths":months_with_raw_shortage})
        save=page.evaluate("savePayload(S)")
        assert page.evaluate("raw=>restore(raw)",save)
        assert not page.evaluate("check(S)")

    # A real v0.34 save has no v0.35 stock seeds and must not be modified on load.
    prior=browser.new_page()
    prior.set_content(OLD_HTML,wait_until="domcontentloaded")
    old=prior.evaluate("""()=>{
        let original=newGame({era:1900,country:'JP',history:'historical',
            difficulty:'normal',name:'旧保存を引継ぐ'});
        const stock=Object.fromEntries(original.firms.map(f=>[f.id,
            Object.fromEntries(Object.entries(f.stock).map(([t,q])=>[t,{q:q.q,v:q.v}]))]));
        const cash=Object.fromEntries(original.firms.map(f=>[f.id,acc(f,'cash')]));
        return {save:savePayload(original),stock,cash};
    }""")
    loaded=page.evaluate("""raw=>{
        if(!restore(raw))return {ok:false};
        const stock=Object.fromEntries(S.firms.map(f=>[f.id,
            Object.fromEntries(Object.entries(f.stock).map(([t,q])=>[t,{q:q.q,v:q.v}]))]));
        const cash=Object.fromEntries(S.firms.map(f=>[f.id,acc(f,'cash')]));
        return {ok:true,stock,cash,errors:check(S)};
    }""",old["save"])
    assert loaded["ok"] and loaded["stock"]==old["stock"] and loaded["cash"]==old["cash"] and not loaded["errors"],loaded
    assert not errors,errors
    print("PASS v0.35: difficulty starts, finite new firms, NPC disruptions, 72 months, legacy saves")
    print("V035_BALANCE",json.dumps(scenarios,ensure_ascii=False))
    browser.close()
