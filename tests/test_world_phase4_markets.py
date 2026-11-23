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
      return {markets,integrity,allForty:countries.size===40&&connected.size===40
        &&WORLD_MARKETS.length===40&&WORLD_CITIES.size===155&&!missing.length,
        missing};
    }""")
    assert result["markets"] and result["integrity"] and result["allForty"], result


def test_australia(page):
    result = page.evaluate("""async () => {
      const buyerConfig={country:'JP',name:'Yokohama wool importer'};
      const old=newWorldGame(buyerConfig);
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
      S.month=12;S.monthCommitted=ym(1900,12)-1;
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
      const identities=firmCurrency(seller,S)==='AUP'
        &&S.worldExpansion.companies[seller.id].jurisdictionId==='JUR-AU'
        &&S.worldExpansion.facilities['FAC-'+plant.id].locationId==='LOC-AU-SYD';
      const purchase=worldBuyRegionalSupply(S,seller.id,plant.id,'AU-SYD-WOOL',12);
      worldBuyRegionalSupply(S,seller.id,plant.id,'AU-SYD-BUNKER-COAL',25);
      const route=worldInternationalRegisterRoute(S,seller.id,profile);
      const warehouse=worldInternationalInstallWarehouse(S,buyer.id,buyer.plants[0].id,profile);
      const order=worldInternationalPlaceOrder(S,buyer.id,{routeId:route.id,warehouseId:warehouse.id,
        productId:'PRD-R21',quantity:12,cargoLitres:32,unitPriceSeller:10,
        maxPaymentBuyer:100000,paymentDays:90});
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      S.month=6;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const [cargo]=S.worldExpansion.internationalShipments;
      const dispatch=purchase.quantity===12&&cargo?.status==='IN_TRANSIT'&&cargo.loadKg===16
        &&cargo.prepaidBuyer>cargo.prepaidSeller&&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R21']?.q;
      S.month=8;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const prepaid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(1913,8);
      S.month=9;worldInternationalReceiveShipments(S);
      const held=cargo.status==='IN_TRANSIT'&&cargo.customs?.arrivalAt===ym(1913,9)
        &&cargo.customs.releasedAt===null&&cargo.customs.duty===0&&cargo.tariffBps===0
        &&cargo.customs.authorityId==='CUSTOMS-JP-YOK-1911'&&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R21']?.q&&worldInternationalTradePanel(buyer,true).includes('保税・通関審査中')
        &&parsePayload(savePayload(S)).worldExpansion.internationalShipments[0].customs.arrivalAt===ym(1913,9);
      const forged=structuredClone(S);forged.worldExpansion.internationalShipments[0].customs.releasedAt=ym(1913,9);
      let prematureRejected=false;
      try{parsePayload(savePayload(forged));}catch{prematureRejected=true;}
      S.month=10;worldInternationalReceiveShipments(S);
      const reopened=parsePayload(savePayload(S));
      const settle=cargo.status==='DELIVERED'&&buyer.stock['PRD-R21'].q===12
        &&buyer.stock['PRD-R21'].v===cargo.totalBuyer&&!acc(seller,'worldShipmentStock')
        &&reopened.worldExpansion.internationalShipments[0].receivedAt===ym(1913,10)
        &&reopened.worldExpansion.internationalShipments[0].customs.releasedAt===ym(1913,10)
        &&!check(reopened).length&&!consolidate(reopened).errors.length;
      return {migration,initiallyClosed,opened,identities,dispatch,prepaid,held,prematureRejected,settle};
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
      const identities=firmCurrency(seller,S)==='GBP'&&firmCurrency(buyer,S)==='GBP'
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
      S.month=2;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const [cargo]=S.worldExpansion.internationalShipments;
      const dispatched=purchase.quantity===10&&cargo?.status==='IN_TRANSIT'&&cargo.loadKg===12
        &&cargo.fuelRequired===15&&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&cargo.sellerRate===cargo.buyerRate&&cargo.prepaidSeller===cargo.prepaidBuyer;
      const dueDate=cargo.credit.dueDate==='1913-03-03';
      S.month=3;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
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
      cancelled.month=6;
      const buyerAtCancellation=company(buyer.id,cancelled),cashBefore=acc(buyerAtCancellation,'cash');
      const voided=worldInternationalRefundShipment(cancelled,cargo.id);
      const refunded=voided.status==='REFUNDED'&&voided.credit.remittance.returnedAt===ym(1913,6)
        &&!acc(buyerAtCancellation,'worldBankRemittance')&&acc(buyerAtCancellation,'cash')===cashBefore+bank.principal
        &&!check(parsePayload(savePayload(cancelled))).length;

      S.month=4;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const prepaid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(1913,4)&&!buyer.stock['PRD-R21']?.q
        &&!acc(buyer,'worldBankRemittance')&&acc(buyer,'worldSupplierAdvances')===cargo.prepaidBuyer
        &&-acc(seller,'worldCustomerAdvances')===cargo.prepaidSeller&&!worldInternationalCashPairs(S).length;
      S.month=5;worldInternationalReceiveShipments(S);
      const restored=parsePayload(savePayload(S));
      const settled=cargo.status==='DELIVERED'&&buyer.stock['PRD-R21'].q===10
        &&buyer.stock['PRD-R21'].v===cargo.totalBuyer&&!acc(seller,'worldShipmentStock')
        &&restored.worldExpansion.internationalShipments[0].receivedAt===ym(1913,5)
        &&!check(restored).length&&!consolidate(restored).errors.length;
      S.month=10;
      return {before,opensOnDominion,noEarlyRoute,identities,dispatched,dueDate,held,forgedRejected,refunded,prepaid,settled,
        documentedPeriod:!worldInternationalRouteAvailable(S,profile)};
    }""")
    assert all(result.values()), result


def test_steamship_export(page, market_data):
    result = page.evaluate("""({profile,country,site,city,currency,year,departure,payMonth,buyerCountry,
                              destination,product,offer,authority,customsCurrency}) => {
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
        maxPaymentBuyer:100000,paymentDays:60});
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      S.month=departure;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const [cargo]=S.worldExpansion.internationalShipments;
      const shipped=purchase.quantity===14&&cargo?.status==='IN_TRANSIT'
        &&cargo.loadKg===worldInternationalLoad(worldInternationalProfile(profile),14,30).loadKg
        &&cargo.prepaidSeller!==cargo.prepaidBuyer&&acc(seller,'worldShipmentStock')===cargo.bookCost;
      S.month=payMonth;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const prepaid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(year,payMonth)
        &&!worldInternationalRouteAvailable(S,profile);
      const arrival=departure+worldInternationalProfile(profile).transitMonths;
      S.month=arrival;worldInternationalReceiveShipments(S);
      const held=authority===null?!cargo.customs&&cargo.status==='DELIVERED':
        cargo.status==='IN_TRANSIT'&&cargo.customs?.arrivalAt===ym(year,arrival)
        &&cargo.customs.authorityId===authority
        &&cargo.customs.currencyId===(customsCurrency??'CUR-USD')
        &&cargo.customs.releasedAt===null&&cargo.customs.duty===0
        &&!buyer.stock[product]?.q;
      if(authority!==null){S.month=arrival+1;worldInternationalReceiveShipments(S);}
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
        &&firmCurrency(buyer,S)==='ITL'
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
        quantity:12,cargoLitres:27,unitPriceSeller:240,maxPaymentBuyer:100000,paymentDays:60});
      const queued=order.status==='OPEN'&&acc(buyer,'cash')===preCash
        &&!S.worldExpansion.internationalShipments.length;
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      S.month=8;worldInternationalResolveOrders(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const loaded=purchase.quantity===28&&cargo?.orderId===order.id
        &&cargo.status==='IN_TRANSIT'&&cargo.quantity===12
        &&cargo.cargoLitres===27&&cargo.loadKg===14
        &&cargo.fuelRequired===2&&cargo.fuelCost>0
        &&seller.stock['PRD-R04'].q===14
        &&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R04']?.q
        &&worldValidateInternationalLogistics(S)&&!check(S).length;
      const forged=structuredClone(S);
      forged.worldExpansion.internationalShipments.at(-1).fuelRequired++;
      const tamper=denies(()=>parsePayload(savePayload(forged)));
      S.month=9;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const paid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(1907,9)
        &&acc(buyer,'worldSupplierAdvances')===cargo.prepaidBuyer
        &&!buyer.stock['PRD-R04']?.q;
      S.month=10;worldInternationalReceiveShipments(S);
      const restored=parsePayload(savePayload(S));
      const delivered=cargo.status==='DELIVERED'&&cargo.receivedAt===ym(1907,10)
        &&buyer.stock['PRD-R04'].q===12
        &&buyer.stock['PRD-R04'].v===cargo.totalBuyer
        &&!acc(buyer,'worldSupplierAdvances')
        &&!acc(seller,'worldShipmentStock')
        &&!check(restored).length
        &&!consolidate(restored).errors.length;
      S.month=11;
      const closed=!worldInternationalRouteAvailable(S,'UK-IT-CARDIFF-GENOA-COAL');
      return {italyOpen,sharedShortage,queued,loaded,tamper,paid,delivered,closed};
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
        &&firmCurrency(seller,S)==='GBP'
        &&S.worldExpansion.companies[seller.id].currencyId==='CUR-GBP'
        &&S.worldExpansion.companies[seller.id].jurisdictionId!==
          S.worldExpansion.companies[buyer.id].jurisdictionId;
      const wool=worldBuyRegionalSupply(S,seller.id,port.id,'ZA-CPT-WOOL',14);
      worldBuyRegionalSupply(S,seller.id,port.id,'ZA-CPT-BUNKER-COAL',22);
      const route=worldInternationalRegisterRoute(S,seller.id,profile);
      const wh=worldInternationalInstallWarehouse(S,buyer.id,depot.id,profile);
      const order=worldInternationalPlaceOrder(S,buyer.id,{
        routeId:route.id,warehouseId:wh.id,productId:'PRD-R21',
        quantity:14,cargoLitres:30,unitPriceSeller:45,maxPaymentBuyer:100000,paymentDays:60});
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      S.month=6;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const freight=wool.quantity===14&&cargo?.orderId===order.id
        &&cargo.status==='IN_TRANSIT'&&cargo.quantity===14
        &&cargo.loadKg===15&&cargo.fuelRequired>0
        &&cargo.sellerRate===cargo.buyerRate&&cargo.prepaidSeller===cargo.prepaidBuyer
        &&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R21']?.q&&!check(S).length;
      const tampered=structuredClone(S);tampered.worldExpansion.internationalShipments.at(-1).loadKg++;
      const tamperRejected=fail(()=>parsePayload(savePayload(tampered)));
      S.month=7;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const paid=cargo.credit.paidAt===ym(1911,7);
      S.month=9;worldInternationalReceiveShipments(S);
      const saved=parsePayload(savePayload(S));
      const delivered=cargo.status==='DELIVERED'&&buyer.stock['PRD-R21'].q===14
        &&buyer.stock['PRD-R21'].v===cargo.totalBuyer
        &&acc(seller,'worldShipmentStock')===0
        &&!check(saved).length&&!consolidate(saved).errors.length;
      S.month=10;
      return {closed,beforeUnion,opened,jurisdictions,freight,tamperRejected,paid,delivered,
        expired:!worldInternationalRouteAvailable(S,profile)};
    }""")
    assert all(result.values()), result


def test_nigeria_colonial_cocoa(page):
    """1914 colonial amalgamation gate, WACB peg, 1922 Lagos-Liverpool cargo."""
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
        &&identity.currencyId==='CUR-WAP'&&firmCurrency(seller,S)==='WAP'
        &&S.world.NG.fx===S.world.UK.fx
        &&S.worldExpansion.facilities['FAC-'+port.id].locationId==='LOC-NG-LAG';
      const originalStock=worldBuyRegionalSupply(S,seller.id,port.id,'NG-LAG-COCOA',14);
      worldBuyRegionalSupply(S,seller.id,port.id,'NG-LAG-BUNKER-COAL',20);
      const route=worldInternationalRegisterRoute(S,seller.id,routeId);
      const warehouse=worldInternationalInstallWarehouse(S,buyer.id,depot.id,routeId);
      const order=worldInternationalPlaceOrder(S,buyer.id,{
        routeId:route.id,warehouseId:warehouse.id,productId:'PRD-R28',
        quantity:14,cargoLitres:30,unitPriceSeller:40,
        maxPaymentBuyer:100000,paymentDays:60});
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      S.month=5;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const shipped=originalStock.quantity===14&&cargo?.status==='IN_TRANSIT'
        &&cargo.quantity===14&&cargo.loadKg===15&&cargo.fuelRequired>0
        &&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R28']?.q&&!check(S).length;
      const forged=structuredClone(S);forged.worldExpansion.internationalShipments.at(-1).cargoLitres++;
      const tamper=rejects(()=>parsePayload(savePayload(forged)));
      S.month=6;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const prepaid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(1922,6)
        &&!worldInternationalRouteAvailable(S,routeId);
      S.month=7;worldInternationalReceiveShipments(S);
      const restored=parsePayload(savePayload(S));
      const delivered=cargo.status==='DELIVERED'&&buyer.stock['PRD-R28'].q===14
        &&buyer.stock['PRD-R28'].v===cargo.totalBuyer
        &&!acc(seller,'worldShipmentStock')
        &&!check(restored).length&&!consolidate(restored).errors.length;
      const pegged=structuredClone(restored);pegged.world.NG.fx+=1;
      const pegProtected=rejects(()=>parsePayload(savePayload(pegged)));
      return {initiallyClosed,preUnion,opened,jurisdiction,shipped,tamper,prepaid,delivered,pegProtected};
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
        &&S.world.PH.fx*2===S.world.US.fx&&firmCurrency(seller,S)==='PHP';
      worldBuyRegionalSupply(S,seller.id,port.id,'PH-MNL-SUGAR',14);
      worldBuyRegionalSupply(S,seller.id,port.id,'PH-MNL-BUNKER-COAL',21);
      const route=worldInternationalRegisterRoute(S,seller.id,profileId);
      const wh=worldInternationalInstallWarehouse(S,buyer.id,depot.id,profileId);
      const order=worldInternationalPlaceOrder(S,buyer.id,{
        routeId:route.id,warehouseId:wh.id,productId:'PRD-M40',quantity:14,
        cargoLitres:30,unitPriceSeller:35,maxPaymentBuyer:100000,paymentDays:60});
      const freeQuota=worldInternationalQuote(S,route,'PRD-M40',14,35,buyer.id,60,30).tariffBps===0
        &&WORLD_INTERNATIONAL_CUSTOMS[profileId].annualQuotaKg===304814400;
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      S.month=5;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const shipped=cargo?.status==='IN_TRANSIT'&&cargo.quantity===14
        &&cargo.tariffBps===0&&cargo.dutyBuyer===0&&cargo.loadKg===15
        &&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-M40']?.q&&!check(S).length;
      S.month=6;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const paid=cargo.credit.paidAt===ym(1911,6)&&!worldInternationalRouteAvailable(S,profileId);
      S.month=7;worldInternationalReceiveShipments(S);
      const held=cargo.status==='IN_TRANSIT'&&cargo.customs?.arrivalAt===ym(1911,7)
        &&cargo.customs.releasedAt===null&&cargo.customs.authorityId==='CUSTOMS-US-SFO-PH1909';
      const altered=structuredClone(S);altered.worldExpansion.internationalShipments.at(-1).customs.duty++;
      const tamper=reject(()=>parsePayload(savePayload(altered)));
      S.month=8;worldInternationalReceiveShipments(S);
      const saved=parsePayload(savePayload(S));
      const settled=cargo.status==='DELIVERED'&&buyer.stock['PRD-M40'].q===14
        &&buyer.stock['PRD-M40'].v===cargo.totalBuyer
        &&cargo.customs.releasedAt===ym(1911,8)
        &&!acc(seller,'worldShipmentStock')&&!check(saved).length
        &&!consolidate(saved).errors.length;
      const fakePeg=structuredClone(saved);fakePeg.world.PH.fx+=.01;
      return {before,prePeso,opened,peg,freeQuota,shipped,paid,held,tamper,settled,
        pegAudit:reject(()=>parsePayload(savePayload(fakePeg)))};
    }""")
    assert all(result.values()),result


