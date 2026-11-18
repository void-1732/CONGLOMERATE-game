"""Check localized logistics and inventory reconciliation in long monthly runs."""

import os
import shutil
from pathlib import Path
from time import perf_counter

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"
SCENARIOS = (
    (1900, "normal", (24, 60, 120, 240), True),
    (1960, "hard", (24, 60), False),
    (2010, "easy", (24,), False),
)


def run_scenario(page, era, difficulty, checkpoints, many_sites):
    page.evaluate("""([era, difficulty, manySites]) => {
        saveAuto = async () => true;
        render = () => {};
        S = newGame({era,country:'JP',difficulty,history:'historical',name:'工場物流の長期検証'});
        VIEW_FIRM = S.playerId;
        const f=current(),plant=beginFactoryConstruction(S,f,'small','integrated','中京工場','JP-NGO');
        plant.construction=null;
        ensureFirmGameplay(f);
        const logistics=ensureWarehouseV038(f);
        openRawStorageV038(f);
        logistics.autoRefill=true;
        logistics.localizedRawTypes=[...RAW_TYPES_V032];
        if (manySites) {
            let total=S.firms.reduce((n,x)=>n+x.plants.length,0);
            const firms=S.firms.filter(x=>x.industry==='auto').slice(0,8);
            for (let i=0;total<100;i++,total++) {
                const owner=firms[i%firms.length];
                owner.plants.push({...owner.plants[0],id:'P'+S.seq++,name:'負荷検証拠点 '+i,
                    paused:true,capacity:7,assetTracked:0,componentLines:undefined});
                ensureFirmGameplay(owner);
            }
        }
    }""", [era, difficulty, many_sites])
    start = perf_counter()
    last = 0
    for checkpoint in checkpoints:
        for first in range(last, checkpoint, 12):
            result = page.evaluate("""async months => {
                for(let i=0;i<months;i++){
                    const previous=S.monthCommitted;
                    await runMonth();
                    if(S.monthCommitted!==previous+1)return {date:previous+1,diagnostic:LAST_MONTH_DIAGNOSTIC?.message};
                    const f=current(),view=inventoryLocationsV038(S,f);
                    const locations=[view.warehouse,...view.locations.values(),...view.otherWarehouses.values()];
                    const entries=locations.flatMap(x=>[...x.items.values()]);
                    for(const account of ['materials','componentStock','goods']){
                        const value=entries.filter(x=>x.account===account).reduce((n,x)=>n+x.value,0);
                        if(value!==acc(f,account))return {date:S.monthCommitted,account,value,book:acc(f,account)};
                    }
                }
                const restored=parsePayload(savePayload(S)),errors=check(restored);
                if(errors.length||restored.monthCommitted!==S.monthCommitted)return {errors};
                S=restored;
                return null;
            }""", min(12, checkpoint - first))
            assert result is None, (era, difficulty, first + 1, result)
        state = page.evaluate("""() => ({
            shipments:current().journals.filter(j=>j.text.startsWith('資材の国内検収')).length,
            sites:S.firms.reduce((n,f)=>n+f.plants.length,0),
            firms:S.firms.length
        })""")
        assert state["shipments"] > 0, (era, difficulty, checkpoint, state)
        if many_sites:
            assert state["sites"] >= 100 and state["firms"] >= 20, state
        print(f"PASS {era} {difficulty} {checkpoint} months, {state['sites']} sites, "
              f"{state['firms']} firms, {state['shipments']} domestic receipts, {perf_counter()-start:.1f}s",
              flush=True)
        last = checkpoint


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
        for scenario in SCENARIOS:
            run_scenario(page, *scenario)
        assert not errors, errors
        browser.close()
