"""Old-game 0%-utilization regression: switch the visible specialist mode and
repair a saved 0-person allocation with ordinary labor and actual raw materials.
"""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8')
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=['--no-sandbox'])
    page=browser.new_page()
    errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
    page.on('dialog',lambda dialog:dialog.accept())
    page.set_content(HTML)
    page.evaluate('saveAuto=async()=>true')
    def seed(with_assembly):
        page.evaluate("""withAssembly=>{
            S=newGame({era:1900,country:'JP',difficulty:'easy',history:'historical',name:'旧工場0%稼働復旧'});
            VIEW_FIRM=S.playerId;const f=current();const base=f.plants[0];
            f.staff.production=130;
            for(const m of f.models)f.plans[m.id]=0;
            for(const type of ['steel','rubber']){
              post(f,{materials:18000},{cash:18000},'製造材料の仕入','operating',S);
              f.stock[type].q+=1200;f.stock[type].v+=18000;
            }
            if(!withAssembly)base.paused=true;
            for(const kind of ['engine','body','components']){
              const id='ZERO-'+kind;
              f.plants.push({...structuredClone(base),id,kind,capacity:50,paused:false,
                construction:null,renovation:null,condition:100,lastProduced:0,lastUtilization:0});
            }
            ensureFactoryV21(f);ensureV11Firm(f);f.factoryOps.mode='legacy';f.factoryOps.modeExplicit=true;
            for(const kind of ['engine','body','components']){
              const id='ZERO-'+kind;
              f.factoryOps.plans[id]=0;
              f.interplant.partPlans[id]=0;
              f.factoryOps.staffAssignments[id]=0;
            }
            syncPlant(f);PAGE='factory';render();
        }""",with_assembly)
        assert not page.evaluate('check(S)'),page.evaluate('check(S)')
    def result():
        return page.evaluate("""()=>{
            const f=current(),labor=factoryLaborPlanV026(f);
            return ['engine','body','components'].map(k=>{
              const p=f.plants.find(x=>x.id==='ZERO-'+k);
              return {type:k,mode:f.factoryOps.mode,plan:f.factoryOps.plans[p.id]||0,
                staff:labor.byId[p.id]?.assigned||0,util:p.lastUtilization,produced:p.lastProduced,
                stock:moduleAtV21(f,p.id)[v21ModuleType(p)]};
            });
        }""")
    def advance():
        before=page.evaluate('S.monthCommitted')
        page.evaluate('async()=>await runMonth()')
        assert page.evaluate('S.monthCommitted')==before+1,page.evaluate('LAST_MONTH_DIAGNOSTIC?.message')
        assert not page.evaluate('check(S)')
        assert not page.evaluate('consolidate(S).errors')
        assert page.evaluate('consolidate(S).cf.reconciled')
    seed(True)
    before=result()
    assert all(x['plan']==0 and x['staff']==0 for x in before),before
    page.get_by_text('専門部品の製造方式・輸送中在庫・一括管理',exact=True).click()
    page.locator('#factoryV21Mode').select_option('detailed')
    page.locator('[data-action="factoryModeV21"]').click()
    configured=result()
    assert all(x['mode']=='detailed' and x['plan']>0 and x['staff']>0 for x in configured),configured
    advance()
    produced=result()
    assert all(x['util']>0 and x['produced']>0 and x['stock']>0 for x in produced),produced
    print('DETAIL SWITCH UTILIZATION:',produced)
    # Without a running assembly facility, the factory must still be able to
    # produce typed parts for inventory; simply keep shipping OFF.
    seed(False)
    assert not page.evaluate('activeFactories(current()).length')
    page.locator('[data-action="activateSupportV026"]').click()
    prepared=result()
    assert all(x['mode']=='detailed' and x['plan']>0 and x['staff']>0 for x in prepared),prepared
    assert not page.evaluate("Object.values(current().factoryOps.routes).some(r=>r.enabled&&r.to)")
    advance()
    stock=result()
    assert all(x['util']>0 and x['produced']>0 and x['stock']>0 for x in stock),stock
    print('NO ASSEMBLY UTILIZATION:',stock)
    assert not errors,errors
    browser.close()
print('PASS: old 0%-idle factories resume by explicit mode action and one-click setup without an assembler')
