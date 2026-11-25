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
        assert not errors,errors
        print("PASS Phase 7 SPEC-126: six paid purchase boundaries, cash, ownership, 5 staged and 6 inherited-scope accounting checks")
        print("PASS Phase 7 SPEC-134: 8 live and restored shareholder registry checks")
        browser.close()

if __name__=="__main__":
    main()
