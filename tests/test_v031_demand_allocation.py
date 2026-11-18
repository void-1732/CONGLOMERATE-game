"""CONGLOMERATE v0.31: demand substitution, regional caps, persistence, and regression."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.set_content(HTML, wait_until="domcontentloaded")
        page.evaluate("""() => {
            saveAuto=async()=>true;
            S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'需要配分検証'});
            VIEW_FIRM=S.playerId;
            PAGE='marketRegion';
        }""")
        # Exercise the actual allocator with two deliberately constructed firms.
        allocation = page.evaluate("""() => {
            const old={sellGoods,exportShipment,segmentCompatibility,exportChannel,enterpriseSynergy};
            try{
                sellGoods=(s,f,id,q)=>{f.goods[id].q-=q;f.sold=(f.sold||0)+q};
                exportShipment=sellGoods;
                segmentCompatibility=(f,m)=>m.score;
                exportChannel=f=>({capacity:f.capacity});
                enterpriseSynergy=()=>({distributionBoost:0});
                const simulate=(demand,aStock,bStock,aCapacity=100,bCapacity=100)=>{
                    const f={id:'A',country:'JP',capacity:aCapacity,goods:{a:{q:aStock}},_shipmentsThisMonth:{}};
                    const g={id:'B',country:'JP',capacity:bCapacity,goods:{b:{q:bStock}},_shipmentsThisMonth:{}};
                    const state={year:1900,month:1},candidates=[
                        {f,m:{id:'a',score:6,priceBase:1}},
                        {f:g,m:{id:'b',score:4,priceBase:1}}
                    ];
                    const out=distributeSegmentV031(state,'JP','mass',demand,candidates,[]);
                    return {a:f.sold||0,b:g.sold||0,out,stocks:[f.goods.a.q,g.goods.b.q]};
                };
                return [
                    simulate(100,20,80),
                    simulate(100,0,30),
                    simulate(100,120,120),
                    simulate(100,20,80,10,50),
                    simulate(0,10,10)
                ];
            }finally{
                Object.assign(window,old);
            }
        }""")
        assert (allocation[0]["a"], allocation[0]["b"]) == (20, 80), allocation
        assert allocation[0]["out"]["reassigned"] == 40, allocation
        assert allocation[1]["out"]["unmet"] == 70, allocation
        assert allocation[2]["out"]["unmet"] == 0, allocation
        assert allocation[3]["a"] <= 10 and allocation[3]["b"] <= 50, allocation
        for item, demand in zip(allocation, [100, 100, 100, 100, 0]):
            assert item["a"] + item["b"] + item["out"]["unmet"] == demand, item
            assert min(item["stocks"]) >= 0, item

        # Run actual month closes; demand ledgers, books, and CF must reconcile.
        for i in range(12):
            result = page.evaluate("""async()=> {
                const before=S.monthCommitted;
                await runMonth();
                const g=consolidate(S);
                const allocations=Object.values(S.marketAllocationV031||{});
                return {
                    advanced:S.monthCommitted===before+1,
                    errs:check(S), group:g.errors, cf:g.cf.reconciled,
                    allocations:allocations.map(x=>({
                        demand:x.demand,
                        assigned:x.initial+x.reassigned+(x.delivered||0)+x.unmet
                    })),
                    diagnostic:LAST_MONTH_DIAGNOSTIC?.message
                };
            }""")
            assert result["advanced"] and not result["errs"] and not result["group"] and result["cf"], (i, result)
            assert result["allocations"] and all(
                x["demand"] == x["assigned"] for x in result["allocations"]
            ), (i, result)

        page.evaluate("() => {PAGE='marketRegion';VIEW_COUNTRY='JP';render()}")
        assert page.get_by_text("v0.31 月間需要の再配分", exact=True).is_visible()
        snapshot = page.evaluate("savePayload(S)")
        assert page.evaluate("raw=>restore(raw)", snapshot)
        assert not page.evaluate("check(S)")
        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    run()
    print("PASS v0.31: allocation, inventory, channels, monthly closes, books, UI and saved state")
