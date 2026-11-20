"""Play actual CONGLOMERATE browser game for 101 simulated years (1212 months).
This is a dedicated non-production integration playthrough on the main-branch game.
"""
import json, os, sys, time, shutil, traceback
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8')
OUT=Path('century_play_result.json')
def emit(kind, payload):
    print('CENTURY_'+kind+' '+json.dumps(payload,ensure_ascii=False,default=str),flush=True)

def main():
    started=time.monotonic()
    with sync_playwright() as pw:
        b=pw.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=['--no-sandbox'])
        page=b.new_page(viewport={'width':1360,'height':900})
        page.set_default_timeout(0)
        errors=[]
        page.on('pageerror',lambda exc: errors.append(str(exc)))
        page.set_content(HTML,wait_until='domcontentloaded')
        initial=page.evaluate("""()=>{
            saveAuto=async()=>true;
            S=newGame({era:1900,country:'JP',difficulty:'easy',history:'historical',name:'百年経営実験'});
            VIEW_FIRM=S.playerId;PAGE='dashboard';
            const f=company(S.playerId,S);
            f.delegate.mode='delegated';
            f.delegate.priority='balanced';
            f.delegate.productionAuto=true;
            f.delegate.researchAuto=true;
            f.delegate.minCashBase=0;
            f.delegate.researchMaxBase=11000;
            f.delegate.automation={...f.delegate.automation,price:true,procurement:true,maintenance:true,marketing:false,limitBase:12000};
            ensureAiCenter(f);
            for(const k of ['production','research','price','procurement','maintenance'])f.delegate.aiCenter.modes[k]='routine';
            f.hr.trainingBudgetBase=500;
            return {year:S.year,month:S.month,firm:f.name,cash:acc(f,'cash'),equity:netWorth(f),
                plants:f.plants.length,employees:f.staff.production,modelCount:f.models.length,
                competitors:S.firms.length,errors:check(S)};
        }""")
        emit('START',initial)
        assert not initial['errors'],initial['errors']
        checkpoints=[]; stop=None; total=1212
        # Headless play still runs the real market, AI, supply, production, tax,
        # credit, research and accounting logic; only repeated DOM rendering and
        # durable autosave writes are disabled to keep the stress test practical.
        for block in range(0,total,12):
            try:
                data=page.evaluate("""async count=>{
                    const draw=render;
                    render=()=>{};
                    try{
                        const f=company(S.playerId,S);
                        const elapsed=S.year-S.startYear;
                        if(elapsed>=0){
                            f.delegate.priority=elapsed%15<10?'balanced':'profit';
                            f.delegate.researchMaxBase=Math.round(11000*eraCostFactor(S.year));
                            f.hr.trainingBudgetBase=Math.min(3000,Math.round(500*eraCostFactor(S.year)));
                        }
                        for(let k=0;k<count;k++){
                            const before=S.monthCommitted;
                            await runMonth();
                            if(S.monthCommitted!==before+1){
                                return {ok:false,at:[S.year,S.month],committed:S.monthCommitted,
                                    prev:before,diagnostic:LAST_MONTH_DIAGNOSTIC,errors:check(S)};
                            }
                        }
                        const owned=company(S.playerId,S),c=consolidate(S);
                        return {ok:true,year:S.year,month:S.month,elapsed:S.year-S.startYear,
                            committed:S.monthCommitted,cash:acc(owned,'cash'),equity:netWorth(owned),
                            revenue:financials(owned).revenue,profit:financials(owned).profit,
                            lastSales:owned.monthly.units,staff:owned.staff.production,
                            production:owned._produced||0,plants:owned.plants.length,
                            modelCount:owned.models.length,activeModels:owned.models.filter(x=>x.status==='active').length,
                            competitors:S.firms.length,groupCash:c.bs.cash,
                            distress:owned.distress,cfOk:c.cf.reconciled,
                            ledgerErrors:c.errors,errors:check(S),
                            diagnostic:LAST_MONTH_DIAGNOSTIC?.message||null};
                    }finally{render=draw;}
                }""",12)
                if not data['ok'] or data['errors'] or data['ledgerErrors'] or not data['cfOk']:
                    stop={'block':block,'data':data};emit('STOP',stop);break
                if (block+12)%60==0 or block==0:
                    checkpoints.append(data)
                    emit('CHECKPOINT',data)
            except Exception as exc:
                stop={'block':block,'exception':str(exc),'trace':traceback.format_exc()[-2000:]}
                emit('EXCEPTION',stop)
                break
            if errors:
                stop={'block':block,'browserErrors':errors[-12:]}
                emit('BROWSER_ERROR',stop);break
        final=page.evaluate("""()=>{
            const f=company(S.playerId,S),g=consolidate(S);
            return {year:S.year,month:S.month,committed:S.monthCommitted,
                elapsed:S.year-S.startYear,cash:acc(f,'cash'),equity:netWorth(f),
                plants:f.plants.length,employees:f.staff.production,
                models:f.models.length,competitors:S.firms.length,
                totalMonths:S.monthCommitted-ym(S.startYear,1)+1,
                errors:check(S),consolidatedErrors:g.errors,cfOk:g.cf.reconciled,
                diagnostic:LAST_MONTH_DIAGNOSTIC?.message||null};
        }""")
        emit('FINAL',final)
        report={'initial':initial,'checkpoints':checkpoints,'final':final,'stop':stop,
                'browserErrors':errors,'elapsedSeconds':round(time.monotonic()-started,2)}
        OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        emit('SUMMARY',{'resultFile':str(OUT),'elapsedSeconds':report['elapsedSeconds'],
             'months':final['totalMonths'],'success':final['elapsed']>=101 and stop is None})
        b.close()
        if stop is not None or final['elapsed']<101 or errors:
            sys.exit(1)

if __name__=='__main__':
    main()
