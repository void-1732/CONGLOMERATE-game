"""Known finite deposits: placement, acquisition, depletion, price and persistence."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]

def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
        page=browser.new_page()
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.set_content((ROOT/"index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        ids=page.evaluate("""async()=>{
          saveAuto=async()=>true;S=newWorldGame({country:'JP',name:'Mining group'});
          VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='corporateSubsidiaries';render();
          document.querySelector('#subName').value='Mine';document.querySelector('#subCountry').value='JP';
          document.querySelector('#subIndustry').value='resource';document.querySelector('#subCapital').value='1100000';
          createSub();syncWorldIdentities(S);
          const f=S.firms.find(x=>x.name==='Mine'),id=f.id;VIEW_FIRM=id;PAGE='facilityExpansion';render();
          document.querySelector('#factoryScale').value='small';document.querySelector('#factoryKind').value='assembly';
          document.querySelector('#factoryName').value='Ashio';document.querySelector('#factorySite').value='JP-ASHIO';
          factoryBuild();
          const p=f.plants.find(x=>x.name==='Ashio'),pid=p.id,start=S.monthCommitted;
          const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
          const reject=fn=>{try{fn();return false}catch{return true}};
          const unavailable=reject(()=>worldClaimKnownDeposit(S,id,pid,'JP-ASHIO'))&&!worldExplorationFieldOpen(S,worldExplorationField('US-MOUNTAINPASS'));
          await close();await close();
          const mf=company(id,S),cash=acc(mf,'cash'),stock=mf.stock['PRD-R02']?.q??0;
          VIEW_FIRM=id;PAGE='facilityProduction';render();
          return {id,pid,start,cash,stock,unavailable};
        }""")
        page.locator('[data-world-known-plant="'+ids["pid"]+'"][data-world-known-field="JP-ASHIO"]').click()
        result=page.evaluate("""async({id,pid,start,cash,stock,unavailable})=>{
          const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
          const reject=fn=>{try{fn();return false}catch{return true}};
          const catalog=Object.keys(WORLD_EXPLORATION_FIELDS).every(key=>{const x=worldKnownDeposit(key);return x?.initialReserve>0&&!!x.field.source&&x.id.endsWith('-KNOWN')});
          const mf=company(id,S),did=worldKnownDeposit('JP-ASHIO').id,d=S.worldExpansion.resourceDeposits[did];
          const claim=d.status==='MODEL_KNOWN'&&d.remaining===180&&(mf.stock['PRD-R02']?.q??0)===stock&&acc(mf,'cash')===cash;
          const duplicate=reject(()=>worldClaimKnownDeposit(S,id,pid,'JP-ASHIO'))&&reject(()=>worldExploreDeposit(S,id,pid,20000,'JP-ASHIO'));
          const forged=structuredClone(S);forged.worldExpansion.resourceDeposits[did].initialReserve++;forged.worldExpansion.resourceDeposits[did].remaining++;
          const tamper=reject(()=>parsePayload(savePayload(forged)));
          worldSetMiningPlan(S,id,pid,did,10,190);await close();
          const a=S.worldExpansion.resourceDeposits[did],n=company(id,S),q=n.stock['PRD-R02'];
          const extraction=a.extracted>0&&a.remaining===180-a.extracted&&q.q===stock+a.extracted;
          const price=worldResourceScarcityBps(S,'JP','PRD-R02')>0&&worldDepositUnitCost(a,190)>190;
          const saved=parsePayload(savePayload(S)),restore=saved.worldExpansion.knownDepositClaims.length===1&&saved.worldExpansion.resourceDeposits[did].remaining===a.remaining;
          const clean=check(S).length===0&&consolidate(S).errors.length===0;
          return {catalog,unavailable,claim,duplicate,tamper,extraction,price,restore,clean,months:S.monthCommitted===start+3};
        }""",ids)
        assert len(result)==10 and all(result.values()),result
        assert not errors,errors
        print("PASS Phase 6 known deposits: 10 checks, UI, 3 real months, scarcity, accounting and restore")
        browser.close()
if __name__=="__main__":main()
