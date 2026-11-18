"""Supply balance diagnostics and production constraints."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"


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
