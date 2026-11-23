"""Run the Phase 4 browser cases and require actual receipts on all sourced routes."""

import json

import test_world_phase4_corridors
import test_world_phase4_credit
import test_world_phase4_international
import test_world_phase4_markets
import test_world_phase4_transshipment


def main():
    expected_markets = set()
    expected_routes = set()
    expected_countries = set()
    receipts = set()
    prefix = "WORLD_FREIGHT_RECEIPT "

    def observe(page):
        catalog = page.evaluate("""() => ({
          markets: WORLD_MARKETS.map(m=>m.id),
          routes: Object.keys(WORLD_INTERNATIONAL_ROUTE_EVIDENCE),
          countries: Object.keys(WORLD_ENGINE_TERRITORY)
        })""")
        expected_markets.update(catalog["markets"])
        expected_routes.update(catalog["routes"])
        expected_countries.update(catalog["countries"])

        def record(message):
            if message.text.startswith(prefix):
                receipts.add(tuple(json.loads(message.text[len(prefix):])))

        page.on("console", record)
        page.evaluate("""prefix => {
          const receive=worldInternationalReceiveShipments;
          const market=code=>WORLD_TERRITORIES.get(WORLD_ENGINE_TERRITORY[code]).marketId;
          worldInternationalReceiveShipments=function(state,events){
            const shipments=state.worldExpansion?.internationalShipments??[];
            const delivered=new Set(shipments.filter(t=>t.status==='DELIVERED').map(t=>t.id));
            receive(state,events);
            for(const t of shipments){
              if(t.status!=='DELIVERED'||delivered.has(t.id))continue;
              const profile=state.worldExpansion.internationalRoutes[t.routeId].profileId;
              const seller=company(t.sellerId,state).country,buyer=company(t.buyerId,state).country;
              console.log(prefix+JSON.stringify([profile,seller,buyer,market(seller),market(buyer)]));
            }
          };
        }""", prefix)

    for test in (
        test_world_phase4_international,
        test_world_phase4_credit,
        test_world_phase4_corridors,
        test_world_phase4_markets,
        test_world_phase4_transshipment,
    ):
        test.main(observe_receipts=observe)

    markets = {market for _, _, _, seller, buyer in receipts for market in (seller, buyer)}
    routes = {receipt[0] for receipt in receipts}
    countries = {code for _, seller, buyer, _, _ in receipts for code in (seller, buyer)}
    assert countries == expected_countries, {
        "missingJurisdictions": sorted(expected_countries - countries),
        "unexpectedJurisdictions": sorted(countries - expected_countries),
    }
    assert len(expected_markets) == 40 and markets == expected_markets, {
        "missingMarkets": sorted(expected_markets - markets),
        "unexpectedMarkets": sorted(markets - expected_markets),
    }
    assert routes == expected_routes, {
        "missingRoutes": sorted(expected_routes - routes),
        "unexpectedRoutes": sorted(routes - expected_routes),
    }
    print("PASS world freight coverage", json.dumps({
        "markets": sorted(markets),
        "marketCount": len(markets),
        "routeCount": len(routes),
        "engineJurisdictionCount": len(countries),
        "receivedRoutes": sorted(receipts),
    }, ensure_ascii=False))


