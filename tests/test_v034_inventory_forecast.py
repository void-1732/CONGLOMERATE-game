"""v0.34: inventory forecasts, lead times, policy persistence and monthly regression."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")


def run():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
            args=["--no-sandbox"])
        page=browser.new_page(viewport={"width":1440,"height":960})
        errors=[]
        page.on("pageerror", lambda e:errors.append(str(e)))
        page.set_content(HTML,wait_until="domcontentloaded")
        metrics=page.evaluate("""() => {
            saveAuto=async()=>true;
            S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'資材予測検証'});
            const f=company(S.playerId,S),t='steel';
            const m=f.models.find(x=>x.status==='active');
            if(m)f.plans[m.id]=Math.max(10,f.plans[m.id]||0);
            const c=f.supply.contracts[t],original={...c};
            const oldStock=f.stock[t].q,oldValue=f.stock[t].v;
            delete c.safetyMonths;c.buffer=2;
            const legacy=safetyMonthsV034(c);
            c.safetyMonths=.5;
            const low=factoryResourceTargetV026(f,t,S);
            c.safetyMonths=2;
            const high=factoryResourceTargetV026(f,t,S);
            c.safetyMonths=.5;
            const node=S.supplyNetwork.nodes.find(n=>n.id===c.supplierId);
            const key=node?.id||'NPC:JP:steel';
            S.supplyRisk.active[key]={delay:2,capacityFactor:1,remaining:2};
            const delay=factoryResourceTargetV026(f,t,S);
            const month=ym(S.year,S.month);
            const inTwo={id:'V034ETA2',type:t,qty:5,totalBase:500,
                due:month+2,supplierId:key,origin:f.country};
            const inThree={id:'V034ETA3',type:t,qty:7,totalBase:700,
                due:month+3,supplierId:key,origin:f.country};
            f.supply.inbound.push(inTwo,inThree);
            const purchase=resourcePurchaseNeedV034(f,t,S,delay);
            const forecast=resourceForecastV034(f,t,S,6);
            f.supply.inbound=f.supply.inbound.filter(x=>!x.id.startsWith('V034ETA'));
            delete S.supplyRisk.active[key];
            Object.assign(c,original);
            return {
                legacy,low:{demand:low.demand,target:low.target,safety:low.safetyStock,lead:low.leadMonths},
                high:{target:high.target,safety:high.safetyStock},
                delay:{target:delay.target,lead:delay.leadMonths},
                purchase,forecastMonths:forecast.rows.length,
                arrivals:forecast.rows.map(x=>x.arrivals),
                conserved:oldStock===f.stock[t].q&&oldValue===f.stock[t].v,
                errors:check(S)
            };
        }""")
        assert metrics["legacy"]==1.5,metrics
        assert metrics["low"]["demand"]>0 and metrics["high"]["target"]>metrics["low"]["target"],metrics
        assert metrics["delay"]["lead"]==2 and metrics["delay"]["target"]>metrics["low"]["target"],metrics
        assert metrics["purchase"]["dueByLead"]==5,metrics
        assert metrics["forecastMonths"]==6 and metrics["arrivals"][2]==5 and metrics["arrivals"][3]==7,metrics
        assert metrics["conserved"] and not metrics["errors"],metrics

        launch=page.evaluate("""() => {
            const f=company(S.playerId,S),parent=f.models.find(m=>m.status==='active');
            if(!parent)throw Error('発売済み車種がありません');
            const type='steel',base=factoryResourceTargetV026(f,type,S).demand;
            const oldSafety=f.supply.contracts[type].safetyMonths;
            f.supply.contracts[type].safetyMonths=1;
            const without=factoryResourceTargetV026(f,type,S).target;
            f.projects.push({kind:'grade',gradeParent:parent.id,design:parent.design,
                name:'次期グレード',status:'developing',left:2});
            const first=supplyExpectedDemandV034(f,type,S,1,base);
            const second=supplyExpectedDemandV034(f,type,S,2,base);
            const scheduled=factoryResourceTargetV026(f,type,S).target;
            const notice=supplyFutureEventsV034(f,S).some(x=>x.description.includes('次期グレード'));
            f.projects.pop();
            f.supply.contracts[type].safetyMonths=oldSafety;
            return {first,second,base,without,scheduled,notice,errors:check(S)};
        }""")
        assert launch["first"]==launch["base"] and launch["second"]>launch["base"],launch
        assert launch["scheduled"]>launch["without"] and launch["notice"] and not launch["errors"],launch

        # All seven material policies are saved by the actual UI, not only helpers.
        settings=page.evaluate("""() => {
            PAGE='supplyContracts';VIEW_FIRM=S.playerId;render();
            const policy=document.getElementById('buffer_steel');
            const automatic=document.getElementById('autoOrder_steel');
            if(!policy||!automatic)throw Error('調達設定UIが見つかりません');
            policy.value='1.5';automatic.checked=false;
            saveSupply();
            const f=company(S.playerId,S);
            return {policy:f.supply.contracts.steel.safetyMonths,
                automatic:f.supply.contracts.steel.autoOrder,
                inPage:(()=>{PAGE='supply';render();return document.body.textContent.includes('6か月先予測')})(),
                errors:check(S)};
        }""")
        assert settings["policy"]==1.5 and settings["automatic"] is False,settings
        assert settings["inPage"] and not settings["errors"],settings

        manual=page.evaluate("""() => {
            const f=company(S.playerId,S);
            procureNetwork(S,[]);
            return {steel:f.supply.lastAttempt.steel,errors:check(S)};
        }""")
        assert manual["steel"]["ordered"]==0 and not manual["errors"],manual

        page.evaluate("""() => {
            const f=company(S.playerId,S);
            f.supply.contracts.steel.autoOrder=true;
        }""")
        for month in range(24):
            result=page.evaluate("""async() => {
                const before=S.monthCommitted;
                await runMonth();
                const conso=consolidate(S);
                return {advanced:S.monthCommitted===before+1,errors:check(S),
                    group:conso.errors,cf:conso.cf.reconciled,
                    diag:LAST_MONTH_DIAGNOSTIC?.message};
            }""")
            assert result["advanced"] and not result["errors"] and not result["group"] and result["cf"],(month,result)

        payload=page.evaluate("savePayload(S)")
        assert page.evaluate("x=>restore(x)",payload)
        assert not page.evaluate("check(S)")
        assert not errors,errors
        browser.close()


if __name__=="__main__":
    run()
    print("PASS v0.34: safety policy, six-month ETA, disabled auto orders, 24-month accounting and saves")
