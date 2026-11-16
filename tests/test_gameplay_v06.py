from pathlib import Path
import json
import os
import shutil
from playwright.sync_api import sync_playwright

html = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True, executable_path=os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
        args=["--no-sandbox"]
    )
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.set_content(html, wait_until="load")
    page.evaluate("""()=>{
      window.__db={meta:{},snapshots:{}};
      idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);
      idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};
      IDB={}; SAVE_INDEX.backend='IndexedDB';
    }""")
    result = page.evaluate("""async()=>{
      S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});
      VIEW_FIRM=S.playerId;PAGE='product';render();
      const gated=!allowedOption('body','sedan') && allowedOption('body','touring');
      document.getElementById('modelName').value='Sport Prototype';
      document.getElementById('design_tune').value='sport';
      document.getElementById('design_size').value='large';
      develop();
      PAGE='factory';render();
      document.getElementById('factoryScale').value='small';
      document.getElementById('factoryKind').value='assembly';
      document.getElementById('factoryName').value='Plant Two';
      factoryBuild();
      for(let i=0;i<6;i++)await runMonth();
      const f=company(S.playerId),m=f.models.find(x=>x.name==='Sport Prototype');
      const built=f.plants.length===2 && f.plants.every(p=>!p.construction);
      for(const p of f.plants)p.focus=m.id;
      for(const x of f.models)f.plans[x.id]=x.id===m.id?0:100;
      await runMonth(); const fixed=company(S.playerId)._produced===0;
      const f2=company(S.playerId);f2.plants.forEach(x=>x.focus='all');f2.plans[m.id]=50;
      await runMonth();const f3=company(S.playerId);
      const s2=parsePayload(savePayload(S)),checks=check(s2),c=consolidate(s2);
      PAGE='people';render();const topics=document.querySelectorAll('.tech-box').length;
      PAGE='product';render();const designFields=document.querySelectorAll('[data-design-field]').length;
      PAGE='market';render();const analytics=document.body.textContent.includes('自社販売分析');
      PAGE='reports';render();const duplicate=document.body.textContent.includes('次の月末処理');
      return {gated,designSize:Object.keys(m.design).length,built,fixed,productionAfter:f3._produced,
          topics,designFields,analytics,duplicate,checks,conso:c.errors,cfOk:c.cf.reconciled,
          marketHistory:f3.marketHistory.length,roundtrip:company(S.playerId,s2).plants.length===2};
    }""")
    print("v0.6 gameplay regression", json.dumps(result, ensure_ascii=False))
    print("browser errors", errors)
    assert not errors and result["gated"] and result["designSize"] == 9
    assert result["built"] and result["fixed"] and result["productionAfter"] > 0
    assert result["topics"] == 6 and result["designFields"] == 9 and result["analytics"]
    assert result["marketHistory"] >= 8 and not result["duplicate"]
    assert result["roundtrip"] and result["cfOk"]
    assert not result["checks"] and not result["conso"]
    browser.close()
