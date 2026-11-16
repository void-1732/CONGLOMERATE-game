"""v0.9 gameplay smoke / monthly accounting. Requires playwright and Chromium."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os

html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,executable_path=os.getenv("CHROMIUM_EXECUTABLE") or None,args=["--no-sandbox"])
    page=b.new_page(viewport={"width":1440,"height":900})
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.set_content(html,wait_until="load")
    page.evaluate("""()=>{
       window.__db={meta:{},snapshots:{}};
       idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);
       idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};
       IDB={};SAVE_INDEX.backend='IndexedDB';
       S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});
       VIEW_FIRM=S.playerId;PAGE='group';render();
    }""")
    result=page.evaluate("""async()=>{
      const initial=S.firms.length,root=company(S.playerId);
      const capBefore=factoryCapacity(root).possible;
      for(const industry of ['resource','manufacturing','trade','service']){
        VIEW_FIRM=S.playerId;PAGE='group';render();
        document.getElementById('subName').value='子会社 '+industry;
        document.getElementById('subCountry').value='JP';
        document.getElementById('subIndustry').value=industry;
        document.getElementById('subCapital').value='450000';
        createSub();
      }
      VIEW_FIRM=S.playerId;PAGE='people';render();
      document.getElementById('hrPremium').value='10';
      document.getElementById('hrTraining').value='5500';
      saveHRPolicy();
      const synergy=enterpriseSynergy(S,root);
      const capAfter=factoryCapacity(root).possible;
      root.hr.relations=12;root.hr.unionLevel=.9;root.hr.strikeMonths=2;
      const checks=[];
      for(let i=0;i<15;i++){
        const old=S.monthCommitted;
        await runMonth();
        const g=consolidate(S);
        checks.push({advanced:S.monthCommitted===old+1,books:check(S),group:g.errors,cf:g.cf.reconciled});
      }
      const saved=parsePayload(savePayload(S));
      return {initial,controlled:controlled().length,capBefore,capAfter,synergy,
       strike:company(S.playerId).hr.history[0].strike,
       adminCount:company(S.playerId).journals.filter(j=>j.text.includes('グループ統治')).length,
       checks,entrant:S.competition.entryCount||0,original:consolidate(S).bs.cash,restored:consolidate(saved).bs.cash};
    }""")
    assert result["initial"]==15 and result["controlled"]==5
    assert result["synergy"]["resourceDiscount"]>0 and result["synergy"]["productionBoost"]>0
    assert result["synergy"]["distributionBoost"]>0 and result["synergy"]["researchBoost"]>0
    assert result["capAfter"]>result["capBefore"] and result["strike"] and result["adminCount"]==15
    assert result["entrant"]>=1 and result["original"]==result["restored"]
    assert all(x["advanced"] and not x["books"] and not x["group"] and x["cf"] for x in result["checks"])
    assert not errors
    print("PASS v0.9 gameplay 15 months, four controlled industries, HR, journals, CF, JSON")
    b.close()
