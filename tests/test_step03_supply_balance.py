"""Supply balance diagnostics and production constraints."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"


def check_finite_market_policy(page):
    result = page.evaluate("""() => {
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'市場能力と障害'});
        const market=npcMarketV033(S,'JP','steel'),capacity=market.capacity;
        const normal=npcCapacityTargetV039(S,'JP','steel',1000);
        const american=npcCapacityTargetV039(S,'US','steel',1000);
        S.year=2010;
        const modern=npcCapacityTargetV039(S,'JP','steel',1000);
        S.config.difficulty='easy';
        const easy=npcCapacityTargetV039(S,'JP','steel',1000);
        S.config.difficulty='hard';
        const hard=npcCapacityTargetV039(S,'JP','steel',1000);
        S.year=1900;
        S.config.difficulty='normal';
        market.stock=0;market.dispatchedTotal=market.producedTotal;
        S.supplyRisk.active[npcIdV033('JP','steel')]={capacityFactor:.5,remaining:2};
        nextMonthDate(S);
        produceNpcV033(S,[]);
        const curtailed=market.lastProduced;
        market.lastRequested=capacity*2;
        market.lastShipped=curtailed;
        market.shortageStreak=2;
        const priorPrice=market.priceIndex;
        settleNpcMarketV033(S);
        const construction=market.construction[0];
        return {normal,american,modern,easy,hard,capacity,curtailed,priceIncreased:market.priceIndex>priorPrice,
            commissionedIn:construction.due-ym(S.year,S.month), errors:validateNpcV033(S)};
    }""")
    assert result["american"] > result["normal"] and result["modern"] > result["normal"], result
    assert result["easy"] > result["modern"] > result["hard"], result
    assert result["curtailed"] == result["capacity"] // 2, result
    assert result["priceIncreased"] and result["commissionedIn"] == 4 and not result["errors"], result


def check_financial_incentives(page):
    result = page.evaluate("""() => {
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'費用と競合判断'});
        const f=company(S.playerId,S), openingValue=acc(f,'materials'),openingCash=acc(f,'cash');
        inventoryInsuranceV039(S);
        const fee=openingCash-acc(f,'cash');
        const rival=S.firms.find(x=>x.industry==='auto'&&!x.player),model=rival.models[0];
        rival._produced=30;
        rival.monthly={units:30,sales:20000000,cogs:10000000,profit:1000000};
        const buy=expansionPaybackV039(S,rival,12000000);
        rival.monthly.units=3;
        const rejected=expansionPaybackV039(S,rival,12000000)===Infinity;
        rival.marketHistory=Array.from({length:3},()=>({markets:{
            [rival.country]:{models:{[model.id]:{units:2}}}
        }}));
        rival.goods[model.id]={q:28,v:0};
        planAILegacy(rival,S);
        const lowPlan=rival.plans[model.id];
        rival.goods[model.id]={q:0,v:0};
        planAILegacy(rival,S);
        const ordinaryPlan=rival.plans[model.id];
        const failingCash=acc(rival,'cash');
        post(rival,{otherExpense:failingCash},{cash:failingCash},'財務悪化の試験','operating',S);
        rival.distress={stage:3,months:4};
        competitorEvolution(S,[]);
        return {fee,ledger:acc(f,'materials')===openingValue,
            booked:f.journals.some(j=>j.text==='資材在庫の保険・管理費'&&j.amount===fee),
            buy,rejected,lowPlan,ordinaryPlan,withdrawn:rival.lifecycle.phase==='withdrawn',
            legalBooksKept:!!company(rival.id,S)&&rival.journals.length>0,errors:check(S)};
    }""")
    assert result["fee"] > 0 and result["ledger"] and result["booked"], result
    assert 0 < result["buy"] <= 60 and result["rejected"], result
    assert result["withdrawn"] and result["legalBooksKept"], result
    assert result["lowPlan"] < result["ordinaryPlan"] and not result["errors"], result


def run_maintenance_scenario(page, maintain):
    return page.evaluate("""async maintain => {
        saveAuto=async()=>true;
        S=newGame({era:1900,country:'JP',difficulty:'normal',
            history:'historical',name:'工場保全と生産実績'});
        VIEW_FIRM=S.playerId;
        const total={planned:0,produced:0,capacityGap:0,operatingGap:0,unfilled:0};
        for(let i=0;i<24;i++){
            const f=current();
            if(maintain&&i%6===0&&f.plants[0].condition<85){
                PAGE='factory';render();
                maintainPlant();
            }
            const previous=S.monthCommitted,beforeCogs=acc(f,'cogs');
            await runMonth();
            if(S.monthCommitted!==previous+1)throw Error(LAST_MONTH_DIAGNOSTIC?.message);
            const currentFirm=current(),row=currentFirm.supply.balanceHistoryV039.at(-1);
            if(row.month!==S.monthCommitted||currentFirm.monthly.cogs!==acc(currentFirm,'cogs')-beforeCogs)
                throw Error('月次実績と帳簿が一致しません');
            for(const key of Object.keys(total))total[key]+=row[key];
        }
        PAGE='supply';render();
        const restored=parsePayload(savePayload(S));
        return {...total,rows:company(restored.playerId,restored).supply.balanceHistoryV039.length,
            errors:check(restored)};
    }""", maintain)


if __name__ == "__main__":
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_page(offline=True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(HTML.read_text(encoding="utf-8"), wait_until="domcontentloaded")
        check_finite_market_policy(page)
        check_financial_incentives(page)
        unattended = run_maintenance_scenario(page, False)
        maintained = run_maintenance_scenario(page, True)
        for scenario in (unattended, maintained):
            assert scenario["planned"] - scenario["produced"] == (
                scenario["capacityGap"] + scenario["operatingGap"]
            ), scenario
            assert scenario["rows"] == 12 and not scenario["errors"], scenario
        assert unattended["capacityGap"] > maintained["capacityGap"], (unattended, maintained)
        assert unattended["produced"] < maintained["produced"], (unattended, maintained)
        page.get_by_text("生産未達と資材在庫の実績", exact=True).click()
        assert page.get_by_role("columnheader", name="能力上限内の未達", exact=True).is_visible()
        assert not errors, errors
        browser.close()
    print("PASS STEP 3: 24-month production diagnostics, cost of sales, maintenance and saves")
