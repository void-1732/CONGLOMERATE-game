"""Phase 6 fixed-duration construction, physical inputs, accounting and UI."""
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
        ids=page.evaluate("""()=>{
          saveAuto=async()=>true;S=newWorldGame({country:'JP',name:'Rail customer'});
          VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='corporateSubsidiaries';render();
          document.querySelector('#subName').value='Builder';
          document.querySelector('#subCountry').value='JP';
          document.querySelector('#subIndustry').value='service';
          document.querySelector('#subCapital').value='650000';
          createSub();syncWorldIdentities(S);
          const bid=S.playerId,buyer=company(bid,S),seller=S.firms.find(f=>f.name==='Builder'),sid=seller.id,bp=buyer.plants[0].id,sp=seller.plants[0].id;
          S.year=1935;S.month=1;S.monthCommitted=ym(S.year,S.month)-1;applyWorldHistory(S);syncWorldIdentities(S);
          for(const f of [buyer,seller]){if(!f.research.tree.done.includes('production-1'))f.research.tree.done.push('production-1');f.auto=false;f.delegate.mode='manual';f.rnd.budgetBase=0;}
          seller.staff.production=15;seller.staffTarget.production=15;
          const add=(f,key,q,unit)=>{const amount=q*unit;post(f,{materials:amount},{cash:amount},'試験用有償調達','operating',S);const st=f.stock[key]??={q:0,v:0};st.q+=q;st.v+=amount};
          add(seller,'PRD-E14',1,300);add(seller,'PRD-E16',1,400);add(seller,'PRD-E17',1,120);add(seller,'PRD-M03',4,20);add(seller,'PRD-M09',4,10);
          VIEW_FIRM=sid;PAGE='worldInfrastructure';render();return {bid,sid,bp,sp};
        }""")
        page.locator("#worldConstructionMachinePlant").select_option(ids["sp"])
        page.locator('[data-world-build-contract="machine"]').click()
        page.evaluate("bid=>{VIEW_FIRM=bid;PAGE='worldInfrastructure';render()}",ids["bid"])
        target="|".join(["DR","JP-SHIMBASHI-YOKOHAMA",ids["bp"],ids["sid"],ids["sp"]])
        page.locator("#worldConstructionTarget").select_option(target)
        page.locator("#worldConstructionFee").fill("40000")
        page.locator('[data-world-build-contract="offer"]').click()
        page.evaluate("sid=>{VIEW_FIRM=sid;PAGE='worldInfrastructure';render()}",ids["sid"])
        page.locator('[data-world-build-contract="accept"]').click()
        result=page.evaluate("""async({bid,sid,bp,sp})=>{
          const c=S.worldExpansion.constructionContracts[0],id=c.id,first=S.monthCommitted;
          const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
          const add=(f,key,q,unit)=>{const amount=q*unit;post(f,{materials:amount},{cash:amount},'試験用有償調達','operating',S);const st=f.stock[key]??={q:0,v:0};st.q+=q;st.v+=amount};
          const place=()=>worldPlaceConstructionContract(S,bid,{kind:'DR',profileId:'JP-SHIMBASHI-YOKOHAMA',buyerPlantId:bp,sellerId:sid,sellerPlantId:sp,feeBase:40000});
          const accepted=c.status==='ACTIVE'&&c.dueAt===c.acceptedAt+1;
          const rev0=acc(company(sid,S),'serviceRevenue');
          await close();let x=S.worldExpansion.constructionContracts.find(x=>x.id===id);
          const wip=x.status==='ACTIVE'&&x.work.length===1&&x.bookCost>0&&acc(company(sid,S),'worldConstructionWip')===x.bookCost&&acc(company(sid,S),'serviceRevenue')===rev0&&Object.keys(S.worldExpansion.domesticRoutes??{}).length===0;
          const savedPartial=parsePayload(savePayload(S)).worldExpansion.constructionContracts[0].bookCost===x.bookCost;
          await close();x=S.worldExpansion.constructionContracts.find(x=>x.id===id);const rec=S.worldExpansion.constructionReceipts.find(y=>y.contractId===id),asset=S.worldExpansion.domesticRoutes[rec.assetId],g=consolidate(S);
          const complete=x.status==='COMPLETE'&&asset.capacityQty===10&&asset.ownerCompanyId===bid;
          const account=acc(company(sid,S),'worldConstructionWip')===0&&acc(company(sid,S),'serviceRevenue')===rev0-x.fee&&g.errors.length===0&&g.cf.reconciled&&g.pl.unrealizedProfit===x.fee-x.bookCost;
          const service=worldServiceActivity(S,'PRD-S11').some(y=>y.ref===rec.id&&y.providerId===sid);
          const forged=structuredClone(S);forged.worldExpansion.constructionContracts[0].work[0].items[0].quantity++;let tamper=false;try{parsePayload(savePayload(forged))}catch{tamper=true}
          const rev1=acc(company(sid,S),'serviceRevenue'),maintenance=asset.constructionMaintenance;
          add(company(sid,S),'PRD-M03',2,20);add(company(sid,S),'PRD-M09',2,10);
          const c2=place();worldAcceptConstructionContract(S,sid,c2.id);await close();const interim=S.worldExpansion.constructionContracts.find(y=>y.id===c2.id);const work=interim.status==='ACTIVE'&&interim.bookCost>0;await close();
          const fail=S.worldExpansion.constructionContracts.find(y=>y.id===c2.id),ff=company(sid,S),bb=company(bid,S);
          const failed=work&&fail.status==='FAILED'&&fail.lossJournal!=null&&acc(ff,'worldConstructionWip')===0&&acc(ff,'serviceRevenue')===rev1&&Object.keys(S.worldExpansion.domesticRoutes).length===1;
          const upkeep=bb.journals.some(j=>j.text.includes('請負建設インフラの固定維持費 '+asset.id)&&j.dr.some(y=>y[0]==='maintenance'&&y[1]===maintenance));
          const clean=check(S).length===0&&consolidate(S).errors.length===0&&parsePayload(savePayload(S)).worldExpansion.constructionContracts.length===2;
          return {accepted,wip,savedPartial,complete,account,service,tamper,failed,upkeep,clean,months:S.monthCommitted===first+4};
        }""",ids)
        assert len(result)==11 and all(result.values()),result
        assert not errors,errors
        print("PASS Phase 6 construction: 11 checks, UI, real monthly work, completion, failed contract, fixed upkeep, accounting and restore")
        browser.close()

if __name__=="__main__":main()
