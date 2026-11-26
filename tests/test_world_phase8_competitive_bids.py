"""Phase 8 SPEC-122 competitive quote selection (actual browser game function)."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads("[[[{\"buyerId\":\"A\",\"targetId\":\"T\",\"total\":100,\"score\":90,\"accepted\":true,\"available\":1000},{\"buyerId\":\"B\",\"targetId\":\"T\",\"total\":120,\"score\":20,\"accepted\":true,\"available\":1000}],\"B\"],[[{\"buyerId\":\"A\",\"targetId\":\"T\",\"total\":100,\"score\":90,\"accepted\":true,\"available\":1000},{\"buyerId\":\"B\",\"targetId\":\"T\",\"total\":120,\"score\":20,\"accepted\":false,\"available\":1000}],\"A\"],[[{\"buyerId\":\"A\",\"targetId\":\"T\",\"total\":100,\"score\":90,\"accepted\":true,\"available\":1000},{\"buyerId\":\"B\",\"targetId\":\"T\",\"total\":120,\"score\":20,\"accepted\":true,\"available\":200}],\"A\"],[[{\"buyerId\":\"B\",\"targetId\":\"T\",\"total\":100,\"score\":90,\"accepted\":true,\"available\":1000},{\"buyerId\":\"A\",\"targetId\":\"T\",\"total\":100,\"score\":20,\"accepted\":true,\"available\":1000}],\"A\"],[[{\"buyerId\":\"A\",\"targetId\":\"T\",\"total\":100,\"score\":90,\"accepted\":false,\"available\":1000}],null],[[{\"buyerId\":\"A\",\"targetId\":\"T\",\"total\":100,\"score\":90,\"accepted\":true,\"available\":1000},{\"buyerId\":\"B\",\"targetId\":\"U\",\"total\":120,\"score\":20,\"accepted\":true,\"available\":1000}],\"A\"]]")

def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto((ROOT / "index.html").as_uri(), wait_until="load")
        for proposals, expected in CASES:
            actual = page.evaluate("(rows) => phase8SelectCompetitiveBid(rows)?.buyerId ?? null", proposals)
            assert actual == expected, (proposals, actual, expected)
        unequal_stakes = [
            {"buyerId":"A","targetId":"T","total":500,"shareQuantity":50,"score":90,"accepted":True,"available":5000},
            {"buyerId":"B","targetId":"T","total":240,"shareQuantity":20,"score":20,"accepted":True,"available":5000},
        ]
        for rows in (unequal_stakes, list(reversed(unequal_stakes))):
            assert page.evaluate("(rows) => phase8SelectCompetitiveBid(rows)?.buyerId",rows)=="B"
        print("Phase 8 SPEC-122: higher price per share wins even with a smaller additional stake")
        base = json.loads("{\"sameCountry\":true,\"sameIndustry\":true,\"buyerValue\":1000,\"targetValue\":300,\"profit\":30,\"sales\":400,\"novelTech\":0,\"marketShare\":0,\"verticalMatches\":0}")
        baseline = page.evaluate("(x) => phase8StrategicScore(x)", base)
        for name, patch, sign in json.loads("[[\"technology\",{\"novelTech\":5},1],[\"share\",{\"marketShare\":0.4},1],[\"vertical\",{\"verticalMatches\":2},1],[\"profit\",{\"profit\":-30},-1],[\"oversize\",{\"targetValue\":3000},-1],[\"no sales\",{\"sales\":0},-1]]"):
            actual = page.evaluate("(x) => phase8StrategicScore(x)", {**base, **patch})
            assert (actual > baseline) - (actual < baseline) == sign, (name, actual, baseline)
        print("Phase 8 strategic scoring: 6/6 passed")
        # Exact additional voting shares, including group ownership and treasury.
        control_cases = [[100,0,[["PUBLIC",100,100]],["A"],70],[100,0,[["A",30,30],["PUBLIC",70,70]],["A"],40],[100,0,[["A",20,20],["B",25,25],["PUBLIC",55,55]],["A","B"],25],[100,10,[["A",20,20],["PUBLIC",70,70]],["A"],43],[100,0,[["A",30,40],["PUBLIC",70,60]],["A"],35],[100,0,[["A",30,30],["B",40,40],["PUBLIC",30,30]],["A"],0],[100,0,[["A",70,70],["PUBLIC",30,30]],["A"],0],[3,0,[["A",1,1],["PUBLIC",2,2]],["A"],2]]
        for issued, treasury, owners, group, expected in control_cases:
            registry = {"issued":issued,"treasury":treasury,"owners":[{"id":i,"count":q,"votes":v} for i,q,v in owners]}
            actual = page.evaluate("([r,g]) => phase8ControlPurchaseQuantity(r,new Set(g))", [registry,group])
            assert actual == expected, (registry,group,actual,expected)
        print("Phase 8 additional whole-share control acquisition: 8/8 passed")
        staged = page.evaluate("""()=>{
          const s=newWorldGame({country:'JP',name:'Phase8 staged acquisition'}),root=company(s.playerId,s);
          const [buyer,target]=s.firms.filter(f=>f.id!==root.id&&f.country==='JP'&&f.owners.every(o=>o.id==='PUBLIC'));
          if(!buyer||!target)throw Error('Test fixture unavailable');
          post(buyer,{cash:1000000000},{capital:1000000000},'検証用資本','financing',s);
          executeMADeal(s,buyer.id,target.id,30,2.5,'ai');
          const quantity=phase8ControlPurchaseQuantity(phase7ReadShareRegistry(target),controlSet(s,buyer.id));
          const percent=phase7SharePercent(target,quantity),quote=maQuote(s,buyer,target,percent,2.5),cash=acc(buyer,'cash');
          const deal=executeMADeal(s,buyer.id,target.id,percent,2.5,'ai');
          const restored=parsePayload(savePayload(s));
          const group=phase8ControlledCompanies(restored);
          return {quantity:quantity===400000,control:controller(s,target.id,buyer.id),
            exact:target.shareRegistry.owners.find(o=>o.id===buyer.id).count===700000,
            payment:cash-acc(buyer,'cash')===localFromBase(quote.total,buyer.country,s),
            deal:deal.actor==='ai'&&deal.control===true,
            independence:group.has(target.id)&&!group.has(buyer.id)&&!group.has(root.id),
            restored:controller(restored,target.id,buyer.id)&&!check(restored).length,
            clean:!check(s).length};
        }""")
        assert len(staged)==8 and all(staged.values()),staged
        print("Phase 8 staged AI acquisition, independent bidder scope, settlement and save: 8/8 passed")
        for market, expected in json.loads("[[{},1],[{\"cycle\":-0.12},0.61],[{\"unemployment\":0.18},0.675],[{\"rate\":0.18},0.675],[{\"war\":true},0.5775],[{\"cycle\":-1},0.35],[{\"cycle\":0.12,\"unemployment\":0.03,\"rate\":0.04},1]]"):
            actual = page.evaluate("(w) => phase8CrisisFactor(w)", market)
            assert abs(actual - expected) < 1e-9, (market, actual, expected)
        print("Phase 8 crisis spending policy: 7/7 passed")
        trade_rows = json.loads("[{\"month\":22800,\"from\":\"US\",\"to\":\"UK\",\"goodsSeller\":101,\"sellerRate\":150000,\"status\":\"DELIVERED\",\"id\":\"a\"},{\"month\":22800,\"from\":\"US\",\"to\":\"UK\",\"goodsSeller\":50,\"sellerRate\":200000,\"status\":\"DELIVERED\",\"id\":\"b\"},{\"month\":22800,\"from\":\"UK\",\"to\":\"US\",\"goodsSeller\":40,\"sellerRate\":50000,\"status\":\"DELIVERED\",\"id\":\"c\"},{\"month\":22800,\"from\":\"US\",\"to\":\"UK\",\"goodsSeller\":101,\"sellerRate\":150000,\"status\":\"IN_TRANSIT\",\"id\":\"d\"},{\"month\":22800,\"from\":\"US\",\"to\":\"UK\",\"goodsSeller\":101,\"sellerRate\":150000,\"status\":\"REFUNDED\",\"id\":\"e\"},{\"month\":22800,\"from\":\"US\",\"to\":\"US\",\"goodsSeller\":101,\"sellerRate\":150000,\"status\":\"DELIVERED\",\"id\":\"f\"},{\"month\":22801,\"from\":\"US\",\"to\":\"UK\",\"goodsSeller\":101,\"sellerRate\":150000,\"status\":\"DELIVERED\",\"id\":\"g\"}]")
        trade_expected = json.loads("[{\"month\":22800,\"jurisdictionId\":\"UK\",\"exports\":20,\"imports\":252},{\"month\":22800,\"jurisdictionId\":\"US\",\"exports\":252,\"imports\":20},{\"month\":22801,\"jurisdictionId\":\"UK\",\"exports\":0,\"imports\":152},{\"month\":22801,\"jurisdictionId\":\"US\",\"exports\":152,\"imports\":0}]")
        assert page.evaluate("(rows) => phase8AggregateTrade(rows)", trade_rows) == trade_expected
        assert page.evaluate("(row) => {try {phase8AggregateTrade([row,row]);return false;}catch(e){return true;}}", trade_rows[0])
        actual = page.evaluate("""() => {
            const w=makeWorldExpansion();
            w.internationalRoutes.R={profileId:'US-UK-SEA-1900'};
            w.internationalShipments=[
              {id:'A',routeId:'R',status:'DELIVERED',receivedAt:ym(1900,2),goodsSeller:100,sellerRate:200000},
              {id:'B',routeId:'R',status:'IN_TRANSIT',receivedAt:null,goodsSeller:100,sellerRate:200000}];
            return phase8TradeByJurisdiction({worldExpansion:w},ym(1900,1),ym(1900,3));
        }""")
        assert actual == [{"month":22801,"jurisdictionId":"JUR-UK","exports":0,"imports":200},{"month":22801,"jurisdictionId":"JUR-US","exports":200,"imports":0}], actual
        print("Phase 8 delivered international trade aggregation: 3/3 passed")
        vehicles = page.evaluate("""async () => {
          S=newWorldGame({country:'JP',name:'Completed vehicle trade evidence'});
          VIEW_FIRM=S.playerId;render=()=>{};saveAuto=async()=>true;
          const firm=company(S.playerId),model=firm.models[0],from=S.monthCommitted+1;
          post(firm,{goods:1200},{cash:1200},'検証用輸出完成車','operating',S);
          firm.goods[model.id]={q:3,v:1200};
          exportShipment(S,firm,model.id,3,200,'UK',[]);
          const noDispatchTrade=phase8TradeByJurisdiction(S,from,from+1).length===0;
          await runMonth();
          const noEarlyReceipt=!(S.worldExpansion.vehicleExportReceipts??[]).length;
          await runMonth();
          if(S.monthCommitted!==from+1||LAST_MONTH_DIAGNOSTIC)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC));
          const restored=parsePayload(savePayload(S)),receipt=restored.worldExpansion.vehicleExportReceipts
            .find(t=>t.firmId===firm.id&&t.country==='UK');
          const trade=phase8TradeByJurisdiction(restored,from+1,from+1);
          const value=Math.round(receipt.goodsSeller*receipt.sellerRate/100000);
          const posted=receipt.quantity===3&&receipt.month===from+1
            &&company(firm.id,restored).journals.find(j=>j.id===receipt.journal).amount===receipt.goodsSeller;
          const balance=trade.find(t=>t.jurisdictionId==='JUR-JP')?.exports===value
            &&trade.find(t=>t.jurisdictionId==='JUR-UK')?.imports===value;
          receipt.sellerRate++;
          let rejects=false;try{parsePayload(savePayload(restored));}catch(e){rejects=e.message.includes('輸出検収');}
          return {noDispatchTrade,noEarlyReceipt,posted,balance,rejects};
        }""")
        assert len(vehicles) == 5 and all(vehicles.values()), vehicles
        print("Phase 8 finished vehicle trade: dispatch exclusion, real delivery, saved accounting and tamper rejection")
        merger=page.evaluate("""()=>{
 const s=newWorldGame({country:'JP',name:'AI merger scenario'}),root=company(s.playerId,s);
 const buyer=initFirm(s,{name:'AI service parent',country:'JP',industry:'service',seedBase:2000000});
 const target=initFirm(s,{name:'AI service target',country:'JP',industry:'service',seedBase:450000});
 syncWorldIdentities(s);ensureMAState(s);
 post(buyer,{cash:1000000000},{capital:1000000000},'検証用資本','financing',s);
 buyer.monthly.profit=20000;target.monthly.profit=100;
 const reject=fn=>{try{fn();return false}catch{return true}};
 const business=phase8MergerBusinessCase(s,buyer,target);
 const notPlayer=reject(()=>startGroupMerger(s,buyer.id,target.id,buyer.id));
 executeMADeal(s,buyer.id,target.id,100,2.5,'ai');
 const p=s.maPlans.find(x=>x.buyer===buyer.id&&x.target===target.id);
 const early=phase8PlanWhollyOwnedMergers(s,[]).length===0;
 p.done=true;p.mode='completed';p.months=p.duration;p.progress=100;
 const saved=parsePayload(savePayload(s));const b=company(buyer.id,saved),t=company(target.id,saved);
 const count=saved.firms.filter(isActiveCorporateFirm).length,assets=acc(b,'ppe')+acc(t,'ppe'),cash=acc(b,'cash')+acc(t,'cash'),staff=b.staff.production+t.staff.production;
 const ev=[];const plans=phase8PlanWhollyOwnedMergers(saved,ev);
 const planned=plans.length===1&&plans[0].actor==='ai'&&plans[0].parentId===b.id;
 if(!planned)throw Error('Merger not planned: '+JSON.stringify({safe:phase8MergerSettlementSafe(saved,b,t),active:isActiveCorporateFirm(t),business:phase8MergerBusinessCase(saved,b,t),equity:financials(t).equity,eligibility:(()=>{try{return siblingMergerEligibility(saved,b,t,b,'ai')}catch(e){return e.message}})()}));
 const once=phase8PlanWhollyOwnedMergers(saved,[]).length===0;
 const duration=plans[0].duration;
 for(let n=0;n<duration;n++){
  const month=ym(saved.year,saved.month)+1;saved.year=Math.floor(month/12);saved.month=month%12+1;
  saved.monthCommitted=month-1;applyWorldHistory(saved);processGroupMergers(saved,ev);
 }
 const b2=company(b.id,saved),t2=company(t.id,saved),plan=groupMergerPlans(saved).find(m=>m.id===plans[0].id);
 const completed=plan.status==='completed';
 if(!completed)throw Error('Merger incomplete: '+plan.issue);
 return {business,notPlayer,early,planned,once,completed,
  activeCount:saved.firms.filter(isActiveCorporateFirm).length===count-1,
  archive:t2.reorgStatus==='integrated'&&t2.integrationInto===b2.id,
  assetSuccession:acc(b2,'ppe')===assets&&acc(b2,'cash')===cash&&b2.staff.production===staff,
  preservedOwner:t2.owners[0].id===b2.id,
  saved:!check(parsePayload(savePayload(saved))).length,
  clean:!check(saved).length&&!consolidate(saved,b2.id).errors.length};
}""")
        assert len(merger)==12 and all(merger.values()),merger
        minority = page.evaluate("""()=>{const s=newWorldGame({country:'JP',name:'Minority merger scenario'}),buyer=initFirm(s,{name:'Parent',country:'JP',industry:'service',seedBase:2000000}),target=initFirm(s,{name:'Minority',country:'JP',industry:'service',seedBase:450000});syncWorldIdentities(s);ensureMAState(s);post(buyer,{cash:1000000000},{capital:1000000000},'検証用資本','financing',s);buyer.monthly.profit=20000;target.monthly.profit=100;executeMADeal(s,buyer.id,target.id,70,2.5,'ai');const pmi=s.maPlans.find(x=>x.buyer===buyer.id&&x.target===target.id);pmi.done=true;pmi.mode='completed';pmi.months=pmi.duration;pmi.progress=100;const before=JSON.stringify([buyer.owners,target.owners,buyer.ledger,target.ledger]),oldCash=acc(buyer,'cash')+acc(target,'cash'),oldAssets=acc(buyer,'ppe')+acc(target,'ppe'),q=phase8MinorityExchangeQuote(s,buyer,target),ev=[],plans=phase8PlanWhollyOwnedMergers(s,ev);if(plans.length!==1)throw Error('no plan');const plan=plans[0];const frozen=JSON.stringify([buyer.owners,target.owners,buyer.ledger,target.ledger])===before;const saved=parsePayload(savePayload(s));const altered=structuredClone(saved),tamper=altered.groupMergerPlans.find(x=>x.id===plan.id);tamper.exchange.newShares++;let bad=false;try{parsePayload(savePayload(altered))}catch(e){bad=true;}const blocked=structuredClone(saved),bt=company(target.id,blocked),bb=company(buyer.id,blocked);const changedBlock=bt.shareBlocks.find(x=>x.holding>0);changedBlock.reserve=2.6;const frozenBlocked=JSON.stringify([bb.owners,bt.owners,bb.ledger,bt.ledger]);const advance=(state)=>{for(let n=0;n<plan.duration;n++){const m=ym(state.year,state.month)+1;state.year=Math.floor(m/12);state.month=m%12+1;state.monthCommitted=m-1;applyWorldHistory(state);processGroupMergers(state,ev);}};advance(blocked);const blockedClean=blocked.groupMergerPlans.find(x=>x.id===plan.id).status==='blocked'&&JSON.stringify([company(buyer.id,blocked).owners,company(target.id,blocked).owners,company(buyer.id,blocked).ledger,company(target.id,blocked).ledger])===frozenBlocked;advance(saved);const b=company(buyer.id,saved),t=company(target.id,saved),done=saved.groupMergerPlans.find(x=>x.id===plan.id);const receiptTamper=structuredClone(saved);receiptTamper.groupMergerPlans.find(x=>x.id===plan.id).exchangeReceipt.newShares++;let receiptBad=false;try{parsePayload(savePayload(receiptTamper))}catch(e){receiptBad=true;}return {quote:phase8ExchangePlanValid(q,buyer.id)&&q.minorityShares===300000&&q.newShares>0,consent:q.allocations.every(a=>BigInt(a.newShares)*BigInt(q.buyerValue)*BigInt(q.targetRegistry.issued)*10000n>=BigInt(a.oldShares)*BigInt(q.targetValue)*BigInt(q.activeShares)*BigInt(q.premiumBps)),frozen,planStored:done.exchange.newShares===q.newShares,tamper:bad,completed:done.status==='completed',issued:b.shareRegistry.issued===q.postShares,receipt:done.exchangeReceipt?.newShares===q.newShares,minorityPreserved:q.allocations.every(a=>b.shareRegistry.external.find(x=>x.id===a.id).count===(q.buyerRegistry.external.find(x=>x.id===a.id)?.count??0)+a.newShares),noCashPayment:acc(b,'cash')===oldCash,assets:acc(b,'ppe')===oldAssets,archive:t.reorgStatus==='integrated'&&t.owners[0].id===b.id,clean:!check(saved).length&&!consolidate(saved,b.id).errors.length,restored:!check(parsePayload(savePayload(saved))).length,blockedClean,receiptTamper:receiptBad};}""")
        assert len(minority)==16 and all(minority.values()),minority
        print("Phase 8 minority exchange: 16/16 passed")
        browser.close()
    print(f"Phase 8 competitive quotes: {len(CASES)}/{len(CASES)} passed")

if __name__ == "__main__":
    main()
