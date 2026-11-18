"""v0.33 STEP 2: finite NPC supply, deterministic fair shares, accounting, persistence."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")

def run():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
        page=browser.new_page()
        faults=[]
        page.on("pageerror",lambda error:faults.append(str(error)))
        page.set_content(HTML,wait_until="domcontentloaded")
        starting=page.evaluate("""() => {
          const s=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'NPC初期在庫'});
          const m=npcMarketV033(s,'JP','steel'),before=m.stock;
          const produced=m.producedTotal;
          produceNpcV033(s,[]);
          return {before,after:m.stock,produced:m.producedTotal,errors:check(s)};
        }""")
        assert starting['before']>0 and starting['after']==starting['before'],starting
        assert starting['produced']==starting['after'] and not starting['errors'],starting

        deterministic=page.evaluate("""() => {
          const allocate=(requests,cap)=>fairAllocationV033(requests,cap);
          const sample=[{id:'F1:steel',need:80},{id:'F2:steel',need:20},{id:'F3:steel',need:40}];
          return {normal:allocate(sample,90),reverse:allocate([...sample].reverse(),90),none:allocate(sample,0)};
        }""")
        assert deterministic["normal"]==deterministic["reverse"],deterministic
        assert sum(deterministic["normal"].values())==90,deterministic
        assert deterministic["none"]=={},deterministic

        # Two automakers compete for the same 15 physical units. Reversing
        # s.firms must not change each firm ID's supply allocation.
        race=page.evaluate("""() => {
          const build=()=>{
            const s=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'公平配分'});
            ensureV20(s);
            const eligible=s.firms.filter(f=>f.country==='JP'&&['auto','manufacturing'].includes(f.industry)).slice(0,2);
            if(eligible.length!==2)throw Error('国内製造法人が不足');
            produceNpcV033(s,[]);
            const m=npcMarketV033(s,'JP','steel');
            m.stock=15;m.producedTotal=m.dispatchedTotal+15;
            for(const f of eligible)for(const item of f.models.filter(x=>x.status==='active'))f.plans[item.id]=100;
            return {s,ids:eligible.map(f=>f.id)};
          };
          const perform=reverse=>{
            const {s,ids}=build();
            if(reverse)s.firms.reverse();
            procureNetwork(s,[]);
            const m=npcMarketV033(s,'JP','steel');
            return {alloc:Object.fromEntries(ids.map(id=>[id,company(id,s).supply.lastAttempt.steel.npcOrdered])),
              stock:m.stock,physical:m.producedTotal-m.dispatchedTotal,errors:check(s),
              receipt:ids.map(id=>company(id,s).supply.history.filter(h=>h.type==='steel').reduce((n,h)=>n+h.qty,0))};
          };
          return {a:perform(false),b:perform(true)};
        }""")
        assert race["a"]["alloc"]==race["b"]["alloc"],race
        assert 0<=sum(race["a"]["alloc"].values())<=15,race
        for run_result in race.values():
            assert run_result["stock"]==run_result["physical"]>=0,run_result
            assert not run_result["errors"],run_result

        # A sustained market shortfall must raise the price and place a
        # physical, delayed investment project rather than mint supply.
        shortage=page.evaluate("""() => {
          const s=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'資源需給テスト'});
          const m=npcMarketV033(s,'JP','steel');
          m.capacity=5;m.stock=0;m.producedTotal=m.dispatchedTotal;m.lastDemand=200;
          const initial=m.priceIndex;
          for(let month=1;month<=3;month++){
            s.month=month;m.lastRequested=150;m.lastShipped=1;
            settleNpcMarketV033(s);
          }
          const planned=m.construction[0],price=m.priceIndex,before=m.capacity;
          if(!planned)throw Error('継続的な供給不足でも設備投資計画が生まれない');
          s.month=planned.due%12+1;s.year=Math.floor(planned.due/12);
          produceNpcV033(s,[]);
          return {initial,price,before,after:m.capacity,due:planned.due,errors:validateNpcV033(s)};
        }""")
        assert shortage["price"]>shortage["initial"],shortage
        assert shortage["after"]>shortage["before"] and not shortage["errors"],shortage

        # Spot purchases are real shipments from the same finite regional
        # inventory and must not create units out of nothing.
        spot=page.evaluate("""() => {
          S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'緊急調達'});
          produceNpcV033(S,[]);
          VIEW_FIRM=S.playerId;PAGE='supply';render();
          const f=company(S.playerId,S),m=npcMarketV033(S,f.country,'steel');
          const original={market:m.stock,dispatched:m.dispatchedTotal,buyer:f.stock.steel.q,book:acc(f,'materials')};
          document.getElementById('spotResourceV026').value='steel';
          document.getElementById('spotQtyV026').value='3';
          window.confirm=()=>true;
          buySpotV026();
          return {before:original,market:m.stock,dispatched:m.dispatchedTotal,
            buyer:f.stock.steel.q,book:acc(f,'materials'),errors:check(S)};
        }""")
        assert spot["market"]==spot["before"]["market"]-3,spot
        assert spot["dispatched"]==spot["before"]["dispatched"]+3,spot
        assert spot["buyer"]==spot["before"]["buyer"]+3,spot
        assert spot["book"]>spot["before"]["book"] and not spot["errors"],spot

        page.evaluate("""() => {
          saveAuto=async()=>true;
          S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'NPC長期検証'});
        }""")
        results=[]
        for i in range(24):
            res=page.evaluate("""async()=> {
              const before=S.monthCommitted;
              await runMonth();
              const npc=ensureNpcV033(S),g=consolidate(S);
              return {advanced:S.monthCommitted===before+1,errors:check(S),group:g.errors,
                cf:g.cf.reconciled,why:LAST_MONTH_DIAGNOSTIC?.message,
                markets:Object.values(npc.markets).reduce((n,c)=>n+Object.values(c).length,0),
                delivered:Object.values(npc.markets).reduce((n,c)=>n+Object.values(c).reduce((a,m)=>a+m.dispatchedTotal,0),0),
                maxPrice:Math.max(...Object.values(npc.markets).flatMap(x=>Object.values(x).map(m=>m.priceIndex))),
                minimumStock:Math.min(...Object.values(npc.markets).flatMap(x=>Object.values(x).map(m=>m.stock)))};
            }""")
            assert res["advanced"] and not res["errors"] and not res["group"] and res["cf"],(i,res)
            assert res["markets"]>0 and res["minimumStock"]>=0,(i,res)
            results.append(res)
        assert results[-1]["delivered"]>0,results[-1]
        snapshot=page.evaluate("savePayload(S)")
        assert page.evaluate("raw=>restore(raw)",snapshot)
        assert not page.evaluate("check(S)")
        assert not faults,faults
        browser.close()

if __name__=="__main__":
    run()
    print("PASS v0.33: finite NPC ledger, fair allocation, 24-month books and saves")
