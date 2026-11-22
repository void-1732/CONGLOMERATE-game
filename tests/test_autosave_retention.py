"""Retention regression: current + preceding two game months for autosaves,
append-only manual backups, legacy manual preservation and IndexedDB reload.

Run: python tests/test_autosave_retention.py
Uses real Chromium and isolated HTTP-origin storage.
"""
import os
import shutil
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

def main():
    server=ThreadingHTTPServer(
        ("127.0.0.1",0),partial(Quiet,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(
                executable_path=os.getenv("CHROMIUM_EXECUTABLE")
                or shutil.which("chromium") or None,
                args=["--no-sandbox"])
            try:
                page=browser.new_page()
                page.set_default_timeout(20000)
                errors=[]
                page.on("pageerror",lambda error:errors.append(str(error)))
                page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
                page.wait_for_function("STORAGE_READY")
                assert page.evaluate("SAVE_INDEX.backend")=="IndexedDB"

                created=page.evaluate("""async()=>{
                  S=newGame({era:2020,country:'JP',difficulty:'normal',
                   history:'historical',name:'STEP14保存ポリシー'});
                  VIEW_FIRM=S.playerId;PAGE='save';render();
                  const first=await saveAuto();
                  if(!first)throw Error(saveWarning);
                  const legacy=slotRecord('manual:0',savePayload(S));
                  await idbWrite('snapshots',legacy);
                  await refreshSaveIndex();
                  return {first,at:ym(S.year,S.month),
                     legacy:legacy.serialized,month:S.monthCommitted};
                }""")
                assert created["first"]
                assert page.locator('[data-action="saveManual"]').count()==1
                page.locator('[data-action="saveManual"]').click()
                page.wait_for_function("SAVE_INDEX.manualArchive.length===1")
                first_archive=page.evaluate("SAVE_INDEX.manualArchive[0].key")
                page.locator('[data-action="saveManual"]').click()
                page.wait_for_function("SAVE_INDEX.manualArchive.length===2")
                first_check=page.evaluate("""async key=>{
                  const r=await idbRead('snapshots',key);
                  return {exists:!!r,valid:check(parsePayload(r.serialized)).length===0,
                    manualIndex:SAVE_INDEX.manualArchive.length,
                    legacy:!!(await idbRead('snapshots','manual:0'))};
                }""",first_archive)
                assert first_check=={
                    "exists":True,"valid":True,"manualIndex":2,"legacy":True
                },first_check

                # Existing engine handles full world, accounting and real autosave
                # each month. No editing of year/month just to simulate time.
                for month in range(1,6):
                    block=page.evaluate("""async()=>{
                      const before=S.monthCommitted;
                      await runMonth();
                      if(S.monthCommitted!==before+1)
                        throw Error('Monthly close stalled');
                      const meta=await idbRead('meta','active');
                      const rows=await Promise.all([0,1,2].map(async i=>{
                        const r=await idbRead('snapshots','auto:'+i);
                        return r?{slot:i,period:ym(r.year,r.month)}:null;
                      }));
                      const last=ym(S.year,S.month);
                      const out={
                        last,rows:rows.filter(Boolean),
                        manual:SAVE_INDEX.manualArchive.length,
                        legacy:!!(await idbRead('snapshots','manual:0')),
                        issues:check(S),
                        alive:!!(await idbRead('snapshots','auto:'+meta.slot)),
                        active:meta.slot,previous:meta.previousSlot
                      };
                      return out;
                    }""")
                    assert block["alive"] and not block["issues"], block
                    assert len(block["rows"]) <= 3, block
                    assert all(block["last"]-2<=r["period"]<=block["last"]
                               for r in block["rows"]),block
                    assert block["manual"]==2 and block["legacy"],block
                    print("AUTO_MONTH",month,block,flush=True)

                # Inject an expired auto-generation in an unprotected slot;
                # pruning must not touch active, previous, or any manual data.
                purged=page.evaluate("""async raw=>{
                  const meta=await idbRead('meta','active');
                  const spare=[0,1,2].find(i=>i!==meta.slot&&i!==meta.previousSlot);
                  const legacyPeriod=parsePayload(raw);
                  await idbWrite('snapshots',slotRecord('auto:'+spare,raw));
                  const before=await idbRead('snapshots','auto:'+spare);
                  const count=await pruneExpiredAutosavesV014(ym(S.year,S.month));
                  const after=await idbRead('snapshots','auto:'+spare);
                  const active=await idbRead('snapshots','auto:'+meta.slot);
                  return {before:ym(before.year,before.month),
                    after:!!after,count,active:!!active,
                    archived:(await idbRead('meta',MANUAL_ARCHIVE_META)).entries.length,
                    legacy:!!(await idbRead('snapshots','manual:0'))};
                }""",created["legacy"])
                assert purged["count"]==1 and not purged["after"],purged
                assert purged["active"] and purged["archived"]==2 and purged["legacy"]
                page.evaluate("()=>{PAGE='save';render()}")
                assert page.get_by_text("手動保存（追記式・自動削除なし）").count()==1
                assert page.locator('[data-action="loadManualArchive"]').count()==2
                assert page.locator('[data-action="loadManual"]').count()==3

                # Reload from actual IndexedDB, retaining all manual archives.
                month_before=page.evaluate("S.monthCommitted")
                page.reload()
                page.wait_for_function("STORAGE_READY")
                loaded=page.evaluate("""async()=>{
                  return {
                    backend:SAVE_INDEX.backend,
                    archive:SAVE_INDEX.manualArchive.length,
                    first:!!(await idbRead('snapshots',SAVE_INDEX.manualArchive[0].key)),
                    legacy:!!(await idbRead('snapshots','manual:0')),
                    month:S?.monthCommitted,
                    errors:S?check(S):['missing']
                  };
                }""")
                assert loaded["backend"]=="IndexedDB" and loaded["archive"]==2
                assert loaded["first"] and loaded["legacy"]
                assert loaded["month"]==month_before and not loaded["errors"],loaded

                # Read older manual backup through the UI; it must still describe
                # the original 2020 / January state despite later autosave cleanup.
                page.on("dialog",lambda dialog:dialog.accept())
                page.evaluate("()=>{PAGE='save';render()}")
                page.locator(f'[data-action="loadManualArchive"][data-key="{first_archive}"]').click()
                assert page.evaluate("S.year") == 2020
                assert page.evaluate("S.month") == 1
                assert page.evaluate("check(S)") == []
                assert not errors,errors
                print("PASS 3-month automatic retention; 2 immutable manual snapshots; "
                      "legacy manuals; IndexedDB reload; older manual restore",flush=True)
            finally:
                browser.close()
    finally:
        server.shutdown()

if __name__=="__main__":
    main()
