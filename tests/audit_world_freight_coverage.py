"""Run the Phase 4 browser cases and require actual receipts on all sourced routes."""

import json

import test_world_phase4_corridors
import test_world_phase4_credit
import test_world_phase4_international
import test_world_phase4_markets
import test_world_phase4_transshipment


def main():
    expected_markets = set()
    expected_routes = set()
    expected_countries = set()
    receipts = set()
    prefix = "WORLD_FREIGHT_RECEIPT "

    def observe(page):
        catalog = page.evaluate("""() => ({
          markets: WORLD_MARKETS.map(m=>m.id),
          routes: Object.keys(WORLD_INTERNATIONAL_ROUTE_EVIDENCE),
          countries: Object.keys(WORLD_ENGINE_TERRITORY)
        })""")
        expected_markets.update(catalog["markets"])
        expected_routes.update(catalog["routes"])
        expected_countries.update(catalog["countries"])

        def record(message):
            if message.text.startswith(prefix):
                receipts.add(tuple(json.loads(message.text[len(prefix):])))

        page.on("console", record)
        page.evaluate("""prefix => {
          const receive=worldInternationalReceiveShipments;
          const market=code=>WORLD_TERRITORIES.get(WORLD_ENGINE_TERRITORY[code]).marketId;
          worldInternationalReceiveShipments=function(state,events){
            const shipments=state.worldExpansion?.internationalShipments??[];
            const delivered=new Set(shipments.filter(t=>t.status==='DELIVERED').map(t=>t.id));
            receive(state,events);
            for(const t of shipments){
              if(t.status!=='DELIVERED'||delivered.has(t.id))continue;
              const profile=state.worldExpansion.internationalRoutes[t.routeId].profileId;
              const seller=company(t.sellerId,state).country,buyer=company(t.buyerId,state).country;
              console.log(prefix+JSON.stringify([profile,seller,buyer,market(seller),market(buyer)]));
            }
          };
        }""", prefix)

    for test in (
        test_world_phase4_international,
        test_world_phase4_credit,
        test_world_phase4_corridors,
        test_world_phase4_markets,
        test_world_phase4_transshipment,
    ):
        test.main(observe_receipts=observe)

    markets = {market for _, _, _, seller, buyer in receipts for market in (seller, buyer)}
    routes = {receipt[0] for receipt in receipts}
    countries = {code for _, seller, buyer, _, _ in receipts for code in (seller, buyer)}
    assert countries == expected_countries, {
        "missingJurisdictions": sorted(expected_countries - countries),
        "unexpectedJurisdictions": sorted(countries - expected_countries),
    }
    assert len(expected_markets) == 40 and markets == expected_markets, {
        "missingMarkets": sorted(expected_markets - markets),
        "unexpectedMarkets": sorted(markets - expected_markets),
    }
    assert routes == expected_routes, {
        "missingRoutes": sorted(expected_routes - routes),
        "unexpectedRoutes": sorted(routes - expected_routes),
    }
    print("PASS world freight coverage", json.dumps({
        "markets": sorted(markets),
        "marketCount": len(markets),
        "routeCount": len(routes),
        "engineJurisdictionCount": len(countries),
        "receivedRoutes": sorted(receipts),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
