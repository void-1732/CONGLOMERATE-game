"""Services prove delivery, paid custody, real agency sales, training and joint development."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result = page.evaluate("""() => {
          S=newWorldGame({country:'JP',name:'Phase 2-L services'});
          const parent=company(S.playerId);
          function subsidiary(name,industry='auto'){
            const capital=60000000,payer=S.seq;
            post(parent,{investment:capital},{cash:capital},'検証用の設立','investing',S);
            const f=initFirm(S,{name,country:'JP',industry,seedBase:600000,publicOwnership:false});
            f.owners=[{id:parent.id,econ:1,vote:1}];
            registerEquityLink(S,{parentId:parent.id,childId:f.id,ratio:1,kind:'foundation',
              considerationLocal:capital,buyerJournal:payer,
              childJournal:f.journals.find(j=>j.text==='創業資本').id,bookEquityBase:baseFromLocal(capital,'JP'),
              cashAcquiredBase:baseFromLocal(acc(f,'cash'),'JP')});
            return f;
          }
          const warehouseFirm=subsidiary('Warehouse'),agent=subsidiary('Agent','sales'),insurer=subsidiary('Insurer','service');
          const origin=parent.plants[0],destination=warehouseFirm.plants[0];
          destination.siteId='JP-YOK';
          const coLocated={...structuredClone(origin),id:'P-WORLD-SVC',siteId:'JP-YOK',name:'同拠点の荷主工場'};
          parent.plants.push(coLocated);syncPlant(parent);
          function date(month){
            S.year=1970;S.month=month;S.monthCommitted=ym(1970,month)-1;
            applyWorldHistory(S);syncWorldIdentities(S);
          }
          date(1);
          const put=(f,id,q,v)=>{
            post(f,{materials:v},{cash:v},'検証用現物仕入','operating',S);
            f.stock[id]={q,v};
          };
          for(const f of [parent,warehouseFirm]){
            if(!f.research.tree.done.includes('production-1'))f.research.tree.done.push('production-1');
          }
          put(parent,'PRD-E16',1,1200);put(parent,'PRD-E17',1,300);
          put(parent,'PRD-R04',8,40);put(parent,'PRD-R19',10,100);
          put(warehouseFirm,'PRD-E20',1,120);
          const route=worldRegisterDomesticRoute(S,parent.id,'JP-TOK','JP-YOK',29,'VERIFIED','JP-SHIMBASHI-YOKOHAMA');
          const depot=worldInstallDomesticWarehouse(S,warehouseFirm.id,destination.id,'JP-YOKOHAMA-SHINKO');
          const storage=worldStartStorageService(S,parent.id,coLocated.id,depot.id,'PRD-R19',5,2,12);
          const hasCustody=parent.stock['PRD-R19'].q===5&&acc(parent,'worldStoredStock')===50
            &&acc(warehouseFirm,'materials')===Object.values(warehouseFirm.stock).reduce((x,t)=>x+t.v,0)
            &&!acc(warehouseFirm,'serviceRevenue')&&worldServiceActivity(S,'PRD-S04').length===0;
          const ship=q=>worldDispatchDomesticShipment(S,route.id,parent.id,origin.id,
            warehouseFirm.id,destination.id,'PRD-R19',q,10);
          let blocksOverfill=false;
          try{ship(4);}catch(e){blocksOverfill=e.message.includes('容量');}
          let blocksHazard=false;
          try{worldStartStorageService(S,parent.id,coLocated.id,depot.id,'PRD-R05',1,1,1);}
          catch(e){blocksHazard=e.message.includes('荷種');}
          const cargo=ship(3),providerCash=acc(insurer,'cash');
          const policy=worldBuyCargoInsurance(S,parent.id,insurer.id,cargo.id,20,3);
          const noEarlyPremium=acc(insurer,'cash')===providerCash+3-20&&acc(insurer,'worldInsuranceReserve')===20
            &&-acc(insurer,'worldInsuranceUnearned')===3&&!acc(insurer,'serviceRevenue')
            &&worldServiceActivity(parsePayload(savePayload(S)),'PRD-S07').length===0;
          const capacity=blocksOverfill&&blocksHazard&&worldDomesticWarehouseReservations(S.worldExpansion,depot.id)===8
            &&worldServiceActivity(S,'PRD-S03').length===0;
          let blockedRetire=false;
          try{worldRetireDomesticAsset(S,warehouseFirm.id,'warehouse',depot.id);}catch{blockedRetire=true;}
          date(2);
          worldReceiveDomesticShipments(S);
          worldFinishStorageServices(S);
          const freight=worldServiceActivity(S,'PRD-S03')[0];
          const noClaim=policy.payout===0&&worldServiceActivity(S,'PRD-S07')[0].amount===3
            &&-acc(insurer,'serviceRevenue')===3&&acc(insurer,'cash')===providerCash+3
            &&!acc(insurer,'worldInsuranceReserve')&&!acc(insurer,'worldInsuranceUnearned');
          const noEarly=blockedRetire&&storage.closedAt===null&&cargo.status==='DELIVERED'
            &&freight?.amount===cargo.freightCost&&!acc(warehouseFirm,'serviceRevenue');
          date(3);
          worldFinishStorageServices(S);
          worldFinishStorageServices(S);
          const paid=worldServiceActivity(S,'PRD-S04');
          const custodySettled=paid.length===1&&paid[0].amount===120&&paid[0].quantity===10
            &&-acc(warehouseFirm,'serviceRevenue')===120
            &&acc(parent,'worldStoredStock')===0&&parent.stock['PRD-R19'].q===7
            &&worldDomesticWarehouseReservations(S.worldExpansion,depot.id)===0&&consolidate(S).pl.intercompanySales===153;

          ensureNetwork(parent,S);agent.staff.sales=5;
          parent.distribution.salesCorporations.JP=agent.id;
          parent.distribution.contracts.JP={...parent.distribution.contracts.JP,channel:'subsidiary',dealerId:agent.id};
          const model=parent.models[0];
          post(parent,{goods:100},{cash:100},'検証用完成品','operating',S);
          parent.goods[model.id]={q:2,v:100};
          parent.marketThisMonth={};parent._salesNow=0;parent._unitsNow=0;
          sellGoods(S,parent,model.id,2,5000,'JP',[]);
          settleRegionalSalesAgentsV035(S,[]);
          const retail=worldServiceActivity(S,'PRD-S13')[0];
          const actualSales=retail?.quantity===2&&retail.amount>0&&-acc(agent,'serviceRevenue')===retail.amount
            &&parent.goods[model.id].q===0;

          parent.staff.designEngineers=12;
          const engineering=parent.partOperations.engineering;
          engineering.policy.trainingBase=1000;
          date(4);
          submitPartProject(S,parent,{family:'engine',name:'共同研究設備',
            values:{...PART_FAMILIES.engine.defaults},parent:null,output:null});
          const project=engineering.projects.at(-1);
          project.budget=project.estimate;project.status='APPROVED';
          const approvalMonth=ym(S.year,S.month),agreement={agreementId:'DEV-'+S.partEconomy.nextSerial++,
            groupId:parent.id,proposedAt:approvalMonth,approvedAt:approvalMonth,termMonths:12,endedAt:null,endReason:null,
            projectId:project.id,rightOwnerFirmId:parent.id,shares:[{firmId:parent.id,basisPoints:6000},
              {firmId:warehouseFirm.id,basisPoints:4000}],maxCommittedLocal:project.estimate,
            approvals:[parent.id,warehouseFirm.id],settlements:[]};
          S.partEconomy.developmentAgreements.push(agreement);
          const noResearchBefore=worldServiceActivity(S,'PRD-S15').length===0;
          for(let i=4;i<=8&&project.status!=='COMPLETED';i++){
            date(i);processEngineering(S,parent);refreshPartContracts(S);
          }
          const training=worldServiceActivity(S,'PRD-S09')[0],research=worldServiceActivity(S,'PRD-S15')[0];
          const realTraining=training?.amount>0&&training.quantity===12&&engineering.policy.skill>0;
          const realResearch=noResearchBefore&&research?.ref===agreement.agreementId&&research.amount>0
            &&project.status==='COMPLETED'&&Math.abs(acc(warehouseFirm,'rndExpense')-research.amount)===0;
          VIEW_FIRM=parent.id;PAGE='financeFunding';render();
          const beforeLoan=acc(parent,'cash'),salesBefore=acc(parent,'serviceRevenue');
          document.getElementById('borrowBase').value='5000000';
          borrow();
          const loan=worldServiceActivity(S,'PRD-S06')[0];
          const realLoan=loan?.principal>0&&loan.amount===0&&acc(parent,'serviceRevenue')===salesBefore
            &&acc(parent,'cash')===beforeLoan+loan.principal&&-acc(parent,'debt')===loan.principal;

          const spec=S.partEconomy.specs.find(x=>x.ownerFirmId===parent.id&&x.family==='engine');
          const line=proposeLineJob(S,parent,origin,'ADD_LINE',null,partKey(spec),2);
          approveLineJob(S,parent,line);
          const beforeConstruction=worldServiceActivity(S,'PRD-S11').length===0;
          date(S.month+line.duration);
          advanceComponentLines(S,[]);
          const construction=worldServiceActivity(S,'PRD-S11')[0];
          const realConstruction=beforeConstruction&&construction?.amount===line.cost
            &&origin.componentLines.some(x=>x.lineId===line.lineId)&&acc(parent,'constructionAssets')===0;

          const lost=ship(2);
          const claim=worldBuyCargoInsurance(S,parent.id,insurer.id,lost.id,20,4);
          destination.paused=true;syncPlant(warehouseFirm);
          date(S.month+2);
          const shipCash=acc(parent,'cash');
          worldRefundDomesticShipment(S,lost.id);
          const lossClaim=claim.payout===20&&acc(parent,'cash')===shipCash-lost.prepaid+20
            &&!acc(parent,'worldInsurancePrepaid')&&!acc(insurer,'worldInsuranceReserve')
            &&-acc(insurer,'serviceRevenue')===7&&-acc(parent,'otherRevenue')===20;

          const stored=parsePayload(savePayload(S));
          const coverage=worldPhase2ExecutableCoverage();
          const unknown=coverage.pending.join(',')==='PRD-S12,PRD-S14'
            &&coverage.counts.SERVICE_PROTOTYPE===13&&allServicesNonphysical(stored);
          function allServicesNonphysical(s){
            return s.firms.every(f=>[...WORLD_PRODUCT_SERVICE_IDS].every(id=>!f.stock[id]&&!f.goods[id]));
          }
          const persisted=!check(stored).length&&!consolidate(stored).errors.length
            &&worldServiceActivity(stored,'PRD-S04')[0].amount===120
            &&worldServiceActivity(stored,'PRD-S13')[0].amount===retail.amount
            &&worldServiceActivity(stored,'PRD-S15')[0].amount===research.amount
            &&worldServiceActivity(stored,'PRD-S06')[0].principal===loan.principal
            &&worldServiceActivity(stored,'PRD-S11')[0].ref===line.planId;
          const bad=structuredClone(stored);
          bad.worldExpansion.storageServices[0].unitFee++;
          let rejectsSpoof=false;
          try{worldValidateDomesticLogistics(bad);}catch(e){rejectsSpoof=e.message.includes('精算仕訳');}
          return {hasCustody,capacity,noEarly,custodySettled,actualSales,realTraining,realResearch,realConstruction,realLoan,noEarlyPremium,noClaim,lossClaim,unknown,persisted,rejectsSpoof};
        }""")
        assert all(result.values()), result
        assert not errors, errors
        browser.close()
    print("PASS Phase 2-L services: actual eight fulfillment pathways, cash/inventory proof, save, and pending gate")


if __name__ == "__main__":
    main()
