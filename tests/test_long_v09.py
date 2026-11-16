"""v0.9 legacy save + 120-month stress regression. Chromium/Playwright required."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os

html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=os.getenv("CHROMIUM_EXECUTABLE") or None,args=["--no-sandbox"])
    page=b.new_page()
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.set_content(html,wait_until="load")
    page.evaluate("""()=>{
      window.__db={meta:{},snapshots:{}};
      idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);
      idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};
      IDB={};SAVE_INDEX.backend='IndexedDB';
      S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});
      const old=structuredClone(S);
      old.firms=old.firms.filter(f=>!V09_COMPETITOR_SEEDS.some(x=>x.name===f.name));
      delete old.competition;
      for(const f of old.firms){delete f.hr;delete f.lifecycle;}
      S=parsePayload(savePayload(old));VIEW_FIRM=S.playerId;PAGE='dashboard';render();
    }""")
    result=page.evaluate("""async()=>{
      const initial=S.firms.length, failures=[];
      for(let i=0;i<120;i++){
        const prev=S.monthCommitted;
        await runMonth();
        const group=consolidate(S),books=check(S);
        if(S.monthCommitted!==prev+1||books.length||group.errors.length||!group.cf.reconciled){
          failures.push({i,advanced:S.monthCommitted-prev,books,group:group.errors,cf:group.cf.unreconciled});
          break;
        }
      }
      const loaded=parsePayload(savePayload(S));
      const a=consolidate(S),b=consolidate(loaded);
      return {initial,failures,months:S.monthCommitted-ym(1900,1)+1,
        finalFirmCount:S.firms.length,entries:S.competition.entryCount||0,
        cf:a.cf.reconciled,roundtrip:JSON.stringify(a.bs)===JSON.stringify(b.bs)
           &&JSON.stringify(a.cf)===JSON.stringify(b.cf)
           &&JSON.stringify(S.firms.map(f=>f.hr))===JSON.stringify(loaded.firms.map(f=>f.hr))};
    }""")
    assert result["initial"]==7 and result["months"]==120 and not result["failures"]
    assert result["entries"]>=1 and result["finalFirmCount"]>7
    assert result["cf"] and result["roundtrip"] and not errors
    print("PASS v0.9 120-month consolidated CF, legacy migration, JSON roundtrip")
    b.close()
