"""Phase 6 mineral region extension, regional price and paid finite domestic grid."""
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
        mineral=page.evaluate("""async()=>{
          saveAuto=async()=>true;
          S=newWorldGame({country:'JP',name:'Phase6 minerals parent'});
          VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='corporateSubsidiaries';render();
          document.querySelector('#subName').value='JP Mine';
          document.querySelector('#subCountry').value='JP';
          document.querySelector('#subIndustry').value='resource';
          document.querySelector('#subCapital').value='1100000';
          createSub();syncWorldIdentities(S);
          const f=S.firms.find(x=>x.name==='JP Mine'),id=f.id;
          VIEW_FIRM=id;PAGE='facilityExpansion';render();
          const allowed=!document.querySelector('[data-action="factoryBuild"]').disabled;
          document.querySelector('#factoryScale').value='small';
          document.querySelector('#factoryKind').value='assembly';
          document.querySelector('#factoryName').value='Ashio Mine';
          document.querySelector('#factorySite').value='JP-ASHIO';
          factoryBuild();
          const p=f.plants.find(p=>p.name==='Ashio Mine'),pid=p.id;
          const reject=fn=>{try{fn();return false}catch{return true}};
          const pending=!!p.construction&&reject(()=>worldExploreDeposit(S,id,pid,20000,'JP-ASHIO'));
          const fields=Object.keys(WORLD_EXPLORATION_FIELDS).length===25&&worldExplorationFieldsAt('JP-KAMIOKA').length===2;
          const catalog=Object.keys(WORLD_EXPLORATION_FIELDS).every(key=>{const x=worldExplorationField(key);
            return !!findSite(x.siteId)&&!!WORLD_PRODUCT_BY_ID.get(x.productId)&&x.reserves.length===3&&!!x.source});
          const eraLock=!worldExplorationFieldOpen(S,worldExplorationField('US-MOUNTAINPASS'));
          const start=S.monthCommitted,months=p.construction.monthsLeft,base=f.reserveUnits;
          for(let n=0;n<months;n++){await runMonth();if(S.monthCommitted!==start+n+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))}
          const mine=company(id,S),plant=mine.plants.find(x=>x.id===pid);
          const construction=!plant.construction&&S.monthCommitted===start+months&&mine.reserveUnits===base&&mine.plant.capacity>0;
          const other=reject(()=>worldExploreDeposit(S,id,pid,20000,'JP-SADO'));
          for(let x=0;x<100000;x++){if(((Math.imul(1664525,x)+1013904223)>>>0)/4294967296<.49){S.rng=x;break}}
          const a=worldExploreDeposit(S,id,pid,20000,'JP-ASHIO'),d=S.worldExpansion.resourceDeposits[a.depositId];
          const deposit=!!d&&d.productId==='PRD-R02'&&d.id==='DEP-JP-ASHIO-COPPER-1'&&d.remaining===180;
          worldSetMiningPlan(S,id,pid,d.id,10,190);const before=S.monthCommitted;await runMonth();
          const dep=S.worldExpansion.resourceDeposits[d.id],mf=company(id,S),stock=mf.stock['PRD-R02'];
          const monthly=S.monthCommitted===before+1&&dep.extracted>0&&stock?.q===dep.extracted&&mf.reserveUnits===base;
          const scarcity=worldResourceScarcityBps(S,'JP','PRD-R02')>0&&worldResourceScarcityBps(S,'DE','PRD-R02')===0;
          const quote=worldPhase3RegionalB2BUnitPrice(S,mf,'PRD-R02',plant.siteId);
          const undep=structuredClone(S);undep.worldExpansion.resourceDeposits[d.id].status='VERIFIED';
          const baseline=worldPhase3RegionalB2BUnitPrice(undep,company(id,undep),'PRD-R02',plant.siteId);
          const price=quote>baseline&&baseline>0;
          const saved=parsePayload(savePayload(S)),forged=structuredClone(saved);
          forged.worldExpansion.explorationAttempts[0].fieldId='JP-SADO';
          const tamper=reject(()=>parsePayload(savePayload(forged)));
          const persistent=saved.worldExpansion.resourceDeposits[d.id].remaining===dep.remaining;
          return {allowed,pending,fields,catalog,eraLock,construction,other,deposit,monthly,scarcity,price,tamper,persistent,
            clean:!check(saved).length&&!consolidate(saved).errors.length};
        }""")
        assert len(mineral)==14 and all(mineral.values()), mineral
        grid=page.evaluate("""async()=>{
          saveAuto=async()=>true;
          S=newWorldGame({country:'JP',name:'Grid monthly'});
          VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='facilityExpansion';render();
          let f=current();const id=f.id,aid=f.plants[0].id;
          f.staff.production=160;f.staffTarget.production=160;f.auto=false;f.delegate.mode='manual';
          for(const model of f.models)f.plans[model.id]=0;
          for(const name of ['energy-1','materials-1','production-1'])if(!f.research.tree.done.includes(name))f.research.tree.done.push(name);
          const build=(name,site)=>{
            document.querySelector('#factoryScale').value='small';
            document.querySelector('#factoryKind').value='integrated';
            document.querySelector('#factoryName').value=name;
            document.querySelector('#factorySite').value=site;factoryBuild();
            return f.plants.find(p=>p.name===name).id;
          };
          const lid=build('Low priority','JP-OSA'),hid=build('High priority','JP-NGO');
          for(let n=0;n<2;n++){const before=S.monthCommitted;await runMonth();if(S.monthCommitted!==before+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))}
          f=company(id,S);const a=f.plants.find(p=>p.id===aid),low=f.plants.find(p=>p.id===lid),high=f.plants.find(p=>p.id===hid);
          const complete=!low.construction&&!high.construction;
          S.year=1950;S.month=4;S.monthCommitted=ym(S.year,S.month)-1;applyWorldHistory(S);syncWorldIdentities(S);
          f.factoryOps.staffAssignments[hid]=20;
          const add=(key,q,price)=>{const amount=q*price;post(f,{materials:amount},{cash:amount},'試験用実物購入','operating',S);
            const st=f.stock[key]??={q:0,v:0};st.q+=q;st.v+=amount};
          add('PRD-E04',1,300);add('PRD-M06',12,20);add('PRD-E29',2,150);add('PRD-R04',5,19);add('PRD-R30',4,5);
          const ppe=acc(f,'ppe'),materials=acc(f,'materials');
          worldInstallGenerator(S,id,aid);const l1=worldInstallPowerLine(S,id,aid,lid),l2=worldInstallPowerLine(S,id,aid,hid);
          const assets=l1.gridMode==='REGIONAL'&&l2.gridMode==='REGIONAL'&&l1.capacityKwh===60&&l2.lossBps===1000
            &&l1.assetValue===270&&acc(f,'ppe')===ppe+840&&acc(f,'materials')===materials-840
            &&f.stock['PRD-M06'].q===0&&f.stock['PRD-E29'].q===0;
          worldPlanSave(f,high,'PRD-M43',2);
          worldSetGridPlan(S,id,aid,'fuel',7);worldSetGridPlan(S,id,lid,'request',40);worldSetGridPlan(S,id,hid,'request',40);
          const reject=fn=>{try{fn();return false}catch{return true}};
          const rejectsInvalid=reject(()=>worldSetGridPlan(S,id,hid,'request',61));
          const priority=worldGridPriority(S,high)<worldGridPriority(S,low);
          const manual=structuredClone(S);worldGeneratePower(manual,id,aid,5);
          const beforeManual=worldPowerAvailable(manual,aid);
          const manualDenied=reject(()=>worldTransferPower(manual,id,aid,lid,40))
            &&beforeManual===45&&worldPowerAvailable(manual,aid)===beforeManual&&!manual.worldExpansion.powerTransfers.length;
          const before=S.monthCommitted;await runMonth();
          const gen=S.worldExpansion.energyReceipts.at(-1),ts=S.worldExpansion.powerTransfers,budget=S.worldExpansion.powerAllocations[hid],
            out=company(id,S).stock['PRD-M43'];
          const month=S.monthCommitted===before+1;
          const conservation=gen.grossKwh===50&&gen.deliveredKwh===45&&ts.reduce((n,t)=>n+t.sentKwh,0)===45
            &&ts.reduce((n,t)=>n+t.fuelBookCost,0)===gen.fuelBookCost;
          const prioritized=ts[0].targetPlantId===hid&&ts[0].deliveredKwh===36&&ts[1].targetPlantId===lid&&ts[1].deliveredKwh===4;
          const production=out?.q===2&&budget.capitalizedFuelCost>0&&budget.usedKwh===10;
          const shortage=S.lastReport.events.some(x=>x.includes('停電'));
          const saved=parsePayload(savePayload(S)),bad=structuredClone(saved);
          bad.worldExpansion.powerLines[hid].transformValue++;
          const tamper=reject(()=>parsePayload(savePayload(bad)));
          const persistent=saved.worldExpansion.powerTransfers.length===2&&saved.worldExpansion.powerLines[hid].monthlyRequestKwh===40;
          return {complete,assets,rejectsInvalid,priority,manualDenied,month,conservation,prioritized,production,shortage,tamper,persistent,
            clean:!check(saved).length&&!consolidate(saved).errors.length};
        }""")
        assert len(grid)==13 and all(grid.values()), grid
        assert not errors, errors
        print("PASS Phase 6 mineral regions 14 checks; physical regional grid 13 checks, real month, manual and scheduled priority, outage, product cost and save")
        browser.close()

if __name__=="__main__":
    main()
