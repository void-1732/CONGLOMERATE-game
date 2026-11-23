"""Phase 4 accepted dates, prepayments, accrued trade credit and failed deliveries."""
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def main(observe_receipts=None):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_context(offline=True).new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        if observe_receipts is not None:
            observe_receipts(page)
        result = page.evaluate("""() => {
          S=newWorldGame({country:'UK',name:'International credit'});
          const buyer=company(S.playerId),plant=buyer.plants[0],capital=300000,payer=S.seq;
          plant.siteId='UK-LIV';
          post(buyer,{investment:capital},{cash:capital},'国際掛取引検証の設立','investing',S);
          const seller=initFirm(S,{name:'French freight supplier',country:'FR',seedBase:570000,publicOwnership:false});
          seller.owners=[{id:buyer.id,econ:1,vote:1}];
          registerEquityLink(S,{parentId:buyer.id,childId:seller.id,ratio:1,kind:'foundation',
            considerationLocal:capital,buyerJournal:payer,
            childJournal:seller.journals.find(j=>j.text==='創業資本').id,
            bookEquityBase:baseFromLocal(financials(seller).equity,'FR'),cashAcquiredBase:baseFromLocal(acc(seller,'cash'),'FR')});
          seller.plants[0].siteId='FR-MAR';
          S.year=2000;S.month=12;S.monthCommitted=ym(2000,12)-1;
          applyWorldHistory(S);syncWorldIdentities(S);
          for(const f of [buyer,seller]){
            f.research.tree.done=[...new Set([...f.research.tree.done,'production-1'])];
            f.auto=false;
          }
          for(const [f,id,q,value] of [[seller,'PRD-E18',1,4500],[seller,'PRD-R04',24,240],
            [seller,'PRD-R19',20,1000],[buyer,'PRD-E20',1,200],[buyer,'PRD-E21',1,300]]){
            post(f,{materials:value},{cash:value},'国際掛取引検証の現物調達','operating',S);
            f.stock[id]={q,v:value};
          }
          const profileId='FR-UK-SEA-1900';
          const route=worldInternationalRegisterRoute(S,seller.id,profileId);
          const wh=worldInternationalInstallWarehouse(S,buyer.id,plant.id,profileId);
          const inputs={routeId:route.id,warehouseId:wh.id,productId:'PRD-R19',
            quantity:2,unitPriceSeller:500,maxPaymentBuyer:100000};
          const rejects=fn=>{try{fn();return false;}catch{return true;}};
          const controls=worldInternationalTradePanel(buyer,true);
          const paymentOptions=[0,30,60,90].every(d=>controls.includes('<option value="'+d+'">'))
            &&rejects(()=>worldInternationalPlaceOrder(S,buyer.id,{...inputs,paymentDays:31}));
          const first=worldInternationalPlaceOrder(S,buyer.id,{...inputs,paymentDays:30});
          const second=worldInternationalPlaceOrder(S,buyer.id,{...inputs,paymentDays:60});
          const third=worldInternationalPlaceOrder(S,buyer.id,{...inputs,paymentDays:90});
          for(const o of [first,second,third])worldInternationalActOrder(S,seller.id,o.id,'approve');
          const before={buyer:acc(buyer,'cash'),seller:acc(seller,'cash')};
          S.year=2001;S.month=1;
          worldInternationalResolveOrders(S);
          const [a,b,c]=S.worldExpansion.internationalShipments;
          const dates=a.credit.dueDate==='2001-01-31'&&b.credit.dueDate==='2001-03-02'&&c.credit.dueDate==='2001-04-01'
            &&worldInternationalCreditDeadline(ym(2000,2),30).dueDate==='2000-03-02'
            &&worldInternationalCreditDeadline(ym(1900,2),30).dueDate==='1900-03-03';
          const noDispatchCash=acc(buyer,'cash')===before.buyer&&acc(seller,'cash')===before.seller
            &&acc(seller,'worldShipmentStock')===a.bookCost+b.bookCost+c.bookCost
            &&!acc(buyer,'worldSupplierAdvances')&&!acc(seller,'sales')&&!check(S).length;
          const pending=parsePayload(savePayload(S));
          const creditSave=pending.worldExpansion.internationalShipments.every(t=>t.credit.paidAt===null);
          worldInternationalSettleCredit(S);
          const advance=a.credit.paidAt===ym(2001,1)&&b.credit.paidAt===null&&c.credit.paidAt===null
            &&acc(buyer,'worldSupplierAdvances')===a.prepaidBuyer
            &&acc(seller,'worldCustomerAdvances')===-a.prepaidSeller
            &&acc(buyer,'worldImportDutyPrepaid')===a.dutyBuyer
            &&!acc(seller,'sales')&&!check(S).length;
          const held=parsePayload(savePayload(S));
          const saveAdvance=held.worldExpansion.internationalShipments[0].credit.journal===a.credit.journal;
          S.month=2;
          worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
          const early=a.status==='IN_TRANSIT'&&b.credit.paidAt===null&&c.credit.paidAt===null;
          S.month=3;
          const heldRate=b.buyerRate;
          S.world.UK.fx*=1.25;
          worldMatchLedgerCurrencyRates(S);
          worldInternationalReceiveShipments(S);
          const claims=b.status==='DELIVERED'&&c.status==='DELIVERED'&&b.credit.paidAt===null
            &&acc(buyer,'worldSupplierAdvances')===0&&acc(seller,'worldShipmentStock')===0
            &&acc(seller,'worldInternationalReceivable')===b.prepaidSeller+c.prepaidSeller
            &&acc(buyer,'worldInternationalPayable')===-(b.prepaidBuyer+c.prepaidBuyer)
            &&acc(buyer,'worldInternationalDutyPayable')===-(b.dutyBuyer+c.dutyBuyer)
            &&-acc(seller,'sales')===a.goodsSeller+b.goodsSeller+c.goodsSeller&&!check(S).length;
          const retirementWhileUnpaid=rejects(()=>worldRetireInternationalAsset(S,seller.id,route.id))
            &&rejects(()=>worldRetireInternationalAsset(S,buyer.id,wh.id));
          const grouped=consolidate(S);
          const elimination=grouped.adjustments.internationalCreditEliminated===baseFromLocal(b.prepaidSeller+c.prepaidSeller,'FR')
            &&grouped.spot.internationalInternalCredit===Math.round(b.prepaidSeller*balanceFxRate(S,seller))
               +Math.round(c.prepaidSeller*balanceFxRate(S,seller))
            &&!grouped.errors.length;
          const broke=structuredClone(S),poor=company(buyer.id,broke);
          post(poor,{ppe:acc(poor,'cash')},{cash:acc(poor,'cash')},'資金不足の検証','investing',broke);
          worldInternationalSettleCredit(broke);
          const retry=broke.worldExpansion.internationalShipments[1].credit.paidAt===null
            &&acc(poor,'cash')===0&&!check(broke).length;
          const accrued=parsePayload(savePayload(S));
          const amended=structuredClone(accrued);
          amended.worldExpansion.internationalShipments[1].credit.dueDate='2001-02-01';
          const blocksTamper=rejects(()=>parsePayload(savePayload(amended)));
          worldInternationalSettleCredit(S);
          const fixedCurrency=b.credit.paidAt===ym(2001,3)&&b.credit.buyerFx!==heldRate&&b.buyerRate===heldRate;
          const debit=b.totalBuyer;
          const once=buyer.journals.find(j=>j.id===b.credit.journal)?.amount===debit;
          const afterPayment=acc(buyer,'cash');
          worldInternationalSettleCredit(S);
          const noDuplicate=acc(buyer,'cash')===afterPayment&&c.credit.paidAt===null;
          S.month=4;worldInternationalSettleCredit(S);
          const paidAll=c.credit.paidAt===ym(2001,4)&&acc(seller,'worldInternationalReceivable')===0
            &&acc(buyer,'worldInternationalPayable')===0&&acc(buyer,'worldInternationalDutyPayable')===0;
          const final=parsePayload(savePayload(S));
          const terminal=!check(final).length&&worldInternationalCashPairs(final).length===3
            &&worldInternationalCashPairs(final).every(t=>Number.isSafeInteger(t.fromCash)&&Number.isSafeInteger(t.toCash));
          const paidLoss=worldInternationalPlaceOrder(S,buyer.id,{...inputs,paymentDays:30});
          const unpaidLoss=worldInternationalPlaceOrder(S,buyer.id,{...inputs,paymentDays:90});
          worldInternationalActOrder(S,seller.id,paidLoss.id,'approve');
          worldInternationalActOrder(S,seller.id,unpaidLoss.id,'approve');
          S.month=5;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
          const [prepaidMissing,unpaidMissing]=S.worldExpansion.internationalShipments.slice(-2);
          plant.paused=true;syncPlant(buyer);
          S.month=7;worldInternationalReceiveShipments(S);
          S.month=8;
          const beforeRefundSeller=acc(seller,'cash'),beforeRefundBuyer=acc(buyer,'cash');
          worldInternationalRefundShipment(S,unpaidMissing.id);
          const unfundedLoss=unpaidMissing.status==='REFUNDED'&&unpaidMissing.credit.paidAt===null
            &&acc(seller,'cash')===beforeRefundSeller&&acc(buyer,'cash')===beforeRefundBuyer;
          post(seller,{ppe:beforeRefundSeller},{cash:beforeRefundSeller},'返金資金不足の検証','investing',S);
          S.world.FR.fx*=1.15;
          worldMatchLedgerCurrencyRates(S);
          worldInternationalRefundShipment(S,prepaidMissing.id);
          const dueRefund=prepaidMissing.status==='REFUND_PENDING'&&prepaidMissing.refundedAt===null
            &&acc(seller,'cash')===0&&acc(buyer,'cash')===beforeRefundBuyer
            &&acc(seller,'worldShipmentStock')===0&&acc(buyer,'worldSupplierAdvances')===0
            &&acc(seller,'worldInternationalPayable')===-prepaidMissing.prepaidSeller
            &&acc(buyer,'worldInternationalReceivable')===prepaidMissing.prepaidBuyer;
          worldInternationalSettleCredit(S);
          const refundNotForged=prepaidMissing.status==='REFUND_PENDING'
            &&worldInternationalCashPairs(S).length===4&&!check(parsePayload(savePayload(S))).length;
          S.month=9;
          const recovered=prepaidMissing.prepaidSeller;
          post(seller,{cash:recovered},{ppe:recovered},'検証用現金回収','investing',S);
          worldInternationalSettleCredit(S);
          const prepaidRepaid=prepaidMissing.status==='REFUNDED'&&prepaidMissing.refundedAt===ym(2001,9)
            &&prepaidMissing.refund.confirmedAt===ym(2001,8)&&acc(seller,'cash')===0
            &&acc(buyer,'cash')===beforeRefundBuyer+prepaidMissing.prepaidBuyer
            &&acc(seller,'worldInternationalPayable')===0&&acc(buyer,'worldInternationalReceivable')===0;
          const settledRefund=S.worldExpansion.internationalShipments.at(-2);
          const invalidConfirmation=structuredClone(S);
          invalidConfirmation.worldExpansion.internationalShipments.at(-2).refund.confirmedAt--;
          const refundsRestored=!check(parsePayload(savePayload(S))).length
            &&settledRefund.refund.journal>settledRefund.journals.terminal
            &&worldInternationalCashPairs(S).length===5
            &&rejects(()=>parsePayload(savePayload(invalidConfirmation)))
            &&rejects(()=>worldInternationalRefundShipment(S,prepaidMissing.id));
          return {paymentOptions,dates,noDispatchCash,creditSave,advance,saveAdvance,early,claims,
            retirementWhileUnpaid,elimination,retry,blocksTamper,fixedCurrency,once,noDuplicate,paidAll,terminal,
            fundedAndLost:prepaidMissing.credit.paidAt===ym(2001,5),unfundedLoss,dueRefund,refundNotForged,
            prepaidRepaid,refundsRestored};
        }""")
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS Phase 4: calendar and leap years, international credit, advances, inventory, foreign cash, restore")


if __name__ == "__main__":
    main()
