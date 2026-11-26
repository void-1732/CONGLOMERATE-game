"""Market onboarding, measured freight, calendar settlement, and V2 save upgrade."""
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def test_all_market_coverage(page):
    """Every connected engine country must have a sourced freight corridor."""
    result = page.evaluate("""() => {
      const state=newWorldGame({country:'JP',name:'Phase 4 coverage audit'});
      const countries=new Set(Object.keys(WORLD_ENGINE_TERRITORY));
      const sourced=Object.entries(WORLD_INTERNATIONAL_CORRIDORS).filter(([id,p])=>
        p.source?.startsWith('https://') &&
        WORLD_INTERNATIONAL_ROUTE_EVIDENCE[id]?.source?.startsWith('https://'));
      const connected=new Set(sourced.flatMap(([,p])=>
        [findSite(p.from)?.country,findSite(p.to)?.country]));
      const missing=[...countries].filter(code=>!connected.has(code));
      const markets=WORLD_MARKETS.every(m=>countries.has(WORLD_ENGINE_BY_MARKET[m.id])
        &&m.cities.every(c=>{
          const loc=worldCityLocation(state,c.id);
          return loc.marketId===m.id&&loc.territoryId===c.territoryId
            &&(loc.jurisdictionId==null?loc.marketOpen===false:true);
        }));
      const integrity=sourced.every(([id,p])=>p.from!==p.to
        &&findSite(p.from)?.country!==findSite(p.to)?.country
        &&p.capacityKg>0&&p.transitMonths>0&&p.opensAt>=WORLD_START_MONTH
        &&WORLD_INTERNATIONAL_ROUTE_EVIDENCE[id].source?.startsWith('https://'));
      return {markets,integrity,allForty:countries.size===connected.size&&countries.has('BE')
        &&WORLD_MARKETS.length===40&&WORLD_CITIES.size===155&&!missing.length,
        missing};
    }""")
    assert result["markets"] and result["integrity"] and result["allForty"], result


def test_australia(page):
    result = page.evaluate("""async () => {
      const buyerConfig={country:'JP',name:'Yokohama wool importer'};
      const old=newWorldGame(buyerConfig,true);
      old.worldExpansion=makeWorldExpansion(1);syncWorldIdentities(old);
      for(const code of Object.keys(old.world)){
        if(!worldInitialEngineCountries(1).includes(code))delete old.world[code];
      }
      old.year=1906;old.month=1;old.monthCommitted=ym(1906,1)-1;
      applyWorldHistory(old);syncWorldIdentities(old);
      const restored=parsePayload(savePayload(old));
      const migration=restored.world.AU?.code==='AU'&&restored.world.NO?.code==='NO'
        &&restored.worldExpansion.appliedEvents.some(e=>e.id==='HIST-AU-1901')
        &&restored.worldExpansion.appliedEvents.some(e=>e.id==='HIST-NO-1905')
        &&restored.worldExpansion.appliedEvents.length
          ===worldHistoryThrough(ym(old.year,old.month),WORLD_MARKET_REGISTRY_VERSION).length
        &&new Set(restored.worldExpansion.appliedEvents.map(e=>e.id)).size
          ===restored.worldExpansion.appliedEvents.length
        &&JSON.stringify(restored.worldExpansion.companies)===JSON.stringify(old.worldExpansion.companies)
        &&restored.rng===old.rng&&!check(restored).length;

      S=newWorldGame(buyerConfig);VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';
      const profile='AU-JP-SYDNEY-WOOL';
      const initiallyClosed=!S.world.AU&&!worldCityLocation(S,'CITY-24-01').marketOpen
        &&!worldInternationalRouteAvailable(S,profile);
      advanceFreightFixtureMonth(12);S.monthCommitted=ym(1900,12)-1;
      saveAuto=async()=>true;await runMonth();
      const opened=S.monthCommitted===ym(1900,12)&&S.world.AU?.code==='AU'
        &&worldCityLocation(S,'CITY-24-01').jurisdictionId==='JUR-AU'
        &&S.worldExpansion.openMarkets['MKT-24']===ym(1901,1)
        &&!worldInternationalRouteAvailable(S,profile);
      S.year=1913;S.month=5;S.monthCommitted=ym(1913,5)-1;
      applyWorldHistory(S);syncWorldIdentities(S);
      PAGE='corporateSubsidiaries';render();
      document.querySelector('#subName').value='Sydney wool exporter';
      document.querySelector('#subCountry').value='AU';
      document.querySelector('#subIndustry').value='manufacturing';
      document.querySelector('#subCapital').value='750000';
      createSub();
      const buyer=company(S.playerId),seller=S.firms.find(f=>f.name==='Sydney wool exporter');
      buyer.plants[0].siteId='JP-YOK';
      const plant=seller.plants[0];
      for(const firm of [buyer,seller]){
        firm.auto=false;firm.research.tree.done=[...new Set([...firm.research.tree.done,'production-1'])];
      }
      for(const [firm,id,value] of [[seller,'PRD-E18',2400],[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
        post(firm,{materials:value},{cash:value},'検証用の有償現物設備','operating',S);
        firm.stock[id]={q:1,v:value};
      }
      syncWorldIdentities(S);
      const identities=firmCurrency(seller,S)==='AUD'
        &&S.worldExpansion.companies[seller.id].jurisdictionId==='JUR-AU'
        &&S.worldExpansion.facilities['FAC-'+plant.id].locationId==='LOC-AU-SYD';
      const purchase=worldBuyRegionalSupply(S,seller.id,plant.id,'AU-SYD-WOOL',12);
      worldBuyRegionalSupply(S,seller.id,plant.id,'AU-SYD-BUNKER-COAL',25);
      const route=worldInternationalRegisterRoute(S,seller.id,profile);
      const warehouse=worldInternationalInstallWarehouse(S,buyer.id,buyer.plants[0].id,profile);
      const fullQuote=worldInternationalQuote(S,route,'PRD-R21',12,10,buyer.id,90,32);
      if(fullQuote.problem)throw Error(fullQuote.problem);
      const order=worldInternationalPlaceOrder(S,buyer.id,{routeId:route.id,warehouseId:warehouse.id,
        productId:'PRD-R21',quantity:12,cargoLitres:32,unitPriceSeller:10,
        maxPaymentBuyer:Math.ceil(fullQuote.totalBuyer*1.1),paymentDays:90});
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      advanceFreightFixtureMonth(6);worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const [cargo]=S.worldExpansion.internationalShipments;
      const dispatch=purchase.quantity===12&&cargo?.status==='IN_TRANSIT'&&cargo.quantity===12&&cargo.loadKg===16
        &&cargo.totalBuyer===fullQuote.totalBuyer&&cargo.freightSeller===worldFreightCharge(worldInternationalProfile(profile,S),16,'AU',S)
        &&cargo.prepaidBuyer>cargo.prepaidSeller&&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R21']?.q;
      advanceFreightFixtureMonth(8);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const prepaid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(1913,8);
      advanceFreightFixtureMonth(9);worldInternationalReceiveShipments(S);
      const held=cargo.status==='IN_TRANSIT'&&cargo.customs?.arrivalAt===ym(1913,9)
        &&cargo.customs.releasedAt===null&&cargo.customs.duty===cargo.dutyBuyer&&cargo.tariffBps===350
        &&cargo.customs.authorityId==='CUSTOMS-JP-YOK-1911'&&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R21']?.q&&worldInternationalTradePanel(buyer,true).includes('保税・通関審査中')
        &&parsePayload(savePayload(S)).worldExpansion.internationalShipments[0].customs.arrivalAt===ym(1913,9);
      const beforeMap=JSON.stringify(S);
      PAGE='worldMap';render();
      document.querySelector('[data-world-map-select-route="'+profile+'"]').click();
      const freightRow=document.querySelector('[data-world-map-shipment="'+cargo.id+'"]');
      const bondedMap=document.querySelectorAll('[data-world-map-freight-site]').length===1
        &&document.querySelector('[data-world-map-freight-site="JP-YOK"]')!==null
        &&freightRow?.cells[3].textContent==='保税・通関審査中'
        &&freightRow?.cells[4].textContent.includes('[JP-YOK]')
        &&freightRow?.cells[5].textContent==='1913年10月'&&JSON.stringify(S)===beforeMap;
      const forged=structuredClone(S);forged.worldExpansion.internationalShipments[0].customs.releasedAt=ym(1913,9);
      let prematureRejected=false;
      try{parsePayload(savePayload(forged));}catch{prematureRejected=true;}
      advanceFreightFixtureMonth(10);worldInternationalReceiveShipments(S);
      const reopened=parsePayload(savePayload(S));
      const settle=cargo.status==='DELIVERED'&&buyer.stock['PRD-R21'].q===12
        &&buyer.stock['PRD-R21'].v===cargo.totalBuyer&&!acc(seller,'worldShipmentStock')
        &&reopened.worldExpansion.internationalShipments[0].receivedAt===ym(1913,10)
        &&reopened.worldExpansion.internationalShipments[0].customs.releasedAt===ym(1913,10)
        &&!check(reopened).length&&!consolidate(reopened).errors.length;
      return {migration,initiallyClosed,opened,identities,dispatch,prepaid,held,bondedMap,prematureRejected,settle};
    }""")
    assert all(result.values()), result


def test_new_zealand(page):
    result = page.evaluate("""async () => {
      S=newWorldGame({country:'UK',name:'London wool importer'});VIEW_FIRM=S.playerId;VIEW_COUNTRY='UK';
      S.year=1907;S.month=9;S.monthCommitted=ym(1907,9)-1;
      applyWorldHistory(S);syncWorldIdentities(S);
      const before=!S.world.NZ&&!worldCityLocation(S,'CITY-25-02').marketOpen;
      saveAuto=async()=>true;await runMonth();
      const opened=worldCityLocation(S,'CITY-25-02');
      const opensOnDominion=S.monthCommitted===ym(1907,9)&&opened.jurisdictionId==='JUR-NZ'
        &&opened.marketOpen&&S.worldExpansion.openMarkets['MKT-25']===ym(1907,10)
        &&S.worldExpansion.appliedEvents.find(e=>e.id==='HIST-NZ-1907')?.effectiveDate==='1907-09-26';
      const profile='NZ-UK-WELLINGTON-WOOL',noEarlyRoute=!worldInternationalRouteAvailable(S,profile);
      S.year=1913;S.month=1;S.monthCommitted=ym(1913,1)-1;
      // This fixture jumps over the 1910 history events before testing payment.
      applyWorldHistory(S);syncWorldIdentities(S);
      PAGE='corporateSubsidiaries';render();
      document.querySelector('#subName').value='Wellington wool exporter';
      document.querySelector('#subCountry').value='NZ';
      document.querySelector('#subIndustry').value='manufacturing';
      document.querySelector('#subCapital').value='650000';
      createSub();
      const buyer=company(S.playerId),seller=S.firms.find(f=>f.name==='Wellington wool exporter');
      const destination=buyer.plants[0],port=seller.plants[0];
      destination.siteId='UK-LON';
      for(const firm of [buyer,seller]){
        firm.auto=false;firm.research.tree.done=[...new Set([...firm.research.tree.done,'production-1'])];
      }
      for(const [firm,id,value] of [[seller,'PRD-E18',2400],[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
        post(firm,{materials:value},{cash:value},'検証用の有償現物設備','operating',S);
        firm.stock[id]={q:1,v:value};
      }
      syncWorldIdentities(S);
      const identities=firmCurrency(seller,S)==='NZD'&&firmCurrency(buyer,S)==='GBP'
        &&S.worldExpansion.companies[seller.id].jurisdictionId==='JUR-NZ'
        &&S.worldExpansion.companies[seller.id].jurisdictionId!==S.worldExpansion.companies[buyer.id].jurisdictionId
        &&S.worldExpansion.facilities['FAC-'+port.id].locationId==='LOC-NZ-WLG';
      const purchase=worldBuyRegionalSupply(S,seller.id,port.id,'NZ-WLG-WOOL',10);
      worldBuyRegionalSupply(S,seller.id,port.id,'NZ-WLG-BUNKER-COAL',35);
      const route=worldInternationalRegisterRoute(S,seller.id,profile);
      const warehouse=worldInternationalInstallWarehouse(S,buyer.id,destination.id,profile);
      const order=worldInternationalPlaceOrder(S,buyer.id,{routeId:route.id,warehouseId:warehouse.id,
        productId:'PRD-R21',quantity:10,cargoLitres:24,unitPriceSeller:12,maxPaymentBuyer:100000,paymentDays:30});
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      advanceFreightFixtureMonth(2);worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const [cargo]=S.worldExpansion.internationalShipments;
      const dispatched=purchase.quantity===10&&cargo?.status==='IN_TRANSIT'&&cargo.loadKg===12
        &&cargo.fuelRequired===worldInternationalFuelRequired(worldInternationalProfile(profile,S),12)&&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&cargo.prepaidBuyer===Math.round(cargo.prepaidSeller*cargo.sellerRate/cargo.buyerRate);
      const dueDate=cargo.credit.dueDate==='1913-03-03';
      advanceFreightFixtureMonth(3);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const bank=cargo.credit.remittance;
      const roundtrip=parsePayload(savePayload(S));
      const held=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===null&&bank.sentAt===ym(1913,3)
        &&bank.bankId==='BANK-BNZ-GBP'&&acc(buyer,'worldBankRemittance')===bank.principal
        &&!acc(seller,'worldCustomerAdvances')&&!buyer.stock['PRD-R21']?.q
        &&acc(company(buyer.id,roundtrip),'worldBankRemittance')===bank.principal
        &&worldInternationalTradePanel(buyer,true).includes('外部銀行で送金中');
      const forged=structuredClone(S);forged.worldExpansion.internationalShipments[0].credit.remittance.principal++;
      let forgedRejected=false;
      try{parsePayload(savePayload(forged));}catch{forgedRejected=true;}

      const cancelled=structuredClone(S);
      cancelled.month=6;applyWorldHistory(cancelled);syncWorldIdentities(cancelled);
      const buyerAtCancellation=company(buyer.id,cancelled),cashBefore=acc(buyerAtCancellation,'cash');
      const voided=worldInternationalRefundShipment(cancelled,cargo.id);
      const refunded=voided.status==='REFUNDED'&&voided.credit.remittance.returnedAt===ym(1913,6)
        &&!acc(buyerAtCancellation,'worldBankRemittance')&&acc(buyerAtCancellation,'cash')===cashBefore+bank.principal
        &&!check(parsePayload(savePayload(cancelled))).length;

      advanceFreightFixtureMonth(4);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const prepaid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(1913,4)&&!buyer.stock['PRD-R21']?.q
        &&!acc(buyer,'worldBankRemittance')&&acc(buyer,'worldSupplierAdvances')===cargo.prepaidBuyer
        &&-acc(seller,'worldCustomerAdvances')===cargo.prepaidSeller&&!worldInternationalCashPairs(S).length;
      advanceFreightFixtureMonth(5);worldInternationalReceiveShipments(S);
      const restored=parsePayload(savePayload(S));
      const settled=cargo.status==='DELIVERED'&&buyer.stock['PRD-R21'].q===10
        &&buyer.stock['PRD-R21'].v===cargo.totalBuyer&&!acc(seller,'worldShipmentStock')
        &&restored.worldExpansion.internationalShipments[0].receivedAt===ym(1913,5)
        &&!check(restored).length&&!consolidate(restored).errors.length;
      advanceFreightFixtureMonth(10);
      return {before,opensOnDominion,noEarlyRoute,identities,dispatched,dueDate,held,forgedRejected,refunded,prepaid,settled,
        documentedPeriod:!worldInternationalRouteAvailable(S,profile)};
    }""")
    assert all(result.values()), result


