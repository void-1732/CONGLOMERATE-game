"""Phase 2-M: S08 needs installed E27, reserved paid workers and delivered care."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"])
        page=browser.new_page()
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.set_content((ROOT/"index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        first=page.evaluate("""() => {
          S=newWorldGame({country:'JP',name:'Medical service acceptance'});
          requestOperationSaveV037=()=>true;saveAuto=async()=>true;
          const parent=company(S.playerId),capital=60000000,payer=S.seq;
          post(parent,{investment:capital},{cash:capital},'検証用の設立','investing',S);
          const clinicFirm=initFirm(S,{name:'東京医療試作法人',country:'JP',industry:'service',
            seedBase:600000,publicOwnership:false});
          clinicFirm.owners=[{id:parent.id,econ:1,vote:1}];
          registerEquityLink(S,{parentId:parent.id,childId:clinicFirm.id,ratio:1,kind:'foundation',
            considerationLocal:capital,buyerJournal:payer,
            childJournal:clinicFirm.journals.find(j=>j.text==='創業資本').id,
            bookEquityBase:baseFromLocal(capital,'JP'),
            cashAcquiredBase:baseFromLocal(acc(clinicFirm,'cash'),'JP')});
          clinicFirm.research.tree.done=[...new Set([...clinicFirm.research.tree.done,'production-1'])];
          S.year=1950;S.month=1;S.monthCommitted=ym(1950,1)-1;
          applyWorldHistory(S);syncWorldIdentities(S);
          const rejects=(fn,term)=>{try{fn();return false;}catch(e){return e.message.includes(term);}};
          const pre=rejects(()=>worldInstallMedicalClinic(S,clinicFirm.id,clinicFirm.plants[0].id,2),'現物医療機器');
          const noPhantom=worldServiceActivity(S,'PRD-S08').length===0
            &&acc(clinicFirm,'serviceRevenue')===0;
          post(clinicFirm,{materials:1500},{cash:1500},'現物医療機器の有償取得','operating',S);
          clinicFirm.stock['PRD-E27']={q:1,v:1500};
          const overstaff=rejects(()=>worldInstallMedicalClinic(S,clinicFirm.id,clinicFirm.plants[0].id,
            clinicFirm.staff.sales+1),'医療従事者');
          clinicFirm.plants[0].paused=true;
          const paused=rejects(()=>worldInstallMedicalClinic(S,clinicFirm.id,clinicFirm.plants[0].id,2),'稼働中');
          clinicFirm.plants[0].paused=false;
          window.medicalFixture={providerId:clinicFirm.id,providerCash:acc(clinicFirm,'cash'),
            clientCash:acc(parent,'cash'),ppe:acc(clinicFirm,'ppe'),rejected:[pre,overstaff,paused,noPhantom]};
          VIEW_FIRM=clinicFirm.id;PAGE='facilityProduction';render();
          return window.medicalFixture.rejected.every(Boolean);
        }""")
        assert first, "equipment, staffing, inactive facility and no-phantom preconditions"
        page.locator("#world-domestic > summary").click()
        install=page.locator('form[data-world-domestic="medical-install"]')
        install.locator('[name="workers"]').fill("2")
        install.get_by_role("button",name="医療機器E27を設置").click()
        installed=page.evaluate("""() => {
          const f=window.medicalFixture,provider=company(f.providerId),parent=company(S.playerId);
          const clinic=Object.values(S.worldExpansion.medicalClinics)[0];
          if(!clinic)return false;
          window.medicalFixture.clinicId=clinic.id;
          const actual=clinic.workers===2&&provider.stock['PRD-E27'].q===0
            &&acc(provider,'ppe')===f.ppe+1500
            &&acc(provider,'serviceRevenue')===0&&worldMedicalOpenSlots(S,clinic)===8;
          VIEW_FIRM=parent.id;PAGE='facilityProduction';render();
          return actual;
        }""")
        assert installed, "medical equipment capitalized without services"
        page.locator("#world-domestic > summary").click()
        request=page.locator('form[data-world-domestic="medical-request"]')
        request.locator('[name="quantity"]').fill("3")
        request.get_by_role("button",name="診療を依頼（未実施は請求なし）").click()
        pending=page.evaluate("""() => {
          const f=window.medicalFixture,provider=company(f.providerId),client=company(S.playerId),
            [r]=S.worldExpansion.medicalRequests;
          const unpaid=r.status==='OPEN'&&r.performedQuantity===0
            &&S.worldExpansion.medicalTreatments.length===0
            &&acc(provider,'cash')===f.providerCash
            &&acc(client,'cash')===f.clientCash
            &&acc(provider,'serviceRevenue')===0;
          const over=(()=>{try{worldRequestMedicalService(S,client.id,f.clinicId,client.plants[0].id,6);return false;}
            catch(e){return e.message.includes('診療枠');}})();
          window.medicalFixture.requestId=r.id;
          VIEW_FIRM=provider.id;PAGE='facilityProduction';render();
          return unpaid&&over&&worldDomesticBlocksReorganization(S,provider.id);
        }""")
        assert pending, "unperformed requests must have no revenue or cash"
        page.locator("#world-domestic > summary").click()
        perform=page.locator('form[data-world-domestic="medical-perform"]')
        perform.locator('[name="quantity"]').fill("2")
        perform.get_by_role("button",name="医療を実施して精算").click()
        partial=page.evaluate("""() => {
          const f=window.medicalFixture,provider=company(f.providerId),client=company(S.playerId);
          const req=S.worldExpansion.medicalRequests[0],t=S.worldExpansion.medicalTreatments[0];
          const fee=2*worldMedicalFee(S);
          const ok=req.status==='PARTIAL'&&req.performedQuantity===2
            &&t.quantity===2&&t.fee===fee&&acc(provider,'serviceRevenue')===-fee
            &&acc(provider,'cash')===f.providerCash+fee&&acc(client,'cash')===f.clientCash-fee
            &&worldServiceActivity(S,'PRD-S08')[0].quantity===2;
          worldCancelMedicalRequest(S,client.id,req.id);
          const noExtra=acc(provider,'serviceRevenue')===-fee&&req.status==='CANCELLED';
          const again=(()=>{try{worldPerformMedicalService(S,provider.id,req.id,1);return false;}
            catch(e){return e.message.includes('医療依頼');}})();
          const second=worldRequestMedicalService(S,client.id,f.clinicId,client.plants[0].id,6);
          const final=worldPerformMedicalService(S,provider.id,second.id,6);
          const full=final.quantity===6&&worldMedicalOpenSlots(S,S.worldExpansion.medicalClinics[f.clinicId])===0;
          const over=(()=>{try{worldRequestMedicalService(S,client.id,f.clinicId,client.plants[0].id,1);return false;}
            catch(e){return e.message.includes('診療枠');}})();
          const report=consolidate(S),spot=accountingFxReview(S,S.playerId,report),total=8*worldMedicalFee(S);
          const ledger=!check(S).length&&report.errors.length===0
            &&report.adjustments.internalSales===total
            &&spot.periodPL.internalSalesEliminated>=total;
          const saved=parsePayload(savePayload(S));
          const tampered=structuredClone(saved);
          tampered.worldExpansion.medicalRequests[0].performedQuantity++;
          const rejects=(fn,term)=>{try{fn();return false;}catch(e){return e.message.includes(term);}};
          const tamper=rejects(()=>worldValidateMedicalServices(tampered),'未実施件数');
          const damaged=structuredClone(saved);
          damaged.worldExpansion.medicalTreatments[0].quantity++;
          const rejectsInflation=rejects(()=>worldValidateMedicalServices(damaged),'実施件数');
          window.medicalFixture.total=total;
          return {ok,noExtra,again,full,over,ledger,tamper,rejectsInflation,
            restored:!check(saved).length&&worldServiceActivity(saved,'PRD-S08').length===2
              &&worldServiceActivity(saved,'PRD-S08').reduce((n,t)=>n+t.quantity,0)===8};
        }""")
        assert all(partial.values()), partial
        final=page.evaluate("""async () => {
          const id=window.medicalFixture.clinicId,providerId=window.medicalFixture.providerId;
          await runMonth();
          const clinic=S.worldExpansion.medicalClinics[id],report=consolidate(S);
          const depreciated=clinic.accumulatedDepreciation>0&&!report.errors.length
            &&report.cf.reconciled;
          worldRetireDomesticAsset(S,providerId,'medical',id);
          const closed=clinic.retiredAt===ym(S.year,S.month)
            &&!check(parsePayload(savePayload(S))).length;
          return {depreciated,closed};
        }""")
        assert all(final.values()), final
        assert not errors,errors
        browser.close()
    print("PASS Phase 2-M S08 E27, real worker allocation, delivery-only revenue, capacity, "
          "journals, consolidation, tamper rejection, save and retirement")

if __name__=="__main__":
    main()
