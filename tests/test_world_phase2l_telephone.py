"""A documented telephone corridor uses an owned exchange and paid fuel power."""

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
        page.evaluate("""async () => {
          S=newWorldGame({country:'JP',name:'Telephone corridor'});
          VIEW_FIRM=S.playerId;PAGE='facilityProduction';
          requestOperationSaveV037=()=>true;
          saveAuto=async()=>true;
          let parent=company(S.playerId),source=parent.plants[0];
          const capital=60000000,payer=S.seq;
          parent.plants.push({...structuredClone(source),id:'P-TEL-YOK',name:'横浜支店',siteId:'JP-YOK'});
          syncPlant(parent);
          post(parent,{investment:capital},{cash:capital},'検証用の設立','investing',S);
          let provider=initFirm(S,{name:'有線電話テスト法人',country:'JP',industry:'service',
            seedBase:600000,publicOwnership:false});
          provider.owners=[{id:parent.id,econ:1,vote:1}];
          registerEquityLink(S,{parentId:parent.id,childId:provider.id,ratio:1,kind:'foundation',
            considerationLocal:capital,buyerJournal:payer,childJournal:provider.journals.find(j=>j.text==='創業資本').id,
            bookEquityBase:baseFromLocal(capital,'JP'),cashAcquiredBase:baseFromLocal(acc(provider,'cash'),'JP')});
          parent.staff.sales=Math.max(2,parent.staff.sales);
          provider.staff.sales=Math.max(2,provider.staff.sales);
          let plant=provider.plants[0];
          provider.research.tree.done=[...new Set([...provider.research.tree.done,'electronics-1','energy-1'])];
          function date(year,month){
            S.year=year;S.month=month;S.monthCommitted=ym(year,month)-1;
            applyWorldHistory(S);syncWorldIdentities(S);
          }
          function rejects(action,part){
            try{action();return false;}catch(e){return e.message.includes(part);}
          }
          for(const [id,q,v] of [['PRD-E23',1,1400],['PRD-E04',1,600],['PRD-R04',2,180]]){
            post(provider,{materials:v},{cash:v},'通信検証の有償現物','operating',S);
            provider.stock[id]={q,v};
          }
          date(1985,3);
          const historical=rejects(()=>worldInstallTelephone(S,provider.id,plant.id),'取扱年代');
          await runMonth();
          if(S.month!==4)throw Error('fixture failed to close the prior month');
          parent=company(S.playerId);source=parent.plants[0];
          provider=company(provider.id);plant=provider.plants[0];
          PAGE='facilityProduction';
          const oldPpe=acc(provider,'ppe'),exchange=worldInstallTelephone(S,provider.id,plant.id);
          const realEquipment=!provider.stock['PRD-E23'].q&&acc(provider,'ppe')===oldPpe+1400;
          const prepare=()=>worldPlaceTelephoneCall(S,parent.id,exchange.id,source.id,'P-TEL-YOK');
          const needsPower=rejects(prepare,'実電力')&&!acc(provider,'serviceRevenue');
          worldInstallGenerator(S,provider.id,plant.id);
          const generation=worldGeneratePower(S,provider.id,plant.id,2);
          const balances={providerCash:acc(provider,'cash'),clientCash:acc(parent,'cash'),materials:acc(provider,'materials')};
          window.phoneFixture={providerId:provider.id,exchangeId:exchange.id,balances,historical,realEquipment,needsPower,
            powerId:generation.id,plantId:plant.id};
          render();
        }""")
        page.locator("#world-domestic > summary").click()
        page.locator('form[data-world-domestic="phone-call"]').get_by_role("button", name="業務電話をつなぐ").click()
        results = page.evaluate("""async () => {
          const f=window.phoneFixture,parent=company(S.playerId),provider=company(f.providerId);
          const w=S.worldExpansion,first=w.telephoneCalls[0],budget=w.powerAllocations[f.plantId];
          const fee=first.fee&&first.fee===worldTelephoneFee(S);
          const uiDelivered=first.powerReceiptId===f.powerId&&first.powerUseAt===0&&budget.usedKwh===1
            &&acc(parent,'cash')===f.balances.clientCash-first.fee
            &&acc(provider,'cash')===f.balances.providerCash+first.fee
            &&acc(provider,'materials')===f.balances.materials&&budget.expensedFuelCost===10;
          const buy=()=>worldPlaceTelephoneCall(S,parent.id,f.exchangeId,parent.plants[0].id,'P-TEL-YOK');
          for(let i=1;i<10;i++)buy();
          let capacity=false;
          try{buy();}catch(e){capacity=e.message.includes('通話枠');}
          const feeTotal=first.fee*10;
          const earned=acc(provider,'serviceRevenue')===-feeTotal&&worldServiceActivity(S,'PRD-S10').length===10
            &&budget.usedKwh===10&&budget.expensedFuelCost===100;
          const saved=parsePayload(savePayload(S));
          const bad=structuredClone(saved);bad.worldExpansion.telephoneCalls[1].powerUseAt=0;
          let rejectsReplay=false;
          try{worldValidateTelephoneCalls(bad);}catch(e){rejectsReplay=e.message.includes('実電力');}
          const group=consolidate(saved);
          const linked=!check(saved).length&&!group.errors.length&&group.adjustments.internalSales===feeTotal;
          await runMonth();
          const closed=consolidate(S),spot=accountingFxReview(S,S.playerId,closed);
          const monthly=S.month===5&&closed.cf.reconciled&&!closed.errors.length
            &&closed.cf.internalCashLegs>=10&&spot.periodPL.internalSalesEliminated>=feeTotal;
          const live=S.worldExpansion.telephoneExchanges[f.exchangeId];
          const depreciation=live.accumulatedDepreciation>0;
          worldRetireDomesticAsset(S,f.providerId,'telephone',f.exchangeId);
          const retirement=live.retiredAt===ym(S.year,S.month)&&!check(parsePayload(savePayload(S))).length;
          return {historical:f.historical,realEquipment:f.realEquipment,needsPower:f.needsPower,fee,uiDelivered,
            capacity,earned,linked,rejectsReplay,monthly,depreciation,retirement};
        }""")
        assert all(results.values()), results
        assert not errors, errors
        browser.close()
    print("PASS Phase 2-L telephone exchange, real kWh/capacity, billed delivery, depreciation, consolidation and save")


if __name__ == "__main__":
    main()
