"""STEP 9: real IndexedDB persistence and previous-generation recovery at month 300.

Uses an HTTP origin and actual Chromium storage. The first 300 month closes
run the original simulation pipeline while only their per-month browser writes
and DOM repaint are suppressed; at month 300, both snapshots and both reloads
use the game's original saveAuto/restoreAuto/boot code.

The test is deliberately isolated in a temporary browser profile: it does not
read, delete, or overwrite any player's existing saves.
"""
import json
import os
import shutil
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
TARGET = 300


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(Quiet, directory=str(ROOT))
    )
    Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/index.html"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
                args=["--no-sandbox"],
            )
            try:
                page = browser.new_page()
                errors = []
                page.on("pageerror", lambda exc: errors.append(str(exc)))
                page.goto(url)
                page.wait_for_function("STORAGE_READY", timeout=60_000)
                assert page.evaluate("SAVE_INDEX.backend") == "IndexedDB"

                # Save the original functions and restore them before testing
                # real IDB. Do not replace/short-circuit the actual month engine.
                init = page.evaluate(
                    """() => {
                      window.__step9NativeSave = saveAuto;
                      window.__step9NativeRender = render;
                      saveAuto = async () => true;
                      render = () => {};
                      S = newGame({era: 2020, country:'JP',
                        difficulty:'normal', history:'historical',
                        name:'大容量保存の長期検証'});
                      const f = company(S.playerId, S);
                      f.research.tree.done = [...new Set([
                        ...f.research.tree.done,'materials-1','energy-5'
                      ])];
                      step5OpenDepartment(f,S,'materials_evaluation');
                      step5OpenDepartment(f,S,'energy_storage_research');
                      VIEW_FIRM = S.playerId;
                      PAGE = 'dashboard';
                      return {count:S.monthCommitted,checks:check(S),
                        departments:f.step4OrgV1.departments.length};
                    }"""
                )
                assert init["departments"] == 2 and not init["checks"], init

                count = 0
                for _ in range(TARGET // 10):
                    block = page.evaluate(
                        """async () => {
                          let done = 0;
                          for (let i = 0; i < 10; i++) {
                            const before = S.monthCommitted;
                            await runMonth();
                            if (S.monthCommitted !== before + 1 ||
                                LAST_MONTH_DIAGNOSTIC)
                              return {done, diagnostic: LAST_MONTH_DIAGNOSTIC?.message};
                            done++;
                          }
                          return {done, committed:S.monthCommitted};
                        }"""
                    )
                    assert block["done"] == 10, {"month": count, **block}
                    count += block["done"]
                    if count % 100 == 0:
                        state = page.evaluate(
                            """() => {
                              const c=consolidate(S);
                              return {checks:check(S),issues:c.errors,
                                cf:c.cf.reconciled,departments:
                                company(S.playerId,S).step4OrgV1.departments.length};
                            }"""
                        )
                        assert not state["checks"] and not state["issues"] and state["cf"], state
                        assert state["departments"] == 2, state
                        print("CHECKPOINT", json.dumps({"months": count, **state}, ensure_ascii=False), flush=True)

                # Switch back to the original IndexedDB implementation.
                snapshot = page.evaluate(
                    """async () => {
                      saveAuto = window.__step9NativeSave;
                      render = window.__step9NativeRender;
                      const sum = consolidate(S);
                      if (check(S).length || sum.errors.length || !sum.cf.reconciled)
                        throw Error('Invalid month-300 ledger');
                      const nativeFirst = S.monthCommitted;
                      S.config.name = 'STEP9-STORAGE-A';
                      if (!await saveAuto())throw Error('Real save A failed: '+saveWarning);
                      const pointerA = await idbRead('meta','active');
                      S.config.name = 'STEP9-STORAGE-B';
                      if (!await saveAuto())throw Error('Real save B failed: '+saveWarning);
                      const pointerB = await idbRead('meta','active');
                      if (pointerA.slot === pointerB.slot ||
                          pointerB.previousSlot !== pointerA.slot)
                        throw Error('IDB active/previous generations not rotated');
                      return {committed:nativeFirst,year:S.year,month:S.month,
                        bytes:savePayload(S).length,slotA:pointerA.slot,
                        slotB:pointerB.slot,backend:SAVE_INDEX.backend};
                    }"""
                )
                assert snapshot["year"] == 2045 and snapshot["month"] == 1, snapshot
                assert snapshot["backend"] == "IndexedDB", snapshot
                assert snapshot["bytes"] >= 10_000_000, snapshot
                print("SAVED", json.dumps(snapshot, ensure_ascii=False), flush=True)

                page.reload()
                page.wait_for_function("STORAGE_READY", timeout=120_000)
                loaded = page.evaluate(
                    """() => ({exists:!!S,config:S?.config?.name,
                      committed:S?.monthCommitted,issues:S?check(S):null,
                      backend:SAVE_INDEX.backend})"""
                )
                assert loaded["exists"] and loaded["config"] == "STEP9-STORAGE-B", loaded
                assert loaded["committed"] == snapshot["committed"] and not loaded["issues"], loaded

                # Damage only the latest generation in this disposable test
                # profile; the old committed generation must be recoverable.
                page.evaluate(
                    """async () => {
                      const meta = await idbRead('meta','active');
                      const key = 'auto:' + meta.slot;
                      const record = await idbRead('snapshots', key);
                      if (!record?.serialized) throw Error('Latest snapshot missing');
                      record.serialized='CORRUPTED-STEP9';
                      await idbWrite('snapshots',record);
                    }"""
                )
                # Disable the emergency copy only for the recovery reload:
                # pagehide would otherwise regenerate it from the current live
                # state and mask whether IDB previous-generation works.
                page.add_init_script(
                    "localStorage.removeItem('conglomerate.emergency.latest')"
                )
                page.reload()
                page.wait_for_function("STORAGE_READY", timeout=120_000)
                recovered = page.evaluate(
                    """() => {
                      if (!S) return {exists:false};
                      const conso=consolidate(S);
                      return {exists:true,config:S.config.name,
                        committed:S.monthCommitted,
                        checks:check(S),issues:conso.errors,
                        cf:conso.cf.reconciled,
                        dept:company(S.playerId,S).step4OrgV1.departments.length};
                    }"""
                )
                assert recovered["exists"] and recovered["config"] == "STEP9-STORAGE-A", recovered
                assert recovered["committed"] == snapshot["committed"], recovered
                assert not recovered["checks"] and not recovered["issues"] and recovered["cf"], recovered
                assert recovered["dept"] == 2 and not errors, (recovered, errors)
                print("PASS", json.dumps({
                    "months": TARGET, "saveBytes": snapshot["bytes"],
                    "realIndexedDB": True, "reload": True,
                    "previousGenerationRecovery": True,
                    "recovered": recovered
                }, ensure_ascii=False), flush=True)
            finally:
                browser.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
