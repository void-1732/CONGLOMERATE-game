"""Phase 7 SPEC-126: actual paid purchases, control boundaries and save checks."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
        page=browser.new_page()
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.set_content((ROOT/"index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result=page.evaluate("""async()=>{
 S=newWorldGame({country:'JP',name:'Phase7 thresholds'});
 VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';
 const root=company(S.playerId,S),target=S.firms.find(f=>f.id!==root.id&&f.country==='JP'&&f.owners.length===1&&f.owners[0].id==='PUBLIC');
 if(!target)throw Error('target unavailable');
 post(root,{cash:1000000000},{capital:1000000000},'検証用資本','financing',S);
 const boundaries=[29.99,30,69.99,70,99.99,100],results=[];
 let prior=0;
 for(const pct of boundaries){
  const amount=Math.round((pct-prior)*100)/100;
  const quote=maQuote(S,root,target,amount,2.5),cash=acc(root,'cash'),targetCash=acc(target,'cash');
  executeMADeal(S,root.id,target.id,amount,2.5,'player');
  const r=phase7ShareholderRights(S,root.id,target.id);
  const group=controlSet(S,root.id),member=group.has(target.id);
  const co=consolidate(S),starts=consolidatedMonths(S,S.equityLinks,S.firms.filter(f=>group.has(f.id)),root.id);
  results.push({pct,rights:r,member,consolidated:co.members.includes(target.id),start:starts[target.id]??null,
    errors:[...check(S),...co.errors],cash:cash-acc(root,'cash')===localFromBase(quote.total,root.country,S)&&acc(target,'cash')===targetCash});
  prior=pct;
 }
 const loaded=parsePayload(savePayload(S));const good=phase7ShareholderRights(loaded,root.id,target.id);
 const bad=structuredClone(loaded),b=company(target.id,bad);b.owners.push({...b.owners[0],econ:0,vote:0});let duplicate=false;try{parsePayload(savePayload(bad))}catch(e){duplicate=e.message.includes('株主名簿')}
 const noCash=structuredClone(loaded),buyer=company(root.id,noCash),other=noCash.firms.find(f=>f.id!==root.id&&f.id!==target.id&&f.owners.every(o=>o.id==='PUBLIC'));
 const available=acc(buyer,'cash');if(available>0)post(buyer,{otherExpense:available},{cash:available},'検証用現金ゼロ','operating',noCash);
 const before=JSON.stringify({o:other.owners,gl:buyer.ledger,j:buyer.journals,links:noCash.equityLinks});let denied=false;try{executeMADeal(noCash,buyer.id,other.id,30,2.5,'player')}catch(e){denied=e.message.includes('資金')}
 const atomic=before===JSON.stringify({o:other.owners,gl:buyer.ledger,j:buyer.journals,links:noCash.equityLinks});
 const fixture={playerId:'a',worldExpansion:{},firms:[{id:'a',owners:[{id:'PUBLIC',econ:1,vote:1}]},{id:'b',owners:[{id:'a',econ:.7,vote:.7},{id:'PUBLIC',econ:.3,vote:.3}]},{id:'c',owners:[{id:'a',econ:.3,vote:.3},{id:'b',econ:.4,vote:.4},{id:'PUBLIC',econ:.3,vote:.3}]}]};
 const indirect=controller(fixture,'c','a')&&!controller(fixture,'c','b')&&phase7ShareholderRights(fixture,'a','c').control;
 const legacy={...fixture,worldExpansion:null};
 const legacyRule=phase7ControlThreshold(legacy,.55)&&!phase7ControlThreshold(fixture,.55);
 return {results,save:good.whollyOwned,duplicate,denied,atomic,indirect,legacyRule};
}""")
        assert [r["pct"] for r in result["results"]]==[29.99,30,69.99,70,99.99,100],result
        for r in result["results"]:
            assert not r["errors"] and r["cash"],r
            assert r["member"]==r["consolidated"]==r["rights"]["control"]==(r["pct"]>=70),r
            assert r["rights"]["meeting"]==(r["pct"]>=30),r
            assert r["rights"]["whollyOwned"]==(r["pct"]==100),r
            assert (r["start"] is not None)==(r["pct"]>=70),r
        assert all(result[k] for k in ("save","duplicate","denied","atomic","indirect","legacyRule")),result
        staged=page.evaluate("""async()=>{
 S=newWorldGame({country:'JP',name:'Staged acquisition'});VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';saveAuto=async()=>true;
 const root=company(S.playerId,S),target=S.firms.find(f=>f.id!==root.id&&f.country==='JP'&&f.owners.length===1&&f.owners[0].id==='PUBLIC');
 post(root,{cash:1000000000},{capital:1000000000},'検証用資本','financing',S);
 const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
 const rootId=root.id,targetId=target.id;await close();
 const buyer=company(rootId,S),t=company(targetId,S);t.auto=false;t.delegate.mode='manual';for(const m of t.models)t.plans[m.id]=0;
 executeMADeal(S,rootId,targetId,30,2.5,'player');
 post(t,{cash:12345},{otherRevenue:12345},'支配前の外部売上','operating',S);
 executeMADeal(S,rootId,targetId,40,2.5,'player');
 const crossing=S.equityLinks.at(-1),atControl=acc(t,'cash');
 post(t,{cash:23456},{otherRevenue:23456},'支配後の外部売上','operating',S);
 await close();
 const c=consolidate(S),targetNow=company(targetId,S),audit=accountingFxReview(S,rootId,c);
 const expected=targetNow.journals.filter(j=>j.when===S.monthCommitted&&j.id>=crossing.buyerJournal).reduce((n,j)=>n+Math.round(journalIncome(j).revenue*Number(j.fxAtPost??worldReferenceFx(targetNow.country,S))),0);
 return {income:audit.periodEntries[targetId].revenue===expected,cf:c.cf.reconciled,scopeCash:c.cf.scopeAdded===Math.round(atControl*crossing.targetFxOnAcq),clean:!c.errors.length&&!check(S).length,restore:!check(parsePayload(savePayload(S))).length};
}""")
        assert len(staged)==5 and all(staged.values()),staged
        indirect=page.evaluate("""async()=>{
 S=newWorldGame({country:'JP',name:'Inherited control'});VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';saveAuto=async()=>true;
 const root=company(S.playerId,S),p=S.firms.find(f=>f.id!==root.id&&f.country==='JP'&&f.owners.length===1&&f.owners[0].id==='PUBLIC');
 post(root,{cash:1000000000},{capital:1000000000},'検証用資本','financing',S);
 const parentId=p.id,rootId=root.id,amount=65000000,payer=S.seq;
 post(p,{investment:amount},{cash:amount},'検証用子会社出資','investing',S);
 const child=initFirm(S,{name:'Inherited subsidiary',country:'JP',industry:'service',seedBase:650000,publicOwnership:false});
 child.owners=[{id:parentId,econ:1,vote:1}];
 registerEquityLink(S,{parentId,childId:child.id,ratio:1,kind:'foundation',considerationLocal:amount,buyerJournal:payer,childJournal:child.journals.find(j=>j.text==='創業資本').id,bookEquityBase:baseFromLocal(amount,'JP',S),cashAcquiredBase:baseFromLocal(acc(child,'cash'),'JP',S)});
 syncWorldIdentities(S);const childId=child.id;
 const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
 await close();
 const parent=company(parentId,S),sub=company(childId,S);
 parent.auto=false;sub.auto=false;parent.delegate.mode='manual';sub.delegate.mode='manual';
 for(const f of [parent,sub])for(const m of f.models)f.plans[m.id]=0;
 post(sub,{cash:12345},{otherRevenue:12345},'支配前の外部売上','operating',S);
 executeMADeal(S,rootId,parentId,70,2.5,'player');
 const crossing=S.equityLinks.at(-1),expectedScope=acc(parent,'cash')+acc(sub,'cash');
 const ids=controlSet(S,rootId),members=S.firms.filter(f=>ids.has(f.id));
 const scope=consolidationScope(S,S.equityLinks.filter(l=>ids.has(l.parentId)&&ids.has(l.childId)),members,rootId);
 const inherited=scope.entries[childId].scopeInherited&&scope.entries[childId].buyerJournal===crossing.buyerJournal;
 post(sub,{cash:23456},{otherRevenue:23456},'支配後の外部売上','operating',S);
 await close();
 const c=consolidate(S),audit=accountingFxReview(S,rootId,c),subNow=company(childId,S);
 const expected=subNow.journals.filter(j=>j.when===S.monthCommitted&&j.id>=crossing.buyerJournal).reduce((n,j)=>n+Math.round(journalIncome(j).revenue*Number(j.fxAtPost??worldReferenceFx(subNow.country,S))),0);
 return {inherited,income:audit.periodEntries[childId].revenue===expected,scopeCash:c.cf.scopeAdded===expectedScope,cf:c.cf.reconciled,clean:!c.errors.length&&!check(S).length,restored:!check(parsePayload(savePayload(S))).length};
}""")
        assert len(indirect)==6 and all(indirect.values()),indirect
        registry=page.evaluate("""()=>{
 const s=newWorldGame({country:'JP',name:'Registry audit'});
 const root=company(s.playerId,s),other=s.firms.find(f=>f.id!==root.id&&f.owners.length===1&&f.owners[0].id==='PUBLIC');
 if(!other)throw Error('registry fixture unavailable');
 const bad=mutate=>{
  const copy=structuredClone(s),f=company(other.id,copy);
  mutate(f);
  const prior=JSON.stringify(f.owners);
  const live=check(copy).some(e=>e.includes('株主名簿'));
  let restored=false;
  try{parsePayload(savePayload(copy))}catch(e){restored=e.message.includes('株主名簿')}
  return live&&restored&&prior===JSON.stringify(f.owners);
 };
 return {
  valid:!check(s).length&&!check(parsePayload(savePayload(s))).length,
  duplicate:bad(f=>f.owners.push({...f.owners[0],econ:0,vote:0})),
  self:bad(f=>f.owners[0].id=f.id),
  unknown:bad(f=>f.owners[0].id='MISSING-OWNER'),
  invalidEquity:bad(f=>f.owners[0].econ=-0.1),
  invalidVotes:bad(f=>f.owners[0].vote=0.5),
  empty:bad(f=>f.owners=[]),
  nonFiniteLive:(()=>{const copy=structuredClone(s);company(other.id,copy).owners[0].vote=NaN;return check(copy).some(e=>e.includes('株主名簿'))})()
 };
}""")
        assert len(registry)==8 and all(registry.values()),registry
        circular=page.evaluate("""()=>{
 const s=newWorldGame({country:'JP',name:'Cross ownership audit'});
 const root=company(s.playerId,s),targets=s.firms.filter(f=>f.id!==root.id&&f.country==='JP'&&f.owners.length===1&&f.owners[0].id==='PUBLIC');
 if(targets.length<2)throw Error('two acquisition targets required');
 const [b,c]=targets;
 post(root,{cash:5000000000},{capital:5000000000},'検証用資本','financing',s);
 for(const f of [b,c])post(f,{cash:1000000000},{capital:1000000000},'検証用資本','financing',s);
 executeMADeal(s,root.id,b.id,70,2.5,'player');
 executeMADeal(s,root.id,c.id,70,2.5,'player');
 executeMADeal(s,b.id,c.id,20,2.5,'player');
 executeMADeal(s,c.id,b.id,20,2.5,'player');
 const g=ownedGroup(s,root.id),co=consolidate(s,root.id);
 const restored=parsePayload(savePayload(s)),r=ownedGroup(restored,root.id);
 const reversed=structuredClone(s);reversed.firms.reverse();const other=ownedGroup(reversed,root.id);
 const exact=x=>Math.abs(x-.875)<1e-9;
 return {
  retained:b.owners.some(o=>o.id===c.id&&o.econ===.2)&&c.owners.some(o=>o.id===b.id&&o.econ===.2),
  shares:exact(g.shares[b.id])&&exact(g.shares[c.id])&&!g.issues.length,
  unique:g.members.length===3&&new Set(co.members).size===3&&co.members.length===3,
  ledger:!check(s).length&&!co.errors.length&&co.bs.liabEquityDiff===0&&co.spot.checkDifference===0,
  order:exact(other.shares[b.id])&&exact(other.shares[c.id])&&!other.issues.length,
  restored:exact(r.shares[b.id])&&exact(r.shares[c.id])&&!check(restored).length&&!consolidate(restored).errors.length,
  unseeded:!controlSet(s,b.id).has(c.id)&&!controlSet(s,c.id).has(b.id)
 };
}""")
        assert len(circular)==7 and all(circular.values()),circular
        print("PASS Phase 7 SPEC-132: seven paid mutual-holding and consolidation checks")
        reserve=page.evaluate("""()=>{
 const s=newWorldGame({country:'JP',name:'Reserved funds audit'}),buyer=company(s.playerId,s);
 const target=s.firms.find(f=>f.id!==buyer.id&&f.country==='JP'&&f.owners.length===1&&f.owners[0].id==='PUBLIC');
 post(buyer,{cash:1000000000},{capital:1000000000},'検証用資本','financing',s);
 const reject=fn=>{try{fn();return false}catch{return true}};
 const cash=acc(buyer,'cash'),r=phase7ProposeMA(s,buyer.id,target.id,30,2.5);
 const held=phase7ReservedCash(s,buyer.id)===r.amountLocal&&phase7AvailableCash(s,buyer)===cash-r.amountLocal&&acc(buyer,'cash')===cash;
 const seq=s.seq,ledger=JSON.stringify(buyer.ledger);
 const blocked=reject(()=>post(buyer,{otherExpense:cash},{cash:cash},'予約済資金の競合支出','operating',s))&&seq===s.seq&&ledger===JSON.stringify(buyer.ledger);
 const duplicate=reject(()=>phase7ProposeMA(s,buyer.id,target.id,30,2.5));
 const loaded=parsePayload(savePayload(s)),saved=phase7ReservedCash(loaded,buyer.id)===r.amountLocal;
 const forged=structuredClone(loaded);forged.worldExpansion.maReservations[0].amountLocal++;
 const tamper=reject(()=>parsePayload(savePayload(forged)));
 phase7CancelMA(s,buyer.id,r.id);const cancelled=phase7AvailableCash(s,buyer)===cash;
 const low=phase7ProposeMA(s,buyer.id,target.id,100,.75);
 const refused=reject(()=>phase7SettleMA(s,buyer.id,low.id))&&phase7ReservedCash(s,buyer.id)===0&&acc(buyer,'cash')===cash;
 const success=phase7ProposeMA(s,buyer.id,target.id,30,2.5);
 phase7SettleMA(s,buyer.id,success.id);
 const paid=cash-acc(buyer,'cash')===success.amountLocal&&phase7ReservedCash(s,buyer.id)===0&&target.owners.some(o=>o.id===buyer.id&&o.econ===.3);
 phase7ProposeMA(s,buyer.id,target.id,10,2.5);phase7ExpireMAReservations(s);
 return {held,blocked,duplicate,saved,tamper,cancelled,refused,paid,expired:phase7ReservedCash(s,buyer.id)===0,clean:!check(s).length&&!check(parsePayload(savePayload(s))).length};
}""")
        assert len(reserve)==10 and all(reserve.values()),reserve
        print("PASS Phase 7 SPEC-128: ten reservation, settlement, release and integrity checks")
        repayment=page.evaluate("""async()=>{
 S=newWorldGame({country:'JP',name:'Monthly external loan'});VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';saveAuto=async()=>true;PAGE='financeFunding';render();
 const root=company(S.playerId,S),id=root.id;
 post(root,{cash:1000000000},{capital:1000000000},'検証用資本','financing',S);
 root.auto=false;root.delegate.mode='manual';
 const field=document.getElementById('borrowBase');
 if(field)field.value='360000';else throw Error('borrowBase not found');
 borrow();
 const loan=root.loans.at(-1);if(!loan?.repayment)throw Error('monthly contract missing');
 const principal=loan.outstanding,installment=Math.floor(principal/36)+(principal%36?1:0),loanId=loan.id;
 const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
 const issue=loan.repayment.principal===principal&&loan.due===loan.repayment.origin+36&&phase7ScheduledPrincipal(S,loan)===0;
 await close();const first=company(id,S).loans.find(l=>l.id===loanId);
 const noEarly=first?.outstanding===principal;
 await close();const debtor=company(id,S),current=debtor.loans.find(l=>l.id===loanId);
 const monthly=current?.outstanding===principal-installment&&debtor.journals.some(j=>j.when===S.monthCommitted&&j.text==='借入元本返済'&&j.amount===installment);
 const interest=debtor.journals.some(j=>j.when===S.monthCommitted&&j.text==='当月借入利息発生'&&j.amount===Math.round(principal*loan.rate/12));
 const restored=parsePayload(savePayload(S)),loaded=company(id,restored).loans.find(l=>l.id===loanId);
 const forged=structuredClone(restored);company(id,forged).loans.find(l=>l.id===loanId).repayment.principal++;
 let tamper=false;try{parsePayload(savePayload(forged))}catch(e){tamper=e.message.includes('返済')}
 return {issue,noEarly,monthly,interest,restored:loaded?.outstanding===current.outstanding&&loaded.repayment.principal===principal,tamper,clean:!check(S).length&&!consolidate(S).errors.length&&consolidate(S).cf.reconciled};
}""")
        assert len(repayment)==7 and all(repayment.values()),repayment
        print("PASS Phase 7 SPEC-086: seven external monthly principal, interest and save checks")
        funding=page.evaluate("""()=>{
 const s=newWorldGame({country:'JP',name:'Acquisition funding audit'}),buyer=company(s.playerId,s),target=s.firms.find(f=>f.id!==buyer.id&&f.country==='JP'&&f.owners.length===1&&f.owners[0].id==='PUBLIC');
 const reject=fn=>{try{fn();return false}catch{return true}};
 const own=acc(buyer,'cash');post(buyer,{otherExpense:own},{cash:own},'検証用現金支出','operating',s);
 const borrowed=1000000000;post(buyer,{cash:borrowed},{debt:borrowed},'銀行借入','financing',s);
 const debtBlocked=phase7RestrictedCash(buyer)===borrowed&&phase7AcquisitionCash(s,buyer)===0&&!maQuote(s,buyer,target,30,2.5).affordable;
 const before=JSON.stringify(s),denied=reject(()=>phase7ProposeMA(s,buyer.id,target.id,30,2.5))&&before===JSON.stringify(s);
 const issued=200000000;post(buyer,{cash:issued},{capital:issued},'外部向け新株発行：検証','financing',s);
 const issueBlocked=phase7RestrictedCash(buyer)===borrowed+issued&&phase7AcquisitionCash(s,buyer)===0;
 const raw=JSON.stringify(buyer.ledger),seq=s.seq;
 const guard=reject(()=>post(buyer,{investment:1},{cash:1},'株式取得：検証','investing',s))&&raw===JSON.stringify(buyer.ledger)&&seq===s.seq;
 post(buyer,{otherExpense:issued},{cash:issued},'通常事業支出','operating',s);
 const consumed=phase7RestrictedCash(buyer)===borrowed;
 post(buyer,{cash:500000000},{otherRevenue:500000000},'外部営業収入','operating',s);
 const earned=phase7AcquisitionCash(s,buyer)===500000000;
 const r=phase7ProposeMA(s,buyer.id,target.id,30,2.5),reserved=phase7AcquisitionCash(s,buyer)===500000000-r.amountLocal;
 const loaded=parsePayload(savePayload(s)),restored=phase7RestrictedCash(company(buyer.id,loaded))===borrowed&&phase7AcquisitionCash(loaded,company(buyer.id,loaded))===500000000-r.amountLocal;
 phase7SettleMA(s,buyer.id,r.id);const settled=phase7RestrictedCash(buyer)===borrowed&&phase7AcquisitionCash(s,buyer)===500000000-r.amountLocal;
 return {debtBlocked,denied,issueBlocked,guard,consumed,earned,reserved,restored,settled,clean:!check(s).length&&!consolidate(s).errors.length};
}""")
        assert len(funding)==10 and all(funding.values()),funding
        print("PASS Phase 7 SPEC-117: ten financing source audit and acquisition checks")
        dividend=page.evaluate("""async()=>{
 S=newWorldGame({country:'JP',name:'Dividend audit'});VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';saveAuto=async()=>true;
 const root=company(S.playerId,S),target=S.firms.find(f=>f.id!==root.id&&f.country==='JP'&&f.owners.length===1&&f.owners[0].id==='PUBLIC'),rootId=root.id,targetId=target.id;
 post(root,{cash:5000000000},{capital:5000000000},'検証用資本','financing',S);
 executeMADeal(S,rootId,targetId,70,2.5);
 post(target,{cash:1000000},{otherRevenue:1000000},'配当原資の営業収益','operating',S);
 const before=consolidate(S),cash=acc(target,'cash'),parentCash=acc(root,'cash'),profit=financials(target).profit;
 const reject=fn=>{try{fn();return false}catch{return true}};
 const snapshot=JSON.stringify(S),rejectOver=reject(()=>phase7PayDividend(S,targetId,phase7DividendLimit(S,target)+1))&&snapshot===JSON.stringify(S);
 const r=phase7PayDividend(S,targetId,100001),p=r.allocations.find(a=>a.ownerId===rootId),ext=r.allocations.find(a=>a.ownerId==='PUBLIC');
 const allocated=p.paid===70001&&ext.paid===30000&&p.paid+ext.paid===r.amount;
 const balances=cash-acc(target,'cash')===r.amount&&acc(root,'cash')-parentCash===p.received&&acc(target,'dividendsPaid')===r.amount;
 const profitPreserved=financials(target).profit===profit;
 const after=consolidate(S),eliminated=after.pl.profit===before.pl.profit&&before.bs.cash-after.bs.cash===ext.paid&&after.bs.liabEquityDiff===0&&after.spot.checkDifference===0;
 const loaded=parsePayload(savePayload(S)),restore=loaded.worldExpansion.dividends[0].amount===r.amount&&!check(loaded).length;
 const forged=structuredClone(loaded);forged.worldExpansion.dividends[0].allocations[0].paid++;
 const tamper=reject(()=>parsePayload(savePayload(forged)));
 const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
 await close();
 const g=consolidate(S),monthly=g.cf.reconciled&&!g.errors.length&&!check(S).length;
 return {rejectOver,allocated,balances,profitPreserved,eliminated,restore,tamper,monthly};
}""")
        assert len(dividend)==8 and all(dividend.values()),dividend
        print("PASS Phase 7 SPEC-056/080/100: eight discretionary distribution and consolidation checks")
        assert not errors,errors
        print("PASS Phase 7 SPEC-126: six paid purchase boundaries, cash, ownership, 5 staged and 6 inherited-scope accounting checks")
        print("PASS Phase 7 SPEC-134: 8 live and restored shareholder registry checks")
        browser.close()

if __name__=="__main__":
    main()
