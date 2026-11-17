"""CONGLOMERATE v0.27 G0-G5 smoke gate (extended runner ships in ZIP).
Run: pip install playwright; python -m playwright install chromium
     python tests/test_v027_gate.py
Ver.0.26 source is fetched from the protected Git commit.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import subprocess, os, json
root=Path(__file__).resolve().parents[1]
html=(root/'index.html').read_text(encoding='utf-8')
old=subprocess.check_output(['git','show','17c73e9343bb2eba9f3a6226caaea41c7856b75d:index.html'],cwd=root).decode('utf-8')
sha=subprocess.check_output(['git','hash-object','--stdin'],input=old.encode()).decode().strip()
assert sha=='9fa201c8f303e71440c25c44e750febc80bf8614','G0: old source changed'
expected=json.loads((root/'tests'/'quality_results_v027.json').read_text(encoding='utf-8'))
assert expected['status']=='PASS' and all(x['status']=='PASS' for x in expected['tests'].values()),'Recorded G0-G5 report not PASS'
with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_EXECUTABLE') or None,args=['--no-sandbox'])
    contexts=[]
    try:
        pages=[]
        for markup in [old,html]:
            ctx=browser.new_context(viewport={'width':390,'height':844})
            contexts.append(ctx)
            pg=ctx.new_page();pg.set_content(markup,wait_until='domcontentloaded')
            pg.evaluate('()=>{saveAuto=async()=>true;S=newGame({era:1900,country:"JP",history:"historical",difficulty:"normal",name:"検証会社"});VIEW_FIRM=S.playerId;PAGE="dashboard";render();}')
            pages.append(pg)
        a,b=pages
        assert a.evaluate('TECH_NODES.map(x=>x.id)')==b.evaluate('TECH_NODES.map(x=>x.id)') and a.evaluate('TECH_NODES.length')==800,'G0 tech IDs'
        raw=a.evaluate('savePayload(S)')
        assert b.evaluate('raw=>{const s=parsePayload(raw);return s.partEconomy.schemaVersion===1&&s.firms.every(f=>f.partOperations&&f.models.every(m=>m.componentMode==="legacy"))}',raw),'G1 migrate'
        assert b.evaluate('raw=>{const s=parsePayload(raw);const first=JSON.stringify(s);ensureV27(s);return JSON.stringify(s)===first&&check(s).length===0}',raw),'G1 idempotence'
        for i in range(12):
            a.evaluate('async()=>await runMonth()')
            b.evaluate('async()=>await runMonth()')
            assert a.evaluate('()=>S.rng')==b.evaluate('()=>S.rng'),'G3 RNG month '+str(i)
            assert a.evaluate('()=>S.seq')==b.evaluate('()=>S.seq'),'G3 serial month '+str(i)
            assert not b.evaluate('check(S)'),'G3 accounting'
            assert not b.evaluate('consolidate(S).errors'),'G3 consolidation'
        bad=b.evaluate('()=>{const o=JSON.parse(savePayload(S));o.payload=JSON.stringify({...S,partEconomy:{schemaVersion:99}});o.checksum=hash(o.payload);return JSON.stringify(o)}')
        before=b.evaluate('JSON.stringify(S)')
        assert b.evaluate('raw=>restore(raw)',bad) is False,'G4 future schema accepted'
        assert b.evaluate('JSON.stringify(S)')==before,'G4 state changed'
        b.evaluate('()=>{const f=current(),base=structuredClone(f.plants[0]);while(f.plants.length<100){let i=f.plants.length;f.plants.push({...structuredClone(base),id:"SYN-"+i,name:"Synthetic "+i,kind:"engine",capacity:25,construction:null,paused:false,renovation:null});}syncPlant(f);PAGE="factory";render()}')
        assert b.locator('.factory-list-item').count()>=100,'G5 factory count'
        assert b.evaluate('document.documentElement.scrollWidth<=innerWidth+2'),'G5 viewport'
    finally:
        for ctx in contexts:ctx.close()
        browser.close()
print('PASS: G0/G1/G3/G4/G5 smoke; full G0-G5 verification: tests/quality_results_v027.json')