def test_steamship_export(page, market_data):
    result = page.evaluate("""({profile,country,site,city,currency,year,departure,payMonth,buyerCountry,
                              destination,product,offer,authority,customsCurrency,strictClosure=true}) => {
      S=newWorldGame({country,name:site+' exporter'});VIEW_FIRM=S.playerId;VIEW_COUNTRY=country;
      const seller=company(S.playerId),port=seller.plants[0],identity=worldCityLocation(S,city);
      const market=identity.marketOpen&&identity.jurisdictionId===WORLD_MARKET_ONBOARDING[country].jurisdictionId
        &&S.worldExpansion.openMarkets[identity.marketId]===ym(1900,1)
        &&port.siteId===site&&firmCurrency(seller,S)===currency
        &&!worldInternationalRouteAvailable(S,profile);
      S.year=year;S.month=departure-1;S.monthCommitted=ym(year,S.month)-1;
      applyWorldHistory(S);syncWorldIdentities(S);
      PAGE='corporateSubsidiaries';render();
      document.querySelector('#subName').value=destination+' importer';
      document.querySelector('#subCountry').value=buyerCountry;
      document.querySelector('#subIndustry').value='manufacturing';
      document.querySelector('#subCapital').value='650000';
      createSub();
      const buyer=S.firms.find(f=>f.name===destination+' importer'),depot=buyer.plants[0];
      depot.siteId=destination;syncWorldIdentities(S);
      for(const firm of [buyer,seller]){
        firm.auto=false;firm.research.tree.done=[...new Set([...firm.research.tree.done,'production-1'])];
      }
      const tractionAssets=worldInternationalProfile(profile).mode==='rail'
        ?[[seller,'PRD-E16',2400],[seller,'PRD-E17',2500]]
        :[[seller,'PRD-E18',2400]];
      for(const [firm,id,value] of [...tractionAssets,[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
        post(firm,{materials:value},{cash:value},'検証用の有償現物設備','operating',S);
        firm.stock[id]={q:1,v:value};
      }
      const purchase=worldBuyRegionalSupply(S,seller.id,port.id,offer,14);
      worldBuyRegionalSupply(S,seller.id,port.id,site+'-BUNKER-COAL',20);
      const route=worldInternationalRegisterRoute(S,seller.id,profile);
      const warehouse=worldInternationalInstallWarehouse(S,buyer.id,depot.id,profile);
      const order=worldInternationalPlaceOrder(S,buyer.id,{routeId:route.id,warehouseId:warehouse.id,
        productId:product,quantity:14,cargoLitres:30,unitPriceSeller:localFromBase(40,country),
        maxPaymentBuyer:1000000,paymentDays:60});
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      advanceFreightFixtureMonth(departure);worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const [cargo]=S.worldExpansion.internationalShipments;
      const shipped=purchase.quantity===14&&cargo?.status==='IN_TRANSIT'
        &&cargo.loadKg===worldInternationalLoad(worldInternationalProfile(profile),14,30).loadKg
        &&cargo.prepaidBuyer===Math.round(cargo.prepaidSeller*cargo.sellerRate/cargo.buyerRate)&&acc(seller,'worldShipmentStock')===cargo.bookCost;
      advanceFreightFixtureMonth(payMonth);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const prepaid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(year,payMonth)
        &&(!strictClosure||!worldInternationalRouteAvailable(S,profile));
      const arrival=departure+worldInternationalProfile(profile).transitMonths;
      advanceFreightFixtureMonth(arrival);worldInternationalReceiveShipments(S);
      const held=authority===null?!cargo.customs&&cargo.status==='DELIVERED':
        cargo.status==='IN_TRANSIT'&&cargo.customs?.arrivalAt===ym(year,arrival)
        &&cargo.customs.authorityId===authority
        &&cargo.customs.currencyId===(customsCurrency??'CUR-USD')
        &&cargo.customs.releasedAt===null&&cargo.customs.duty===cargo.dutyBuyer
        &&cargo.tariffBps===WORLD_PHASE4_TARIFF_BPS[buyer.country]
        &&!buyer.stock[product]?.q;
      if(authority!==null){advanceFreightFixtureMonth(arrival+1);worldInternationalReceiveShipments(S);}
      const reopened=parsePayload(savePayload(S));
      const done=cargo.status==='DELIVERED'&&buyer.stock[product].q===14
        &&buyer.stock[product].v===cargo.totalBuyer&&!acc(seller,'worldShipmentStock')
        &&reopened.worldExpansion.internationalShipments[0].receivedAt===ym(year,arrival+(authority!==null?1:0))
        &&!check(reopened).length&&!consolidate(reopened).errors.length;
      return {market,shipped,prepaid,held,done};
    }""", market_data)
    assert all(result.values()), (market_data["profile"], result)



def test_italy_coal_import(page):
    """Cardiff-to-Genoa coal, including cargo/fuel sharing one physical stock."""
    result = page.evaluate("""() => {
      const denies=fn=>{try{fn();return false}catch{return true}};
      S=newWorldGame({country:'IT',name:'Italian coal importer'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='IT';
      const buyer=company(S.playerId),depot=buyer.plants[0];
      const italyOpen=S.world.IT?.code==='IT'
        &&worldCityLocation(S,'CITY-04-01').jurisdictionId==='JUR-IT'
        &&worldCityLocation(S,'CITY-04-01').marketOpen
        &&firmCurrency(buyer,S)==='EUR'
        &&S.world.IT.fx===S.world.FR.fx
        &&S.worldExpansion.companies[buyer.id].currencyId==='CUR-EUR'
        &&depot.siteId==='IT-GEN'
        &&!worldInternationalRouteAvailable(S,'UK-IT-CARDIFF-GENOA-COAL');
      S.year=1907;S.month=7;S.monthCommitted=ym(1907,7)-1;
      applyWorldHistory(S);syncWorldIdentities(S);
      PAGE='corporateSubsidiaries';render();
      document.querySelector('#subName').value='Cardiff coal exporter';
      document.querySelector('#subCountry').value='UK';
      document.querySelector('#subIndustry').value='manufacturing';
      document.querySelector('#subCapital').value='650000';
      createSub();
      const seller=S.firms.find(f=>f.name==='Cardiff coal exporter'),port=seller.plants[0];
      port.siteId='UK-CDF';syncWorldIdentities(S);
      for(const firm of [buyer,seller]){
        firm.auto=false;firm.research.tree.done=[...new Set([...firm.research.tree.done,'production-1'])];
      }
      for(const [firm,id,value] of [[seller,'PRD-E18',2400],[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
        post(firm,{materials:value},{cash:value},'検証用の有償現物設備','operating',S);
        firm.stock[id]={q:1,v:value};
      }
      const purchase=worldBuyRegionalSupply(S,seller.id,port.id,'UK-CDF-COAL',28);
      const route=worldInternationalRegisterRoute(S,seller.id,'UK-IT-CARDIFF-GENOA-COAL');
      const warehouse=worldInternationalInstallWarehouse(S,buyer.id,depot.id,'UK-IT-CARDIFF-GENOA-COAL');
      const sharedShortage=Boolean(worldInternationalQuote(S,route,'PRD-R04',28,240,buyer.id,60,0).problem);
      const preCash=acc(buyer,'cash');
      const order=worldInternationalPlaceOrder(S,buyer.id,{
        routeId:route.id,warehouseId:warehouse.id,productId:'PRD-R04',
        quantity:12,cargoLitres:27,unitPriceSeller:240,maxPaymentBuyer:1000000,paymentDays:60});
      const queued=order.status==='OPEN'&&acc(buyer,'cash')===preCash
        &&!S.worldExpansion.internationalShipments.length;
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      advanceFreightFixtureMonth(8);worldInternationalResolveOrders(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const loaded=purchase.quantity===28&&cargo?.orderId===order.id
        &&cargo.status==='IN_TRANSIT'&&cargo.quantity===12
        &&cargo.cargoLitres===27&&cargo.loadKg===14
        &&cargo.fuelRequired===3&&cargo.fuelCost>0
        &&seller.stock['PRD-R04'].q===13
        &&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R04']?.q
        &&worldValidateInternationalLogistics(S)&&!check(S).length;
      const forged=structuredClone(S);
      forged.worldExpansion.internationalShipments.at(-1).fuelRequired++;
      const tamper=denies(()=>parsePayload(savePayload(forged)));
      advanceFreightFixtureMonth(9);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const paid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(1907,9)
        &&acc(buyer,'worldSupplierAdvances')===cargo.prepaidBuyer
        &&!buyer.stock['PRD-R04']?.q;
      advanceFreightFixtureMonth(10);worldInternationalReceiveShipments(S);
      const restored=parsePayload(savePayload(S));
      const delivered=cargo.status==='DELIVERED'&&cargo.receivedAt===ym(1907,10)
        &&buyer.stock['PRD-R04'].q===12
        &&buyer.stock['PRD-R04'].v===cargo.totalBuyer
        &&!acc(buyer,'worldSupplierAdvances')
        &&!acc(seller,'worldShipmentStock')
        &&!check(restored).length
        &&!consolidate(restored).errors.length;
      advanceFreightFixtureMonth(11);
      const closed=!worldInternationalRouteAvailable(S,'UK-IT-CARDIFF-GENOA-COAL');
      return {italyOpen,sharedShortage,queued,loaded,tamper,paid,delivered,closed};
    }""")
    assert all(result.values()), result


