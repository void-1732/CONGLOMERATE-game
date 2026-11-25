"""Demand deposits segregate cash and reconcile both counterparties and group reports."""

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
          S=newWorldGame({country:'JP',name:'Demand deposits'});
          VIEW_FIRM=S.playerId;PAGE='financeFunding';
          requestOperationSaveV037=()=>true;
          saveAuto=async()=>true;
          const parent=company(S.playerId),capital=60000000,payer=S.seq;
          post(parent,{investment:capital},{cash:capital},'検証用の設立','investing',S);
          const bank=initFirm(S,{name:'預金受入テスト法人',country:'JP',industry:'service',seedBase:600000,publicOwnership:false});
          bank.owners=[{id:parent.id,econ:1,vote:1}];
          registerEquityLink(S,{parentId:parent.id,childId:bank.id,ratio:1,kind:'foundation',
            considerationLocal:capital,buyerJournal:payer,childJournal:bank.journals.find(j=>j.text==='創業資本').id,
            bookEquityBase:baseFromLocal(capital,'JP'),cashAcquiredBase:baseFromLocal(acc(bank,'cash'),'JP')});
          syncWorldIdentities(S);
          window.before={bank:bank.id,clientCash:acc(parent,'cash'),bankCash:acc(bank,'cash'),group:consolidate(S)};
          render();
        }""")
        form = page.locator('form[data-world-bank="open"]')
        form.locator('[name="principal"]').fill("10000")
        form.get_by_role("button", name="銀行に預ける").click()
        opened = page.evaluate("""() => {
          const before=window.before,client=company(S.playerId),bank=company(before.bank);
          const [receipt]=S.worldExpansion.bankDeposits,report=consolidate(S),spot=accountingFxReview(S,S.playerId,report);
          const stored=parsePayload(savePayload(S));
          const rejects=(fn,msg)=>{try{fn();return false;}catch(e){return e.message.includes(msg);}};
          const ownOnly=rejects(()=>worldWithdrawBankDeposit(S,bank.id,receipt.id),'自己');
          const cashOnly=rejects(()=>worldOpenBankDeposit(S,client.id,bank.id,acc(client,'cash')+1),'現金');
          const noSelf=rejects(()=>worldOpenBankDeposit(S,bank.id,bank.id,1),'操作権限');
          const office=bank.plants[0];office.paused=true;
          const noInactiveBranch=rejects(()=>worldOpenBankDeposit(S,client.id,bank.id,1),'稼働');
          office.paused=false;
          const tamper=structuredClone(stored);tamper.worldExpansion.bankDeposits[0].principal++;
          const falsified=rejects(()=>worldValidateBankDeposits(tamper),'仕訳');
          return {
            ui:receipt.principal===10000&&receipt.returnedAt===null&&acc(client,'cash')===before.clientCash-10000,
            balances:acc(client,'worldBankDeposits')===10000&&acc(bank,'cash')===before.bankCash
              &&acc(bank,'worldBankReserve')===10000&&acc(bank,'worldDemandDeposits')===-10000&&!acc(bank,'serviceRevenue'),
            consolidated:!report.errors.length&&report.bs.assets===before.group.bs.assets
              &&report.bs.liab===before.group.bs.liab&&report.bs.cash===before.group.bs.cash-10000
              &&report.adjustments.bankDepositsEliminated===10000&&spot.bs.bankDepositsEliminated===10000,
            restored:!check(stored).length&&worldServiceActivity(stored,'PRD-S05').length===1
              &&worldServiceActivity(stored,'PRD-S05')[0].amount===0,
            reorg:worldDomesticBlocksReorganization(S,bank.id,office)&&worldDomesticBlocksReorganization(S,client.id),
            ownOnly,cashOnly,noSelf,noInactiveBranch,falsified
          };
        }""")
        assert all(opened.values()), opened
        month_closed = page.evaluate("""async () => {
          await runMonth();
          const report=consolidate(S),f=company(S.playerId);
          window.beforeRefund={cash:acc(f,'cash'),bankCash:acc(company(window.before.bank),'cash')};
          PAGE='financeFunding';render();
          return S.month===2&&!report.errors.length&&report.cf.reconciled
            &&report.adjustments.bankDepositsEliminated===10000;
        }""")
        assert month_closed
        page.locator('form[data-world-bank="withdraw"]').get_by_role("button", name="全額を払い戻す").click()
        closed = page.evaluate("""async () => {
          const before=window.before,client=company(S.playerId),bank=company(before.bank),receipt=S.worldExpansion.bankDeposits[0];
          const userRefund=receipt.returnedAt===ym(S.year,S.month)&&acc(client,'cash')===window.beforeRefund.cash+10000
            &&acc(bank,'cash')===window.beforeRefund.bankCash&&acc(client,'worldBankDeposits')===0
            &&acc(bank,'worldBankReserve')===0&&acc(bank,'worldDemandDeposits')===0;
          const tx=worldOpenBankDeposit(S,client.id,bank.id,9000);
          bank.plants[0].paused=true;syncPlant(bank);
          await runMonth();
          const saved=parsePayload(savePayload(S)),report=consolidate(saved),bankAfter=company(bank.id,saved);
          const refunded=saved.worldExpansion.bankDeposits.find(r=>r.id===tx.id);
          return {
            userRefund,
            monthlyRefund:refunded.returnedAt===ym(1900,2)&&Number.isSafeInteger(refunded.returnJournal)
              &&acc(bankAfter,'worldBankReserve')===0&&acc(bankAfter,'worldDemandDeposits')===0,
            balanced:!check(saved).length&&!report.errors.length&&report.cf.reconciled
              &&report.adjustments.bankDepositsEliminated===0&&!acc(bankAfter,'serviceRevenue')
          };
        }""")
        assert all(closed.values()), closed
        london = page.evaluate("""async()=>{
          S=newWorldGame({country:'UK',name:'London banking group'});
          VIEW_FIRM=S.playerId;VIEW_COUNTRY='UK';PAGE='corporateSubsidiaries';render();
          document.querySelector('#subName').value='London Bank';
          document.querySelector('#subCountry').value='UK';
          document.querySelector('#subIndustry').value='service';
          document.querySelector('#subCapital').value='1200000';
          createSub();syncWorldIdentities(S);
          const bank=S.firms.find(f=>f.name==='London Bank'),bid=bank.id;
          const noMidlands=!worldBankCanReceive(S,bank)&&bank.plants[0].siteId==='UK-MID';
          VIEW_FIRM=bid;PAGE='facilityExpansion';render();
          document.querySelector('#factoryName').value='London branch';
          document.querySelector('#factorySite').value='UK-LON';
          factoryBuild();
          const p=bank.plants.find(p=>p.name==='London branch');
          if(!p?.construction||p.siteId!=='UK-LON'||worldBankCanReceive(S,bank))throw Error('London branch commissioning gate');
          for(let n=0;n<2;n++){const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))}
          const ready=worldBankCanReceive(S,company(bid,S));
          VIEW_FIRM=S.playerId;PAGE='financeFunding';render();
          return {bid,plantId:p.id,noMidlands,ready};
        }""")
        assert london["noMidlands"] and london["ready"], london
        deposit_form = page.locator('form[data-world-bank="open"]')
        deposit_form.locator('[name="bank"]').select_option(london["bid"])
        deposit_form.locator('[name="principal"]').fill("10000")
        deposit_form.get_by_role("button", name="銀行に預ける").click()
        loan_form = page.locator('form[data-world-bank="borrow"]')
        loan_form.locator('[name="bank"]').select_option(london["bid"])
        loan_form.locator('[name="principal"]').fill("12000")
        loan_form.locator('[name="months"]').select_option("12")
        loan_form.get_by_role("button", name="普通融資を申し込む").click()
        london_result = page.evaluate("""async({bid,plantId})=>{
          const bank=company(bid,S),client=company(S.playerId,S),w=S.worldExpansion;
          const deposit=w.bankDeposits[0],loan=w.bankLoans[0];
          const local=firmCurrency(bank,S)==='GBP'&&firmCurrency(client,S)==='GBP'
            &&deposit.bankId===bid&&deposit.clientId===client.id&&deposit.principal===10000
            &&loan.country==='UK'&&loan.principal===12000&&acc(bank,'worldBankReserve')===10000;
          const initial=parsePayload(savePayload(S)),report=consolidate(initial);
          const consolidated=!report.errors.length&&report.cf.reconciled&&report.adjustments.bankDepositsEliminated>0;
          const foreign=S.firms.find(f=>f.country==='JP');
          const deny=action=>{try{action();return false}catch{return true}};
          const crossBorder=deny(()=>worldOpenBankDeposit(S,foreign.id,bid,100))&&deny(()=>phase7IssueBankLoan(S,bid,foreign.id,100,12));
          const branch=bank.plants.find(p=>p.id===plantId);
          const blocked=worldDomesticBlocksReorganization(S,bid,branch)&&!worldDomesticBlocksReorganization(S,bid,bank.plants[0]);
          branch.paused=true;syncPlant(bank);
          for(let n=0;n<2;n++){const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))}
          const loaded=parsePayload(savePayload(S)),creditor=company(bid,loaded);
          const returned=loaded.worldExpansion.bankDeposits[0].returnedAt!==null&&acc(creditor,'worldBankReserve')===0;
          const paid=loaded.worldExpansion.bankLoans[0].remaining===11000&&acc(creditor,'loanrec')===11000
            &&loaded.worldExpansion.bankLoans[0].interestPaid>0;
          return {local,consolidated,crossBorder,blocked,returned,paid,clean:!check(loaded).length&&!consolidate(loaded).errors.length};
        }""", london)
        assert all(london_result.values()), london_result
        assert not errors, errors
        browser.close()
    print("PASS demand deposits and bank loans: Tokyo regression, London GBP accounting, branch commissioning, closure and save")


if __name__ == "__main__":
    main()
