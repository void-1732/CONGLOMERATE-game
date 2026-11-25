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
        assert not errors,errors
        print("PASS Phase 7 SPEC-126: six paid purchase boundaries, indirect control, cash, ownership validation and save")
        browser.close()

if __name__=="__main__":
    main()
