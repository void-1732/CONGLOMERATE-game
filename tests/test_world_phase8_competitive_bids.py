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
          return {quantity:quantity===400000,control:controller(s,target.id,buyer.id),
            exact:target.shareRegistry.owners.find(o=>o.id===buyer.id).count===700000,
            payment:cash-acc(buyer,'cash')===localFromBase(quote.total,buyer.country,s),
            deal:deal.actor==='ai'&&deal.control===true,
            restored:controller(restored,target.id,buyer.id)&&!check(restored).length,
            clean:!check(s).length};
        }""")
        assert len(staged)==7 and all(staged.values()),staged
        print("Phase 8 staged AI acquisition, settlement and save: 7/7 passed")
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
        browser.close()
    print(f"Phase 8 competitive quotes: {len(CASES)}/{len(CASES)} passed")

if __name__ == "__main__":
    main()
