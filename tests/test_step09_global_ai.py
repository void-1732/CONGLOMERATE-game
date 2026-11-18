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
        japan.stock=Math.max(600,japan.stock);america.stock=Math.max(600,america.stock);
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
        assert not errors, errors
        browser.close()
    print('PASS STEP 9: policy mode, regional override, UI, save, finite supply and 24-month ledger reconciliation')
