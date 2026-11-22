"""Phase 2-B: finite resource conservation and 15 nonphysical service handoffs."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
            args=["--no-sandbox"],
        )
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result = page.evaluate("""() => {
          saveAuto=async()=>true;
          S=newWorldGame({country:'JP',name:'有限資源と非物理サービス試験'});
          const emptyAtStart=Object.keys(S.worldExpansion.resourceDeposits).length===0;
          const services=WORLD_PRODUCTS.filter(p=>p.category==='service')
            .map(p=>worldServiceTerms(p.id));
          const allFifteen=services.length===15 && services.every(s=>
            !s.physicalInventory&&s.requiresVerifiedCompletion&&
            s.revenueState==='NOT_IMPLEMENTED'&&s.settlementState==='NOT_IMPLEMENTED');
          const finance=services.filter(s=>s.executionClass==='FINANCIAL').length===3;
          const freight=services.filter(s=>s.executionClass==='TRANSPORT_AND_STORAGE').length===4;
          const telecom=services.some(s=>s.productId==='PRD-S10'&&s.executionClass==='NETWORK');
          let rejectsNonsvc=false;
          try{worldServiceTerms('PRD-R01')}catch{rejectsNonsvc=true}
          const f=S.firms.find(f=>f.industry==='resource'&&f.plants?.some(
            p=>!p.construction&&!p.paused&&factoryLaborPlanV026(f).byId[p.id]?.assigned>0));
          if(!f)return {error:'staffed resource firm not found',emptyAtStart,allFifteen};
          const p=f.plants.find(p=>!p.construction&&!p.paused&&
            factoryLaborPlanV026(f).byId[p.id]?.assigned>0);
          const q=Math.min(3,factoryLaborPlanV026(f).byId[p.id].assigned,
            Math.floor(p.capacity*p.condition/100));
          const id='DEP-PHASE2B-TEST';
          S.worldExpansion.resourceDeposits[id]={
            id,productId:'PRD-R01',status:'TEST_FIXTURE',
            ownerCompanyId:f.id,plantId:p.id,locationId:'LOC-'+p.siteId,
            initialReserve:4,remaining:4,extracted:0,
            availableFromYear:1900,requiredTech:null,lastExtractedAt:null
          };
          const b={cash:acc(f,'cash'),materials:acc(f,'materials'),
            stock:f.stock['PRD-R01']?.q||0,journals:f.journals.length};
          const events=[];
          const produced=worldExtractFromDeposit(S,f.id,p.id,id,q,17,events);
          const sameMonth=worldExtractFromDeposit(S,f.id,p.id,id,1,17,events);
          const d=S.worldExpansion.resourceDeposits[id];
          const after1={
            mined:produced===q&&q>0,once:sameMonth===0&&events.length===1,
            reserve:d.remaining===4-q&&d.extracted===q,
            cash:b.cash-acc(f,'cash')===q*17,
            materials:acc(f,'materials')-b.materials===q*17,
            stock:(f.stock['PRD-R01']?.q||0)===b.stock+q,
            journals:f.journals.length===b.journals+1
          };
          let rejectsOverdraw=false,rejectsInconsistent=false,rejectsWrongOwner=false;
          const tampered=structuredClone(S);
          tampered.worldExpansion.resourceDeposits[id].remaining+=1;
          try{validateWorldResourceDeposits(tampered)}catch{rejectsInconsistent=true}
          try{worldExtractFromDeposit(S,'NO_SUCH_FIRM',p.id,id,1,17,events)}
          catch{rejectsWrongOwner=true}
          S.month=2;
          const before=d.remaining;
          const mined2=worldExtractFromDeposit(S,f.id,p.id,id,100,17,events);
          const remaining=d.remaining;
          const capped=mined2<=before&&remaining>=0&&d.extracted+remaining===4;
          const replay=parsePayload(savePayload(S));
          const saved=replay.worldExpansion.resourceDeposits[id].remaining===remaining;
          const clean=check(S).length===0&&consolidate(S).errors.length===0;
          return {emptyAtStart,allFifteen,finance,freight,telecom,rejectsNonsvc,
            ...after1,rejectsInconsistent,rejectsWrongOwner,capped,saved,clean,
            mined2, remaining};
        }""")
        assert result.pop("finance") == 3, result
        assert result.pop("freight") == 4, result
        assert result.pop("mined2") >= 0, result
        assert result.pop("remaining") >= 0, result
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS: resource reserve conservation, ownership, cash, service classification, save")


if __name__ == "__main__":
    main()
