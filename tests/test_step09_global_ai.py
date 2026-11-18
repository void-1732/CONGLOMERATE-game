"""STEP 9 unit 1: opt-in global purchasing, country overrides and ledger-safe month runs."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

HTML = Path(__file__).resolve().parents[1] / 'index.html'


def policy_and_save(page):
    result = page.evaluate("""()=>{
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'グループ調達AI検証'});
        VIEW_FIRM=S.playerId;
        const f=current(),original=structuredClone(f.supply.contracts);
        const manual=supplyPolicyModeV045(S,f);
        const noPolicy=policySupplierV045(S,{f,type:'steel',needed:20},new Map(),new Map());
        const japan=npcMarketV033(S,'JP','steel'),america=npcMarketV033(S,'US','steel');
        // Fixture injects only accounted NPC production, never free inventory.
        for(const market of [japan,america]){
            const added=Math.max(0,600-market.stock);
            market.stock+=added;market.producedTotal+=added;
        }
        ensureSupplyNetwork(S);
        const nodes=new Map(S.supplyNetwork.nodes.map(node=>[node.id,node]));
        const remaining=new Map(),request={f,type:'steel',needed:20};
        f.globalSupplyPolicyV045={mode:'domestic',regions:{}};
        const domestic=policySupplierV045(S,request,nodes,remaining);
        f.globalSupplyPolicyV045={mode:'cost',regions:{JP:'domestic',US:'stable'}};
        const override=supplyPolicyModeV045(S,f);
        const best=policySupplierV045(S,request,nodes,remaining);
        const saved=parsePayload(savePayload(S)),restored=saved.firms.find(item=>item.id===saved.playerId);
        const unchanged=JSON.stringify(original)===JSON.stringify(f.supply.contracts);
        const invalid=structuredClone(S);
        invalid.firms.find(item=>item.id===invalid.playerId).globalSupplyPolicyV045.mode='invalid';
        PAGE='supply';render();
        return {manual,noPolicy,domestic,override,best,unchanged,
          restored:restored.globalSupplyPolicyV045,invalid:check(invalid),errors:check(S)};
    }""")
    assert result['manual'] == 'manual' and result['noPolicy'] is None, result
    assert result['domestic'] == 'NPC:JP:steel', result
    assert result['override'] == 'domestic' and result['best'], result
    assert result['unchanged'] and result['restored']['mode'] == 'cost', result
    assert result['restored']['regions'] == {'JP': 'domestic', 'US': 'stable'}, result
    assert result['invalid'] and not result['errors'], result
    assert page.get_by_role('heading', name='国際供給網AI・グループ調達方針').is_visible()
    page.locator('#supplyPolicyModeV045').select_option('stable')
    page.locator('#supplyPolicyRegionV045_JP').select_option('group')
    page.get_by_role('button', name='グループ調達方針を保存').click()
    after = page.evaluate("""()=>({
        selected:S.firms.find(x=>x.id===S.playerId).globalSupplyPolicyV045,
        errors:check(S),restored:parsePayload(savePayload(S)).firms.find(x=>x.id===S.playerId).globalSupplyPolicyV045
    })""")
    assert after['selected'] == after['restored'], after
    assert after['selected']['mode'] == 'stable' and after['selected']['regions']['JP'] == 'group', after
    assert not after['errors'], after


def run_with_policy(page):
    observed = page.evaluate("""async()=>{
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'調達AI会計検証'});
        VIEW_FIRM=S.playerId;saveAuto=async()=>true;render=()=>{};
        S.firms.find(x=>x.id===S.playerId).globalSupplyPolicyV045={mode:'stable',regions:{JP:'domestic'}};
        const initial=ym(S.year,S.month),runs=[];
        for(let i=0;i<24;i++){
            const currentMonth=S.monthCommitted;
            await runMonth();
            if(S.monthCommitted!==currentMonth+1)return {failed:i,error:LAST_MONTH_DIAGNOSTIC?.message};
            const errors=check(S),accounts=consolidate(S);
            if(errors.length||accounts.errors.length||!accounts.cf.reconciled)
                return {failed:i,errors,accounts:accounts.errors,cf:accounts.cf.reconciled};
            runs.push(S.firms.find(f=>f.id===S.playerId).supply.lastAttempt.steel.ordered||0);
        }
        const saved=parsePayload(savePayload(S));
        return {count:runs.length,total:runs.reduce((a,b)=>a+b,0),
          mode:supplyPolicyModeV045(saved,saved.firms.find(f=>f.id===saved.playerId)),
          elapsed:ym(S.year,S.month)-initial,errors:check(saved)};
    }""")
    assert observed.get('count') == 24, observed
    assert observed['elapsed'] == 24 and observed['mode'] == 'domestic', observed
    assert not observed['errors'], observed



def logistics_policy_and_save(page):
    result = page.evaluate("""()=>{
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'物流方針検証'});
        VIEW_FIRM=S.playerId;
        const root=current();
        const missing=logisticsPolicyModeV045(S,root);
        root.globalSupplyPolicyV045={
            mode:'manual',regions:{},logistics:{mode:'fast',regions:{JP:'resilient',US:'economy'}}
        };
        const chosen=logisticsPolicyModeV045(S,root);
        const bad=structuredClone(S);
        bad.firms.find(f=>f.id===bad.playerId).globalSupplyPolicyV045.logistics.regions.JP='invalid';
        const saved=parsePayload(savePayload(S));
        PAGE='supply';render();
        return {missing,chosen,bad:check(bad),errors:check(S),
            saved:saved.firms.find(f=>f.id===saved.playerId).globalSupplyPolicyV045.logistics};
    }""")
    assert result['missing'] == 'manual' and result['chosen'] == 'resilient', result
    assert result['saved']['regions'] == {'JP': 'resilient', 'US': 'economy'}, result
    assert result['bad'] and not result['errors'], result
    assert page.get_by_role('heading', name='工場・倉庫の自動補充方針').is_visible()
    page.locator('#logisticsPolicyModeV045').select_option('economy')
    page.locator('#logisticsPolicyRegionV045_JP').select_option('fast')
    page.get_by_role('button', name='グループ調達方針を保存').click()
    after = page.evaluate("""()=>{
        const f=current(),source=f.globalSupplyPolicyV045;
        const restored=parsePayload(savePayload(S)).firms.find(x=>x.id===S.playerId).globalSupplyPolicyV045;
        return {mode:logisticsPolicyModeV045(S,f),source,restored,errors:check(S)};
    }""")
    assert after['mode'] == 'fast' and after['source'] == after['restored'], after
    assert after['source']['logistics']['mode'] == 'economy', after
    assert not after['errors'], after


def logistics_physical_transfer(page):
    result = page.evaluate("""()=>{
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'現物補充検証'});
        VIEW_FIRM=S.playerId;
        const f=current(),home=homeSite(f.country);
        const away=SITE_CATALOG.find(site=>site.country===f.country&&site.id!==home.id);
        if(!away)return {failed:'同国内に第二拠点がありません'};
        const p=f.plants.find(plant=>['integrated','assembly'].includes(plant.kind));
        if(!p)return {failed:'生産工場がありません'};
        p.siteId=away.id;p.siteCountry=away.country;
        const logistics=ensureWarehouseV038(f);
        logistics.autoRefill=true;logistics.localizedRawTypes=['steel'];
        f.globalSupplyPolicyV045={
            mode:'manual',regions:{},logistics:{mode:'resilient',regions:{}}
        };
        const opening=centralRawStockV038(f,'steel').q,events=[];
        const scoreFast=logisticsOriginScoreV045(S,f,away,{id:'warehouse',site:home},'steel','fast');
        const scoreLocal=logisticsOriginScoreV045(S,f,away,{id:'onSite',site:away,stock:{steel:{q:50}}},'steel','fast');
        autoRefillRawFactoriesV038(S,events);
        const dispatched=logistics.rawShipments.filter(shipment=>shipment.to===p.id&&shipment.type==='steel');
        const closing=centralRawStockV038(f,'steel').q;
        const restored=parsePayload(savePayload(S));
        return {opening,closing,scoreFast,scoreLocal,dispatched,events,errors:check(S),
            restoredShipments:restored.firms.find(row=>row.id===f.id).inventoryLogisticsV038.rawShipments};
    }""")
    assert 'failed' not in result and result['scoreLocal'] < result['scoreFast'], result
    assert result['opening'] > 0, result
    assert result['dispatched'] and result['dispatched'][0]['quantity'] > 0, result
    assert result['opening'] - result['closing'] == sum(x['quantity'] for x in result['dispatched']), result
    assert len(result['dispatched']) == len(result['restoredShipments']), result
    assert not result['errors'], result



def group_network_allocation(page):
    result = page.evaluate("""()=>{
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'グループ全体調達の検証'});
        VIEW_FIRM=S.playerId;
        const buyer=current(),sourceAmounts=[6,9],suppliers=[];
        for(const [index,qty] of sourceAmounts.entries()){
            const firm=initFirm(S,{name:'グループ試験鉱山'+index,country:'JP',
                industry:'resource',seedBase:3000000});
            firm.owners=[{id:buyer.id,econ:1,vote:1}];
            firm.shareBlocks=[];
            ensureRawV032(firm);
            const bin=rawBinV032(firm,'steel'),value=qty*1000;
            post(firm,{goods:value},{cash:value},'確認済み実在庫','operating',S);
            bin.q=qty;bin.v=value;
            suppliers.push(firm);
        }
        buyer.globalSupplyPolicyV045={mode:'group',regions:{},
            logistics:{mode:'manual',regions:{}}};
        for(const model of buyer.models.filter(m=>m.status==='active')){
            buyer.plans[model.id]=Math.max(1000,buyer.plans[model.id]||0);
        }
        buyer.supply.contracts.steel.longTermV036.enabled=false;
        ensureSupplyNetwork(S);
        const nodes=new Map(S.supplyNetwork.nodes.map(node=>[node.id,node]));
        const pool=policyCandidatePoolV045(S,nodes);
        const entries=suppliers.map(f=>({id:'CORP:'+f.id+':steel',qty:rawBinV032(f,'steel').q}));
        const remaining=new Map(entries.map(x=>[x.id,x.qty]));
        const request={f:buyer,type:'steel',needed:40};
        const chosen=policySupplierV045(S,request,nodes,remaining,pool);
        remaining.set(chosen,0);
        const alternate=policySupplierV045(S,request,nodes,remaining,pool);
        remaining.set(alternate,0);
        const external=policySupplierV045(S,request,nodes,remaining,pool);
        const overview=groupSupplyOverviewV045(S).find(x=>x.type==='steel');
        PAGE='supply';render();
        const before=suppliers.map(f=>rawBinV032(f,'steel').q);
        const stockBefore=buyer.stock.steel.q;
        const events=[];
        procureNetwork(S,events);
        const after=suppliers.map(f=>rawBinV032(f,'steel').q);
        const stockAfter=buyer.stock.steel.q;
        const saved=parsePayload(savePayload(S));
        const groupReceipts=buyer.supply.history.filter(x=>x.type==='steel'&&x.group)
            .reduce((n,x)=>n+x.qty,0);
        return {entries,chosen,alternate,external,overview,before,after,stockBefore,stockAfter,
            groupReceipts,errors:check(S),restoredErrors:check(saved),events:events.length};
    }""")
    ids = {x['id'] for x in result['entries']}
    assert result['chosen'] in ids and result['alternate'] in ids, result
    assert result['chosen'] != result['alternate'], result
    assert result['external'].startswith('NPC:'), result
    assert result['overview']['free'] == sum(x['qty'] for x in result['entries']), result
    assert result['overview']['supplierCount'] == 2, result
    assert result['groupReceipts'] > 0, result
    assert sum(result['before']) - sum(result['after']) == result['groupReceipts'], result
    assert result['stockAfter'] >= result['stockBefore'] + result['groupReceipts'], result
    assert not result['errors'] and not result['restoredErrors'], result
    assert page.get_by_role('heading', name='グループ供給網・需給バランス').is_visible()



def world_maturation(page):
    baseline = page.evaluate("""()=>{
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'世界市場成熟検証'});
        const legacy=structuredClone(S),evolving=structuredClone(S);
        legacy.year=1950;evolving.year=1950;
        evolving.worldEvolutionV046={enabled:true,anchorYear:1900};
        const legacyFactor=worldDevelopmentV046(legacy,'JP').factor;
        const changed=worldDevelopmentV046(evolving,'JP');
        updateWorld(legacy,{});updateWorld(evolving,{});
        const w=legacy.world.JP,base=COUNTRIES.JP;
        const oldFormula=Math.max(10,Math.round(base.demand*(w.pop/base.pop)**1.1*
            (w.wealth/base.wealth)**.66*(1+w.cycle)*1.1));
        const saved=parsePayload(savePayload(evolving));
        const bad=structuredClone(saved);bad.worldEvolutionV046.anchorYear=1700;
        return {legacyFactor,changed,oldFormula,legacyDemand:w.demand,
            newDemand:evolving.world.JP.demand,restored:saved.worldEvolutionV046,
            invalid:validateWorldEvolutionV046(bad),errors:check(saved)};
    }""")
    assert baseline['legacyFactor'] == 1, baseline
    assert baseline['changed']['factor'] > 1, baseline
    assert baseline['legacyDemand'] == baseline['oldFormula'], baseline
    assert baseline['newDemand'] > baseline['legacyDemand'], baseline
    assert baseline['restored'] == {'enabled': True, 'anchorYear': 1900}, baseline
    assert baseline['invalid'] and not baseline['errors'], baseline

    page.evaluate("""()=>{
        S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'成熟モデルUI'});
        VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='marketRegion';render();
    }""")
    assert page.get_by_role('heading', name='年代別市場発展・自動車普及モデル').is_visible()
    page.locator('#worldEvolutionModeV046').select_option('evolving')
    page.get_by_role('button', name='世界市場の発展方針を保存').click()
    check = page.evaluate("""()=>({
        source:S.worldEvolutionV046,
        restored:parsePayload(savePayload(S)).worldEvolutionV046,
        errors:check(S)
    })""")
    assert check['source'] == check['restored'], check
    assert check['source']['enabled'] and not check['errors'], check

    endurance = page.evaluate("""async()=>{
        saveAuto=async()=>true;render=()=>{};
        const start=ym(S.year,S.month);
        for(let i=0;i<12;i++){
            const before=S.monthCommitted;
            await runMonth();
            if(S.monthCommitted!==before+1)return {failed:i,reason:LAST_MONTH_DIAGNOSTIC?.message};
            const errors=check(S),financial=consolidate(S);
            if(errors.length||financial.errors.length||!financial.cf.reconciled)
                return {failed:i,errors,financialErrors:financial.errors};
        }
        return {months:ym(S.year,S.month)-start,settings:parsePayload(savePayload(S)).worldEvolutionV046,
            errors:check(S)};
    }""")
    assert endurance.get('months') == 12, endurance
    assert endurance['settings']['enabled'] and not endurance['errors'], endurance


if __name__ == '__main__':
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium'),
            args=['--no-sandbox'])
        page = browser.new_page(offline=True)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.set_content(HTML.read_text(encoding='utf-8'), wait_until='domcontentloaded')
        policy_and_save(page)
        run_with_policy(page)
        logistics_policy_and_save(page)
        logistics_physical_transfer(page)
        group_network_allocation(page)
        # document.write alone retains the previous JS realm (and its render stub).
        page.goto('about:blank')
        page.set_content(HTML.read_text(encoding='utf-8'), wait_until='domcontentloaded')
        world_maturation(page)
        assert not errors, errors
        browser.close()
    print('PASS STEP 9: global stock network, regional logistics, simulated market maturation, save and 24-month accounting')