def audit_monthly_receipts():
    """Every evidenced route must deliver via runMonth, not manual time jumps."""
    import os
    import shutil
    from pathlib import Path
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
                                     args=["--no-sandbox"])
        page = browser.new_context(offline=True).new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        ids = page.evaluate("Object.keys(WORLD_INTERNATIONAL_ROUTE_EVIDENCE)")
        assert len(ids) >= 53
        receipts = []
        for route_id in ids:
            result = page.evaluate("""async id=>{
 const p=worldInternationalProfile(id),e=WORLD_INTERNATIONAL_ROUTE_EVIDENCE[id],product=e.products?.[0]??'PRD-R19';
 S=newWorldGame({country:'JP',name:'Monthly freight audit'});
 VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='reports';
 const parent=company(S.playerId,S);
 const open=worldInternationalOpeningMonth(p,e);
 const date=m=>{S.year=Math.floor(m/12);S.month=m%12+1;S.monthCommitted=m-1;applyWorldHistory(S);syncWorldIdentities(S)};
 let first=open,found=false;
 for(;first<Math.min(e.untilMonth??open+36,open+36);first++){
  date(first);
  if(!worldInternationalRouteAvailable(S,id))continue;
  date(first+1);
  if(worldInternationalRouteAvailable(S,id)){date(first);found=true;break}
 }
 if(!found)throw Error('no open pair');
 // 1994 channel companies are founded in 1900, with matching opening books.
 if(p.mode==='road+rail-shuttle'){S=newWorldGame({country:'JP',name:'Monthly freight audit'});VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';}
 const root=company(S.playerId,S);
 const make=(code,name)=>{
  const cap=localFromBase(750000,root.country),j=S.seq;
  post(root,{investment:cap},{cash:cap},'監査用法人払込','investing',S);
  const f=initFirm(S,{name,country:code,industry:'manufacturing',seedBase:750000,size:.5,publicOwnership:false});
  f.owners=[{id:root.id,econ:1,vote:1}];
  registerEquityLink(S,{parentId:root.id,childId:f.id,ratio:1,kind:'foundation',considerationLocal:cap,buyerJournal:j,
   childJournal:f.journals.find(j=>j.text==='創業資本').id,bookEquityBase:baseFromLocal(financials(f).equity,code),cashAcquiredBase:baseFromLocal(acc(f,'cash'),code)});
  f.auto=false;f.research.tree.done=[...new Set([...f.research.tree.done,'production-1'])];return f;
 };
 let seller=make(findSite(p.from).country,'Exporter'),buyer=make(findSite(p.to).country,'Importer');
 if(p.mode==='road+rail-shuttle')date(first);
 seller.plants[0].siteId=p.from;buyer.plants[0].siteId=p.to;
 // Paid fixture inventory; this does not assert local production of all cargo.
 const put=(f,key,q)=>{const v=Math.max(q,localFromBase(200*q,f.country));post(f,{materials:v},{cash:v},'監査用有償現物','operating',S);const old=f.stock[key]??{q:0,v:0};f.stock[key]={q:old.q+q,v:old.v+v}};
 for(const key of p.vehicles??[p.truck])put(seller,key,1);
 for(const key of p.terminals??['PRD-E20'])put(buyer,key,1);
 put(seller,product,20);
 put(seller,p.fuel,Math.max(20,worldInternationalFuelRequired(p,2)+20));
 if(p.transfer){
  const terminal={id:'P'+S.seq++,name:'横浜新港',siteId:'JP-YOK',siteCountry:'JP',capacity:15,kind:'assembly',scale:'small',condition:100,focus:'all',construction:null,lastProduced:0,lastUtilization:0};
  const cost=localFromBase(siteInvestmentQuote('JP-YOK','small','assembly',S),'JP');
  post(seller,{ppe:cost},{cash:cost},'監査用有償積替拠点','investing',S);seller.plants.push(terminal);syncPlant(seller);syncWorldIdentities(S);
  put(seller,'PRD-E20',1);worldInstallDomesticWarehouse(S,seller.id,terminal.id,'JP-YOKOHAMA-SHINKO');
 }
 syncWorldIdentities(S);
 const route=worldInternationalRegisterRoute(S,seller.id,id),wh=worldInternationalInstallWarehouse(S,buyer.id,buyer.plants[0].id,id);
 const price=Math.max(100,Math.ceil(seller.stock[product].v/seller.stock[product].q*1.25)),q=worldInternationalQuote(S,route,product,2,price,buyer.id,0,2);
 if(q.problem)throw Error(q.problem+' '+JSON.stringify({cash:acc(buyer,'cash'),materials:acc(seller,'materials'),price}));
 const order=worldInternationalPlaceOrder(S,buyer.id,{routeId:route.id,warehouseId:wh.id,productId:product,quantity:2,cargoLitres:2,unitPriceSeller:price,maxPaymentBuyer:Math.max(100000,q.totalBuyer*2)});
 worldInternationalActOrder(S,seller.id,order.id,'approve');saveAuto=async()=>true;
 const close=async()=>{const m=ym(S.year,S.month);await runMonth();if(S.monthCommitted!==m||LAST_MONTH_DIAGNOSTIC)throw Error('close '+m+' '+LAST_MONTH_DIAGNOSTIC?.message);seller=company(seller.id,S);buyer=company(buyer.id,S);return S.worldExpansion.internationalShipments.find(t=>t.orderId===order.id)};
 await close();let cargo=await close();
 if(cargo?.status!=='IN_TRANSIT'||cargo.quantity!==2||acc(seller,'worldShipmentStock')!==cargo.bookCost||buyer.stock[product]?.q)throw Error('dispatch '+JSON.stringify(S.worldExpansion.internationalOrders.at(-1)));
 for(let i=0;i<12&&cargo.status==='IN_TRANSIT';i++)cargo=await close();
 if(cargo.status!=='DELIVERED')throw Error('not delivered '+JSON.stringify(cargo));
 const saved=parsePayload(savePayload(S)),g=consolidate(saved);
 return {id,received:cargo.receivedAt,tariffBps:cargo.tariffBps,ok:cargo.tariffBps===WORLD_PHASE4_TARIFF_BPS[buyer.country]
  &&cargo.dutyBuyer===Math.round(cargo.goodsSeller*cargo.sellerRate/cargo.buyerRate*cargo.tariffBps/10000)
  &&buyer.stock[product]?.q===2&&buyer.stock[product].v===cargo.totalBuyer&&acc(seller,'worldShipmentStock')===0&&acc(buyer,'worldSupplierAdvances')===0&&!check(saved).length&&!g.errors.length&&g.cf.reconciled};
}""", route_id)
            assert result["ok"], result
            receipts.append(result)
        assert len(receipts) == len(ids) and not errors, errors
        print("PASS monthly world freight", json.dumps(receipts, ensure_ascii=False))
        browser.close()


if __name__ == "__main__":
    main()
    audit_monthly_receipts()
