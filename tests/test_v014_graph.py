"""v0.14: integrated 600-node research map and specializations."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os, shutil

html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
    page=browser.new_page(viewport={"width":1480,"height":920})
    errors=[]
    page.on("pageerror",lambda e:errors.append(str(e)))
    page.set_content(html,wait_until="load")
    page.evaluate("""()=>{window.__db={meta:{},snapshots:{}};idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};IDB={};SAVE_INDEX.backend='IndexedDB';S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});VIEW_FIRM=S.playerId;PAGE='people';PEOPLE_VIEW='research';render()}""")
    result=page.evaluate("""()=>({nodes:TECH_NODES.length,special:TECH_NODES.filter(n=>n.special).length,visible:document.querySelectorAll('.tech-node').length,old:TECH_BY_ID['powertrain-20'].name,unresolved:TECH_NODES.filter(n=>n.prereq.some(id=>!TECH_BY_ID[id])).length})""")
    assert result["nodes"]==600 and result["special"]==300 and result["visible"]==240
    assert result["old"]=="次世代エネルギー技術" and not result["unresolved"]
    page.locator("[data-tech-family=intelligence]").click()
    assert page.locator(".tech-node").count()==240
    page.locator("[data-tech-family=industry]").click()
    assert page.locator(".tech-node").count()==120
    page.locator("[data-tech-family=vehicle]").click()
    page.select_option("#researchFocus","lightweight")
    page.locator('[data-action="researchFocusSave"]').click()
    assert page.evaluate("()=>current().research.focus")=="lightweight"
    page.locator('[data-tech-select="materials-31"]').click()
    assert "軽量" in page.locator(".tech-detail h3").first.inner_text()
    assert not errors,errors
    print("PASS v0.14 integrated tech families, specialization and research focus")
    browser.close()
