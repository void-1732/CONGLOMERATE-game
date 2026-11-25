"""Phase 9 structural traceability and offline 12-month replay.

This test is not the 174-item final acceptance. It verifies all IDs are
tracked, evidence paths exist and a saved world can be replayed offline.
"""
import argparse
import json
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def audit_matrix(require_accepted=False):
    data = json.loads((ROOT / "docs/WORLD_ECONOMY_ACCEPTANCE.json").read_text(encoding="utf-8"))
    rows = data["items"]
    assert [r["id"] for r in rows] == list(range(1,175))
    counts = {}
    for row in rows:
        status = row["status"]
        assert status in {"OPEN_SCOPE","CANDIDATE_EVIDENCE","UNMAPPED","ACCEPTED"}, row
        counts[status] = counts.get(status,0) + 1
        assert len(row["evidence"]) == len(set(row["evidence"])), row
        for evidence in row["evidence"]:
            assert evidence.startswith("tests/") and (ROOT / evidence).is_file(), row
        if status == "ACCEPTED":
            assert row["evidence"] and row.get("reviewed_sha") and row.get("run_url") and row.get("review_note"), row
    print("TRACEABILITY (not acceptance)", json.dumps(counts), flush=True)
    if require_accepted:
        assert counts.get("ACCEPTED",0) == 174, counts


def test_replay():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
        context = browser.new_context(offline=True)
        page = context.new_page()
        errors, external = [], []
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.on("request",lambda r:external.append(r.url) if r.url.startswith(("http://","https://","ws://","wss://")) else None)
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result = page.evaluate("""async()=>{
          S=newWorldGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'Phase9 replay'});
          VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';
          render=()=>{};saveAuto=async()=>true;
          const initial=savePayload(S),start=S.monthCommitted;
          const capture=()=>JSON.stringify({
            month:S.monthCommitted,rng:S.rng,firms:S.firms,world:S.world,
            expansion:S.worldExpansion,consolidated:S.consoHistory,equity:S.equityLinks
          });
          async function advance(){
            for(let i=0;i<12;i++){
              const before=S.monthCommitted;
              await runMonth();
              if(S.monthCommitted!==before+1||LAST_MONTH_DIAGNOSTIC||MONTH_DIAGNOSTIC_OPEN)
                throw Error('Month failed: '+JSON.stringify(LAST_MONTH_DIAGNOSTIC));
            }
            const c=consolidate(S);
            if(check(S).length||c.errors.length||!c.cf.reconciled||c.spot.checkDifference!==0)
              throw Error('Accounting invariant failed');
            if(S.monthCommitted!==start+12)throw Error('Wrong month count');
            return capture();
          }
          const a=await advance();
          S=parsePayload(initial);
          const b=await advance();
          const saved=parsePayload(savePayload(S));
          return {replay:a===b,clean:check(saved).length===0,
            marketCount:WORLD_MARKETS.length,productCount:WORLD_PRODUCTS.length,
            distinctProducts:new Set(WORLD_PRODUCTS.map(p=>p.id)).size,
            technologyCount:TECH_NODES.length,
            months:S.monthCommitted-start};
        }""")
        assert result == {"replay":True,"clean":True,"marketCount":40,"productCount":150,
                          "distinctProducts":150,"technologyCount":800,"months":12},result
        assert not errors and not external,(errors,external)
        browser.close()
    print("PASS Phase 9 offline world replay, catalog and accounting")


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--require-accepted",action="store_true")
    args=parser.parse_args()
    audit_matrix(args.require_accepted)
    test_replay()
