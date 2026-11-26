"""Dated rail trips settle real business travel costs without generic service sales."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        page.evaluate("""() => {
          S=newWorldGame({country:'JP',name:'Rail trips'});
          VIEW_FIRM=S.playerId;PAGE='facilityProduction';
          requestOperationSaveV037=()=>true;
          saveAuto=async()=>true;
          const parent=company(S.playerId),origin=parent.plants[0];
          for(const [siteId,name] of [['JP-NGO','名古屋'],['UK-LON','ロンドン'],['FR-PAR','パリ']]){
            parent.plants.push({...structuredClone(origin),siteId,name,id:'P-TRIP-'+siteId});
          }
          syncPlant(parent);syncWorldIdentities(S);
          function date(year,month){
            S.year=year;S.month=month;S.monthCommitted=ym(year,month)-1;
            applyWorldHistory(S);syncWorldIdentities(S);
          }
          date(1964,9);
          function rejects(action,fragment){try{action();return false;}catch(e){return e.message.includes(fragment);}}
          const bookDomestic=n=>worldBookPassengerTrip(S,parent.id,'RAIL-JP-TOK-NGO',origin.id,'P-TRIP-JP-NGO',n);
          const domesticEra=rejects(()=>bookDomestic(1),'運行年代');
          date(1994,11);
          const bookInternational=n=>worldBookPassengerTrip(S,parent.id,'RAIL-UK-LON-FR-PAR',
            'P-TRIP-UK-LON','P-TRIP-FR-PAR',n);
          const internationalEra=rejects(()=>bookInternational(1),'運行年代');
          date(1994,12);parent.staff.sales=6;
          const expense=acc(parent,'otherExpense'),priorCash=acc(parent,'cash');
          window.tripFixtures={domesticEra,internationalEra,expense,priorCash};
          render();
        }""")
        page.locator("#world-domestic > summary").click()
        domestic = page.locator('form[data-world-domestic="trip-book"]:has(option[value^="RAIL-JP-TOK-NGO|"])')
        domestic.locator('input[name="people"]').fill("4")
        domestic.get_by_role("button", name="鉄道出張を予約").click()
        result = page.evaluate("""async () => {
          const parent=company(S.playerId),origin=parent.plants[0],w=S.worldExpansion;
          const {domesticEra,internationalEra,expense,priorCash}=window.tripFixtures;
          const domestic=w.passengerTrips[0];
          const uiBooked=domestic.passengers===4&&domestic.status==='BOOKED'&&domestic.routeId==='RAIL-JP-TOK-NGO'
            &&acc(parent,'cash')===priorCash-domestic.fare&&acc(parent,'otherExpense')===expense
            &&acc(parent,'worldTravelAdvance')===domestic.fare&&worldServiceActivity(S,'PRD-S01').length===0;
          const bookInternational=n=>worldBookPassengerTrip(S,parent.id,'RAIL-UK-LON-FR-PAR',
            'P-TRIP-UK-LON','P-TRIP-FR-PAR',n);
          const rejects=(action,fragment)=>{try{action();return false;}catch(e){return e.message.includes(fragment);}};
          const rejectsStaff=rejects(()=>bookInternational(3),'人数');
          parent.staff.sales=20;
          const rejectsCapacity=rejects(()=>worldBookPassengerTrip(S,parent.id,'RAIL-JP-TOK-NGO',
            origin.id,'P-TRIP-JP-NGO',3),'予約枠');
          parent.staff.sales=6;
          const rejectsSite=rejects(()=>worldBookPassengerTrip(S,parent.id,'RAIL-JP-TOK-NGO',
            origin.id,'P-TRIP-FR-PAR',1),'拠点');
          const canceled=bookInternational(2);
          const blocksClosure=worldDomesticBlocksReorganization(S,parent.id,parent.plants.find(p=>p.id==='P-TRIP-FR-PAR'));
          worldCancelPassengerTrip(S,parent.id,canceled.id);
          const refund=canceled.status==='REFUNDED'&&acc(parent,'cash')===priorCash-domestic.fare
            &&rejects(()=>worldCancelPassengerTrip(S,parent.id,canceled.id),'未利用');
          const international=bookInternational(2);
          const saved=parsePayload(savePayload(S)),pendingRestored=!check(saved).length
            &&saved.worldExpansion.passengerTrips.find(x=>x.id===international.id).status==='BOOKED';
          const bad=structuredClone(saved);bad.worldExpansion.passengerTrips[0].fare++;
          const rejectsAltered=rejects(()=>worldValidatePassengerTrips(bad),'運賃');
          const scope=cloned=>{
            const provider=initFirm(cloned,{name:'No earned service',country:'JP',industry:'service'});
            provider._salesNow=0;provider._unitsNow=0;
            sellMonthly(cloned,[]);
            return -acc(provider,'serviceRevenue');
          };
          const worldIncome=scope(structuredClone(S)),legacy=structuredClone(S);
          delete legacy.worldExpansion;
          const refusesGenericService=!worldIncome&&scope(legacy)>0;
          await runMonth();
          const arrivals=S.worldExpansion.passengerTrips.filter(t=>t.status==='ARRIVED');
          const delivered=arrivals.length===2&&worldServiceActivity(S,'PRD-S01')[0]?.amount===domestic.fare
            &&worldServiceActivity(S,'PRD-S02')[0]?.amount===international.fare
            &&worldServiceActivity(S,'PRD-S02')[0]?.providerId===null;
          const closed=parsePayload(savePayload(S)),firm=company(S.playerId,closed);
          const settled=acc(firm,'worldTravelAdvance')===0&&!check(closed).length&&!consolidate(closed).errors.length
            &&arrivals.every(t=>firm.journals.find(j=>j.id===t.finishJournal)?.dr[0][0]==='otherExpense')
            &&acc(firm,'serviceRevenue')===0;
          return {domesticEra,internationalEra,uiBooked,rejectsStaff,rejectsCapacity,rejectsSite,blocksClosure,refund,
            pendingRestored,rejectsAltered,refusesGenericService,delivered,settled};
        }""")
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS Phase 2-L dated domestic/international passenger travel, prepaid/expense/refund, save")


if __name__ == "__main__":
    main()
