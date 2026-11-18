"""Diagnostic: output real planned/produced utilization across starting eras.

This is a non-gating balance probe; inadequate utilization requires attribution to
raw materials, labor, cash or other factories before tightening the 95% target.
"""
import json
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8')

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=['--no-sandbox'])
    page=browser.new_page()
    page.set_content(HTML,wait_until='domcontentloaded')
    for era in [1900,1960,2010]:
        page.evaluate("""era=>{
            saveAuto=async()=>true;
            S=newGame({era,country:'JP',difficulty:'normal',history:'historical',name:'供給均衡診断'});
        }""",era)
        planned=0;actual=0;constrained=0;shortage_months=0;ratios=[]
        for month in range(12):
            row=page.evaluate("""async()=>{
                const f=company(S.playerId,S);
                const plan=Object.values(f.plans).reduce((n,x)=>n+(x||0),0);
                const potential=factoryCapacity(f,S).possible;
                const before=S.monthCommitted;
                await runMonth();
                const current=company(S.playerId,S);
                const raw=ensureNpcV033(S);
                const d=npcDemandV033(S,'JP','steel');
                const c=npcTotalSupplyV033(S,'JP','steel')+npcMarketV033(S,'JP','steel').capacity;
                return {
                    advanced:S.monthCommitted===before+1,
                    errors:check(S),
                    planned:plan,possible:potential,produced:current._produced,
                    shortages:Object.values(current.supply.lastAttempt||{}).reduce((n,x)=>n+(x.shortage||0),0),
                    ratio:d>0?Math.round(c/d*100)/100:null,
                    why:LAST_MONTH_DIAGNOSTIC?.message
                };
            }""")
            assert row['advanced'] and not row['errors'],(era,month,row)
            planned+=row['planned'];actual+=row['produced'];constrained+=min(row['planned'],row['possible'])
            shortage_months+=int(row['shortages']>0)
            if row['ratio'] is not None:ratios.append(row['ratio'])
        print(json.dumps({'era':era,'months':12,'producedOverPlan':round(actual/max(1,planned),3),
            'producedOverPhysicalCapability':round(actual/max(1,constrained),3),
            'marketSupplyOverDemand':round(sum(ratios)/len(ratios),3) if ratios else None,
            'monthsWithUnfulfilledRawOrders':shortage_months},ensure_ascii=False))
    browser.close()