def test_ireland_textiles_import(page):
    """Ireland: independent economy, fixed EUR ledger, monthly physical cargo."""
    result = page.evaluate("""async () => {
 const profile='UK-IE-HOLYHEAD-DUBLIN-TEXTILES',product='PRD-M36',city='CITY-01-04';
 S=newWorldGame({country:'UK',name:'Holyhead textile exporter'});
 VIEW_FIRM=S.playerId;VIEW_COUNTRY='UK';PAGE='reports';
 let seller=company(S.playerId,S);
 const before=!S.world.IE&&!worldCityLocation(S,city).marketOpen&&!worldInternationalRouteAvailable(S,profile);
 const date=(y,m)=>{S.year=y;S.month=m;S.monthCommitted=ym(y,m)-1;applyWorldHistory(S);syncWorldIdentities(S)};
 date(1922,12);
 const preIndependence=!S.world.IE&&worldCityLocation(S,city).jurisdictionId==='JUR-UK';
 date(1923,1);
 const opened=S.world.IE?.currency==='EUR'&&S.world.IE.fx===S.world.FR.fx
  &&worldCityLocation(S,city).marketOpen&&worldCityLocation(S,city).jurisdictionId==='JUR-IE'
  &&S.worldExpansion.openMarkets['MKT-01']===ym(1900,1)&&WORLD_ENGINE_BY_MARKET['MKT-01']==='UK'
  &&!worldInternationalRouteAvailable(S,profile);
 const market=WORLD_MARKET_BY_ID.get('MKT-01'),irish=worldPhase3ConsumerQuoteForEngine(S,market,'PRD-C01','IE'),
  british=worldPhase3ConsumerQuoteForEngine(S,market,'PRD-C01','UK');
 const demand=irish.cities.length===1&&irish.cities[0].cityId===city
  &&irish.cities[0].quantity===irish.nationalQuantity&&british.cities.every(c=>c.cityId!==city);
 const legacy=structuredClone(S),old=makeWorldExpansion(20);
 for(const event of worldHistoryThrough(ym(legacy.year,legacy.month),20))recordWorldEvent(old,event);
 Object.assign(legacy.worldExpansion,{marketRegistryVersion:20,territoryJurisdictions:old.territoryJurisdictions,
  openMarkets:old.openMarkets,appliedEvents:old.appliedEvents});
 for(const [code,row] of Object.entries(WORLD_MARKET_ONBOARDING))if(row.introducedIn>20){delete legacy.world[code];delete legacy.npcSupplyV033.markets[code];}ensureSupplyNetwork(legacy);syncWorldIdentities(legacy);
 const legacyAccepted=!check(legacy).length,restoredLegacy=parsePayload(savePayload(legacy));
 const migration=legacyAccepted&&restoredLegacy.world.IE?.code==='IE'
  &&JSON.stringify(restoredLegacy.firms.map(f=>[f.id,f.owners,f.journals,f.stock]))
   ===JSON.stringify(legacy.firms.map(f=>[f.id,f.owners,f.journals,f.stock]))&&!check(restoredLegacy).length;
 date(1932,5);
 const capital=localFromBase(750000,seller.country),payer=S.seq;
 post(seller,{investment:capital},{cash:capital},'アイルランド輸入会社への払込','investing',S);
 let buyer=initFirm(S,{name:'Dublin textile importer',country:'IE',industry:'manufacturing',seedBase:750000,size:.5,publicOwnership:false});
 buyer.owners=[{id:seller.id,econ:1,vote:1}];
 registerEquityLink(S,{parentId:seller.id,childId:buyer.id,ratio:1,kind:'foundation',considerationLocal:capital,
  buyerJournal:payer,childJournal:buyer.journals.find(j=>j.text==='創業資本').id,
  bookEquityBase:baseFromLocal(financials(buyer).equity,buyer.country),cashAcquiredBase:baseFromLocal(acc(buyer,'cash'),buyer.country)});
 const port=seller.plants[0],depot=buyer.plants[0];port.siteId='UK-HOL';
 for(const f of [seller,buyer]){f.auto=false;f.research.tree.done=[...new Set([...f.research.tree.done,'production-1'])]}
 for(const [f,id,v] of [[seller,'PRD-E18',2400],[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
  post(f,{materials:v},{cash:v},'検証用の有償現物設備','operating',S);f.stock[id]={q:1,v};
 }
 syncWorldIdentities(S);
 const identity=depot.siteId==='IE-DUB'&&firmCurrency(buyer,S)==='EUR'
  &&S.worldExpansion.companies[buyer.id].jurisdictionId==='JUR-IE'
  &&S.worldExpansion.companies[buyer.id].currencyId==='CUR-EUR'
  &&worldCityLocation(S,city).historicalMoney.currencyId==='CUR-IEP';
 const line=worldMapNetwork(S).routes.find(r=>r.id===profile);
 const mapMatch=line.fromId===port.siteId&&line.toId===depot.siteId&&line.available
  &&worldMapCityFacilityStatus(S,city).status==='CONNECTED';
 const purchase=worldBuyRegionalSupply(S,seller.id,port.id,'UK-HOL-DUBLIN-TEXTILES',14);
 worldBuyRegionalSupply(S,seller.id,port.id,'UK-HOL-BUNKER-COAL',20);
 const route=worldInternationalRegisterRoute(S,seller.id,profile),h=worldInternationalInstallWarehouse(S,buyer.id,depot.id,profile);
 const price=Math.ceil(seller.stock[product].v/seller.stock[product].q*1.25);
 const quote=worldInternationalQuote(S,route,product,14,price,buyer.id,60,30);
 if(quote.problem)throw Error('quote '+JSON.stringify(quote));
 const order=worldInternationalPlaceOrder(S,buyer.id,{routeId:route.id,warehouseId:h.id,productId:product,
  quantity:14,cargoLitres:30,unitPriceSeller:price,maxPaymentBuyer:Math.max(100000,quote.totalBuyer*2),paymentDays:60});
 worldInternationalActOrder(S,seller.id,order.id,'approve');
 saveAuto=async()=>true;
 const close=async month=>{
   await runMonth();
   if(S.monthCommitted!==ym(1932,month)||LAST_MONTH_DIAGNOSTIC)
    throw Error('アイルランド月次 '+month+' '+LAST_MONTH_DIAGNOSTIC?.message);
   seller=company(seller.id,S);buyer=company(buyer.id,S);
   return S.worldExpansion.internationalShipments.at(-1);
 };
 await close(5);
 let cargo=await close(6);
 if(!cargo)throw Error('allocation '+JSON.stringify({order:S.worldExpansion.internationalOrders.at(-1),quote,price,stock:seller.stock[product]}));
 const shipped=purchase.quantity===14&&cargo.status==='IN_TRANSIT'&&cargo.loadKg===15
  &&cargo.orderId===order.id&&acc(seller,'worldShipmentStock')===cargo.bookCost
  &&!buyer.stock[product]?.q&&cargo.tariffBps===300&&cargo.sellerRate!==cargo.buyerRate;
 cargo=await close(7);
 const paid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(1932,7)
  &&acc(buyer,'worldSupplierAdvances')===cargo.prepaidBuyer&&S.consoHistory.at(-1).cf.reconciled;
 cargo=await close(8);
 const restored=parsePayload(savePayload(S)),consolidated=consolidate(restored);
 const delivered=cargo.status==='DELIVERED'&&cargo.receivedAt===ym(1932,8)&&buyer.stock[product]?.q===14
  &&buyer.stock[product].v===cargo.totalBuyer&&acc(buyer,'worldSupplierAdvances')===0&&acc(seller,'worldShipmentStock')===0
  &&!check(restored).length&&!consolidated.errors.length&&consolidated.cf.reconciled;
 if(!delivered)throw Error('receipt '+JSON.stringify({cargo,stock:buyer.stock[product],advance:acc(buyer,'worldSupplierAdvances'),sellerStock:acc(seller,'worldShipmentStock'),check:check(restored),consoErrors:consolidated.errors,cf:consolidated.cf.reconciled}));
 const forged=structuredClone(restored);forged.worldExpansion.companies[buyer.id].currencyId='CUR-IEP';
 let tamper=false;try{parsePayload(step7NativeSavePayload(forged))}catch{tamper=true}
 return {before,preIndependence,opened,demand,migration,identity,mapMatch,shipped,paid,delivered,tamper};
}""")
    assert all(result.values()), result


def test_remaining_jurisdictions(page, d):
    """Use normal monthly close for physical freight, credit and save in each new jurisdiction."""
    result=page.evaluate("""async d => {
      S=newWorldGame({country:'JP',name:'Remaining jurisdiction freight'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='reports';
      const parent=company(S.playerId,S);
      const date=(y,m)=>{S.year=y;S.month=m;S.monthCommitted=ym(y,m)-1;applyWorldHistory(S);syncWorldIdentities(S)};
      const initial=worldCityLocation(S,d.city);
      const initialGate=initial.marketOpen===!d.open;
      if(d.open){
        const [y,m]=d.open;
        date(y,m-1);
        if(S.world[d.code])throw Error('early jurisdiction '+d.code);
        date(y,m);
        if(!S.world[d.code])throw Error('missing jurisdiction '+d.code);
      }
      date(d.year,d.month);
      const identity=worldCityLocation(S,d.city);
      const primary=identity.marketId===d.market&&identity.jurisdictionId===d.jur
        &&identity.marketOpen&&WORLD_ENGINE_BY_MARKET[d.market]===d.rep
        &&Object.keys(S.worldExpansion.openMarkets).length===40;
      const legacy=structuredClone(S),old=makeWorldExpansion(21);
      for(const e of worldHistoryThrough(ym(legacy.year,legacy.month),21))recordWorldEvent(old,e);
      Object.assign(legacy.worldExpansion,{marketRegistryVersion:21,territoryJurisdictions:old.territoryJurisdictions,
        openMarkets:old.openMarkets,appliedEvents:old.appliedEvents});
      for(const [code,row] of Object.entries(WORLD_MARKET_ONBOARDING))if(row.introducedIn>21){
        delete legacy.world[code];delete legacy.npcSupplyV033.markets[code];
      }
      ensureSupplyNetwork(legacy);syncWorldIdentities(legacy);
      const upgraded=parsePayload(savePayload(legacy));
      const migration=!!upgraded.world[d.code]&&!check(upgraded).length
        &&JSON.stringify(upgraded.firms.map(f=>[f.id,f.owners,f.journals,f.stock]))===JSON.stringify(legacy.firms.map(f=>[f.id,f.owners,f.journals,f.stock]));
      const make=(code,name)=>{
        const capital=localFromBase(750000,parent.country),j=S.seq;
        post(parent,{investment:capital},{cash:capital},'輸送試験会社払込','investing',S);
        const f=initFirm(S,{name,country:code,industry:'manufacturing',seedBase:750000,size:.5,publicOwnership:false});
        f.owners=[{id:parent.id,econ:1,vote:1}];
        registerEquityLink(S,{parentId:parent.id,childId:f.id,ratio:1,kind:'foundation',considerationLocal:capital,
          buyerJournal:j,childJournal:f.journals.find(j=>j.text==='創業資本').id,
          bookEquityBase:baseFromLocal(financials(f).equity,code),cashAcquiredBase:baseFromLocal(acc(f,'cash'),code)});
        f.auto=false;f.research.tree.done=[...new Set([...f.research.tree.done,'production-1'])];
        return f;
      };
      let seller=make(d.code,d.code+' exporter'),buyer=make(d.destCountry,d.dest+' importer');
      const port=seller.plants[0],depot=buyer.plants[0];
      const location=port.siteId===d.site&&firmCurrency(seller,S)===d.currency;
      port.siteId=d.exportSite||d.site;depot.siteId=d.dest;
      for(const [f,id,v] of [...(d.rail?[[seller,'PRD-E16',2400],[seller,'PRD-E17',2500]]:[[seller,'PRD-E18',2400]]),[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
        post(f,{materials:v},{cash:v},'有償輸送設備','operating',S);f.stock[id]={q:1,v};
      }
      syncWorldIdentities(S);
      const line=worldMapNetwork(S).routes.find(r=>r.id===d.profile);
      const map=line?.fromId===port.siteId&&line.toId===depot.siteId&&line.available;
      const purchase=worldBuyRegionalSupply(S,seller.id,port.id,port.siteId+'-'+d.code+'-CARGO',14);
      worldBuyRegionalSupply(S,seller.id,port.id,port.siteId+'-BUNKER-COAL',20);
      const route=worldInternationalRegisterRoute(S,seller.id,d.profile),wh=worldInternationalInstallWarehouse(S,buyer.id,depot.id,d.profile);
      const price=Math.ceil(seller.stock[d.product].v/seller.stock[d.product].q*1.25);
      const q=worldInternationalQuote(S,route,d.product,14,price,buyer.id,60,30);
      if(q.problem)throw Error('quote '+JSON.stringify(q));
      const o=worldInternationalPlaceOrder(S,buyer.id,{routeId:route.id,warehouseId:wh.id,productId:d.product,quantity:14,cargoLitres:30,unitPriceSeller:price,maxPaymentBuyer:Math.max(100000,q.totalBuyer*2),paymentDays:60});
      worldInternationalActOrder(S,seller.id,o.id,'approve');saveAuto=async()=>true;
      const close=async m=>{
        await runMonth();
        if(S.monthCommitted!==ym(d.year,m)||LAST_MONTH_DIAGNOSTIC)throw Error(d.code+' close '+m+' '+LAST_MONTH_DIAGNOSTIC?.message);
        seller=company(seller.id,S);buyer=company(buyer.id,S);
        return S.worldExpansion.internationalShipments.at(-1);
      };
      await close(d.month);
      let cargo=await close(d.month+1);
      const shipped=purchase.quantity===14&&cargo?.orderId===o.id&&cargo.status==='IN_TRANSIT'&&cargo.quantity===14
        &&cargo.fuelRequired>0&&acc(seller,'worldShipmentStock')===cargo.bookCost&&!buyer.stock[d.product]?.q;
      cargo=await close(d.month+2);
      const paid=cargo?.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(d.year,d.month+2)
        &&acc(buyer,'worldSupplierAdvances')===cargo.prepaidBuyer;
      cargo=await close(d.month+3);
      const restored=parsePayload(savePayload(S)),group=consolidate(restored);
      const delivered=cargo?.status==='DELIVERED'&&buyer.stock[d.product]?.q===14&&buyer.stock[d.product].v===cargo.totalBuyer
        &&acc(buyer,'worldSupplierAdvances')===0&&acc(seller,'worldShipmentStock')===0&&!check(restored).length&&!group.errors.length&&group.cf.reconciled;
      const damaged=structuredClone(restored);damaged.worldExpansion.companies[seller.id].currencyId='INVALID';
      let tamper=false;try{parsePayload(step7NativeSavePayload(damaged))}catch{tamper=true}
      return {initialGate,primary,migration,location,map,shipped,paid,delivered,tamper};
    }""",d)
    assert all(result.values()), (d["code"],result)


