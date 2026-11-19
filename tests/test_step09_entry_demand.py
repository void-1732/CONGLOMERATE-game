"""STEP 9 / 05-A: opening-year permission and bounded emerging vehicle demand.

Tests the shared policy only: dealer, subsidiary, JV, factory and acquisition UI
activation are reserved for the subsequent step 05 implementation.
"""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
with sync_playwright() as pw:
    browser = pw.chromium.launch(
        executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
        args=["--no-sandbox"],
    )
    page = browser.new_page()
    page.set_content(html)
    page.evaluate("saveAuto=async()=>true")
    audit = page.evaluate("""() => {
        const checks=[],legacy=[],events=[];
        const make=(year,expanded)=>newGame({era:year,country:'JP',
            difficulty:'normal',history:'historical',name:'参入規制・需要上限',
            marketExpansionV047:expanded});
        const modes={export:'direct',dealer:'dealer',subsidiary:'subsidiary',
            joint:'joint',factory:'factory',acquisition:'acquisition',rival:'rival'};
        for(const [code,profile] of Object.entries(EMERGING_MARKET_PROFILES_V047)){
            for(const [opening,mode] of Object.entries(modes)){
                const year=profile.opening[opening];
                for(const candidate of [year-1,year,year+1]){
                    const s=make(candidate,true),f=company(s.playerId,s);
                    const phase=marketPhaseV047(s,code);
                    const key=opening==='export'?'trade':opening;
                    const permitted=marketEntryPermissionV047(s,f,code,mode);
                    const expected=candidate>=year;
                    const direct=mode==='direct'?directExportPilotV048(s,f,code):null;
                    checks.push({code,mode,candidate,expected,phase:phase[key],permitted,direct,
                        initialEntry:f.marketPresence.includes(code),errors:check(s)});
                }
            }
            const old=make(2010,false),f=company(old.playerId,old);
            checks.push({code,mode:'disabled',permitted:marketEntryPermissionV047(old,f,code,'direct'),
                expected:false,phase:marketPhaseV047(old,code).visible,errors:check(old)});
        }
        for(const year of [1900,1960,2010]){
            const s=make(year,false),expanded=make(year,true);
            for(const code of LEGACY_MARKETS_V047){
                const snapshot=marketDemandSnapshotV031(s,code);
                legacy.push({year,code,demand:snapshot.demand,
                    raw:adjustedRegionalDemandV044(s,code),
                    cap:emergingVehicleDemandCapV049(s,code),
                    segments:Object.values(snapshot.segments).reduce((n,q)=>n+q,0)});
            }
            for(const code of EMERGING_MARKETS_V047){
                const snapshot=marketDemandSnapshotV031(expanded,code),raw=adjustedRegionalDemandV044(expanded,code);
                events.push({year,code,demand:snapshot.demand,cap:emergingVehicleDemandCapV049(expanded,code),
                    raw,segments:Object.values(snapshot.segments).reduce((n,q)=>n+q,0)});
            }
        }
        return {checks,legacy,events};
    }""")
    assert audit["checks"], "No policy cases"
    for item in audit["checks"]:
        assert not item["errors"], item
        assert not item.get("initialEntry"), item
        if item["mode"] == "disabled":
            assert not item["permitted"] and not item["phase"], item
            continue
        assert item["phase"] == item["expected"], item
        assert item["permitted"] == item["expected"], item
        if item["mode"] == "direct":
            assert item["direct"] == item["expected"], item
    for item in audit["legacy"]:
        assert item["cap"] is None and item["demand"] == item["raw"], item
        assert item["segments"] == item["demand"], item
    assert len(audit["events"]) == 9
    assert any(x["demand"] < x["raw"] for x in audit["events"])
    for item in audit["events"]:
        assert 0 <= item["demand"] <= item["raw"], item
        assert item["demand"] == min(item["raw"], item["cap"]), item
        assert item["segments"] == item["demand"], item

    page.evaluate("""() => {
        S=newGame({era:1980,country:'JP',difficulty:'normal',history:'historical',
            name:'12か月需要上限回帰',marketExpansionV047:true});
        VIEW_FIRM=S.playerId;
    }""")
    for month in range(12):
        before = page.evaluate("S.monthCommitted")
        page.evaluate("async()=>await runMonth()")
        result = page.evaluate("""() => ({
            month:S.monthCommitted,errors:check(S),group:consolidate(S).errors,
            cf:consolidate(S).cf.reconciled,
            demand:Object.fromEntries(EMERGING_MARKETS_V047.map(code=>[code,
                {snapshot:marketDemandSnapshotV031(S,code),
                recorded:S.marketAllocationV031[code]}]))
        })""")
        assert result["month"] == before + 1, result
        assert not result["errors"] and not result["group"] and result["cf"], result
        for code, entry in result["demand"].items():
            assert entry["recorded"]["demand"] <= entry["snapshot"]["demand"] + 10000, (month, code, entry)
    saved = page.evaluate("savePayload(S)")
    assert page.evaluate("raw=>restore(raw)", saved)
    assert not page.evaluate("check(S)")
    browser.close()

print("PASS: emerging-market phase boundaries, legacy compatibility, demand caps and 12-month books")
