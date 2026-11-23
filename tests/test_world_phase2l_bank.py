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
        assert not errors, errors
        browser.close()
    print("PASS Phase 2-L demand deposit opening, full reserve, standalone/group/FX reporting, UI refund and save")


if __name__ == "__main__":
    main()