def test_portugal_coal_import(page):
    result = page.evaluate("""async () => {
      S=newWorldGame({country:'UK',name:'Cardiff to Lisbon coal'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='UK';PAGE='corporateSubsidiaries';
      const profileId='UK-PT-CARDIFF-LISBON-COAL',cityId='CITY-05-03';
      const initiallyClosed=S.world.ES?.currency==='EUR'&&!S.world.PT
        &&worldCityLocation(S,cityId).jurisdictionId==='JUR-PT-KINGDOM'
        &&!worldCityLocation(S,cityId).marketOpen&&!worldInternationalRouteAvailable(S,profileId);
      S.year=1911;S.month=5;S.monthCommitted=ym(1911,5)-1;
      applyWorldHistory(S);syncWorldIdentities(S);render();
      const beforeReform=worldCityLocation(S,cityId).jurisdictionId==='JUR-PT-REPUBLIC'
        &&!S.world.PT&&!document.querySelector('#subCountry option[value="PT"]');
      saveAuto=async()=>true;
      await runMonth();
      const opened=S.monthCommitted===ym(1911,5)
        &&S.world.PT?.currency==='EUR'&&S.world.ES?.currency==='EUR'
        &&worldCityLocation(S,cityId).marketOpen
        &&worldCityLocation(S,cityId).historicalMoney.currencyId==='CUR-PTE'
        &&S.worldExpansion.openMarkets['MKT-05']===ym(1900,1)
        &&WORLD_ENGINE_BY_MARKET['MKT-05']==='ES'
        &&Object.keys(S.worldExpansion.openMarkets).length===40
        &&!worldInternationalRouteAvailable(S,profileId);

      S.year=1912;S.month=8;S.monthCommitted=ym(1912,8)-1;
      applyWorldHistory(S);syncWorldIdentities(S);PAGE='corporateSubsidiaries';render();
      document.querySelector('#subName').value='Lisbon coal importer';
      document.querySelector('#subCountry').value='PT';
      document.querySelector('#subIndustry').value='manufacturing';
      document.querySelector('#subCapital').value='650000';
      createSub();
      let seller=company(S.playerId),buyer=S.firms.find(f=>f.name==='Lisbon coal importer');
      const port=seller.plants[0],depot=buyer.plants[0];
      port.siteId='UK-CDF';syncWorldIdentities(S);
      const registration=S.worldExpansion.companies[buyer.id];
      const currency=registration.territoryId==='TER-05-02'
        &&registration.jurisdictionId==='JUR-PT-REPUBLIC'&&registration.currencyId==='CUR-EUR'
        &&firmCurrency(buyer,S)==='EUR'&&firmCurrency(seller,S)==='GBP'
        &&S.worldExpansion.facilities['FAC-'+depot.id].locationId==='LOC-PT-LIS';
      for(const firm of [buyer,seller]){
        firm.auto=false;firm.research.tree.done=[...new Set([...firm.research.tree.done,'production-1'])];
      }
      for(const [firm,id,value] of [[seller,'PRD-E18',2400],[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
        post(firm,{materials:value},{cash:value},'検証用の有償設備','operating',S);
        firm.stock[id]={q:1,v:value};
      }
      const source=worldBuyRegionalSupply(S,seller.id,port.id,'UK-CDF-LISBON-COAL',28);
      const route=worldInternationalRegisterRoute(S,seller.id,profileId);
      const warehouse=worldInternationalInstallWarehouse(S,buyer.id,depot.id,profileId);
      const order=worldInternationalPlaceOrder(S,buyer.id,{routeId:route.id,warehouseId:warehouse.id,
        productId:'PRD-R04',quantity:12,cargoLitres:27,unitPriceSeller:240,
        maxPaymentBuyer:1000000,paymentDays:60});
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      async function close(month){
        await runMonth();
        if(S.monthCommitted!==ym(1912,month)||LAST_MONTH_DIAGNOSTIC)
          throw Error('リスボン試験の月次処理 '+month+' '+LAST_MONTH_DIAGNOSTIC?.message);
        seller=company(seller.id,S);buyer=company(buyer.id,S);
        return S.worldExpansion.internationalShipments.at(-1);
      }
      await close(8);
      let cargo=await close(9);
      const shipped=cargo?.status==='IN_TRANSIT'&&cargo.orderId===order.id&&cargo.loadKg===14
        &&cargo.sellerRate!==cargo.buyerRate&&!buyer.stock['PRD-R04']?.q
        &&seller.stock['PRD-R04'].q===source.quantity-cargo.quantity-cargo.fuelRequired
        &&acc(seller,'worldShipmentStock')===cargo.bookCost;
      cargo=await close(10);
      const paid=cargo.status==='IN_TRANSIT'&&cargo.credit.dueDate==='1912-10-31'
        &&cargo.credit.paidAt===ym(1912,10)&&acc(buyer,'worldSupplierAdvances')===cargo.prepaidBuyer
        &&S.consoHistory.at(-1).cf.reconciled;
      cargo=await close(11);
      const restored=parsePayload(savePayload(S)),consolidated=consolidate(restored);
      const delivered=cargo.status==='DELIVERED'&&buyer.stock['PRD-R04'].q===12
        &&acc(buyer,'worldSupplierAdvances')===0&&acc(seller,'worldShipmentStock')===0
        &&buyer.stock['PRD-R04'].v===cargo.totalBuyer
        &&restored.worldExpansion.internationalShipments.at(-1).receivedAt===ym(1912,11)
        &&!check(restored).length&&!consolidated.errors.length&&consolidated.cf.reconciled;
      const forged=structuredClone(restored);
      forged.worldExpansion.companies[buyer.id].currencyId='CUR-PTE';
      let auditRejects=false;
      try{parsePayload(step7NativeSavePayload(forged));}catch{auditRejects=true;}
      return {initiallyClosed,beforeReform,opened,currency,shipped,paid,delivered,auditRejects};
    }""")
    assert all(result.values()), result


def test_south_africa_union(page):
    """Historical 1910 Union gate and sourced 1911 Cape-to-London wool."""
    result = page.evaluate("""() => {
      const fail=fn=>{try{fn();return false}catch{return true}};
      S=newWorldGame({country:'UK',name:'London wool buyer'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='UK';
      const profile='ZA-UK-CAPE-WOOL',buyer=company(S.playerId);
      const closed=!S.world.ZA&&!worldCityLocation(S,'CITY-33-03').marketOpen
        &&!worldInternationalRouteAvailable(S,profile);
      S.year=1910;S.month=5;S.monthCommitted=ym(1910,5)-1;
      applyWorldHistory(S);
      const beforeUnion=!S.world.ZA;
      S.month=6;applyWorldHistory(S);syncWorldIdentities(S);
      const opened=S.world.ZA?.code==='ZA'&&worldCityLocation(S,'CITY-33-03').marketOpen
        &&S.worldExpansion.openMarkets['MKT-33']===ym(1910,6)
        &&S.worldExpansion.appliedEvents.some(e=>e.effectiveDate==='1910-05-31')
        &&firmCurrency(buyer,S)==='GBP';
      S.year=1911;S.month=5;S.monthCommitted=ym(1911,5)-1;
      applyWorldHistory(S);syncWorldIdentities(S);
      PAGE='corporateSubsidiaries';render();
      document.querySelector('#subName').value='Cape wool exporter';
      document.querySelector('#subCountry').value='ZA';
      document.querySelector('#subIndustry').value='manufacturing';
      document.querySelector('#subCapital').value='650000';
      createSub();
      const seller=S.firms.find(f=>f.name==='Cape wool exporter'),port=seller.plants[0],depot=buyer.plants[0];
      depot.siteId='UK-LON';
      for(const firm of [seller,buyer]){
        firm.auto=false;firm.research.tree.done=[...new Set([...firm.research.tree.done,'production-1'])];
      }
      for(const [firm,id,value] of [[seller,'PRD-E18',2400],[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
        post(firm,{materials:value},{cash:value},'検証用の有償現物設備','operating',S);
        firm.stock[id]={q:1,v:value};
      }
      syncWorldIdentities(S);
      const identity=worldCityLocation(S,'CITY-33-03');
      const jurisdictions=identity.jurisdictionId==='JUR-ZA-UNION'
        &&firmCurrency(seller,S)==='ZAR'
        &&S.worldExpansion.companies[seller.id].currencyId==='CUR-ZAR'
        &&S.worldExpansion.companies[seller.id].jurisdictionId!==
          S.worldExpansion.companies[buyer.id].jurisdictionId;
      const wool=worldBuyRegionalSupply(S,seller.id,port.id,'ZA-CPT-WOOL',14);
      worldBuyRegionalSupply(S,seller.id,port.id,'ZA-CPT-BUNKER-COAL',22);
      const route=worldInternationalRegisterRoute(S,seller.id,profile);
      const wh=worldInternationalInstallWarehouse(S,buyer.id,depot.id,profile);
      const terms={
        routeId:route.id,warehouseId:wh.id,productId:'PRD-R21',
        quantity:14,cargoLitres:30,unitPriceSeller:45,maxPaymentBuyer:1000000,paymentDays:60};
      const bankFixture=structuredClone(S);
      const order=worldInternationalPlaceOrder(S,buyer.id,terms);
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      advanceFreightFixtureMonth(6);worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const freight=wool.quantity===14&&cargo?.orderId===order.id
        &&cargo.status==='IN_TRANSIT'&&cargo.quantity===14
        &&cargo.loadKg===15&&cargo.fuelRequired>0
        &&cargo.prepaidBuyer===Math.round(cargo.prepaidSeller*cargo.sellerRate/cargo.buyerRate)
        &&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R21']?.q&&!check(S).length;
      const tampered=structuredClone(S);tampered.worldExpansion.internationalShipments.at(-1).loadKg++;
      const tamperRejected=fail(()=>parsePayload(savePayload(tampered)));
      advanceFreightFixtureMonth(7);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const paid=cargo.credit.paidAt===ym(1911,7)&&!cargo.credit.remittance;
      advanceFreightFixtureMonth(9);worldInternationalReceiveShipments(S);
      const saved=parsePayload(savePayload(S));
      const delivered=cargo.status==='DELIVERED'&&buyer.stock['PRD-R21'].q===14
        &&buyer.stock['PRD-R21'].v===cargo.totalBuyer
        &&acc(seller,'worldShipmentStock')===0
        &&!check(saved).length&&!consolidate(saved).errors.length;
      advanceFreightFixtureMonth(10);
      const expired=!worldInternationalRouteAvailable(S,profile);

      S=bankFixture;
      const importer=company(buyer.id),exporter=company(seller.id);
      const bankId='BANK-STANDARD-ZA-GBP';
      const invalidBankRejected=fail(()=>worldInternationalPlaceOrder(S,importer.id,
        {...terms,bankId:'BANK-BNZ-GBP'}))&&fail(()=>worldInternationalPlaceOrder(S,importer.id,
        {...terms,bankId,paymentDays:0}));
      VIEW_FIRM=importer.id;VIEW_COUNTRY='UK';PAGE='logisticsHubs';render();
      const form=document.querySelector('form[data-world-international="order"]');
      for(const [name,value] of [
        ['choice',[route.id,wh.id,terms.productId,bankId].join('|')],
        ['quantity',terms.quantity],['cargoLitres',terms.cargoLitres],['price',terms.unitPriceSeller],
        ['limit',terms.maxPaymentBuyer],['paymentDays',terms.paymentDays]
      ])form.elements.namedItem(name).value=String(value);
      form.requestSubmit();
      const bankOrder=S.worldExpansion.internationalOrders[0];
      const submitted=bankOrder?.bankId===bankId&&bankOrder.paymentDays===60;
      worldInternationalActOrder(S,exporter.id,bankOrder.id,'approve');
      advanceFreightFixtureMonth(6);worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const [bankCargo]=S.worldExpansion.internationalShipments;
      const payment=bankCargo.credit.remittance;
      const cashBefore=acc(importer,'cash'),sellerBefore=acc(exporter,'cash');
      advanceFreightFixtureMonth(7);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const pending=parsePayload(savePayload(S));
      const pendingPayment=pending.worldExpansion.internationalShipments[0].credit.remittance;
      const escrow=payment?.bankId===bankId&&payment.currencyId==='CUR-GBP'
        &&pendingPayment.sentAt===ym(1911,7)&&payment.principal===bankCargo.prepaidBuyer
        &&bankCargo.credit.paidAt===null&&acc(importer,'worldBankRemittance')===payment.principal
        &&acc(importer,'cash')===cashBefore-payment.principal&&acc(exporter,'cash')===sellerBefore
        &&!check(pending).length&&!consolidate(pending).errors.length;
      const altered=structuredClone(pending);
      delete altered.worldExpansion.internationalOrders[0].bankId;
      const bankTamperRejected=fail(()=>parsePayload(savePayload(altered)));
      advanceFreightFixtureMonth(8);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const remitted=bankCargo.credit.paidAt===ym(1911,8)&&bankCargo.status==='IN_TRANSIT'
        &&acc(importer,'worldBankRemittance')===0&&acc(importer,'cash')===cashBefore-bankCargo.totalBuyer
        &&acc(exporter,'cash')===sellerBefore+bankCargo.prepaidSeller
        &&worldInternationalTradePanel(importer,true).includes(bankId);
      advanceFreightFixtureMonth(9);worldInternationalReceiveShipments(S);
      const final=parsePayload(savePayload(S));
      const bankDelivered=bankCargo.status==='DELIVERED'
        &&importer.stock['PRD-R21'].v===bankCargo.totalBuyer
        &&final.worldExpansion.internationalShipments[0].credit.remittance.bankId===bankId
        &&!check(final).length&&!consolidate(final).errors.length;
      return {closed,beforeUnion,opened,jurisdictions,freight,tamperRejected,paid,delivered,
        expired,invalidBankRejected,submitted,escrow,bankTamperRejected,remitted,bankDelivered};
    }""")
    assert all(result.values()), result


