"""STEP 9 / Step 02: preserve the original five-market contracts before regional expansion.

This intentionally tests the currently active markets, not proposed CN/IN/BR gameplay.
When Step 03 adds markets, these invariants must hold for every active country.
"""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"


def audit_market_foundations(page):
    return page.evaluate("""() => {
        const result = [];
        for (const era of [1900, 1960, 2010]) {
            const s = newGame({
                era, country: 'JP', difficulty: 'normal',
                history: 'historical', name: '国際市場互換性監査'
            });
            const codes = Object.keys(s.world);
            const mandatory = ['JP', 'US', 'UK', 'DE', 'FR'];
            const routes = [], inconsistencies = [];
            const seenCurrencies = new Set();
            for (const country of codes) {
                const definition = COUNTRIES[country];
                const meta = TRADE_GEOGRAPHY_V041[country];
                if (!definition || !NAMES[country] || !meta ||
                    !Array.isArray(meta.ports) || meta.ports.length < 2 ||
                    !Number.isFinite(s.world[country]?.fx) ||
                    !Number.isFinite(s.world[country]?.demand) ||
                    !Number.isFinite(MARKET_TAX_V043[country]) ||
                    !homeSite(country) || homeSite(country).country !== country)
                    inconsistencies.push('country metadata: ' + country);
                if (seenCurrencies.has(definition?.currency))
                    inconsistencies.push('duplicate currency: ' + country);
                seenCurrencies.add(definition?.currency);
                const snapshot = marketDemandSnapshotV031(s, country);
                if (!Number.isSafeInteger(snapshot.demand) || snapshot.demand < 0 ||
                    Object.values(snapshot.segments).reduce((a,b) => a+b,0) !== snapshot.demand)
                    inconsistencies.push('segment allocation: ' + country);
                for (const other of codes) {
                    if (country === other) continue;
                    const possibilities = internationalRoutesV041(s, country, other);
                    routes.push(country + '/' + other);
                    if (possibilities.length < 2 ||
                        possibilities.some(x => !x.id || !x.months || !x.capacity))
                        inconsistencies.push('route: '+country+'/'+other);
                    for (const cargo of ['bulk','parts','vehicle']) {
                        const quote = internationalQuoteV041(s, country, other, cargo, 100);
                        if (!quote || quote.room < 1)
                            inconsistencies.push('quote: '+country+'/'+other+'/'+cargo);
                    }
                }
                const market = npcMarketV033(s, country, 'steel');
                if (!market || market.stock + market.dispatchedTotal !== market.producedTotal)
                    inconsistencies.push('NPC stock: '+country);
            }

            const seller = s.firms.find(f => f.id === s.playerId);
            const legacy = structuredClone(s);
            delete legacy.worldEvolutionV046;
            delete seller.globalSupplyPolicyV045;
            const recovered = parsePayload(savePayload(legacy));
            const restoredFirm = recovered.firms.find(f => f.id === recovered.playerId);
            const oldCountries = Object.keys(recovered.world);
            if (JSON.stringify(oldCountries) !== JSON.stringify(codes) ||
                JSON.stringify(recovered.world) !== JSON.stringify(legacy.world) ||
                restoredFirm.globalSupplyPolicyV045 !== undefined ||
                worldDevelopmentV046(recovered,'JP').factor !== 1)
                inconsistencies.push('legacy save migration');
            if (!mandatory.every(code => codes.includes(code)))
                inconsistencies.push('original country lost');
            const currency = 'USD';
            if (currencyMarketV042(currency) !== 'US' ||
                !(currencyRatioV042(s, seller, currency) > 0))
                inconsistencies.push('foreign currency mapping');
            const stateErrors=check(s),saveErrors=check(recovered);
            if (stateErrors.length || saveErrors.length)
                inconsistencies.push('ledger or inventory: '+JSON.stringify([...stateErrors,...saveErrors]));
            result.push({era,marketCount:codes.length,routeCount:routes.length,
                errors:inconsistencies});
        }
        return result;
    }""")


if __name__ == "__main__":
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_page(offline=True)
        page.set_content(HTML.read_text(encoding="utf-8"), wait_until="domcontentloaded")
        results = audit_market_foundations(page)
        for result in results:
            assert result["marketCount"] >= 5, result
            assert result["routeCount"] == result["marketCount"] * (result["marketCount"] - 1), result
            assert not result["errors"], result
        browser.close()
    print("PASS STEP 9 market-readiness: 1900/1960/2010 global routes, currencies, NPC stock, segments and legacy saves")
