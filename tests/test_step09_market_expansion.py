"""STEP 9 / step 03: optional market catalog, migration and accounting regression.

New markets are observation-only until the cross-border settlement and entry
gates are implemented in steps 04-05. All cases run in the real offline browser.
"""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"


def catalog_and_new_game(page):
    result = page.evaluate("""() => {
        const errs=validateMarketCatalogV047();
        const cases=[];
        for (const year of [1900,1960,2010]) {
            const cfg={era:year,country:'JP',difficulty:'normal',history:'historical',
                name:'8市場カタログ検証'};
            const standard=newGame(cfg),expanded=newGame({...cfg,marketExpansionV047:true});
            const legacyKeys=Object.keys(standard.world),expandedKeys=Object.keys(expanded.world);
            const fx=EMERGING_MARKETS_V047.map(code=>({
                country:code,currency:COUNTRIES[code].currency,
                worldFx:expanded.world[code].fx,
                sites:INDUSTRIAL_SITES[code].length,
                ports:TRADE_GEOGRAPHY_V041[code].ports,
                siteCountry:homeSite(code).country,
                rate:currencyRatioV042(expanded,expanded.firms[0],COUNTRIES[code].currency),
                initialNpc:npcMarketV033(expanded,code,'steel'),
                maturity:worldDevelopmentV046(expanded,code)
            }));
            const codes=Object.keys(expanded.world),routes=codes.flatMap(a=>
                codes.filter(b=>a!==b).map(b=>internationalRoutesV041(expanded,a,b)));
            let countryBlocked=false;
            try { newGame({...cfg,country:'CN',marketExpansionV047:true}); }
            catch(e){countryBlocked=true;}
            const stateErrors=check(expanded),financial=consolidate(expanded);
            const saved=parsePayload(savePayload(expanded));
            cases.push({year,legacyKeys,expandedKeys,fx,
                routeCount:routes.length,missingRoute:routes.some(r=>r.length<2),
                sellerCount:expanded.firms.filter(f=>EMERGING_MARKETS_V047.includes(f.country)).length,
                countryBlocked,permission:marketInvestmentAllowedV043(
                    expanded,expanded.firms.find(f=>f.player),'CN'),
                trade:internationalTradeAllowedV041(expanded,'JP','CN','vehicle'),
                serialization:saved.marketExpansionV047,
                savedKeys:Object.keys(saved.world),
                errors:stateErrors,financialErrors:financial.errors,
                reconciled:financial.cf.reconciled,
                legacyReconciled:consolidate(standard).cf.reconciled});
        }
        return {catalogErrors:errs,cases};
    }""")
    assert not result["catalogErrors"], result
    for item in result["cases"]:
        assert item["legacyKeys"] == ["JP", "US", "UK", "DE", "FR"], item
        assert item["expandedKeys"] == ["JP","US","UK","DE","FR","CN","IN","BR"], item
        assert item["savedKeys"] == item["expandedKeys"], item
        assert item["routeCount"] == 56 and not item["missingRoute"], item
        assert not item["sellerCount"] and item["countryBlocked"], item
        assert not item["permission"], item
        assert item["trade"] == (item["year"] >= 1980), item
        assert item["serialization"]["enabled"], item
        assert not item["errors"] and not item["financialErrors"], item
        assert item["reconciled"] == item["legacyReconciled"], item
        for market in item["fx"]:
            assert market["worldFx"] > 0 and market["rate"] > 0, market
            assert market["sites"] >= 3 and market["siteCountry"] == market["country"], market
            assert market["initialNpc"]["stock"] + market["initialNpc"]["dispatchedTotal"] == market["initialNpc"]["producedTotal"], market
            assert market["maturity"]["factor"] == 1, market


