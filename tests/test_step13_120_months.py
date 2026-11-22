"""STEP13: 120 month full-engine stress, growth, saved state and UI after growth."""
import argparse
import json
import os
import shutil
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")

def run(era):
    with sync_playwright() as pw:
        browser=pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE")
                or shutil.which("chromium") or None,args=["--no-sandbox"])
        page=browser.new_page(viewport={"width":1440,"height":900})
        page.set_default_timeout(30000)
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        started=time.monotonic()
        try:
            page.set_content(HTML,wait_until="domcontentloaded")
            first=page.evaluate("""era=>{
                window.__longNativeRender=render;
                saveAuto=async()=>true;
                S=newGame({era,country:'JP',difficulty:'easy',
                    history:'historical',name:'STEP13長期検証'});
                VIEW_FIRM=S.playerId;PAGE='facilityExpansion';render();
                return {firms:S.firms.length,plants:S.firms.reduce(
                  (n,f)=>n+(f.plants||[]).length,0),
                  cash:acc(current(),'cash'),errors:check(S)};
            }""",era)
            assert first["errors"] == []
            page.locator("#factoryName").fill("STEP13新工場")
            page.locator("#factoryKind").select_option("engine")
            page.locator("#factoryScale").select_option("small")
            page.locator('[data-action="factoryBuild"]').click()
            extra=page.evaluate("""()=>{
                const p=current().plants.find(x=>x.name==='STEP13新工場');
                return {plants:S.firms.reduce((n,f)=>n+(f.plants||[]).length,0),
                        cash:acc(current(),'cash'),construction:p?.construction?.monthsLeft,
                        errors:check(S)};
            }""")
            assert extra["plants"]==first["plants"]+1 and extra["construction"]>0
            assert extra["cash"]<first["cash"] and extra["errors"]==[]
            page.evaluate("()=>{render=()=>{};saveAuto=async()=>true;}")
            max_batch=0
            checkpoint=None
            for month in range(12,121,12):
                tick=time.monotonic()
                progress=page.evaluate("""async()=>{
                    for(let i=0;i<12;i++){
                      const prior=S.monthCommitted;
                      await runMonth();
                      if(S.monthCommitted!==prior+1 ||
                         LAST_MONTH_DIAGNOSTIC || MONTH_DIAGNOSTIC_OPEN)
                        return {failedAt:i,month:S.monthCommitted,
                          diagnostic:LAST_MONTH_DIAGNOSTIC?.message,
                          stage:LAST_MONTH_DIAGNOSTIC?.stage};
                    }
                    return {month:S.monthCommitted};
                }""")
                elapsed=time.monotonic()-tick
                max_batch=max(max_batch,elapsed)
                assert progress["month"]==month,progress
                checkpoint=page.evaluate("""()=>{
                    const c=consolidate(S),raw=savePayload(S);
                    const parsed=parsePayload(raw),cp=consolidate(parsed);
                    const ok=!check(S).length&&!c.errors.length&&
                      c.cf.reconciled&&c.spot.checkDifference===0&&
                      !check(parsed).length&&!cp.errors.length&&
                      cp.cf.reconciled&&cp.spot.checkDifference===0&&
                      JSON.stringify(c.bs)===JSON.stringify(cp.bs)&&
                      parsed.monthCommitted===S.monthCommitted;
                    const out={
                      year:S.year,month:S.month,committed:S.monthCommitted,
                      firms:S.firms.length,
                      plants:S.firms.reduce((n,f)=>n+(f.plants||[]).length,0),
                      journals:S.firms.reduce((n,f)=>n+(f.journals||[]).length,0),
                      bytes:raw.length,ok,
                      checks:check(S).slice(0,3),
                      consolidation:c.errors.slice(0,3),cf:c.cf.reconciled
                    };
                    if(ok)S=parsed;
                    return out;
                }""")
                assert checkpoint["ok"],checkpoint
                assert checkpoint["committed"]==month
                assert checkpoint["year"]==era+month//12
                assert checkpoint["month"]==1+month%12
                assert not errors,errors
                print("CHECKPOINT",json.dumps({
                    "era":era,"elapsed":round(time.monotonic()-started,2),
                    "batchSeconds":round(elapsed,2),**checkpoint
                },ensure_ascii=False),flush=True)
            pages=page.evaluate("""()=>{
                render=window.__longNativeRender;
                const routes=Object.values(SECTIONS)
                    .map(s=>s.pages[0][0]).concat(
                      ['corporateSubsidiaries','ma','corporateMerger',
                       'corporateHoldings','supplyContracts','marketExport',
                       'facilityProduction','save']);
                return routes.map(route=>{
                    PAGE=route;render();
                    const el=document.getElementById('content');
                    if(!el?.textContent?.trim())throw Error('Empty page: '+route);
                    return {route,chars:el.innerHTML.length};
                });
            }""")
            assert len(pages)==16 and not errors,(pages,errors)
            print("PASS STEP13",json.dumps({
                "era":era,"months":120,"firms":checkpoint["firms"],
                "plants":checkpoint["plants"],"journals":checkpoint["journals"],
                "saveBytes":checkpoint["bytes"],
                "max12MonthBatchSeconds":round(max_batch,2),
                "elapsedSeconds":round(time.monotonic()-started,2),
                "pages":pages
            },ensure_ascii=False),flush=True)
        finally:
            page.close();browser.close()

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--era",type=int,choices=(1900,2020),required=True)
    run(parser.parse_args().era)
