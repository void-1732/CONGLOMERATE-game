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
          const beforeLand=acc(f,'cash'),title=worldPurchaseMiningLand(S,id,'JP-ASHIO');
          const titleBeforeOperating=!!p.construction&&acc(f,'worldMiningLand')===title.amount&&acc(f,'cash')===beforeLand-title.amount;
          const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
          const reject=fn=>{try{fn();return false}catch{return true}};
          const unavailable=reject(()=>worldClaimKnownDeposit(S,id,pid,'JP-ASHIO'))&&!worldExplorationFieldOpen(S,worldExplorationField('US-MOUNTAINPASS'));
          await close();await close();
          const mf=company(id,S),cash=acc(mf,'cash'),stock=mf.stock['PRD-R02']?.q??0;
          VIEW_FIRM=id;PAGE='facilityProduction';render();
          return {id,pid,start,cash,stock,unavailable,titleBeforeOperating};
        }""")
        page.locator('[data-world-known-plant="'+ids["pid"]+'"][data-world-known-field="JP-ASHIO"]').click()
        result=page.evaluate("""async({id,pid,start,cash,stock,unavailable,titleBeforeOperating})=>{
          const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
          const reject=fn=>{try{fn();return false}catch{return true}};
          const known=Object.keys(WORLD_EXPLORATION_FIELDS).map(worldKnownDeposit);
          const catalog=known.every(x=>x?.initialReserve>0&&!!x.field.source&&x.id.endsWith('-KNOWN'));
          const minerals=new Set(known.map(x=>x.field.productId));
          const regions=new Set(known.map(x=>x.field.country));
          const coverage=minerals.size===18&&regions.size===10&&new Set(known.map(x=>x.id)).size===known.length;
          const oil=worldExplorationField('US-SPINDLETOP'),gas=worldExplorationField('US-PANHANDLE');
          const historicalOpening=!worldExplorationFieldOpen({...S,year:1900},oil)
            &&worldExplorationFieldOpen({...S,year:1901},oil)
            &&!worldExplorationFieldOpen({...S,year:1917},gas)
            &&worldExplorationFieldOpen({...S,year:1918},gas);
          const brokenHill=worldExplorationFieldsAt('AU-BROKENHILL').map(worldKnownDeposit);
          const colocated=brokenHill.length===3&&new Set(brokenHill.map(x=>x.field.productId)).size===3;
          const mf=company(id,S),did=worldKnownDeposit('JP-ASHIO').id,d=S.worldExpansion.resourceDeposits[did];
          const claim=d.status==='MODEL_KNOWN'&&d.remaining===180&&(mf.stock['PRD-R02']?.q??0)===stock&&acc(mf,'cash')===cash;
          const title=S.worldExpansion.miningLandTitles['JP-ASHIO'];
          const claimTitle=S.worldExpansion.knownDepositClaims[0].landTitleId===title.id;
          const beforeInvalid=JSON.stringify(S);
          const duplicateTitle=reject(()=>worldPurchaseMiningLand(S,id,'JP-ASHIO'));
          const foreignTitle=reject(()=>worldPurchaseMiningLand(S,id,'DE-RUH'))&&JSON.stringify(S)===beforeInvalid;
          const legacy=structuredClone(S),legacyMine=company(id,legacy),legacyClaim=legacy.worldExpansion.knownDepositClaims[0];
          delete legacy.worldExpansion.miningLandTitles;delete legacy.worldExpansion.miningLandFromSeq;
          delete legacyClaim.landTitleId;delete legacyMine.ledger.worldMiningLand;
          legacyMine.ledger.cash+=title.amount;legacyMine.journals=legacyMine.journals.filter(j=>j.id!==title.journal);
          const migrated=parsePayload(savePayload(legacy));
          const legacyRestore=migrated.worldExpansion.miningLandFromSeq===legacy.seq&&migrated.worldExpansion.resourceDeposits[did].remaining===180;
          const missingTitle=structuredClone(S);delete missingTitle.worldExpansion.knownDepositClaims[0].landTitleId;
          const forgedTitle=structuredClone(S);forgedTitle.worldExpansion.miningLandTitles['JP-ASHIO'].amount++;
          const titleAudit=reject(()=>parsePayload(savePayload(missingTitle)))&&reject(()=>parsePayload(savePayload(forgedTitle)));
          const duplicate=reject(()=>worldClaimKnownDeposit(S,id,pid,'JP-ASHIO'))&&reject(()=>worldExploreDeposit(S,id,pid,20000,'JP-ASHIO'));
          const forged=structuredClone(S);forged.worldExpansion.resourceDeposits[did].initialReserve++;forged.worldExpansion.resourceDeposits[did].remaining++;
          const tamper=reject(()=>parsePayload(savePayload(forged)));
          worldSetMiningPlan(S,id,pid,did,10,190);await close();
          const a=S.worldExpansion.resourceDeposits[did],n=company(id,S),q=n.stock['PRD-R02'];
          const extraction=a.extracted>0&&a.remaining===180-a.extracted&&q.q===stock+a.extracted;
          const price=worldResourceScarcityBps(S,'JP','PRD-R02')>0&&worldDepositUnitCost(a,190)>190;
          const saved=parsePayload(savePayload(S)),restore=saved.worldExpansion.knownDepositClaims.length===1&&saved.worldExpansion.resourceDeposits[did].remaining===a.remaining
            &&saved.worldExpansion.miningLandTitles['JP-ASHIO'].id===title.id&&acc(company(id,saved),'worldMiningLand')===title.amount;
          const clean=check(S).length===0&&consolidate(S).errors.length===0;
          return {catalog,coverage,historicalOpening,colocated,unavailable,claim,duplicate,tamper,extraction,price,restore,clean,months:S.monthCommitted===start+3,
            titleBeforeOperating,claimTitle,duplicateTitle,foreignTitle,legacyRestore,titleAudit};
        }""",ids)
        assert len(result)==19 and all(result.values()),result
        land=page.evaluate("""({id})=>{
          const parent=company(S.playerId,S);
          // The first mine and three monthly closes already consumed founding capital.
          // Fund the second real UI incorporation explicitly rather than assuming cash.
          post(parent,{cash:500000000},{capital:500000000},'検証用資本','financing',S);
          VIEW_FIRM=S.playerId;PAGE='corporateSubsidiaries';render();
          document.querySelector('#subName').value='Second mining company';
          document.querySelector('#subCountry').value='JP';
          document.querySelector('#subIndustry').value='resource';
          document.querySelector('#subCapital').value='1100000';
          createSub();syncWorldIdentities(S);
          const a=company(id,S),b=S.firms.find(x=>x.name==='Second mining company');
          if(!a||!b)throw Error('Mining transfer fixture: both subsidiaries must be established before transfer');
          const title=worldPurchaseMiningLand(S,id,'JP-SADO'),amount=title.amount,ac=acc(a,'cash'),bc=acc(b,'cash'),before=acc(a,'worldMiningLand');
          const reject=fn=>{try{fn();return false}catch{return true}};
          const encumbered=reject(()=>worldTransferMiningLand(S,id,b.id,'JP-ASHIO'));
          const tx=worldTransferMiningLand(S,id,b.id,'JP-SADO');
          const accounting=acc(a,'cash')===ac+amount&&acc(b,'cash')===bc-amount&&acc(a,'worldMiningLand')===before-amount&&acc(b,'worldMiningLand')===amount;
          const ownership=title.firmId===b.id&&title.originFirmId===id&&worldMiningLandOwnerAt(title,Number(tx.id.slice(4)))===id&&worldMiningLandOwnerAt(title,S.seq)===b.id;
          const oldOwner=reject(()=>worldTransferMiningLand(S,id,b.id,'JP-SADO'));
          const saved=parsePayload(savePayload(S)),record=saved.worldExpansion.miningLandTitles['JP-SADO'];
          const restore=record.firmId===b.id&&record.transfers[0].id===tx.id&&acc(company(b.id,saved),'worldMiningLand')===amount;
          const fake=structuredClone(saved);fake.worldExpansion.miningLandTitles['JP-SADO'].transfers[0].amount++;
          const tamper=reject(()=>parsePayload(savePayload(fake)));
          const paired=worldMiningLandCashPairs(S).some(x=>x.fromJournal===tx.sellerJournal&&x.toJournal===tx.buyerJournal);
          const clean=!check(saved).length&&!consolidate(saved).errors.length;
          return {encumbered,accounting,ownership,oldOwner,restore,tamper,paired,clean};
        }""",ids)
        assert len(land)==8 and all(land.values()),land
        print("PASS Phase 6 unencumbered mining land: book-value transfer, legal history, cash pairs, save and tamper")
        assert not errors,errors
        print("PASS Phase 6 known deposits: 19 checks, 18 minerals, 10 countries, independent titles, UI, extraction and restore")
        browser.close()
if __name__=="__main__":main()