def test_nigeria_colonial_cocoa(page):
    """1914 colonial amalgamation gate, fixed modern NGN ledger, 1922 Lagos-Liverpool cargo."""
    result = page.evaluate("""() => {
      const rejects=fn=>{try{fn();return false;}catch{return true;}};
      S=newWorldGame({country:'UK',name:'Liverpool cocoa importer'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='UK';
      const buyer=company(S.playerId),routeId='NG-UK-LAGOS-COCOA';
      const initiallyClosed=!S.world.NG&&!worldCityLocation(S,'CITY-35-01').marketOpen
        &&!worldInternationalRouteAvailable(S,routeId);
      S.year=1913;S.month=12;S.monthCommitted=ym(1913,12)-1;
      applyWorldHistory(S);
      const preUnion=!S.world.NG;
      S.year=1914;S.month=1;S.monthCommitted=ym(1914,1)-1;
      applyWorldHistory(S);syncWorldIdentities(S);
      const opened=S.world.NG?.code==='NG'
        &&S.worldExpansion.openMarkets['MKT-35']===ym(1914,1)
        &&worldCityLocation(S,'CITY-35-01').jurisdictionId==='JUR-NG-COLONY'
        &&S.worldExpansion.appliedEvents.some(e=>e.id==='HIST-NG-1914');
      S.year=1922;S.month=4;S.monthCommitted=ym(1922,4)-1;
      applyWorldHistory(S);syncWorldIdentities(S);
      PAGE='corporateSubsidiaries';render();
      document.querySelector('#subName').value='Lagos cocoa producer';
      document.querySelector('#subCountry').value='NG';
      document.querySelector('#subIndustry').value='manufacturing';
      document.querySelector('#subCapital').value='650000';
      createSub();
      const seller=S.firms.find(f=>f.name==='Lagos cocoa producer'),port=seller.plants[0],depot=buyer.plants[0];
      depot.siteId='UK-LIV';
      for(const f of [seller,buyer]){
        f.auto=false;f.research.tree.done=[...new Set([...f.research.tree.done,'production-1'])];
      }
      for(const [f,id,value] of [[seller,'PRD-E18',2400],[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
        post(f,{materials:value},{cash:value},'検証用の有償現物設備','operating',S);
        f.stock[id]={q:1,v:value};
      }
      syncWorldIdentities(S);
      const identity=S.worldExpansion.companies[seller.id];
      const jurisdiction=identity.jurisdictionId==='JUR-NG-COLONY'
        &&identity.currencyId==='CUR-NGN'&&firmCurrency(seller,S)==='NGN'
        &&worldUsesModernCurrency(S)
        &&S.worldExpansion.facilities['FAC-'+port.id].locationId==='LOC-NG-LAG';
      const originalStock=worldBuyRegionalSupply(S,seller.id,port.id,'NG-LAG-COCOA',14);
      worldBuyRegionalSupply(S,seller.id,port.id,'NG-LAG-BUNKER-COAL',20);
      const route=worldInternationalRegisterRoute(S,seller.id,routeId);
      const warehouse=worldInternationalInstallWarehouse(S,buyer.id,depot.id,routeId);
      const order=worldInternationalPlaceOrder(S,buyer.id,{
        routeId:route.id,warehouseId:warehouse.id,productId:'PRD-R28',
        quantity:14,cargoLitres:30,unitPriceSeller:40,
        maxPaymentBuyer:1000000,paymentDays:60});
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      advanceFreightFixtureMonth(5);worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const shipped=originalStock.quantity===14&&cargo?.status==='IN_TRANSIT'
        &&cargo.quantity===14&&cargo.loadKg===15&&cargo.fuelRequired>0
        &&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R28']?.q&&!check(S).length;
      const forged=structuredClone(S);forged.worldExpansion.internationalShipments.at(-1).cargoLitres++;
      const tamper=rejects(()=>parsePayload(savePayload(forged)));
      advanceFreightFixtureMonth(6);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const prepaid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(1922,6)
        &&!worldInternationalRouteAvailable(S,routeId);
      advanceFreightFixtureMonth(7);worldInternationalReceiveShipments(S);
      const restored=parsePayload(savePayload(S));
      const delivered=cargo.status==='DELIVERED'&&buyer.stock['PRD-R28'].q===14
        &&buyer.stock['PRD-R28'].v===cargo.totalBuyer
        &&!acc(seller,'worldShipmentStock')
        &&!check(restored).length&&!consolidate(restored).errors.length;
      const floating=structuredClone(restored);floating.world.NG.fx*=1.01;
      const independentRate=floating.world.NG.fx;
      floating.world.UK.fx*=1.05;worldMatchLedgerCurrencyRates(floating);
      const roundtrip=parsePayload(savePayload(floating));
      const independentFx=independentRate!==restored.world.NG.fx
        &&roundtrip.world.NG.fx===independentRate&&roundtrip.world.NG.currency==='NGN'
        &&JSON.stringify(roundtrip.firms)===JSON.stringify(restored.firms);
      return {initiallyClosed,preUnion,opened,jurisdiction,shipped,tamper,prepaid,delivered,independentFx};
    }""")
    assert all(result.values()), result


def test_philippines_sugar_customs(page):
    """1903 gold peso, 1909 duty-free sugar quota, 1911 actual cargo/receipt."""
    result=page.evaluate("""() => {
      const reject=fn=>{try{fn();return false;}catch{return true}};
      S=newWorldGame({country:'US',name:'San Francisco sugar buyer'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='US';
      const buyer=company(S.playerId),profileId='PH-US-MANILA-SUGAR';
      const before=!S.world.PH&&!worldCityLocation(S,'CITY-23-01').marketOpen;
      S.year=1903;S.month=3;S.monthCommitted=ym(1903,3)-1;applyWorldHistory(S);
      const prePeso=!S.world.PH;
      S.month=4;applyWorldHistory(S);syncWorldIdentities(S);
      const opened=S.world.PH?.code==='PH'
        &&S.worldExpansion.openMarkets['MKT-23']===ym(1903,4)
        &&worldCityLocation(S,'CITY-23-01').jurisdictionId==='JUR-PH-INSULAR'
        &&S.worldExpansion.appliedEvents.some(e=>e.id==='HIST-PH-1903');
      S.year=1911;S.month=4;S.monthCommitted=ym(1911,4)-1;
      applyWorldHistory(S);syncWorldIdentities(S);
      PAGE='corporateSubsidiaries';render();
      document.querySelector('#subName').value='Manila sugar exporter';
      document.querySelector('#subCountry').value='PH';
      document.querySelector('#subIndustry').value='manufacturing';
      document.querySelector('#subCapital').value='650000';
      createSub();
      const seller=S.firms.find(f=>f.name==='Manila sugar exporter'),port=seller.plants[0],depot=buyer.plants[0];
      depot.siteId='US-SFO';
      for(const f of [buyer,seller]){
        f.auto=false;f.research.tree.done=[...new Set([...f.research.tree.done,'production-1'])];
      }
      for(const [f,id,v] of [[seller,'PRD-E18',2400],[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
        post(f,{materials:v},{cash:v},'検証用の有償現物設備','operating',S);
        f.stock[id]={q:1,v};
      }
      syncWorldIdentities(S);
      const identity=S.worldExpansion.companies[seller.id];
      const peg=identity.jurisdictionId==='JUR-PH-INSULAR'&&identity.currencyId==='CUR-PHP'
        &&worldUsesModernCurrency(S)&&firmCurrency(seller,S)==='PHP';
      const sugar=worldBuyRegionalSupply(S,seller.id,port.id,'PH-MNL-SUGAR',14);
      const unitPriceSeller=Math.ceil(sugar.amount/sugar.quantity)+1;
      worldBuyRegionalSupply(S,seller.id,port.id,'PH-MNL-BUNKER-COAL',21);
      const route=worldInternationalRegisterRoute(S,seller.id,profileId);
      const wh=worldInternationalInstallWarehouse(S,buyer.id,depot.id,profileId);
      const order=worldInternationalPlaceOrder(S,buyer.id,{
        routeId:route.id,warehouseId:wh.id,productId:'PRD-M40',quantity:14,
        cargoLitres:30,unitPriceSeller,maxPaymentBuyer:1000000,paymentDays:60});
      const freeQuota=worldInternationalQuote(S,route,'PRD-M40',14,unitPriceSeller,buyer.id,60,30).tariffBps===300
        &&WORLD_INTERNATIONAL_CUSTOMS[profileId].annualQuotaKg===304814400;
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      advanceFreightFixtureMonth(5);worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const shipped=cargo?.status==='IN_TRANSIT'&&cargo.quantity===14
        &&cargo.tariffBps===300&&cargo.dutyBuyer===Math.round(cargo.goodsSeller*cargo.sellerRate/cargo.buyerRate*.03)&&cargo.loadKg===15
        &&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-M40']?.q&&!check(S).length;
      advanceFreightFixtureMonth(6);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const paid=cargo.credit.paidAt===ym(1911,6)&&!worldInternationalRouteAvailable(S,profileId);
      advanceFreightFixtureMonth(7);worldInternationalReceiveShipments(S);
      const held=cargo.status==='IN_TRANSIT'&&cargo.customs?.arrivalAt===ym(1911,7)
        &&cargo.customs.releasedAt===null&&cargo.customs.authorityId==='CUSTOMS-US-SFO-PH1909';
      const altered=structuredClone(S);altered.worldExpansion.internationalShipments.at(-1).customs.duty++;
      const tamper=reject(()=>parsePayload(savePayload(altered)));
      advanceFreightFixtureMonth(8);worldInternationalReceiveShipments(S);
      const saved=parsePayload(savePayload(S));
      const settled=cargo.status==='DELIVERED'&&buyer.stock['PRD-M40'].q===14
        &&buyer.stock['PRD-M40'].v===cargo.totalBuyer
        &&cargo.customs.releasedAt===ym(1911,8)
        &&!acc(seller,'worldShipmentStock')&&!check(saved).length
        &&!consolidate(saved).errors.length;
      const floating=structuredClone(saved);floating.world.PH.fx*=1.01;
      const independentRate=floating.world.PH.fx;
      floating.world.US.fx*=1.05;worldMatchLedgerCurrencyRates(floating);
      const roundtrip=parsePayload(savePayload(floating));
      const independentFx=independentRate!==saved.world.PH.fx
        &&roundtrip.world.PH.fx===independentRate&&roundtrip.world.PH.currency==='PHP'
        &&JSON.stringify(roundtrip.firms)===JSON.stringify(saved.firms);
      return {before,prePeso,opened,peg,freeQuota,shipped,paid,held,tamper,settled,independentFx};
    }""")
    assert all(result.values()),result


def test_korean_colonial_rice(page):
    """1910 annexation, fixed modern KRW ledger, 1914 Busan rice shipment."""
    result=page.evaluate("""() => {
      const rejects=fn=>{try{fn();return false;}catch{return true;}};
      S=newWorldGame({country:'JP',name:'Osaka rice importer'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';
      const buyer=company(S.playerId),profileId='KR-JP-BUSAN-RICE';
      const initiallyClosed=!S.world.KR&&!worldCityLocation(S,'CITY-17-02').marketOpen;
      S.year=1910;S.month=8;S.monthCommitted=ym(1910,8)-1;applyWorldHistory(S);
      const beforeAnnexation=!S.world.KR;
      S.month=9;applyWorldHistory(S);syncWorldIdentities(S);
      const opened=S.world.KR?.code==='KR'
        &&S.worldExpansion.openMarkets['MKT-17']===ym(1910,9)
        &&worldCityLocation(S,'CITY-17-02').jurisdictionId==='JUR-KR-COLONIAL'
        &&S.worldExpansion.appliedEvents.some(e=>e.id==='HIST-KR-1910');
      S.year=1914;S.month=5;S.monthCommitted=ym(1914,5)-1;
      applyWorldHistory(S);syncWorldIdentities(S);
      PAGE='corporateSubsidiaries';render();
      document.querySelector('#subName').value='Busan rice exporter';
      document.querySelector('#subCountry').value='KR';
      document.querySelector('#subIndustry').value='manufacturing';
      document.querySelector('#subCapital').value='650000';
      createSub();
      const seller=S.firms.find(f=>f.name==='Busan rice exporter'),port=seller.plants[0],depot=buyer.plants[0];
      depot.siteId='JP-OSA';
      for(const f of [buyer,seller]){
        f.auto=false;f.research.tree.done=[...new Set([...f.research.tree.done,'production-1'])];
      }
      for(const [f,id,v] of [[seller,'PRD-E18',2400],[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
        post(f,{materials:v},{cash:v},'検証用の有償現物設備','operating',S);
        f.stock[id]={q:1,v};
      }
      syncWorldIdentities(S);
      const identity=S.worldExpansion.companies[seller.id];
      const parity=identity.jurisdictionId==='JUR-KR-COLONIAL'
        &&identity.currencyId==='CUR-KRW'&&firmCurrency(seller,S)==='KRW'
        &&firmCurrency(buyer,S)==='JPY'&&worldUsesModernCurrency(S);
      const rice=worldBuyRegionalSupply(S,seller.id,port.id,'KR-BUS-RICE',14);
      worldBuyRegionalSupply(S,seller.id,port.id,'KR-BUS-BUNKER-COAL',20);
      const route=worldInternationalRegisterRoute(S,seller.id,profileId);
      const wh=worldInternationalInstallWarehouse(S,buyer.id,depot.id,profileId);
      const order=worldInternationalPlaceOrder(S,buyer.id,{
        routeId:route.id,warehouseId:wh.id,productId:'PRD-R23',quantity:14,
        cargoLitres:30,unitPriceSeller:Math.ceil(rice.amount/rice.quantity)+1,maxPaymentBuyer:1000000,paymentDays:60});
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      advanceFreightFixtureMonth(6);worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const shipped=cargo?.status==='IN_TRANSIT'&&cargo.quantity===14&&cargo.loadKg===15
        &&cargo.prepaidBuyer===Math.round(cargo.prepaidSeller*cargo.sellerRate/cargo.buyerRate)
        &&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R23']?.q&&!check(S).length;
      const damaged=structuredClone(S);damaged.worldExpansion.internationalShipments.at(-1).loadKg++;
      const tamper=rejects(()=>parsePayload(savePayload(damaged)));
      advanceFreightFixtureMonth(7);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const paid=cargo.credit.paidAt===ym(1914,7)
        &&!worldInternationalRouteAvailable(S,profileId);
      advanceFreightFixtureMonth(8);worldInternationalReceiveShipments(S);
      const restored=parsePayload(savePayload(S));
      const delivered=cargo.status==='DELIVERED'&&buyer.stock['PRD-R23'].q===14
        &&buyer.stock['PRD-R23'].v===cargo.totalBuyer
        &&!acc(seller,'worldShipmentStock')&&!check(restored).length
        &&!consolidate(restored).errors.length;
      const floating=structuredClone(restored);floating.world.KR.fx*=1.01;
      const independentRate=floating.world.KR.fx;
      worldMatchLedgerCurrencyRates(floating);
      const roundtrip=parsePayload(savePayload(floating));
      const independentFx=independentRate!==restored.world.KR.fx
        &&roundtrip.world.KR.fx===independentRate&&roundtrip.world.KR.currency==='KRW'
        &&JSON.stringify(roundtrip.firms)===JSON.stringify(restored.firms);
      return {initiallyClosed,beforeAnnexation,opened,parity,shipped,tamper,paid,delivered,independentFx};
    }""")
    assert all(result.values()),result


