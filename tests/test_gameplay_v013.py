"""CONGLOMERATE v0.13: tech domains, research caps, vehicle unlock and era costs."""
from pathlib import Path
from playwright.sync_api import sync_playwright
html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
    b=p.chromium.launch(headless=True,args=["--no-sandbox"])
    page=b.new_page(viewport={"width":1500,"height":900})
    errors=[]
    page.on("pageerror",lambda e: errors.append(str(e)))
    page.set_content(html,wait_until="load")
    page.evaluate("""()=>{window.__db={meta:{},snapshots:{}};idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};IDB={};SAVE_INDEX.backend='IndexedDB';S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});VIEW_FIRM=S.playerId;PAGE='people';PEOPLE_VIEW='research';render()}""")
    result=page.evaluate("""()=>({nodeCount:TECH_NODES.length,domainCount:TECH_BRANCHES.length,familyCount:Object.keys(TECH_FAMILIES).length,subtracks:TECH_BRANCHES.map(x=>TECH_SUBFIELDS[x].length),screenNodes:document.querySelectorAll('.tech-node').length,cap1900:techEraCap(1900),cap2020:techEraCap(2020),cap2100:techEraCap(2100),oldId:TECH_BY_ID['powertrain-20'].name,acyclic:TECH_NODES.every(x=>x.prereq.every(id=>TECH_BY_ID[id]?.tier<x.tier))})""")
    assert result["nodeCount"]==300 and result["domainCount"]==10 and result["familyCount"]==3
    assert result["screenNodes"]==30 and all(2<=x<=3 for x in result["subtracks"])
    assert result["cap1900"]==1 and result["cap2020"]==5 and result["cap2100"]==7
    assert result["acyclic"] and result["oldId"]=="次世代エネルギー技術"
    page.locator("[data-tech-family=intelligence]").click()
    page.locator("[data-tech-domain=software]").click()
    assert page.locator(".tech-node").count()==30
    page.locator("[data-tech-select=software-5]").click()
    assert "車載コンピュータOS" in page.locator("#researchTreePanel").inner_text()
    cost=page.evaluate("""()=>{const a=newGame({...setup,era:1900,country:'JP',difficulty:'easy'}),b=newGame({...setup,era:2020,country:'JP',difficulty:'easy'});return {early:productCostQuote(company(a.playerId,a),DESIGN_DEFAULT,a).unitCost,late:productCostQuote(company(b.playerId,b),DESIGN_DEFAULT,b).unitCost,earlyFactory:siteInvestmentQuote('JP-NGO','small','integrated',a),lateFactory:siteInvestmentQuote('JP-NGO','small','integrated',b)}}""")
    assert cost["late"]>cost["early"]*2 and cost["lateFactory"]>cost["earlyFactory"]*2
    assert not errors,errors
    print("PASS v0.13 300 technology nodes, research eras, UI and indexed unit costs")
    b.close()
