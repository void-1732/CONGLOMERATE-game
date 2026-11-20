"""Real-browser tests for fail-closed restoration and factory debug-label removal."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0), partial(Quiet,directory=str(ROOT)))
Thread(target=server.serve_forever,daemon=True).start()
URL=f'http://127.0.0.1:{server.server_port}/index.html'
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(args=['--no-sandbox'])
        context=browser.new_context()
        context.add_init_script("""
            Object.defineProperty(window,'indexedDB',{configurable:true,value:undefined});
        """)
        page=context.new_page()
        page.goto(URL)
        page.wait_for_function('STORAGE_READY')
        assert page.evaluate('RECOVERY_STORAGE_UNAVAILABLE_V035')
        assert page.evaluate('RECOVERY_BLOCKED_V038')
        assert page.locator('#modalHost').get_by_text('保存済みゲームの復旧').count()==1
        assert page.locator('#modalHost').get_by_text('新しい企業経営を始める').count()==0
        assert page.evaluate('S===null')
        context.close()
        context=browser.new_context()
        page=context.new_page()
        page.goto(URL)
        page.wait_for_function('STORAGE_READY')
        page.evaluate("""async()=>{
            S=newGame({era:1920,country:'JP',difficulty:'normal',history:'historical',name:'保存障害確認'});
            VIEW_FIRM=S.playerId; VIEW_COUNTRY='JP';
            if(!await saveAuto())throw Error('Could not save a fixture');
            const f=current();
            const html=factoryDetailMarkup(f,f.plants[0],true);
            if(html.includes('修正ビルド')||html.includes('SPECIALIST-2'))throw Error('Factory debug build label is visible');
            if(!html.includes(f.plants[0].id))throw Error('Factory ID missing');
        }""")
        before=page.evaluate("()=>({year:S.year,month:S.month,id:S.playerId,name:current().name})")
        page.reload();page.wait_for_function('STORAGE_READY')
        after=page.evaluate("()=>({year:S.year,month:S.month,id:S.playerId,name:current().name})")
        assert before==after,(before,after)
        browser.close()
finally:
    server.shutdown()
print('PASS: storage denied recovery screen, no debug build label, regular reload')