def test_dated_colonial_export(page, data):
    """Sourced jurisdiction/currency opening, shipping, inspection, ledger, save."""
    result=page.evaluate("""({profile,country,city,site,currency,year,opensYear,opensMonth,
                                offer,buyerCountry,destination,product,departure,payMonth}) => {
      S=newWorldGame({country:buyerCountry,name:destination+' colonial importer'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY=buyerCountry;
      const buyer=company(S.playerId);
      const initiallyClosed=!S.world[country]&&!worldCityLocation(S,city).marketOpen;
      S.year=opensYear;S.month=opensMonth-1;S.monthCommitted=ym(opensYear,opensMonth-1)-1;
      applyWorldHistory(S);
      const before=!S.world[country];
      S.month=opensMonth;applyWorldHistory(S);syncWorldIdentities(S);
      const opened=S.world[country]?.code===country
        &&S.worldExpansion.openMarkets[WORLD_TERRITORIES.get(WORLD_MARKET_ONBOARDING[country].territoryId).marketId]===
          ym(opensYear,opensMonth)
        &&worldCityLocation(S,city).jurisdictionId===WORLD_MARKET_ONBOARDING[country].jurisdictionId;
      S.year=year;S.month=departure-1;S.monthCommitted=ym(year,departure-1)-1;
      applyWorldHistory(S);syncWorldIdentities(S);
      PAGE='corporateSubsidiaries';render();
      document.querySelector('#subName').value=site+' sourced exporter';
      document.querySelector('#subCountry').value=country;
      document.querySelector('#subIndustry').value='manufacturing';
      document.querySelector('#subCapital').value='650000';
      createSub();
      const seller=S.firms.find(f=>f.name===site+' sourced exporter'),port=seller.plants[0],depot=buyer.plants[0];
      depot.siteId=destination;
      for(const f of [buyer,seller]){
        f.auto=false;f.research.tree.done=[...new Set([...f.research.tree.done,'production-1'])];
      }
      for(const [f,id,v] of [[seller,'PRD-E18',2400],[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
        post(f,{materials:v},{cash:v},'検証用有償設備','operating',S);
        f.stock[id]={q:1,v};
      }
      syncWorldIdentities(S);
      const identities=S.worldExpansion.companies[seller.id].jurisdictionId===WORLD_MARKET_ONBOARDING[country].jurisdictionId
        &&firmCurrency(seller,S)===currency&&port.siteId===site
        &&S.worldExpansion.facilities['FAC-'+port.id].locationId==='LOC-'+site;
      worldBuyRegionalSupply(S,seller.id,port.id,offer,14);
      worldBuyRegionalSupply(S,seller.id,port.id,site+'-BUNKER-COAL',20);
      const route=worldInternationalRegisterRoute(S,seller.id,profile);
      const warehouse=worldInternationalInstallWarehouse(S,buyer.id,depot.id,profile);
      const o=worldInternationalPlaceOrder(S,buyer.id,{
        routeId:route.id,warehouseId:warehouse.id,productId:product,quantity:14,
        cargoLitres:30,unitPriceSeller:localFromBase(40,country),
        maxPaymentBuyer:1000000,paymentDays:60});
      worldInternationalActOrder(S,seller.id,o.id,'approve');
      const weightDuty=profile==='KE-UK-MOMBASA-COFFEE';
      // Explicit pre-SPEC-079 fixture: preserve the historical dispatch and its refund tests.
      if(weightDuty)delete S.worldExpansion.uniformDutyFromSeq;
      const legacy=weightDuty?structuredClone(S):null;
      advanceFreightFixtureMonth(departure);worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const unpaidAtDispatch=weightDuty?structuredClone(S):null;
      const shipped=cargo?.status==='IN_TRANSIT'&&cargo.quantity===14&&cargo.loadKg===15
        &&cargo.fuelRequired>0&&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock[product]?.q&&!check(S).length;
      const forged=structuredClone(S);
      forged.worldExpansion.internationalShipments.at(-1).loadKg++;
      const tamper=(()=>{try{parsePayload(savePayload(forged));return false;}catch{return true;}})();
      advanceFreightFixtureMonth(payMonth);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const prepaid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(year,payMonth)
        &&!worldInternationalRouteAvailable(S,profile);
      const arrival=departure+worldInternationalProfile(profile).transitMonths;
      let protectedBasis=true,heldForRelease=true,safeDelay=true,unusedDutyRefund=true,reassessedDuty=true;
      if(weightDuty){
        legacy.worldExpansion.marketRegistryVersion=17;
        delete legacy.world.BE;
        delete legacy.world.PT;
        for(const [code,row] of Object.entries(WORLD_MARKET_ONBOARDING))if(row.introducedIn>17){delete legacy.world[code];delete legacy.npcSupplyV033.markets[code];}
        const oldWorld17=makeWorldExpansion(17);
        for(const event of worldHistoryThrough(ym(legacy.year,legacy.month),17))recordWorldEvent(oldWorld17,event);
        Object.assign(legacy.worldExpansion,{territoryJurisdictions:oldWorld17.territoryJurisdictions,openMarkets:oldWorld17.openMarkets,appliedEvents:oldWorld17.appliedEvents});
        delete legacy.worldExpansion.weightDutyFromSeq;
        const upgradedBeforeDispatch=parsePayload(savePayload(legacy));
        upgradedBeforeDispatch.month=departure;
        worldInternationalResolveOrders(upgradedBeforeDispatch);
        const newCargo=upgradedBeforeDispatch.worldExpansion.internationalShipments[0];
        legacy.month=departure;syncWorldIdentities(legacy);
        worldInternationalResolveOrders(legacy);
        const oldCargo=legacy.worldExpansion.internationalShipments[0];
        const migrated=parsePayload(savePayload(legacy));
        protectedBasis=oldCargo.tariffBps===250&&!oldCargo.customs
          &&migrated.worldExpansion.weightDutyFromSeq===legacy.seq
          &&JSON.stringify(migrated.worldExpansion.internationalShipments[0])===JSON.stringify(oldCargo)
          &&newCargo?.tariffBps===250&&newCargo.customs?.centsPerHundredweight===undefined
          &&newCargo.dutyBuyer===Math.round(newCargo.goodsSeller*newCargo.sellerRate/newCargo.buyerRate*.025);
        migrated.month=arrival;worldInternationalReceiveShipments(migrated);
        worldInternationalSettleCredit(migrated);
        const oldDelivery=parsePayload(savePayload(migrated)).worldExpansion.internationalShipments[0];
        protectedBasis&&=oldDelivery.receivedAt===ym(year,arrival)&&!oldDelivery.customs
          &&oldDelivery.dutyBuyer===oldCargo.dutyBuyer;
        const late=structuredClone(S);
        late.year=1924;late.month=5;late.monthCommitted=ym(1924,5)-1;
        applyWorldHistory(late);syncWorldIdentities(late);worldInternationalReceiveShipments(late);
        late.month=6;late.monthCommitted=ym(1924,6)-1;
        worldInternationalReceiveShipments(late);
        const outOfWindow=parsePayload(savePayload(late)).worldExpansion.internationalShipments[0];
        safeDelay=outOfWindow.status==='IN_TRANSIT'&&outOfWindow.customs.arrivalAt===ym(1924,5)
          &&outOfWindow.customs.releasedAt===null&&outOfWindow.dutyBuyer===39;
        for(const paid of [true,false]){
          const delayed=structuredClone(paid?S:unpaidAtDispatch);
          delayed.year=1924;delayed.month=6;delayed.monthCommitted=ym(1924,6)-1;
          applyWorldHistory(delayed);syncWorldIdentities(delayed);
          const importer=company(buyer.id,delayed);
          if(!paid){
            post(importer,{otherExpense:acc(importer,'cash')},{cash:acc(importer,'cash')},
              '検証用の資金不足','operating',delayed);
          }
          const before=acc(importer,'cash');
          worldInternationalReceiveShipments(delayed);worldInternationalSettleCredit(delayed);
          const beforeClearance=parsePayload(savePayload(delayed)).worldExpansion.internationalShipments[0];
          const fullWarehouse=paid?structuredClone(delayed):null;
          delayed.month=7;delayed.monthCommitted=ym(1924,7)-1;
          worldInternationalReceiveShipments(delayed);
          const assessed=delayed.worldExpansion.internationalShipments[0];
          const restoredAssessment=parsePayload(savePayload(delayed));
          const forgedDuty=structuredClone(restoredAssessment);
          forgedDuty.worldExpansion.internationalShipments[0].customs.assessedDuty++;
          const rejection=(()=>{try{parsePayload(savePayload(forgedDuty));return false;}catch{return true;}})();
          reassessedDuty&&=beforeClearance.customs.arrivalAt===ym(1924,6)
            &&beforeClearance.customs.releasedAt===null&&beforeClearance.dutyBuyer===39
            &&assessed.status==='DELIVERED'&&assessed.customs.assessmentId==='UK-COFFEE-DUTY-1924'
            &&assessed.customs.assessedDuty===19&&assessed.dutyBuyer===39&&assessed.receivedAt===ym(1924,7)
            &&importer.stock[product]?.v===assessed.prepaidBuyer+19
            &&acc(importer,'cash')===before+(paid?20:0)
            &&acc(importer,'worldImportDutyPrepaid')===0
            &&-acc(importer,'worldInternationalDutyPayable')===(paid?0:19)
            &&rejection&&!check(restoredAssessment).length&&!consolidate(restoredAssessment).errors.length;
          if(paid){
            const receiver=company(buyer.id,fullWarehouse),full=Math.floor(receiver.plants[0].capacity*10);
            post(receiver,{materials:full},{cash:full},'検証用の満杯在庫','operating',fullWarehouse);
            receiver.stock[product]={q:full,v:full};
            fullWarehouse.month=7;fullWarehouse.monthCommitted=ym(1924,7)-1;
            worldInternationalReceiveShipments(fullWarehouse);
            const blocked=fullWarehouse.worldExpansion.internationalShipments[0];
            const canRefund=blocked.status==='IN_TRANSIT'&&blocked.customs.assessedDuty===19;
            const cash=acc(receiver,'cash'),expense=acc(receiver,'otherExpense');
            worldInternationalRefundShipment(fullWarehouse,blocked.id);
            reassessedDuty&&=canRefund&&blocked.status==='REFUNDED'
              &&acc(receiver,'cash')===cash+blocked.prepaidBuyer+20
              &&acc(receiver,'otherExpense')===expense+19&&receiver.stock[product].q===full
              &&!check(parsePayload(savePayload(fullWarehouse))).length;
          }else{
            const amount=assessed.prepaidBuyer+19;
            post(importer,{cash:amount},{capital:amount},'検証用増資','financing',delayed);
            worldInternationalSettleCredit(delayed);
            reassessedDuty&&=assessed.credit.paidAt===ym(1924,7)&&acc(importer,'cash')===0
              &&acc(importer,'worldInternationalDutyPayable')===0&&!check(parsePayload(savePayload(delayed))).length;
          }
        }
        for(const pending of [false,true]){
          const cancelled=structuredClone(S);
          cancelled.month=arrival+1;cancelled.monthCommitted=ym(year,arrival);
          applyWorldHistory(cancelled);syncWorldIdentities(cancelled);
          const importer=company(buyer.id,cancelled),exporter=company(seller.id,cancelled);
          const before=acc(importer,'cash'),expense=acc(importer,'otherExpense');
          if(pending){
            post(exporter,{otherExpense:acc(exporter,'cash')},{cash:acc(exporter,'cash')},
              '検証用の現金支出','operating',cancelled);
          }
          const refund=worldInternationalRefundShipment(cancelled,cargo.id);
          const savedRefund=parsePayload(savePayload(cancelled));
          const forged=structuredClone(savedRefund);
          delete forged.worldExpansion.internationalShipments[0].unassessedDutyReturned;
          const rejected=(()=>{try{parsePayload(savePayload(forged));return false;}catch{return true;}})();
          const internal=worldInternationalCashPairs(savedRefund)
            .find(pair=>pair.toJournal===refund.journals.terminal+1);
          unusedDutyRefund&&=refund.unassessedDutyReturned===true
            &&refund.status===(pending?'REFUND_PENDING':'REFUNDED')
            &&acc(importer,'cash')===before+39+(pending?0:refund.prepaidBuyer)
            &&acc(importer,'worldImportDutyPrepaid')===0&&acc(importer,'otherExpense')===expense
            &&(pending?!internal:internal?.toCash===refund.prepaidBuyer)
            &&!check(savedRefund).length&&!consolidate(savedRefund).errors.length&&rejected;
          if(pending){
            post(exporter,{cash:refund.prepaidSeller},{capital:refund.prepaidSeller},
              '検証用の有償増資','financing',cancelled);
            worldInternationalSettleCredit(cancelled);
            unusedDutyRefund&&=refund.status==='REFUNDED'
              &&acc(importer,'cash')===before+39+refund.prepaidBuyer
              &&!check(parsePayload(savePayload(cancelled))).length;
          }
        }
      }
      advanceFreightFixtureMonth(arrival);
      worldInternationalReceiveShipments(S);
      if(weightDuty){
        const forged=structuredClone(S);
        forged.worldExpansion.internationalShipments[0].customs.centsPerHundredweight++;
        const rejectsWeightTampering=(()=>{try{parsePayload(savePayload(forged));return false;}catch{return true;}})();
        heldForRelease=cargo.status==='IN_TRANSIT'&&cargo.tariffBps===undefined&&cargo.dutyBuyer===39
          &&cargo.customs?.centsPerHundredweight===140&&cargo.customs.weightKg===14
          &&cargo.customs.arrivalAt===ym(year,arrival)&&cargo.customs.releasedAt===null
          &&cargo.customs.authorityId==='CUSTOMS-UK-LONDON-1922-COFFEE'
          &&acc(buyer,'worldImportDutyPrepaid')===39&&!buyer.stock[product]?.q&&rejectsWeightTampering;
        advanceFreightFixtureMonth(arrival+1);worldInternationalReceiveShipments(S);
      }
      const saved=parsePayload(savePayload(S));
      const done=cargo.status==='DELIVERED'&&buyer.stock[product]?.q===14
        &&buyer.stock[product].v===cargo.totalBuyer&&!acc(seller,'worldShipmentStock')
        &&!check(saved).length&&!consolidate(saved).errors.length;
      return {initiallyClosed,before,opened,identities,shipped,tamper,prepaid,
        protectedBasis,heldForRelease,safeDelay,unusedDutyRefund,reassessedDuty,done};
    }""",data)
    assert all(result.values()), (data["country"],result)


