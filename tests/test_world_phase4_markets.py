"""Market onboarding, measured freight, calendar settlement, and V2 save upgrade."""
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


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
        &&restored.worldExpansion.appliedEvents.map(e=>e.id).join()==='HIST-AU-1901,HIST-NO-1905'
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
                              destination,product,offer,authority}) => {
      S=newWorldGame({country,name:site+' exporter'});VIEW_FIRM=S.playerId;VIEW_COUNTRY=country;
      const seller=company(S.playerId),port=seller.plants[0],identity=worldCityLocation(S,city);
      const market=identity.marketOpen&&identity.jurisdictionId==='JUR-'+country
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
      for(const [firm,id,value] of [[seller,'PRD-E18',2400],[buyer,'PRD-E20',700],[buyer,'PRD-E21',900]]){
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
      const shipped=purchase.quantity===14&&cargo?.status==='IN_TRANSIT'&&cargo.loadKg===15
        &&cargo.prepaidSeller!==cargo.prepaidBuyer&&acc(seller,'worldShipmentStock')===cargo.bookCost;
      S.month=payMonth;worldInternationalReceiveShipments(S);worldInternationalSettleCredit(S);
      const prepaid=cargo.status==='IN_TRANSIT'&&cargo.credit.paidAt===ym(year,payMonth)
        &&!worldInternationalRouteAvailable(S,profile);
      const arrival=departure+worldInternationalProfile(profile).transitMonths;
      S.month=arrival;worldInternationalReceiveShipments(S);
      const held=authority===null?!cargo.customs&&cargo.status==='DELIVERED':
        cargo.status==='IN_TRANSIT'&&cargo.customs?.arrivalAt===ym(year,arrival)
        &&cargo.customs.authorityId===authority&&cargo.customs.currencyId==='CUR-USD'
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
        assert not errors, errors
        browser.close()
    print("PASS Phase 4 Canada, Australia, New Zealand, Mexico, Brazil, Argentina, Chile, Colombia, Sweden, Netherlands, Italy, Egypt, India and South Africa: sourced cargo, loading, shipment and settlement")


if __name__ == "__main__":
    main()
