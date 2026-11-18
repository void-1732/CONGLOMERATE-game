"""v0.32 STEP1: actual resource inventory, physical allocation and save migration."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")

def run():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
        page=browser.new_page()
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.set_content(HTML,wait_until="domcontentloaded")
        info=page.evaluate("""() => {
            saveAuto=async()=>true;
            S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'STEP1 供給検証'});
            const buyer=company(S.playerId,S);
            const seller=initFirm(S,{name:'資源専用検証会社',country:'JP',industry:'resource',size:1,seedBase:2500000});
            seller.owners=[{id:buyer.id,econ:1,vote:1}];seller.shareBlocks=[];
            seller.reserveUnits=4000;
            // Preserve quantity and accounting value on old generic RESOURCE -> six physical bins migration.
            post(seller,{goods:1200},{cash:1200},'旧資源棚卸','operating',S);
            seller.goods.RESOURCE={q:12,v:1200};
            ensureSupplyNetwork(S);
            const bins=RAW_TYPES_V032.map(t=>rawBinV032(seller,t));
            const migrated={qty:bins.reduce((n,x)=>n+x.q,0),value:bins.reduce((n,x)=>n+x.v,0),book:acc(seller,'goods')};
            const initialQ=bins.reduce((n,x)=>n+x.q,0);
            // Production and procurement occur in this order in runMonth.
            laborAndPlant(S,[],'resource');
            ensureSupplyNetwork(S);
            const produced=RAW_TYPES_V032.map(t=>rawBinV032(seller,t).q).reduce((a,b)=>a+b,0)-initialQ;
            const stock=rawBinV032(seller,'steel');
            const external=rawBinV032(seller,'rubber');
            const totalBefore=RAW_TYPES_V032.reduce((n,t)=>n+rawBinV032(seller,t).q,0);
            const capacity=S.supplyNetwork.nodes.find(n=>n.firmId===seller.id&&n.type==='steel').capacity;
            buyer.supply.contracts.steel={supplierId:'CORP:'+seller.id+':steel',backupId:'',buffer:1};
            // Deliberately create a shipment larger than the seller's steel stock.
            const order={id:'SHIP'+S.seq++,type:'steel',origin:'JP',supplierId:'CORP:'+seller.id+':steel',
                qty:stock.q+3,totalBase:(stock.q+3)*100,due:ym(S.year,S.month)};
            buyer.supply.inbound.push(order);
            const priorBuyer=buyer.stock.steel.q,priorSeller=stock.q;
            deliverMaterials(S,buyer,[]);
            const received=buyer.stock.steel.q-priorBuyer;
            const pending=buyer.supply.inbound.find(x=>x.id===order.id);
            const finalQty=RAW_TYPES_V032.reduce((n,t)=>n+rawBinV032(seller,t).q,0);
            const result={migrated,produced,capacity,received,priorSeller,
                pending:pending?.qty||0,oldGeneric:seller.goods.RESOURCE??null,
                change:totalBefore-finalQty,bookErrors:check(S)};
            S._step1TestResult=result;
            return result;
        }""")
        assert info["migrated"]=={"qty":12,"value":1200,"book":1200},info
        assert info["produced"]>=0 and info["capacity"]==info["priorSeller"],info
        assert info["received"]==info["priorSeller"],info
        assert info["pending"]==3 and info["change"]==info["received"],info
        assert info["oldGeneric"] is None and not info["bookErrors"],info
        page.evaluate("""() => {delete S._step1TestResult;}""")
        # Synthetic ownership was used only to isolate the group delivery routine.
        # Exercise normal month closing on a game with fully registered ownership.
        page.evaluate("""() => {
            S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'STEP1 月次検証'});
        }""")
        # Month closing uses resource-first production without double-producing a resource firm.
        for _ in range(6):
            outcome=page.evaluate("""async()=> {
                const before=S.monthCommitted;
                await runMonth();
                return {advanced:S.monthCommitted===before+1,errors:check(S),
                    month:S.monthCommitted,why:LAST_MONTH_DIAGNOSTIC?.message};
            }""")
            assert outcome["advanced"] and not outcome["errors"],outcome
        snapshot=page.evaluate("savePayload(S)")
        assert page.evaluate("raw=>restore(raw)",snapshot)
        assert not page.evaluate("check(S)")
        assert not errors,errors
        browser.close()

if __name__=="__main__":
    run()
    print("PASS v0.32 STEP1: legacy migration, real stock, partial deliveries, 6 months, save")