def test_saudi_rice_import(page):
    """1932 kingdom opening, British India rice exporter, Jeddah import and settlement."""
    result=page.evaluate("""() => {
      const rejects=fn=>{try{fn();return false;}catch{return true;}};
      S=newWorldGame({country:'IN',name:'Bombay rice exporter'});
      VIEW_FIRM=S.playerId;VIEW_COUNTRY='IN';
      const seller=company(S.playerId),port=seller.plants[0],profileId='IN-SA-BOMBAY-JEDDAH-RICE';
      const initiallyClosed=!S.world.SA&&!worldCityLocation(S,'CITY-39-02').marketOpen
        &&!worldInternationalRouteAvailable(S,profileId);
      S.year=1932;S.month=9;S.monthCommitted=ym(1932,9)-1;
      applyWorldHistory(S);
      const beforeUnification=!S.world.SA;
      S.month=10;applyWorldHistory(S);syncWorldIdentities(S);
      const opened=S.world.SA?.code==='SA'
        &&S.worldExpansion.openMarkets['MKT-39']===ym(1932,10)
        &&worldCityLocation(S,'CITY-39-02').jurisdictionId==='JUR-SA-KINGDOM'
        &&S.worldExpansion.appliedEvents.some(e=>e.id==='HIST-SA-1932');
      S.year=1934;S.month=4;S.monthCommitted=ym(1934,4)-1;
      applyWorldHistory(S);syncWorldIdentities(S);
      PAGE='corporateSubsidiaries';render();
      document.querySelector('#subName').value='Jeddah rice importer';
      document.querySelector('#subCountry').value='SA';
      document.querySelector('#subIndustry').value='manufacturing';
      document.querySelector('#subCapital').value='650000';
      createSub();
      const buyer=S.firms.find(f=>f.name==='Jeddah rice importer'),whPlant=buyer.plants[0];
      for(const f of [buyer,seller]){
        f.auto=false;f.research.tree.done=[...new Set([...f.research.tree.done,'production-1'])];
      }
      for(const [f,id,value] of [[seller,'PRD-E18',2400],[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
        post(f,{materials:value},{cash:value},'検証用有償現物設備','operating',S);
        f.stock[id]={q:1,v:value};
      }
      syncWorldIdentities(S);
      const registration=S.worldExpansion.companies[buyer.id];
      const currency=registration.jurisdictionId==='JUR-SA-KINGDOM'
        &&registration.currencyId==='CUR-SAR'&&firmCurrency(buyer,S)==='SAR'
        &&S.worldExpansion.facilities['FAC-'+whPlant.id].locationId==='LOC-SA-JED';
      worldBuyRegionalSupply(S,seller.id,port.id,'IN-BOM-RICE-1934',14);
      worldBuyRegionalSupply(S,seller.id,port.id,'IN-BOM-BUNKER-COAL-1934',20);
      const route=worldInternationalRegisterRoute(S,seller.id,profileId);
      const warehouse=worldInternationalInstallWarehouse(S,buyer.id,whPlant.id,profileId);
      const o=worldInternationalPlaceOrder(S,buyer.id,{routeId:route.id,warehouseId:warehouse.id,
        productId:'PRD-R23',quantity:14,cargoLitres:30,
        unitPriceSeller:localFromBase(40,'IN'),maxPaymentBuyer:1000000,paymentDays:60});
      worldInternationalActOrder(S,seller.id,o.id,'approve');
      advanceFreightFixtureMonth(5);worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const shipped=cargo?.status==='IN_TRANSIT'&&cargo.quantity===14
        &&cargo.loadKg===15&&cargo.sellerRate!==cargo.buyerRate
        &&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R23']?.q&&!check(S).length;
      const damaged=structuredClone(S);damaged.worldExpansion.internationalShipments.at(-1).fuelRequired++;
      const tamper=rejects(()=>parsePayload(savePayload(damaged)));
      advanceFreightFixtureMonth(6);worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const paid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(1934,6)
        &&!worldInternationalRouteAvailable(S,profileId);
      advanceFreightFixtureMonth(7);worldInternationalReceiveShipments(S);
      const restored=parsePayload(savePayload(S));
      const done=cargo.status==='DELIVERED'&&buyer.stock['PRD-R23'].q===14
        &&buyer.stock['PRD-R23'].v===cargo.totalBuyer&&!acc(seller,'worldShipmentStock')
        &&!check(restored).length&&!consolidate(restored).errors.length;
      return {initiallyClosed,beforeUnification,opened,currency,shipped,tamper,paid,done};
    }""")
    assert all(result.values()),result