def test_korean_colonial_rice(page):
    """1910 annexation, colonial yen parity, 1914 Busan rice shipment."""
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
        &&identity.currencyId==='CUR-KPY'&&firmCurrency(seller,S)==='KPY'
        &&firmCurrency(buyer,S)==='JPY'&&S.world.KR.fx===S.world.JP.fx;
      worldBuyRegionalSupply(S,seller.id,port.id,'KR-BUS-RICE',14);
      worldBuyRegionalSupply(S,seller.id,port.id,'KR-BUS-BUNKER-COAL',20);
      const route=worldInternationalRegisterRoute(S,seller.id,profileId);
      const wh=worldInternationalInstallWarehouse(S,buyer.id,depot.id,profileId);
      const order=worldInternationalPlaceOrder(S,buyer.id,{
        routeId:route.id,warehouseId:wh.id,productId:'PRD-R23',quantity:14,
        cargoLitres:30,unitPriceSeller:80,maxPaymentBuyer:100000,paymentDays:60});
      worldInternationalActOrder(S,seller.id,order.id,'approve');
      S.month=6;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const shipped=cargo?.status==='IN_TRANSIT'&&cargo.quantity===14&&cargo.loadKg===15
        &&cargo.sellerRate===cargo.buyerRate&&cargo.prepaidSeller===cargo.prepaidBuyer
        &&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R23']?.q&&!check(S).length;
      const damaged=structuredClone(S);damaged.worldExpansion.internationalShipments.at(-1).loadKg++;
      const tamper=rejects(()=>parsePayload(savePayload(damaged)));
      S.month=7;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const paid=cargo.credit.paidAt===ym(1914,7)
        &&!worldInternationalRouteAvailable(S,profileId);
      S.month=8;worldInternationalReceiveShipments(S);
      const restored=parsePayload(savePayload(S));
      const delivered=cargo.status==='DELIVERED'&&buyer.stock['PRD-R23'].q===14
        &&buyer.stock['PRD-R23'].v===cargo.totalBuyer
        &&!acc(seller,'worldShipmentStock')&&!check(restored).length
        &&!consolidate(restored).errors.length;
      const incorrectFx=structuredClone(restored);incorrectFx.world.KR.fx+=.1;
      const pegRejected=rejects(()=>parsePayload(savePayload(incorrectFx)));
      return {initiallyClosed,beforeAnnexation,opened,parity,shipped,tamper,paid,delivered,pegRejected};
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
        maxPaymentBuyer:100000,paymentDays:60});
      worldInternationalActOrder(S,seller.id,o.id,'approve');
      S.month=departure;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const shipped=cargo?.status==='IN_TRANSIT'&&cargo.quantity===14&&cargo.loadKg===15
        &&cargo.fuelRequired>0&&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock[product]?.q&&!check(S).length;
      const forged=structuredClone(S);
      forged.worldExpansion.internationalShipments.at(-1).loadKg++;
      const tamper=(()=>{try{parsePayload(savePayload(forged));return false;}catch{return true;}})();
      S.month=payMonth;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const prepaid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(year,payMonth)
        &&!worldInternationalRouteAvailable(S,profile);
      S.month=departure+worldInternationalProfile(profile).transitMonths;
      worldInternationalReceiveShipments(S);
      const saved=parsePayload(savePayload(S));
      const done=cargo.status==='DELIVERED'&&buyer.stock[product]?.q===14
        &&buyer.stock[product].v===cargo.totalBuyer&&!acc(seller,'worldShipmentStock')
        &&!check(saved).length&&!consolidate(saved).errors.length;
      return {initiallyClosed,before,opened,identities,shipped,tamper,prepaid,done};
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
      S.year=1934;S.month=5;S.monthCommitted=ym(1934,5)-1;
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
        unitPriceSeller:localFromBase(40,'IN'),maxPaymentBuyer:100000,paymentDays:60});
      worldInternationalActOrder(S,seller.id,o.id,'approve');
      S.month=6;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
      const cargo=S.worldExpansion.internationalShipments.at(-1);
      const shipped=cargo?.status==='IN_TRANSIT'&&cargo.quantity===14
        &&cargo.loadKg===15&&cargo.sellerRate!==cargo.buyerRate
        &&acc(seller,'worldShipmentStock')===cargo.bookCost
        &&!buyer.stock['PRD-R23']?.q&&!check(S).length;
      const damaged=structuredClone(S);damaged.worldExpansion.internationalShipments.at(-1).fuelRequired++;
      const tamper=rejects(()=>parsePayload(savePayload(damaged)));
      S.month=7;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const paid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(1934,7)
        &&!worldInternationalRouteAvailable(S,profileId);
      S.month=8;worldInternationalReceiveShipments(S);
      const restored=parsePayload(savePayload(S));
      const done=cargo.status==='DELIVERED'&&buyer.stock['PRD-R23'].q===14
        &&buyer.stock['PRD-R23'].v===cargo.totalBuyer&&!acc(seller,'worldShipmentStock')
        &&!check(restored).length&&!consolidate(restored).errors.length;
      return {initiallyClosed,beforeUnification,opened,currency,shipped,tamper,paid,done};
    }""")
    assert all(result.values()),result

def main():
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
        result = page.evaluate("""() => {
          const rejects=action=>{try{action();return false;}catch{return true;}};
          const legacy=newGame({country:'UK',era:1900,difficulty:'normal',history:'historical',name:'Legacy world'});
          const originalPlayer=company(legacy.playerId,legacy);
          legacy.config.scenario='world';
          legacy.worldExpansion=makeWorldExpansion(0);
          delete legacy.worldExpansion.marketRegistryVersion;
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
          S.month=6;worldInternationalResolveOrders(S);worldInternationalSettleCredit(S);
          const [a,b]=S.worldExpansion.internationalShipments;
          const loading=a?.quantity===6&&a.cargoLitres===51&&a.loadKg===26&&a.fuelRequired===8
            &&b?.quantity===1&&b.cargoLitres===4&&b.loadKg===2&&b.fuelRequired===1
            &&first.acceptedQty===6&&second.acceptedQty===1;
          const ownership=purchase.quantity===20&&a?.status==='IN_TRANSIT'&&a.credit.paidAt===null
            &&acc(seller,'worldShipmentStock')===a.bookCost+b.bookCost
            &&!buyer.stock['PRD-R22']?.q&&seller.stock['PRD-R22'].q===13&&!check(S).length;
          const altered=structuredClone(S);altered.worldExpansion.internationalShipments[0].loadKg--;
          const audit=rejects(()=>parsePayload(savePayload(altered)));
          S.month=7;
          worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
          const prepaid=a?.credit.paidAt===ym(1909,7)&&a.status==='IN_TRANSIT'
            &&acc(buyer,'worldSupplierAdvances')===a.prepaidBuyer+b.prepaidBuyer
            &&acc(buyer,'worldImportDutyPrepaid')===a.dutyBuyer+b.dutyBuyer;
          S.month=8;worldInternationalReceiveShipments(S);
          const restored=parsePayload(savePayload(S));
          const shipment=restored.worldExpansion.internationalShipments[0];
          const settlement=a?.status==='DELIVERED'&&b?.status==='DELIVERED'
            &&shipment.cargoLitres===51&&shipment.credit.paidAt===ym(1909,7)
            &&buyer.stock['PRD-R22'].q===7&&buyer.stock['PRD-R22'].v===a.totalBuyer+b.totalBuyer
            &&!acc(seller,'worldShipmentStock')&&!acc(buyer,'worldSupplierAdvances')
            &&!check(restored).length&&!consolidate(restored).errors.length;
          S.month=11;
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
            "currency": "MXP", "year": 1906, "offer": "MX-VER-COFFEE", "authority": "CUSTOMS-US-NOLA-1897",
        })
        test_steamship_export(page, {
            **gulf_coffee,
            "profile": "BR-US-RIO-COFFEE", "country": "BR", "site": "BR-RIO", "city": "CITY-29-01",
            "currency": "BRM", "year": 1910, "offer": "BR-RIO-COFFEE", "authority": "CUSTOMS-US-NOLA-1909",
        })
        test_steamship_export(page, {
            "profile": "AR-UK-BUENOSAIRES-WHEAT", "country": "AR", "site": "AR-BUE", "city": "CITY-30-01",
            "currency": "ARM", "year": 1921, "offer": "AR-BUE-WHEAT", "authority": None,
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
            "currency": "NLG", "year": 1907, "offer": "NL-ROT-PULP", "authority": None,
            "buyerCountry": "US", "destination": "US-PHL", "product": "PRD-M13", "departure": 3, "payMonth": 4,
        })
        test_steamship_export(page, {
            "profile": "EG-UK-ALEXANDRIA-COTTON", "country": "EG", "site": "EG-ALX",
            "city": "CITY-34-02", "currency": "EGP", "year": 1908, "offer": "EG-ALX-COTTON",
            "authority": None, "buyerCountry": "UK", "destination": "UK-LIV",
            "product": "PRD-R20", "departure": 6, "payMonth": 7,
        })
        test_italy_coal_import(page)
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
            "customsCurrency": "CUR-STS", "buyerCountry": "SG", "destination": "SG-SIN",
            "product": "PRD-R23", "departure": 4, "payMonth": 5,
        })
        test_steamship_export(page, {
            "profile": "SG-UK-SINGAPORE-RUBBER", "country": "SG", "site": "SG-SIN",
            "city": "CITY-22-01", "currency": "STS", "year": 1911,
            "offer": "SG-SIN-RUBBER", "authority": None,
            "buyerCountry": "UK", "destination": "UK-LON",
            "product": "PRD-R29", "departure": 3, "payMonth": 4,
        })
        test_steamship_export(page, {
            "profile": "CN-UK-HANKOW-SOY", "country": "CN", "site": "CN-HAN",
            "city": "CITY-15-04", "currency": "CNT", "year": 1907,
            "offer": "CN-HAN-SOY", "authority": None,
            "buyerCountry": "UK", "destination": "UK-LIV", "product": "PRD-R25",
            "departure": 5, "payMonth": 6,
        })
        test_steamship_export(page, {
            "profile": "ID-JP-BATAVIA-SUGAR", "country": "ID", "site": "ID-BAT",
            "city": "CITY-18-01", "currency": "IDG", "year": 1907,
            "offer": "ID-BAT-SUGAR", "authority": None,
            "buyerCountry": "JP", "destination": "JP-YOK", "product": "PRD-M40",
            "departure": 5, "payMonth": 6,
        })
        test_nigeria_colonial_cocoa(page)
        test_steamship_export(page, {
            "profile": "ES-UK-BILBAO-IRON", "country": "ES", "site": "ES-BIL",
            "city": "CITY-05-01", "currency": "ESP", "year": 1907,
            "offer": "ES-BIL-IRON", "authority": None,
            "buyerCountry": "UK", "destination": "UK-CDF", "product": "PRD-R01",
            "departure": 5, "payMonth": 6,
        })
        test_philippines_sugar_customs(page)
        test_steamship_export(page, {
            "profile": "RU-UK-PETERSBURG-TIMBER", "country": "RU", "site": "RU-SPB",
            "city": "CITY-06-02", "currency": "RUR", "year": 1904,
            "offer": "RU-SPB-TIMBER", "authority": None,
            "buyerCountry": "UK", "destination": "UK-LON", "product": "PRD-R19",
            "departure": 5, "payMonth": 6,
        })
        test_steamship_export(page, {
            "profile": "TR-UK-SMYRNA-COTTON", "country": "TR", "site": "TR-IZM",
            "city": "CITY-38-03", "currency": "OTL", "year": 1909,
            "offer": "TR-IZM-COTTON", "authority": None,
            "buyerCountry": "UK", "destination": "UK-LIV", "product": "PRD-R20",
            "departure": 5, "payMonth": 6,
        })
        test_korean_colonial_rice(page)
        test_steamship_export(page, {
            "profile": "MY-UK-PENANG-RUBBER", "country": "MY", "site": "MY-PEN",
            "city": "CITY-21-02", "currency": "STS", "year": 1911,
            "offer": "MY-PEN-RUBBER", "authority": None,
            "buyerCountry": "UK", "destination": "UK-LON", "product": "PRD-R29",
            "departure": 4, "payMonth": 5,
        })
        test_dated_colonial_export(page, {
            "profile": "KE-UK-MOMBASA-COFFEE", "country": "KE", "site": "KE-MBA",
            "city": "CITY-36-02", "currency": "EAS", "year": 1923,
            "opensYear": 1922, "opensMonth": 8, "offer": "KE-MBA-COFFEE",
            "buyerCountry": "UK", "destination": "UK-LON", "product": "PRD-R27",
            "departure": 5, "payMonth": 6,
        })
        test_dated_colonial_export(page, {
            "profile": "MA-FR-CASABLANCA-WHEAT", "country": "MA", "site": "MA-CAS",
            "city": "CITY-37-02", "currency": "MAF", "year": 1923,
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
            "city": "CITY-12-01", "currency": "AHK", "year": 1905,
            "offer": "AT-VIE-TIMBER", "authority": None,
            "buyerCountry": "DE", "destination": "DE-MUN", "product": "PRD-R19",
            "departure": 4, "payMonth": 5,
        })
        test_steamship_export(page, {
            "profile": "GR-FR-PIRAEUS-OLIVE", "country": "GR", "site": "GR-PIR",
            "city": "CITY-13-02", "currency": "GRD", "year": 1907,
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
            "city": "CITY-19-02", "currency": "ICP", "year": 1907,
            "offer": "VN-SGN-RICE", "authority": None,
            "buyerCountry": "FR", "destination": "FR-MAR", "product": "PRD-R23",
            "departure": 5, "payMonth": 6,
        })
        test_steamship_export(page, {
            "profile": "IR-IN-BANDARABBAS-WOOL", "country": "IR", "site": "IR-BND",
            "city": "CITY-40-01", "currency": "IRK", "year": 1905,
            "offer": "IR-BND-WOOL", "authority": None,
            "buyerCountry": "IN", "destination": "IN-BOM", "product": "PRD-R21",
            "departure": 5, "payMonth": 6,
        })
        test_saudi_rice_import(page)
        assert not errors, errors
        browser.close()
    print("PASS Phase 4 Canada, Australia, New Zealand, Mexico, Brazil, Argentina, Chile, Colombia, Sweden, Netherlands, Italy, Egypt, India, South Africa, Siam, Straits Singapore, Qing China, Netherlands East Indies and Colonial Nigeria, Spain, Philippines, Russian Empire, Colonial Korea, Ottoman Empire, British Malaya, Kenya, Morocco, Switzerland, Austria, Poland, Greece, French Indochina, Qajar Persia and Saudi Arabia: sourced cargo, loading, shipment and settlement")


if __name__ == "__main__":
    main()
