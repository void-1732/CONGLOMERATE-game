"""v0.35 STEP 4: startup materials are paid for, capped, difficulty-sensitive and save-safe."""
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
        page=browser.new_page()
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.set_content(HTML,wait_until="domcontentloaded")
        scenarios={}
        for difficulty in ("easy","normal","hard"):
            result=page.evaluate("""(difficulty) => {
                saveAuto=async()=>true;
                S=newGame({era:1900,country:'JP',difficulty,history:'historical',name:'創業需給回帰'});
                const f=company(S.playerId,S);
                const start=f.startupSupplyV035;
                const before=JSON.stringify(Object.fromEntries(SUPPLY_TYPES.map(t=>[t,f.stock[t]])));
                const initialCash=acc(f,'cash'),initialMaterial=acc(f,'materials');
                const paid=start.items.reduce((n,x)=>n+x.cost,0);
                const materials=SUPPLY_TYPES.map(t=>({
                    type:t,stock:f.stock[t].q,
                    supplier:f.supply.contracts[t].supplierId,
                    safety:f.supply.contracts[t].safetyMonths
                }));
                seedStartupSupplyV035(S);
                const idempotent=before===JSON.stringify(Object.fromEntries(SUPPLY_TYPES.map(t=>[t,f.stock[t]])));
                const payload=savePayload(S);
                const recovered=parsePayload(payload);
                const restored=company(recovered.playerId,recovered);
                return {coverage:start.coverage,paid,spent:start.spentLocal,initialCash,
                    initialMaterial,materials,idempotent,
                    restoredStock:SUPPLY_TYPES.every(t=>restored.stock[t].q===f.stock[t].q&&restored.stock[t].v===f.stock[t].v),
                    restoredPaid:restored.startupSupplyV035.spentLocal===paid,
                    errors:check(S),restoredErrors:check(recovered)}
            }""",difficulty)
            assert not result["errors"] and not result["restoredErrors"],(difficulty,result)
            assert result["idempotent"] and result["restoredStock"] and result["restoredPaid"],result
            assert result["spent"]==result["paid"] and result["paid"]>=0,result
            assert result["initialCash"]>=0 and result["initialMaterial"]>=result["paid"],result
            assert all(x["supplier"]=="NPC:JP:"+x["type"] for x in result["materials"]),result
            assert len(result["materials"])==7,result
            scenarios[difficulty]=result
        assert scenarios["easy"]["coverage"]>scenarios["normal"]["coverage"]>scenarios["hard"]["coverage"]
        assert scenarios["easy"]["materials"][0]["safety"]==1
        assert scenarios["normal"]["materials"][0]["safety"]==.5
        assert scenarios["hard"]["materials"][0]["safety"]==.25
        # Execute and audit 24 months of the normal new-game lifecycle.
        page.evaluate("""() => {
            S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'長期検証'});
            saveAuto=async()=>true;
        }""")
        for month in range(24):
            result=page.evaluate("""() => {
                const prior=S.monthCommitted;
                runMonth();
                const group=consolidate(S);
                return {advanced:S.monthCommitted===prior+1,errors:check(S),
                    groupErrors:group.errors,balanced:group.cf.reconciled,
                    diag:LAST_MONTH_DIAGNOSTIC?.message}
            }""")
            assert result["advanced"] and not result["errors"] and not result["groupErrors"] and result["balanced"],(month,result)
        assert not errors,errors
        browser.close()

if __name__=="__main__":
    run()
    print("PASS v0.35 founder inventory: difficulty, payment, local NPC, save, 24 months")