def main(observe_receipts=None):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_context(offline=True).new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        if observe_receipts is not None:
            observe_receipts(page)
        # SPEC-079: every registered jurisdiction has a single provisional rate.
        # Unregistered jurisdictions still fail closed.
        tariff_guard = page.evaluate("""() => {
          const s=newWorldGame({country:'BE',name:'Belgian tariff guard'});
          const buyer=company(s.playerId,s);
          const before=JSON.stringify(s);
          const q=worldInternationalQuote(s,{ownerCompanyId:buyer.id,
            profileId:'UK-PT-CARDIFF-LISBON-COAL'},'PRD-R04',1,100,buyer.id);
          const missing=Object.keys(WORLD_INTERNATIONAL_ROUTE_EVIDENCE)
            .filter(id=>!Object.hasOwn(WORLD_PHASE4_TARIFF_BPS,
              findSite(WORLD_INTERNATIONAL_CORRIDORS[id].to)?.country))
            .concat(Object.keys(WORLD_ENGINE_TERRITORY).filter(code=>!Object.hasOwn(WORLD_PHASE4_TARIFF_BPS,code)));
          return {blocked:!worldInternationalImportTariffAvailable(s,'ZZ')
             &&worldInternationalImportTariffAvailable(s,'BE')
             &&worldInternationalTariffBps(s,'BE',null)===300&&!!q.problem,
            supported:worldInternationalImportTariffAvailable(s,'UK'),
            noMutation:before===JSON.stringify(s),missing};
        }""")
        assert tariff_guard["blocked"] and tariff_guard["supported"] and tariff_guard["noMutation"], tariff_guard
        assert not tariff_guard["missing"], tariff_guard
        # These cargo scenarios jump directly to dispatch, arrival, and payment
        # months. Apply the same world history as the normal monthly close.
        page.evaluate("""() => {
          window.advanceFreightFixtureMonth=month=>{
            S.month=month;applyWorldHistory(S);syncWorldIdentities(S);
          };
        }""")
        result = page.evaluate("""() => {
          const rejects=action=>{try{action();return false;}catch{return true;}};
          const legacy=newGame({country:'UK',era:1900,difficulty:'normal',history:'historical',name:'Legacy world'});
          const originalPlayer=company(legacy.playerId,legacy);
          legacy.config.scenario='world';
          legacy.worldExpansion=makeWorldExpansion(0);
          delete legacy.worldExpansion.marketRegistryVersion;
          delete legacy.worldExpansion.weightDutyFromSeq;
          syncWorldIdentities(legacy);
          const legacyRaw=savePayload(legacy);
          const upgraded=parsePayload(legacyRaw);
          const registryUpgrade=upgraded.worldExpansion.marketRegistryVersion===WORLD_MARKET_REGISTRY_VERSION
            &&upgraded.worldExpansion.openMarkets['MKT-27']===ym(1900,1)&&upgraded.world.CA?.code==='CA'
            &&upgraded.worldExpansion.openMarkets['MKT-24']===null&&!upgraded.world.AU
            &&company(upgraded.playerId,upgraded).id===originalPlayer.id
            &&acc(company(upgraded.playerId,upgraded),'cash')===acc(originalPlayer,'cash')
            &&upgraded.rng===legacy.rng&&JSON.stringify(upgraded.world.UK)===JSON.stringify(legacy.world.UK)
            &&!check(parsePayload(savePayload(upgraded))).length;
          const forged=structuredClone(upgraded);delete forged.worldExpansion.marketRegistryVersion;
          const downgradeRejected=rejects(()=>parsePayload(savePayload(forged)));

          const canadastart=newWorldGame({country:'CA',name:'Canadian start'});
          const canadianIdentity=worldCityLocation(canadastart,'CITY-27-03');
          const player=company(canadastart.playerId,canadastart);
          const selected=canadianIdentity.jurisdictionId==='JUR-CA'&&canadianIdentity.marketOpen
            &&player.plants[0].siteId==='CA-MTL'&&firmCurrency(player,canadastart)==='CAD'
            &&worldPhase3ConsumerQuote(canadastart,'MKT-27','PRD-C01').nationalQuantity>0
            &&canadastart.worldExpansion.facilities['FAC-'+player.plants[0].id].locationId==='LOC-CA-MTL'
            &&!check(canadastart).length;
          S=newWorldGame({country:'UK',name:'Importer Liverpool'});
          const buyer=company(S.playerId),home=buyer.plants[0];
          home.siteId='UK-LIV';
          const capital=localFromBase(750000,buyer.country),payer=S.seq;
          post(buyer,{investment:capital},{cash:capital},'輸出取引検証用の払込','investing',S);
          const seller=initFirm(S,{name:'Montreal grain exporter',country:'CA',seedBase:750000,publicOwnership:false});
          seller.owners=[{id:buyer.id,econ:1,vote:1}];
          registerEquityLink(S,{parentId:buyer.id,childId:seller.id,ratio:1,kind:'foundation',considerationLocal:capital,
            buyerJournal:payer,childJournal:seller.journals.find(j=>j.text==='創業資本').id,
            bookEquityBase:baseFromLocal(financials(seller).equity,seller.country),
            cashAcquiredBase:baseFromLocal(acc(seller,'cash'),seller.country)});
          const profile='CA-UK-MONTREAL-GRAIN',closedAtStart=!worldInternationalRouteAvailable(S,profile);
          const plant=seller.plants[0];
          S.year=1909;S.month=5;S.monthCommitted=ym(1909,5)-1;
          applyWorldHistory(S);syncWorldIdentities(S);
          for(const f of [buyer,seller]){
            f.auto=false;f.research.tree.done=[...new Set([...f.research.tree.done,'production-1'])];
          }
          for(const [f,id,q,amount] of [[seller,'PRD-E18',1,2500],[buyer,'PRD-E20',1,600],[buyer,'PRD-E21',1,900]]){
            post(f,{materials:amount},{cash:amount},'検証用の有償現物設備','operating',S);
            f.stock[id]={q,v:amount};
          }
          const purchase=worldBuyRegionalSupply(S,seller.id,plant.id,'CA-MTL-WHEAT',20);
          worldBuyRegionalSupply(S,seller.id,plant.id,'CA-MTL-COAL',30);
          const route=worldInternationalRegisterRoute(S,seller.id,profile);
          const warehouse=worldInternationalInstallWarehouse(S,buyer.id,home.id,profile);
          const base={routeId:route.id,warehouseId:warehouse.id,productId:'PRD-R22',
            quantity:10,cargoLitres:85,unitPriceSeller:localFromBase(400,seller.country),
            maxPaymentBuyer:10000000,paymentDays:60};
          const invalid=rejects(()=>worldInternationalPlaceOrder(S,buyer.id,{...base,cargoLitres:-1}))
            &&rejects(()=>worldInternationalPlaceOrder(S,buyer.id,{...base,productId:'PRD-R04'}));
          const first=worldInternationalPlaceOrder(S,buyer.id,base);
          const second=worldInternationalPlaceOrder(S,buyer.id,{...base,quantity:2,cargoLitres:8});
          for(const o of [first,second])worldInternationalActOrder(S,seller.id,o.id,'approve');
          advanceFreightFixtureMonth(6);worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
          const [a,b]=S.worldExpansion.internationalShipments;
          const loading=a?.quantity===6&&a.cargoLitres===51&&a.loadKg===26&&a.fuelRequired===8
            &&b?.quantity===1&&b.cargoLitres===4&&b.loadKg===2&&b.fuelRequired===1
            &&first.acceptedQty===6&&second.acceptedQty===1;
          const ownership=purchase.quantity===20&&a?.status==='IN_TRANSIT'&&a.credit.paidAt===null
            &&acc(seller,'worldShipmentStock')===a.bookCost+b.bookCost
            &&!buyer.stock['PRD-R22']?.q&&seller.stock['PRD-R22'].q===13&&!check(S).length;
          const altered=structuredClone(S);altered.worldExpansion.internationalShipments[0].loadKg--;
          const audit=rejects(()=>parsePayload(savePayload(altered)));
          advanceFreightFixtureMonth(7);
          worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
          const prepaid=a?.credit.paidAt===ym(1909,7)&&a.status==='IN_TRANSIT'
            &&acc(buyer,'worldSupplierAdvances')===a.prepaidBuyer+b.prepaidBuyer
            &&acc(buyer,'worldImportDutyPrepaid')===a.dutyBuyer+b.dutyBuyer;
          advanceFreightFixtureMonth(8);worldInternationalReceiveShipments(S);
          const restored=parsePayload(savePayload(S));
          const shipment=restored.worldExpansion.internationalShipments[0];
          const settlement=a?.status==='DELIVERED'&&b?.status==='DELIVERED'
            &&shipment.cargoLitres===51&&shipment.credit.paidAt===ym(1909,7)
            &&buyer.stock['PRD-R22'].q===7&&buyer.stock['PRD-R22'].v===a.totalBuyer+b.totalBuyer
            &&!acc(seller,'worldShipmentStock')&&!acc(buyer,'worldSupplierAdvances')
            &&!check(restored).length&&!consolidate(restored).errors.length;
          advanceFreightFixtureMonth(11);
          const seasonal=closedAtStart&&!worldInternationalRouteAvailable(S,profile)
            &&rejects(()=>worldInternationalPlaceOrder(S,buyer.id,base));
          return {registryUpgrade,downgradeRejected,selected,invalid,loading,ownership,audit,prepaid,settlement,seasonal};
        }""")
        assert all(result.values()), result
        test_all_market_coverage(page)
        test_australia(page)
        test_new_zealand(page)
        gulf_coffee = {"buyerCountry": "US", "destination": "US-NEWORLEANS", "product": "PRD-R27",
                       "departure": 6, "payMonth": 7}
        test_steamship_export(page, {
            **gulf_coffee,
            "profile": "MX-US-VERACRUZ-COFFEE", "country": "MX", "site": "MX-VER", "city": "CITY-28-04",
            "currency": "MXN", "year": 1906, "offer": "MX-VER-COFFEE", "authority": "CUSTOMS-US-NOLA-1897",
        })
        test_steamship_export(page, {
            **gulf_coffee,
            "profile": "BR-US-RIO-COFFEE", "country": "BR", "site": "BR-RIO", "city": "CITY-29-01",
            "currency": "BRL", "year": 1910, "offer": "BR-RIO-COFFEE", "authority": "CUSTOMS-US-NOLA-1909",
        })
        test_steamship_export(page, {
            "profile": "AR-UK-BUENOSAIRES-WHEAT", "country": "AR", "site": "AR-BUE", "city": "CITY-30-01",
            "currency": "ARS", "year": 1921, "offer": "AR-BUE-WHEAT", "authority": None,
            "buyerCountry": "UK", "destination": "UK-LIV", "product": "PRD-R22", "departure": 2, "payMonth": 4,
        })
        test_steamship_export(page, {
            "profile": "CL-UK-VALPARAISO-COPPER", "country": "CL", "site": "CL-VAP", "city": "CITY-31-02",
            "currency": "CLP", "year": 1913, "offer": "CL-VAP-COPPER", "authority": None,
            "buyerCountry": "UK", "destination": "UK-LIV", "product": "PRD-M05", "departure": 6, "payMonth": 7,
        })
        test_steamship_export(page, {
            **gulf_coffee,
            "profile": "CO-US-CARTAGENA-COFFEE", "country": "CO", "site": "CO-CTG", "city": "CITY-32-04",
            "currency": "COP", "year": 1906, "offer": "CO-CTG-COFFEE", "authority": "CUSTOMS-US-NOLA-1897",
        })
        test_steamship_export(page, {
            "profile": "SE-UK-GOTHENBURG-TIMBER", "country": "SE", "site": "SE-GOT", "city": "CITY-10-02",
            "currency": "SEK", "year": 1904, "offer": "SE-GOT-TIMBER", "authority": None,
            "buyerCountry": "UK", "destination": "UK-HULL", "product": "PRD-R19", "departure": 6, "payMonth": 7,
        })
        test_steamship_export(page, {
            "profile": "NL-US-ROTTERDAM-PULP", "country": "NL", "site": "NL-ROT", "city": "CITY-08-02",
            "currency": "EUR", "year": 1907, "offer": "NL-ROT-PULP", "authority": None,
            "buyerCountry": "US", "destination": "US-PHL", "product": "PRD-M13", "departure": 3, "payMonth": 4,
        })
        test_steamship_export(page, {
            "profile": "EG-UK-ALEXANDRIA-COTTON", "country": "EG", "site": "EG-ALX",
            "city": "CITY-34-02", "currency": "EGP", "year": 1908, "offer": "EG-ALX-COTTON",
            "authority": None, "buyerCountry": "UK", "destination": "UK-LIV",
            "product": "PRD-R20", "departure": 6, "payMonth": 7,
        })
        test_steamship_export(page, {
            "profile": "BE-US-ANTWERP-GLASS", "country": "BE", "site": "BE-ANR", "city": "CITY-08-03",
            "currency": "EUR", "year": 1910, "offer": "BE-ANR-GLASS", "authority": None,
            "buyerCountry": "US", "destination": "US-NYC", "product": "PRD-M11",
            "departure": 6, "payMonth": 7, "strictClosure": False,
        })
        test_italy_coal_import(page)
        test_portugal_coal_import(page)
        test_ireland_textiles_import(page)
        for data in [{"code":"LU","city":"CITY-08-04","market":"MKT-08","jur":"JUR-LU","rep":"NL","open":None,"year":1913,"month":4,"destCountry":"FR","dest":"FR-LONGWY","site":"LU-LUX","exportSite":None,"currency":"EUR","rail":True,"product":"PRD-R01","profile":"LU-FR-LUXEMBOURG-IRON"},{"code":"YU","city":"CITY-13-03","market":"MKT-13","jur":"JUR-YU","rep":"GR","open":[1918,12],"year":1922,"month":4,"destCountry":"IT","dest":"IT-TRI","site":"YU-ZAG","exportSite":None,"currency":"RSD","rail":True,"product":"PRD-R19","profile":"YU-IT-ZAGREB-TRIESTE-TIMBER"},{"code":"AL","city":"CITY-13-04","market":"MKT-13","jur":"JUR-AL","rep":"GR","open":[1912,12],"year":1937,"month":8,"destCountry":"IT","dest":"IT-BAR","site":"AL-TIR","exportSite":"AL-DUR","currency":"ALL","rail":False,"product":"PRD-R19","profile":"AL-IT-DURRES-BARI-TIMBER"}]:
            test_remaining_jurisdictions(page,data)
        test_steamship_export(page, {
            "profile": "IN-UK-BOMBAY-COTTON", "country": "IN", "site": "IN-BOM",
            "city": "CITY-16-02", "currency": "INR", "year": 1908, "offer": "IN-BOM-COTTON",
            "authority": None, "buyerCountry": "UK", "destination": "UK-LIV",
            "product": "PRD-R20", "departure": 4, "payMonth": 5,
        })
        test_south_africa_union(page)
        test_steamship_export(page, {
            "profile": "TH-SG-BANGKOK-RICE", "country": "TH", "site": "TH-BKK",
            "city": "CITY-20-01", "currency": "THB", "year": 1909,
            "offer": "TH-BKK-RICE", "authority": "CUSTOMS-SG-1909",
            "customsCurrency": "CUR-SGD", "buyerCountry": "SG", "destination": "SG-SIN",
            "product": "PRD-R23", "departure": 4, "payMonth": 5,
        })
        test_steamship_export(page, {
            "profile": "SG-UK-SINGAPORE-RUBBER", "country": "SG", "site": "SG-SIN",
            "city": "CITY-22-01", "currency": "SGD", "year": 1911,
            "offer": "SG-SIN-RUBBER", "authority": None,
            "buyerCountry": "UK", "destination": "UK-LON",
            "product": "PRD-R29", "departure": 3, "payMonth": 4,
        })
        test_steamship_export(page, {
            "profile": "CN-UK-HANKOW-SOY", "country": "CN", "site": "CN-HAN",
            "city": "CITY-15-04", "currency": "CNY", "year": 1907,
            "offer": "CN-HAN-SOY", "authority": None,
            "buyerCountry": "UK", "destination": "UK-LIV", "product": "PRD-R25",
            "departure": 5, "payMonth": 6,
        })
        test_steamship_export(page, {
            "profile": "ID-JP-BATAVIA-SUGAR", "country": "ID", "site": "ID-BAT",
            "city": "CITY-18-01", "currency": "IDR", "year": 1907,
            "offer": "ID-BAT-SUGAR", "authority": None,
            "buyerCountry": "JP", "destination": "JP-YOK", "product": "PRD-M40",
            "departure": 5, "payMonth": 6,
        })
        test_nigeria_colonial_cocoa(page)
        test_steamship_export(page, {
            "profile": "ES-UK-BILBAO-IRON", "country": "ES", "site": "ES-BIL",
            "city": "CITY-05-01", "currency": "EUR", "year": 1907,
            "offer": "ES-BIL-IRON", "authority": None,
            "buyerCountry": "UK", "destination": "UK-CDF", "product": "PRD-R01",
            "departure": 5, "payMonth": 6,
        })
        test_philippines_sugar_customs(page)
        test_steamship_export(page, {
            "profile": "RU-UK-PETERSBURG-TIMBER", "country": "RU", "site": "RU-SPB",
            "city": "CITY-06-02", "currency": "RUB", "year": 1904,
            "offer": "RU-SPB-TIMBER", "authority": None,
            "buyerCountry": "UK", "destination": "UK-LON", "product": "PRD-R19",
            "departure": 5, "payMonth": 6,
        })
        test_steamship_export(page, {
            "profile": "TR-UK-SMYRNA-COTTON", "country": "TR", "site": "TR-IZM",
            "city": "CITY-38-03", "currency": "TRY", "year": 1909,
            "offer": "TR-IZM-COTTON", "authority": None,
            "buyerCountry": "UK", "destination": "UK-LIV", "product": "PRD-R20",
            "departure": 5, "payMonth": 6,
        })
        test_korean_colonial_rice(page)
        test_steamship_export(page, {
            "profile": "MY-UK-PENANG-RUBBER", "country": "MY", "site": "MY-PEN",
            "city": "CITY-21-02", "currency": "MYR", "year": 1911,
            "offer": "MY-PEN-RUBBER", "authority": None,
            "buyerCountry": "UK", "destination": "UK-LON", "product": "PRD-R29",
            "departure": 4, "payMonth": 5,
        })
        test_dated_colonial_export(page, {
            "profile": "KE-UK-MOMBASA-COFFEE", "country": "KE", "site": "KE-MBA",
            "city": "CITY-36-02", "currency": "KES", "year": 1923,
            "opensYear": 1922, "opensMonth": 8, "offer": "KE-MBA-COFFEE",
            "buyerCountry": "UK", "destination": "UK-LON", "product": "PRD-R27",
            "departure": 5, "payMonth": 6,
        })
        test_dated_colonial_export(page, {
            "profile": "MA-FR-CASABLANCA-WHEAT", "country": "MA", "site": "MA-CAS",
            "city": "CITY-37-02", "currency": "MAD", "year": 1923,
            "opensYear": 1920, "opensMonth": 7, "offer": "MA-CAS-WHEAT",
            "buyerCountry": "FR", "destination": "FR-MAR", "product": "PRD-R22",
            "departure": 5, "payMonth": 6,
        })
        test_steamship_export(page, {
            "profile": "CH-DE-BASEL-TEXTILES", "country": "CH", "site": "CH-BAS",
            "city": "CITY-09-04", "currency": "CHF", "year": 1906,
            "offer": "CH-BAS-TEXTILES", "authority": None,
            "buyerCountry": "DE", "destination": "DE-FRE", "product": "PRD-M36",
            "departure": 4, "payMonth": 5,
        })
        test_steamship_export(page, {
            "profile": "AT-DE-VIENNA-TIMBER", "country": "AT", "site": "AT-VIE",
            "city": "CITY-12-01", "currency": "EUR", "year": 1905,
            "offer": "AT-VIE-TIMBER", "authority": None,
            "buyerCountry": "DE", "destination": "DE-MUN", "product": "PRD-R19",
            "departure": 4, "payMonth": 5,
        })
        test_steamship_export(page, {
            "profile": "GR-FR-PIRAEUS-OLIVE", "country": "GR", "site": "GR-PIR",
            "city": "CITY-13-02", "currency": "EUR", "year": 1907,
            "offer": "GR-PIR-OLIVE-OIL", "authority": None,
            "buyerCountry": "FR", "destination": "FR-MAR", "product": "PRD-M39",
            "departure": 5, "payMonth": 6,
        })
        test_dated_colonial_export(page, {
            "profile": "PL-UK-GDYNIA-COAL", "country": "PL", "site": "PL-GDY",
            "city": "CITY-07-01", "currency": "PLN", "year": 1928,
            "opensYear": 1924, "opensMonth": 5, "offer": "PL-GDY-COAL",
            "buyerCountry": "UK", "destination": "UK-HULL", "product": "PRD-R04",
            "departure": 5, "payMonth": 6,
        })
        test_steamship_export(page, {
            "profile": "VN-FR-SAIGON-RICE", "country": "VN", "site": "VN-SGN",
            "city": "CITY-19-02", "currency": "VND", "year": 1907,
            "offer": "VN-SGN-RICE", "authority": None,
            "buyerCountry": "FR", "destination": "FR-MAR", "product": "PRD-R23",
            "departure": 5, "payMonth": 6,
        })
        test_steamship_export(page, {
            "profile": "IR-IN-BANDARABBAS-WOOL", "country": "IR", "site": "IR-BND",
            "city": "CITY-40-01", "currency": "IRR", "year": 1905,
            "offer": "IR-BND-WOOL", "authority": None,
            "buyerCountry": "IN", "destination": "IN-BOM", "product": "PRD-R21",
            "departure": 5, "payMonth": 6,
        })
        test_saudi_rice_import(page)
        assert not errors, errors
        browser.close()
    print("PASS Phase 4 Canada, Australia, New Zealand, Mexico, Brazil, Argentina, Chile, Colombia, Sweden, Netherlands, Italy, Egypt, India, Belgium, Portugal, South Africa, Siam, Straits Singapore, Qing China, Netherlands East Indies and Colonial Nigeria, Spain, Philippines, Russian Empire, Colonial Korea, Ottoman Empire, British Malaya, Kenya, Morocco, Switzerland, Austria, Poland, Greece, French Indochina, Qajar Persia and Saudi Arabia: sourced cargo, loading, shipment and settlement")


if __name__ == "__main__":
    main()
