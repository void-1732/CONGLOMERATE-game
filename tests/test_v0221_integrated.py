"""v0.22.1: integrated factory self-manufacture and accounting smoke test."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os, shutil

html=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8')
cases=[('integrated',0,8,8),('integrated',2,8,6),
       ('assembly',0,0,0),('assembly',8,8,0)]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,
        executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,
        args=['--no-sandbox'])
    for kind,delivered,want_produced,want_internal in cases:
        page=browser.new_page()
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.set_content(html,wait_until='domcontentloaded')
        for _ in range(4):
            page.locator('[data-action="wizardNext"]').click()
        page.evaluate("""([kind,delivered])=>{
          const f=current(),plant=f.plants[0];
          f.factoryOps.mode='detailed';plant.kind=kind;
          plant.capacity=54;plant.condition=100;f.staff.production=145;
          f.plans[f.models[0].id]=8;
          for(const typ of ['aluminum','copper','glass','chemicals']){
            f.stock[typ].q+=100;f.stock[typ].v+=200;
            post(f,{materials:200},{cash:200},'test materials','operating');
          }
          for(const typ of V21_MODULE_TYPES)if(delivered){
            const cost=delivered*15;
            f.stock[typ].q+=delivered;f.stock[typ].v+=cost;
            post(f,{materials:cost},{cash:cost},'test module delivery','operating');
            moduleAtV21(f,plant.id)[typ]+=delivered;
          }
          saveAuto=async()=>true;syncPlant(f);render();
        }""",[kind,delivered])
        assert page.evaluate('TECH_NODES.length')==800
        assert page.evaluate('check(S)')==[]
        page.evaluate('async()=>await runMonth()')
        out=page.evaluate("""()=>({
          produced:current()._produced,internal:current().plants[0].lastInternalModules||0,
          monthError:LAST_MONTH_DIAGNOSTIC,errors:check(S),
          conso:consolidate(S).errors,cf:consolidate(S).cf.reconciled
        })""")
        assert out['produced']==want_produced and out['internal']==want_internal,(kind,out)
        assert out['monthError'] is None and not out['errors'] and not out['conso'] and out['cf']
        assert not errors, errors
        page.close()
    browser.close()
print('PASS v0.22.1 integrated internal modules, assembly imports, accounting checks')
