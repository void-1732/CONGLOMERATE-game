"""Phase 6: paid exploration, finite shared parcels, depletion cost and save/ledger audit."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None, args=["--no-sandbox"])
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        setup = page.evaluate("""() => {
          S=newWorldGame({country:'DE',name:'Phase6 Parent'});
          saveAuto=async()=>true;
          VIEW_FIRM=S.playerId;VIEW_COUNTRY='DE';PAGE='corporateSubsidiaries';render();
          document.querySelector('#subName').value='Phase6 Mine';
          document.querySelector('#subCountry').value='DE';
          document.querySelector('#subIndustry').value='resource';
          document.querySelector('#subCapital').value='650000';
          createSub();syncWorldIdentities(S);
          const f=S.firms.find(f=>f.name==='Phase6 Mine'),p=f?.plants[0];
          if(!p||p.siteId!=='DE-RUH'||!controller(S,f.id))throw Error('controlled mine missing');
          VIEW_FIRM=f.id;PAGE='facilityProduction';render();
          return {firmId:f.id,plantId:p.id};
        }""")
        button = page.locator('[data-world-explore="'+setup["plantId"]+'"]')
        assert button.is_visible() and button.is_enabled()
        page.locator('#'+button.get_attribute("data-world-explore-budget")).fill("1000")
        before = page.evaluate("""id => {
          const f=company(id,S),low=worldExplorationTerms(1000);
          for(let x=0;x<100000;x++){
            const roll=Math.floor(((Math.imul(1664525,x)+1013904223)>>>0)/4294967296*10000);
            if(roll>=low.chanceBps){S.rng=x;break}
          }
          return acc(f,'cash');
        }""", setup["firmId"])
        button.click()
        assert button.is_disabled()
        result = page.evaluate("""({firmId,plantId,before}) => {
          const f=company(firmId,S),p=f.plants.find(x=>x.id===plantId),id=f.id,pid=p.id;
          const seedFor=pred=>{for(let x=0;x<100000;x++){
            const n=(Math.imul(1664525,x)+1013904223)>>>0;
            if(pred(Math.floor(n/4294967296*10000)))return x;
          }throw Error('seed')};
          const reject=fn=>{try{fn();return false}catch{return true}};
          const advance=()=>{if(++S.month>12){S.month=1;S.year++}
            S.monthCommitted=ym(S.year,S.month)-1;applyWorldHistory(S);syncWorldIdentities(S)};
          const low=worldExplorationTerms(1000),high=worldExplorationTerms(1000000),mid=worldExplorationTerms(20000);
          const odds=high.chanceBps>mid.chanceBps&&mid.chanceBps>low.chanceBps
            &&high.precisionBps>mid.precisionBps&&mid.precisionBps>low.precisionBps;
          const wrong=S.firms.find(x=>x.industry==='resource'&&x.country==='DE'&&x.id!==f.id);
          const beforeInvalid=JSON.stringify(S);
          const unauthorized=reject(()=>worldExploreDeposit(S,wrong.id,wrong.plants[0].id,1000))
            &&JSON.stringify(S)===beforeInvalid;
          const fail=S.worldExpansion.explorationAttempts[0];
          const paidFailure=fail.depositId===null&&acc(f,'cash')===before-fail.amount
            &&Object.keys(S.worldExpansion.resourceDeposits).length===0;
          const beforeDuplicate=JSON.stringify(S);
          const duplicate=reject(()=>worldExploreDeposit(S,id,pid,1000))&&JSON.stringify(S)===beforeDuplicate;
          advance();S.rng=seedFor(x=>x<mid.chanceBps);
          const cash2=acc(f,'cash'),ok=worldExploreDeposit(S,id,pid,20000);
          const d=S.worldExpansion.resourceDeposits[ok.depositId];
          const discovered=!!d&&d.initialReserve===d.remaining&&acc(f,'cash')===cash2-ok.amount&&ok.estimate>0;
          const forged=structuredClone(S);forged.worldExpansion.explorationAttempts.at(-1).amount++;
          const tamper=reject(()=>parsePayload(savePayload(forged)));
          const phantom=structuredClone(S);delete phantom.worldExpansion.explorationAttempts;
          const missingAudit=reject(()=>parsePayload(savePayload(phantom)));
          const cash=acc(f,'cash'),stock=f.stock['PRD-R04']?.q??0;
          worldSetMiningPlan(S,id,pid,d.id,10,19);
          const n=worldExtractFromDeposit(S,id,pid,d.id,10,19);
          const mined=n>0&&d.remaining===d.initialReserve-n&&(f.stock['PRD-R04']?.q??0)===stock+n&&acc(f,'cash')===cash-n*19;
          const depletionCost=worldDepositUnitCost(d,19)>19;
          let allCosts=true;
          for(let i=0;i<30&&d.remaining>0;i++){
            advance();const cost=worldDepositUnitCost(d,19),pre=acc(f,'cash');
            const q=worldExtractFromDeposit(S,id,pid,d.id,100000,19);
            allCosts&&=q>0&&acc(f,'cash')===pre-q*cost;
          }
          advance();
          const stopped=d.remaining===0&&d.extracted===d.initialReserve&&worldExtractFromDeposit(S,id,pid,d.id,100,19)===0;
          S.rng=seedFor(x=>x<mid.chanceBps);
          const next=worldExploreDeposit(S,id,pid,20000);
          const followup=next.depositId!==ok.depositId&&S.worldExpansion.resourceDeposits[next.depositId]?.initialReserve===180&&d.remaining===0;
          const saved=parsePayload(savePayload(S));
          const preserved=saved.worldExpansion.resourceDeposits[d.id].remaining===0&&saved.worldExpansion.explorationAttempts.length===3;
          return {odds,unauthorized,paidFailure,duplicate,discovered,tamper,missingAudit,mined,depletionCost,allCosts,stopped,followup,preserved,
            clean:!check(saved).length,conso:!consolidate(saved).errors.length,panel:worldResourceAndPowerPanel(f,true).includes('有償探鉱を実行')};
        }""", {**setup, "before": before})
        assert len(result)==16 and all(result.values()), result
        assert not errors, errors
        print("PASS Phase 6 exploration: 16 checks, paid UI failure, finite discovery, depletion, additional exploration, accounting and restore")
        browser.close()

if __name__ == "__main__":
    main()
