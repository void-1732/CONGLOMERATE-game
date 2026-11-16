from pathlib import Path
from playwright.sync_api import sync_playwright
import os,shutil

html=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")
with sync_playwright() as p:
 b=p.chromium.launch(headless=True,executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),args=["--no-sandbox"])
 page=b.new_page()
 errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
 page.set_content(html,wait_until="load")
 page.evaluate("""()=>{window.__db={meta:{},snapshots:{}};idbRead=async(k,id)=>structuredClone(window.__db[k][id]??null);idbWrite=async(k,o)=>{window.__db[k][o.key]=structuredClone(o)};IDB={};SAVE_INDEX.backend='IndexedDB';S=newGame({...setup,era:1900,country:'JP',difficulty:'easy'});VIEW_FIRM=S.playerId;PAGE='factory';render();}""")
 assert page.evaluate("()=>S.firms.length")==30
 assert page.locator("#factorySite option").count()==15
 assert page.evaluate("()=>siteInvestmentQuote('JP-NGO','small','integrated') < siteInvestmentQuote('JP-TOK','small','integrated')")
 page.select_option("#factorySite","JP-NGO")
 page.fill("#factoryName","中京工場")
 before=page.evaluate("()=>acc(company(S.playerId),'cash')")
 price=page.evaluate("()=>siteInvestmentQuote(inputValue('factorySite'),inputValue('factoryScale'),inputValue('factoryKind'))")
 page.click("[data-action=factoryBuild]")
 assert page.evaluate("()=>company(S.playerId).plants.at(-1).siteId")=="JP-NGO"
 assert before-page.evaluate("()=>acc(company(S.playerId),'cash')")==price*100
 page.evaluate("()=>{PAGE='group';render()}")
 page.select_option("#delegateMode","delegated")
 for k in ("price","procurement","maintenance","marketing"):page.check("#auto_"+k)
 page.fill("#autoLimitBase","5000")
 page.click("[data-action=saveDelegate]")
 for i in range(7):
  state=page.evaluate("""async()=>{const old=S.monthCommitted;await runMonth();const g=consolidate(S),f=company(S.playerId);return {step:S.monthCommitted-old,errors:check(S),group:g.errors,cf:g.cf.reconciled,spend:f.delegate.monthSpendBase}}""")
  assert state["step"]==1 and not state["errors"] and not state["group"] and state["cf"] and state["spend"]<=5000
 assert not errors
 print("PASS 7-month factory placement, delegated automation, ledger and cashflow")
 b.close()
