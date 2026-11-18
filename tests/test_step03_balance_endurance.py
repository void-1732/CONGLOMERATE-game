"""Exercise maintenance, inventory and demand shocks across eras and difficulties."""

import json
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"
SCENARIOS = (
    (1900, "JP", "normal", "maintained", (24, 60, 120, 240)),
    (1960, "DE", "hard", "buffered", (24, 60)),
    (2010, "US", "easy", "lean", (24,)),
    (1960, "DE", "hard", "recession", (24,)),
)


def run_scenario(page, era, country, difficulty, policy, checkpoints):
    page.evaluate("""([era,country,difficulty,policy]) => {
        saveAuto=async()=>true;
        render=()=>{};
        S=newGame({era,country,difficulty,history:'historical',name:'供給網の長期検証'});
        VIEW_FIRM=S.playerId;
        const months=policy==='lean'?.25:policy==='maintained'?.5:1.5;
        for(const c of Object.values(current().supply.contracts))c.safetyMonths=months;
        return null;
    }""", [era, country, difficulty, policy])
    summary = dict(planned=0, produced=0, capacityGap=0, operatingGap=0, unfilled=0,
                   revenue=0, profit=0, inventory=0, insurance=0, unsold=0)
    last = 0
    at_24 = None
    for checkpoint in checkpoints:
        for start in range(last, checkpoint, 12):
            count = min(12, checkpoint - start)
            result = page.evaluate("""async ([start,count,policy]) => {
                const total={planned:0,produced:0,capacityGap:0,operatingGap:0,unfilled:0,
                    revenue:0,profit:0,inventory:0,insurance:0,unsold:0};
                for(let i=start;i<start+count;i++){
                    const company=current(),country=company.country,plant=company.plants[0];
                    if(plant.condition<85&&i%6===0){
                        const cost=localFromBase((2000+plant.capacity*95)*eraCostFactor(S.year),country);
                        if(acc(company,'cash')>=cost){
                            post(company,{maintenance:cost},{cash:cost},'基準ケースの工場定期保全','operating',S);
                            plant.condition=Math.min(100,plant.condition+18);
                            syncPlant(company);
                        }
                    }
                    if(policy==='recession'&&i>=4&&i<16){
                        S.world[country].cycle=-.18;
                        S.world[country].demand=Math.max(10,Math.floor(S.world[country].demand*.55));
                        for(const t of ['steel','rubber','components']){
                            const id=npcIdV033(country,t);
                            S.supplyRisk.active[id]={type:t,country,supplierName:'試験シナリオの市場',
                                reason:'景気後退と操業停止',capacityFactor:.35,pricePct:.22,delay:2,remaining:3};
                        }
                    }
                    const previous=S.monthCommitted;
                    await runMonth();
                    if(S.monthCommitted!==previous+1)return {failedAt:previous+1,reason:LAST_MONTH_DIAGNOSTIC?.message};
                    const f=current(),row=f.supply.balanceHistoryV039.at(-1);
                    for(const key of ['planned','produced','capacityGap','operatingGap','unfilled','inventory','insurance'])
                        total[key]+=row[key];
                    total.revenue+=f.monthly.sales;
                    total.profit+=f.monthly.profit;
                    total.unsold+=Math.max(0,row.produced-f.monthly.units);
                }
                const snapshot=parsePayload(savePayload(S));
                const errors=check(snapshot);
                if(errors.length)return {errors};
                S=snapshot;
                return {total};
            }""", [start, count, policy])
            assert "total" in result, (era, country, difficulty, policy, start + 1, result)
            for key, amount in result["total"].items():
                summary[key] += amount
        observed = {
            "era": era, "country": country, "difficulty": difficulty, "policy": policy,
            "months": checkpoint, **summary,
            "productionRate": round(summary["produced"] / max(1, summary["planned"]), 4),
            "profitMargin": round(summary["profit"] / max(1, summary["revenue"]), 4),
            "averageInventory": round(summary["inventory"] / checkpoint),
        }
        assert summary["planned"] - summary["produced"] == (
            summary["capacityGap"] + summary["operatingGap"]
        ), observed
        assert summary["insurance"] > 0 and summary["inventory"] > 0, observed
        if checkpoint == 24:
            at_24 = observed
        print(json.dumps(observed, ensure_ascii=False), flush=True)
        last = checkpoint
    return at_24


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
        scenarios = {scenario[3]: run_scenario(page, *scenario) for scenario in SCENARIOS}
        assert scenarios["recession"]["productionRate"] < scenarios["buffered"]["productionRate"], scenarios
        assert scenarios["recession"]["unfilled"] > scenarios["buffered"]["unfilled"], scenarios
        assert not errors, errors
        browser.close()