def legacy_migration(page):
    result=page.evaluate("""() => {
        const cfg={era:1980,country:'JP',difficulty:'normal',history:'historical',
            name:'既存5市場の変換テスト'};
        const s=newGame(cfg);
        const root=s.firms.find(f=>f.id===s.playerId);
        s.worldEvolutionV046={enabled:true,anchorYear:1980};
        const before={
            world:structuredClone(s.world),firms:structuredClone(s.firms),
            shipment:structuredClone(s.logisticsV041),rng:s.rng,
            npc:structuredClone(s.npcSupplyV033.markets),
            conso:structuredClone(s.consoHistory),
            oldNodes:s.supplyNetwork.nodes.filter(n=>LEGACY_MARKETS_V047.includes(n.country))
        };
        const changed=activateEmergingMarketsV047(s);
        const second=activateEmergingMarketsV047(changed);
        const firm=changed.firms.find(f=>f.id===root.id);
        const newWorld=EMERGING_MARKETS_V047.map(code=>({
            code,anchor:changed.marketExpansionV047.anchorYear,
            developed:worldDevelopmentV046(changed,code),
            npc:npcMarketV033(changed,code,'steel'),
            channel:firm.distribution.contracts[code],
            sites:TRADE_GEOGRAPHY_V041[code].ports
        }));
        const oldChannelsEqual=s.firms.every((f,i)=>LEGACY_MARKETS_V047.every(code=>
            JSON.stringify(f.distribution.contracts[code])===
            JSON.stringify(changed.firms[i].distribution.contracts[code])));
        const stable={
            sameOriginal:!s.marketExpansionV047&&Object.keys(s.world).length===5,
            sameLegacyWorld:JSON.stringify(before.world)===
                JSON.stringify(Object.fromEntries(LEGACY_MARKETS_V047.map(c=>[c,changed.world[c]]))),
            sameFinance:s.firms.every((f,i)=>
                JSON.stringify(f.ledger)===JSON.stringify(changed.firms[i].ledger)&&
                JSON.stringify(f.stock)===JSON.stringify(changed.firms[i].stock)&&
                JSON.stringify(f.goods)===JSON.stringify(changed.firms[i].goods)&&
                JSON.stringify(f.journals)===JSON.stringify(changed.firms[i].journals)&&
                JSON.stringify(f.supply.inbound)===JSON.stringify(changed.firms[i].supply.inbound)&&
                JSON.stringify(f.distribution.outbound)===JSON.stringify(changed.firms[i].distribution.outbound)),
            oldChannelsEqual,
            sameLogistics:JSON.stringify(before.shipment)===JSON.stringify(changed.logisticsV041),
            sameRng:changed.rng===before.rng,
            sameHistory:JSON.stringify(before.conso)===JSON.stringify(changed.consoHistory),
            sameExistingNPC:LEGACY_MARKETS_V047.every(c=>
                JSON.stringify(before.npc[c])===JSON.stringify(changed.npcSupplyV033.markets[c])),
            idempotent:changed===second,
            errors:check(changed),
            savedKeys:Object.keys(parsePayload(savePayload(changed)).world),
            oldKeyCount:Object.keys(parsePayload(savePayload(s)).world).length,
            newWorld
        };
        const invalids=[];
        const invalid=structuredClone(changed);
        delete invalid.world.BR;
        invalids.push(validateMarketExpansionV047(invalid));
        const missingFlag=structuredClone(changed);
        delete missingFlag.marketExpansionV047;
        invalids.push(validateMarketExpansionV047(missingFlag));
        const partial=structuredClone(s);
        partial.marketExpansionV047={enabled:true,anchorYear:partial.year,
            activatedAt:ym(partial.year,partial.month)};
        invalids.push(validateMarketExpansionV047(partial));
        stable.invalids=invalids;
        return stable;
    }""")
    for k in ["sameOriginal","sameLegacyWorld","sameFinance","oldChannelsEqual",
              "sameLogistics","sameRng","sameHistory","sameExistingNPC","idempotent"]:
        assert result[k], (k,result)
    assert result["oldKeyCount"] == 5 and len(result["savedKeys"]) == 8, result
    assert not result["errors"],result
    assert all(result["invalids"]),result
    for x in result["newWorld"]:
        assert x["anchor"] == 1980 and x["developed"]["factor"] == 1, x
        assert x["npc"]["stock"] == x["npc"]["producedTotal"] == 0, x
        assert x["channel"]["capacity"] > 0 and len(x["sites"]) >= 2, x


def ui_and_months(page):
    page.evaluate("""() => {
        S=newGame({era:1980,country:'JP',difficulty:'normal',history:'historical',
            name:'新興市場UIと月次'});
        VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='marketRegion';render();
    }""")
    assert page.get_by_role("heading",name="新興国・地域市場（STEP 9）").is_visible()
    button=page.get_by_role("button",name="中国・インド・ブラジルを市場観測に追加")
    assert button.is_visible()
    button.click()
    result=page.evaluate("""() => ({
        keys:Object.keys(S.world),expansion:S.marketExpansionV047,
        errors:check(S),saved:parsePayload(savePayload(S)).marketExpansionV047
    })""")
    assert result["keys"] == ["JP","US","UK","DE","FR","CN","IN","BR"],result
    assert result["expansion"] == result["saved"] and not result["errors"],result
    assert page.get_by_text("直接輸出・原材料輸入可能").count() == 3

    months=page.evaluate("""async() => {
        saveAuto=async()=>true;render=()=>{};
        const start=ym(S.year,S.month);
        for(let i=0;i<12;i++){
            const old=S.monthCommitted;
            await runMonth();
            if(S.monthCommitted!==old+1)
                return {failed:i,reason:LAST_MONTH_DIAGNOSTIC?.message};
            const errors=check(S),financial=consolidate(S);
            if(errors.length||financial.errors.length||!financial.cf.reconciled)
                return {failed:i,errors,financialErrors:financial.errors};
            if(EMERGING_MARKETS_V047.some(code=>S.firms.some(f=>f.country===code)))
                return {failed:i,reason:'premature competitor creation'};
        }
        return {months:ym(S.year,S.month)-start,
            errors:check(S),markets:Object.keys(S.world).length,
            saved:parsePayload(savePayload(S)).marketExpansionV047};
    }""")
    assert months.get("months") == 12 and months["markets"] == 8,months
    assert months["saved"]["enabled"] and not months["errors"],months


if __name__=="__main__":
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"])
        page=browser.new_page(offline=True)
        errors=[]
        page.on("pageerror",lambda e: errors.append(str(e)))
        page.set_content(HTML.read_text(encoding="utf-8"),wait_until="domcontentloaded")
        catalog_and_new_game(page)
        legacy_migration(page)
        page.goto("about:blank")
        page.set_content(HTML.read_text(encoding="utf-8"),wait_until="domcontentloaded")
        ui_and_months(page)
        assert not errors,errors
        browser.close()
    print("PASS STEP 9 new market foundations: eight catalog entries, atomic migration, UI, twelve months and ledger reconciliation")
