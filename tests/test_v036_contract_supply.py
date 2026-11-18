"""v0.36 STEP 5: limited contracted dispatch, supplier claims, cancellation, foreign NPC and saves."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML=(Path(__file__).resolve().parents[1]/"index.html").read_text(encoding="utf-8")

def run():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
            args=["--no-sandbox"])
        page=browser.new_page(viewport={"width":1440,"height":980})
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.set_content(HTML,wait_until="domcontentloaded")
        seed=page.evaluate("""() => {
            S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'長期契約'});
            saveAuto=async()=>true;
            const f=company(S.playerId,S);
            const terms=SUPPLY_TYPES.map(t=>contractV036(f,t));
            return {all:terms.length,enabled:terms.every(t=>t.enabled&&t.quantity===0&&t.months===12),
                suppliers:terms.map(t=>t.supplierId),errors:check(S)};
        }""")
        assert seed["enabled"] and seed["all"]==7 and not seed["errors"],seed
        assert all(a.startswith("NPC:JP:") for a in seed["suppliers"]),seed

        # Simultaneous allocation reserves 10% of finite supply for manual emergency
        # procurement even when long-term promises exceed physical availability.
        race=page.evaluate("""() => {
            const run=reverse=>{
              const s=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'公平契約'});
              const all=s.firms.filter(f=>f.country==='JP'&&['auto','manufacturing'].includes(f.industry));
              const player=company(s.playerId,s);
              for(const f of all)for(const model of f.models.filter(m=>m.status==='active'))
                f.plans[model.id]=200;
              const m=npcMarketV033(s,'JP','steel');
              m.capacity=100;m.stock=50;m.producedTotal=m.dispatchedTotal+50;
              const reserved=marketEmergencyReserveV036(m);
              if(reverse)s.firms.reverse();
              procureNetwork(s,[]);
              const attempt=player.supply.lastAttempt.steel;
              return {reserved,stock:m.stock,dispatched:m.dispatchedTotal,
                priority:attempt.longTermOrdered,requested:attempt.longTermRequested,
                errors:check(s),delivered:all.map(f=>[f.id,f.supply.lastAttempt.steel.npcOrdered])};
            };
            return {forward:run(false),reverse:run(true)};
        }""")
        a,b=race["forward"],race["reverse"]
        assert not a["errors"] and not b["errors"],race
        assert a["priority"]>0 and a["priority"]<=a["requested"],race
        assert a["stock"]>=a["reserved"] and b["stock"]>=b["reserved"],race
        assert a["stock"]==b["stock"] and a["priority"]==b["priority"],race
        assert dict(a["delivered"])==dict(b["delivered"]),race

        # Supplier under-delivery creates a future bill discount. No funds are
        # credited on the breach date, and the discount cannot exceed 10%/invoice.
        credit=page.evaluate("""() => {
            const s=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'未達補償'});
            const f=company(s.playerId,s),type='steel',term=contractV036(f,type);
            for(const model of f.models.filter(m=>m.status==='active'))f.plans[model.id]=240;
            const market=npcMarketV033(s,'JP',type);
            market.capacity=100;market.stock=10;market.producedTotal=market.dispatchedTotal+10;
            const cashBefore=acc(f,'cash');
            procureNetwork(s,[]);
            const issuedCredit=term.creditBase,cashAfter=acc(f,'cash');
            // Add 10 produced units, then ship them explicitly and accurately.
            market.stock+=10;market.producedTotal+=10;
            market.stock-=10;market.dispatchedTotal+=10;market.lastShipped+=10;
            const invoice=10000;
            f.supply.inbound.push({id:'CREDIT-SHIP',type,origin:'JP',
              supplierId:term.supplierId,qty:10,totalBase:invoice,due:ym(s.year,s.month),
              npcReserved:true,contractV036:true});
            const materialBefore=f.stock[type].v;
            deliverMaterials(s,f,[]);
            const discount=Math.min(issuedCredit,Math.floor(invoice*.10));
            return {issuedCredit,cashBefore,cashAfter,creditRemaining:term.creditBase,
              expectedDiscount:discount,bookDelta:f.stock[type].v-materialBefore,
              history:f.supply.history.at(-1),errors:check(s)};
        }""")
        assert credit["issuedCredit"]>0 and credit["cashAfter"]==credit["cashBefore"],credit
        assert credit["history"]["creditBase"]==credit["expectedDiscount"],credit
        assert credit["creditRemaining"]==credit["issuedCredit"]-credit["expectedDiscount"],credit
        assert credit["bookDelta"]>0 and not credit["errors"],credit

        # UI supports an overseas NPC supplier; re-signing a live contract incurs
        # an actual booked cancellation fee. Save and restore retain terms.
        ui=page.evaluate("""() => {
            S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'契約UI'});
            saveAuto=async()=>true;PAGE='supply';VIEW_FIRM=S.playerId;render();
            const f=company(S.playerId,S);
            const supplier=document.getElementById('supplier_steel');
            const months=document.getElementById('ltMonths_steel');
            const quantity=document.getElementById('ltQty_steel');
            const enabled=document.getElementById('ltEnable_steel');
            if(!supplier||!months||!quantity||!enabled)throw Error('契約UIが存在しない');
            const hasForeign=[...supplier.options].some(x=>x.value==='NPC:US:steel');
            const beforeCash=acc(f,'cash');
            supplier.value='NPC:US:steel';months.value='24';quantity.value='20';enabled.checked=true;
            saveSupply();
            const after=contractV036(f,'steel'),afterCash=acc(f,'cash');
            const payload=savePayload(S),restored=parsePayload(payload);
            return {hasForeign,contract:after,loss:beforeCash-afterCash,
                saved:contractV036(company(S.playerId,restored),'steel'),
                errors:check(S),restoredErrors:check(restored)};
        }""")
        assert ui["hasForeign"] and ui["contract"]["supplierId"]=="NPC:US:steel",ui
        assert ui["contract"]["months"]==24 and ui["contract"]["quantity"]==20,ui
        assert ui["loss"]>0 and ui["saved"]==ui["contract"],ui
        assert not ui["errors"] and not ui["restoredErrors"],ui

        # A genuine pre-v0.36 save has no contract records; it still loads unchanged.
        migration=page.evaluate("""() => {
            const f=company(S.playerId,S);
            const before=JSON.stringify(f.stock);
            for(const firm of S.firms)for(const t of SUPPLY_TYPES)
              delete firm.supply.contracts[t].longTermV036;
            const payload=savePayload(S),restored=parsePayload(payload);
            const prev=company(restored.playerId,restored);
            return {same:before===JSON.stringify(prev.stock),
               disabled:SUPPLY_TYPES.every(t=>!contractV036(prev,t)),
               errors:check(restored)};
        }""")
        assert migration["same"] and migration["disabled"] and not migration["errors"],migration

        for era in (1900,1960,2010):
            page.evaluate("""(era) => {
              saveAuto=async()=>true;
              S=newGame({era,country:'JP',difficulty:'normal',history:'historical',name:'契約長期運営'});
            }""",era)
            for i in range(12):
                result=page.evaluate("""async() => {
                  const before=S.monthCommitted;
                  await runMonth();
                  const c=consolidate(S);
                  return {advanced:S.monthCommitted===before+1,errors:check(S),
                    grouped:c.errors,cf:c.cf.reconciled,diagnostic:LAST_MONTH_DIAGNOSTIC?.message};
                }""")
                assert result["advanced"] and not result["errors"] and not result["grouped"] and result["cf"],(era,i,result)
        assert not errors,errors
        browser.close()

if __name__=="__main__":
    run()
    print("PASS v0.36: contract reserve, shortfall credits, international UI, penalty, 3x12-month accounting")
