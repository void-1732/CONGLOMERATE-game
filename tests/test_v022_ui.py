"""v0.22 current release UI smoke (pip install playwright, install Chromium)."""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright
html=(Path(__file__).resolve().parents[1]/'index.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':900})
    errors=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content(html,wait_until='domcontentloaded')
    for _ in range(4):page.locator('[data-action="wizardNext"]').click()
    assert page.evaluate('TECH_NODES.length')==800
    page.locator('[data-section="vehicles"]').click()
    page.locator('[data-page="people"]').click()
    assert page.locator('#researchTreePanel').count()==1
    page.locator('[data-people-view="hr"]').first.click()
    assert page.locator('#researchTreePanel').count()==0
    assert page.locator('#hrPremium').count()==1
    page.locator('#hrPremium').fill('6')
    page.locator('#hrTraining').fill('1200')
    page.locator('[data-action="hrSave"]').click()
    assert page.evaluate('Math.round(current().hr.payPremium*100)')==6
    page.locator('[data-section="corporate"]').click()
    page.locator('[data-page="automation"]').click()
    page.locator('#delegateMode').select_option('delegated')
    page.locator('#auto_price').check()
    page.locator('[data-action="saveDelegate"]').click()
    assert page.evaluate('current().delegate.automation.price')
    page.evaluate('''()=>{
      const f=current(),origin=f.plants[0];
      for(let i=0;i<48;i++){const kind=['engine','body','components','assembly'][i%4];
        f.plants.push({...structuredClone(origin),id:'SMOKE'+i,name:'試験工場 '+i,kind,capacity:25,paused:i%7===0,construction:null,renovation:null,equipmentTier:1,assetTracked:0});
      }
      ensureFactoryV21(f);syncPlant(f);render();
    }''')
    page.locator('[data-section="operations"]').click()
    assert page.locator('.factory-list-item').count()==49
    assert page.locator('.factory-list-item:visible').count()==20
    page.locator('#factoryPageNext').click()
    assert page.locator('#factoryPageLabel').inner_text()=='2 / 3ページ'
    page.locator('#factoryPagePrev').click()
    page.locator('#factoryKindFilter').select_option('support')
    assert page.locator('.factory-list-item:visible').count()==20
    page.locator('#factorySearch').fill('存在しない工場')
    assert page.locator('.factory-list-item:visible').count()==0
    page.locator('#factorySearch').fill('')
    page.locator('.factory-list-item:visible').first.click()
    assert page.locator('#factoryOneAction').count()==1
    assert page.locator('#factoryOnePlan').count()==1
    assert not page.evaluate('check(S)')
    assert not errors,errors
    browser.close()
print('PASS v0.22 HR, automation, factory 49 plants, filters and pagination')
