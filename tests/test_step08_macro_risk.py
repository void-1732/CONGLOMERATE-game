"""Check the macroeconomy, trade shock lifecycle, and risk mitigation on real books."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / 'index.html'


def check_macro(page):
    observed = page.evaluate("""()=>{
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'経済危機の検証'});
        VIEW_FIRM=S.playerId;
        nextMonthDate(S);
        const baseline=structuredClone(S),month=ym(S.year,S.month),f=current();
        const cashOpening=acc(f,'cash');
        startEconomicShockV044(S,'financial',['DE'],{id:'TEST-credit',months:3});
        startEconomicShockV044(S,'energy',['JP'],{id:'TEST-energy',months:3});
        const before=marketDemandSnapshotV031(baseline,'DE').demand;
        const after=marketDemandSnapshotV031(S,'DE').demand;
        const neighboring=economicExposureV044(S,'FR').demand;
        const unaffected=economicExposureV044(S,'US').demand;
        const resource=supplierPriceBase(S,{country:'JP',type:'steel'});
        const originalPrice=supplierPriceBase(baseline,{country:'JP',type:'steel'});
        produceNpcV033(baseline,[]);produceNpcV033(S,[]);
        const capacities=[npcMarketV033(baseline,'JP','steel').lastEffectiveCapacity,npcMarketV033(S,'JP','steel').lastEffectiveCapacity];
        updateWorld(baseline,{});updateWorld(S,{});
        const shock={rates:[baseline.world.DE.rate,S.world.DE.rate],inflation:[baseline.world.JP.inflation,S.world.JP.inflation],
            currency:[baseline.world.DE.fx,S.world.DE.fx]};
        const restored=parsePayload(savePayload(S));
        const failure=structuredClone(restored);failure.economicShocksV044[0].countries=['void'];
        for(let i=0;i<3;i++)nextMonthDate(restored);
        const ended=activeEconomicShocksV044(restored).length;
        const history=structuredClone(S);history.year=1907;history.month=10;
        advanceEconomicShocksV044(history,[]);advanceEconomicShocksV044(history,[]);
        const historical=history.economicShocksV044.filter(event=>event.id==='1907-credit').length;
        PAGE='market';VIEW_COUNTRY='JP';render();
        return {before,after,neighboring,unaffected,resource,originalPrice,capacities,shock,
         cashPreserved:cashOpening===acc(f,'cash'),ended,historical,errors:check(restored),badState:check(failure),month};
    }""")
    assert observed['after'] == round(observed['before'] * .72), observed
    assert .72 < observed['neighboring'] < 1 and observed['unaffected'] == 1, observed
    assert observed['resource'] > observed['originalPrice'] and observed['capacities'][1] < observed['capacities'][0], observed
    s = observed['shock']
    assert s['rates'][1] > s['rates'][0] and s['inflation'][1] > s['inflation'][0] and s['currency'][1] < s['currency'][0], observed
    assert observed['cashPreserved'] and observed['ended'] == 0 and observed['historical'] == 1, observed
    assert not observed['errors'] and observed['badState'], observed
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.get_by_role('heading', name='国際経済・供給網リスク').is_visible()
    assert page.get_by_text('金融危機', exact=False).count() >= 1
    assert page.get_by_role('button', name='安全在庫・代替調達・契約').is_enabled()


def check_trade_and_disaster(page):
    observed = page.evaluate("""()=>{
        S=newGame({era:1960,country:'JP',difficulty:'normal',history:'historical',name:'通商と災害の検証'});
        VIEW_FIRM=S.playerId;
        const f=current(),m=f.models[0];
        post(f,{goods:18000},{cash:18000},'災害試験の輸出在庫','operating',S);
        f.goods[m.id].q+=3;f.goods[m.id].v+=18000;
        exportShipment(S,f,m.id,3,m.priceBase,'US',[]);
        const cargo=f.distribution.outbound[0],initial=cargo.internationalV041.routeId,book=acc(f,'goodsTransit');
        while(ym(S.year,S.month)<cargo.due)nextMonthDate(S);
        startEconomicShockV044(S,'disaster',['JP']);
        const originDuty=tariffRateV041(S,'JP','US','vehicle');
        startEconomicShockV044(S,'tariff',['JP','US'],{lane:['JP','US']});
        const duty=tariffRateV041(S,'JP','US','vehicle');
        deliverExports(S,[]);
        const rerouted=cargo.internationalV041.routeId;
        const ban=startEconomicShockV044(S,'sanctions',['JP','US'],{lane:['JP','US'],months:4});
        while(ym(S.year,S.month)<cargo.due)nextMonthDate(S);
        const limit=internationalQuoteV041(S,'JP','US','vehicle',m.priceBase);
        const other=internationalQuoteV041(S,'DE','FR','vehicle',m.priceBase);
        deliverExports(S,[]);
        const inTransit=acc(f,'goodsTransit'),soldBefore=acc(f,'sales');
        while(ym(S.year,S.month)<ban.end)nextMonthDate(S);
        Object.assign(S.world.US,{demand:100,cycle:0,war:false});
        f._salesNow=0;f._unitsNow=0;f.marketThisMonth={};
        deliverExports(S,[]);
        const customs=f.journals.find(j=>j.text.startsWith('輸出品の通関・代替輸送'));
        return {initial,rerouted,book,inTransit,soldBefore,blocked:!limit,other:!!other,duty,originDuty,
          imported:f.marketThisMonth.US?.units,remaining:acc(f,'goodsTransit'),customs:customs?.amount,errors:check(S)};
    }""")
    assert observed['initial'] == 'JP/US/sea' and observed['rerouted'] == 'JP/US/alternateSea', observed
    assert observed['blocked'] and observed['other'] and observed['duty'] > observed['originDuty'], observed
    assert observed['soldBefore'] == 0 and observed['book'] == observed['inTransit'] > 0, observed
    assert observed['imported'] == 3 and observed['remaining'] == 0 and observed['customs'] > 0 and not observed['errors'], observed


def check_mitigation(page):
    result = page.evaluate("""async()=>{
        const fresh=()=>newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'危機対策の比較'});
        saveAuto=async()=>true;render=()=>{};
        const prepare=(s,stocked,drain)=>{
            const f=company(s.playerId,s),steel=f.stock.steel,model=f.models[0];
            post(f,{otherExpense:steel.v},{materials:steel.v},'対策比較の開始前消費','operating',s);
            f.stock.steel={q:0,v:0};
            f.plans[model.id]=12;
            const market=npcMarketV033(s,'JP','steel'),c=f.supply.contracts.steel;
            c.backupId=npcIdV033('US','steel');c.backupShareV040=50;c.safetyMonths=stocked?2:.25;
            if(stocked){
                const qty=Math.min(market.stock,Math.ceil(materialRequirement(model.design,f).steel*15));
                const cost=localFromBase(qty*supplierPriceBase(s,{country:'JP',type:'steel',npc:true}),'JP');
                post(f,{materials:cost},{cash:cost},'危機前の安全在庫確保','operating',s);
                f.stock.steel={q:qty,v:cost};market.stock-=qty;market.dispatchedTotal+=qty;
            }
            if(drain){market.dispatchedTotal+=market.stock;market.stock=0;}
            return f;
        };
        const baseline=fresh(),buffered=structuredClone(baseline);
        prepare(baseline,false,true);prepare(buffered,true,true);
        const output=[];
        for(const game of [baseline,buffered]){
            S=game;VIEW_FIRM=S.playerId;
            startEconomicShockV044(S,'disaster',['JP']);
            const date=S.monthCommitted;
            await runMonth();
            const f=current(),g=consolidate(S);
            output.push({approved:S.monthCommitted===date+1,units:f._produced,errors:check(S),cf:g.cf.reconciled,
             alternate:f.supply.inbound.find(row=>row.type==='steel'&&row.origin==='US')?.internationalV041?.routeId});
        }
        const priced=fresh(),source={country:'JP',type:'steel',npc:true};
        const locked=supplierPriceBase(priced,source),variable=structuredClone(priced);
        const prices=[];
        for(const [game,mode] of [[priced,'fixed'],[variable,'market']]){
            const f=prepare(game,false,false),term=contractV036(f,'steel');
            Object.assign(term,{quantity:4,priceMode:mode,unitBase:locked});
            startEconomicShockV044(game,'energy',['JP']);
            procureNetwork(game,[]);
            const entry=f.supply.history.find(row=>row.type==='steel'&&row.qty===4&&row.origin==='JP');
            prices.push(entry?.totalBase/4);
        }
        return {output,locked,prices};
    }""")
    exposed, buffered = result['output']
    assert exposed['alternate'] == 'US/JP/alternateSea' and 0 <= exposed['units'] < buffered['units'], result
    assert all(row['approved'] and row['cf'] and not row['errors'] for row in result['output']), result
    assert result['prices'][0] == result['locked'] < result['prices'][1], result
    print(f"Mitigation: {exposed['units']} versus {buffered['units']} vehicles, fixed/market steel {result['prices']}")


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium'),
                                             args=['--no-sandbox'])
        page = browser.new_page(offline=True)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content(HTML.read_text(encoding='utf-8'), wait_until='domcontentloaded')
        check_macro(page)
        check_trade_and_disaster(page)
        check_mitigation(page)
        assert not errors, errors
        browser.close()
    print('PASS STEP 8: regional cycles, rates, inflation, FX, physical supply, sanctions, tariffs, routing, and saves')
