"""SPEC-165: finite first-come hiring, costs, company founding, save and month."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
        page=browser.new_page()
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.set_content((ROOT/"index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result=page.evaluate("""async()=>{
          S=newWorldGame({country:'JP',name:'Hiring group'});
          saveAuto=async()=>true;const root=S.playerId;
          const use=(id,pageName)=>{VIEW_FIRM=id;VIEW_COUNTRY='JP';PAGE=pageName;STEP2_HR_VIEW='staff';render()};
          const create=name=>{use(root,'corporateSubsidiaries');document.querySelector('#subName').value=name;
            document.querySelector('#subCountry').value='JP';document.querySelector('#subIndustry').value='service';
            document.querySelector('#subCapital').value='650000';createSub();syncWorldIdentities(S)};
          create('Hiring subsidiary');
          const sub=S.firms.find(f=>f.name==='Hiring subsidiary'),id=sub.id;
          const a=company(root,S),b=company(id,S);
          const realCap=worldLaborCapacity,cap=realCap(S,'JP'),employed=worldLaborEmployed(S,'JP');
          const reference=cap===Math.floor((anchorPopulation('JP',1900)??COUNTRIES.JP.pop)*10000)
            &&worldLaborAvailable(S,'JP')===cap-employed;
          const allNationalBaselines=Object.keys(COUNTRIES).every(code=>Number.isSafeInteger(realCap(S,code))&&realCap(S,code)>0);
          // Stress fixture: only three vacancies in JP, without creating a huge payroll.
          const constrained=employed+3;
          worldLaborCapacity=(s,code)=>s.worldExpansion&&code==='JP'?constrained:realCap(s,code);
          const hire=(firm,field,q)=>{use(firm.id,'hr');document.querySelector('#hireArea').value=field;
            document.querySelector('#hireCount').value=String(q);hireStaff()};
          const cost=(f,n)=>localFromBase(n*S.world[f.country].wage*.4*eraCostFactor(S.year),f.country,S);
          const aa=a.staff.production,bb=b.staff.research,ac=acc(a,'cash'),bc=acc(b,'cash');
          const aj=a.journals.length,bj=b.journals.length;
          hire(a,'production',2);
          const first=a.staff.production===aa+2&&worldLaborAvailable(S,'JP')===1
            &&acc(a,'cash')===ac-cost(a,2)&&a.journals.length===aj+1;
          hire(b,'research',2);
          const second=b.staff.research===bb+1&&worldLaborAvailable(S,'JP')===0
            &&acc(b,'cash')===bc-cost(b,1)&&b.journals.length===bj+1;
          const other=worldLaborAvailable(S,'US'),cc=acc(a,'cash'),nn=a.journals.length;
          hire(a,'production',1);
          const reject=a.staff.production===aa+2&&acc(a,'cash')===cc&&a.journals.length===nn
            &&worldLaborAvailable(S,'US')===other;
          const before=S.firms.length;
          create('No vacancy subsidiary');
          const founding=S.firms.length===before&&acc(a,'cash')===cc&&a.journals.length===nn;
          const saved=parsePayload(savePayload(S));
          const persistent=worldLaborEmployed(saved,'JP')===constrained&&worldLaborAvailable(saved,'JP')===0
            &&company(root,saved).staff.production===aa+2&&company(id,saved).staff.research===bb+1
            &&!check(saved).length&&!consolidate(saved).errors.length;
          const forged=structuredClone(saved);company(id,forged).staff.research++;
          const denied=x=>{try{parsePayload(savePayload(x));return false}catch(e){return e.message.includes('労働市場')}};
          const tamper=denied(forged);
          // Departure releases the slot; the next employer can fill it.
          a.staff.production--;
          hire(b,'research',1);
          const released=b.staff.research===bb+2&&worldLaborAvailable(S,'JP')===0;
          // Run a genuine monthly close under the stress fixture.
          const start=S.monthCommitted;await runMonth();
          const month=S.monthCommitted===start+1&&worldLaborEmployed(S,'JP')<=constrained
            &&!check(S).length&&!consolidate(S).errors.length&&consolidate(S).cf.reconciled;
          worldLaborCapacity=realCap;
          // Production-model cap is independently validated without the fixture.
          const huge=structuredClone(S);company(root,huge).staff.production+=realCap(huge,'JP');
          const realTamper=denied(huge);
          // Exercise the actual rival-capex and new-entry paths with scarce workers.
          S=newWorldGame({country:'JP',name:'AI labor test'});VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';
          const rival=S.firms.find(f=>f.country==='JP'&&!controller(S,f.id)&&['auto','manufacturing'].includes(f.industry)
            &&f.lifecycle?.phase==='active'&&f.plants.some(p=>!p.construction&&['integrated','assembly'].includes(p.kind)));
          const rp=rival.plants.find(p=>!p.construction&&['integrated','assembly'].includes(p.kind)),staff=rival.staff.production,capacity=rp.capacity;
          const used=worldLaborEmployed(S,'JP');worldLaborCapacity=(s,code)=>code==='JP'?used+2:realCap(s,code);
          for(const f of S.firms){f.lifecycle.growthStreak=0;f.monthly.profit=0}
          rival.lifecycle.growthStreak=5;rival.lifecycle.investmentMonth=-1;rival.monthly.profit=100;
          const policy=ensureCompetitionPolicy(rival,S);policy.annualCapexBudgetBase=100000000;policy.reserveBase=0;policy.spentThisYearBase=0;
          const reserve=localFromBase(3000000,rival.country,S);
          if(acc(rival,'cash')<reserve)post(rival,{cash:reserve},{capital:reserve},'検証用追加資本','financing',S);
          S.competition.lastEntry=ym(S.year,S.month);competitorEvolution(S,[]);
          const aiExpansion=rp.capacity===capacity+8&&rival.staff.production===staff+2&&worldLaborAvailable(S,'JP')===0;
          const n=S.firms.length,entries=S.competition.entryCount??0,caps=Object.fromEntries(Object.keys(S.world).map(code=>[code,worldLaborEmployed(S,code)]));
          worldLaborCapacity=(s,code)=>caps[code]??realCap(s,code);
          S.competition.lastEntry=ym(S.year,S.month)-20;S.competition.maxFirms=S.firms.length+10;
          for(const f of S.firms){f.lifecycle.growthStreak=0;f.monthly.profit=0}
          competitorEvolution(S,[]);
          const aiEntryDenied=S.firms.length===n&&(S.competition.entryCount??0)===entries;
          worldLaborCapacity=realCap;
          return {reference,allNationalBaselines,first,second,reject,founding,persistent,tamper,released,month,realTamper,aiExpansion,aiEntryDenied};
        }""")
        assert len(result)==13 and all(result.values()),result
        assert not errors,errors
        print("PASS SPEC-165: 13 checks, national baselines, finite first-come hiring, costs, AI expansion/entry, monthly close, save and tamper")
        browser.close()

if __name__=="__main__":
    main()
