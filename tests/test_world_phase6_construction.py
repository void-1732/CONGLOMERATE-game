"""Phase 6 fixed-duration construction, physical inputs, accounting and UI."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]

def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
        page=browser.new_page()
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.set_content((ROOT/"index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        ids=page.evaluate("""()=>{
          saveAuto=async()=>true;S=newWorldGame({country:'JP',name:'Rail customer'});
          VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='corporateSubsidiaries';render();
          document.querySelector('#subName').value='Builder';
          document.querySelector('#subCountry').value='JP';
          document.querySelector('#subIndustry').value='service';
          document.querySelector('#subCapital').value='650000';
          createSub();syncWorldIdentities(S);
          const bid=S.playerId,buyer=company(bid,S),seller=S.firms.find(f=>f.name==='Builder'),sid=seller.id,bp=buyer.plants[0].id,sp=seller.plants[0].id;
          S.year=1935;S.month=1;S.monthCommitted=ym(S.year,S.month)-1;applyWorldHistory(S);syncWorldIdentities(S);
          for(const f of [buyer,seller]){if(!f.research.tree.done.includes('production-1'))f.research.tree.done.push('production-1');f.auto=false;f.delegate.mode='manual';f.rnd.budgetBase=0;}
          seller.staff.production=15;seller.staffTarget.production=15;
          const add=(f,key,q,unit)=>{const amount=q*unit;post(f,{materials:amount},{cash:amount},'試験用有償調達','operating',S);const st=f.stock[key]??={q:0,v:0};st.q+=q;st.v+=amount};
          add(seller,'PRD-E14',1,300);add(seller,'PRD-E16',1,400);add(seller,'PRD-E17',1,120);add(seller,'PRD-M03',4,20);add(seller,'PRD-M09',4,10);
          VIEW_FIRM=sid;PAGE='worldInfrastructure';render();return {bid,sid,bp,sp};
        }""")
        page.locator("#worldConstructionMachinePlant").select_option(ids["sp"])
        page.locator('[data-world-build-contract="machine"]').click()
        reserved_construction=page.evaluate("""({bid,sid,bp,sp})=>{
          const s=structuredClone(S),buyer=company(bid,s);
          const target=s.firms.find(f=>f.id!==bid&&f.id!==sid&&f.country==='JP'&&f.owners.every(o=>o.id==='PUBLIC'));
          const args={kind:'DR',profileId:'JP-SHIMBASHI-YOKOHAMA',buyerPlantId:bp,sellerId:sid,sellerPlantId:sp,feeBase:40000};
          const c=worldPlaceConstructionContract(s,bid,args);
          const amount=localFromBase(maQuote(s,buyer,target,30,2.5).total,buyer.country,s);
          post(buyer,{cash:amount+c.fee+1000},{capital:amount+c.fee+1000},'検証用資本','financing',s);
          const r=phase7ProposeMA(s,bid,target.id,30,2.5);
          const spend=phase7AvailableCash(s,buyer)-(c.fee-1);
          post(buyer,{otherExpense:spend},{cash:spend},'検証用支出','operating',s);
          const reject=fn=>{try{fn();return false}catch(e){return e.message.includes('支払資金')}};
          const before=JSON.stringify(s);
          const acceptance=reject(()=>worldAcceptConstructionContract(s,sid,c.id))&&before===JSON.stringify(s);
          const completion=!worldConstructionFundingReady(s,c,buyer);
          // Use the same valid fixture without an already offered contract.
          s.worldExpansion.constructionContracts=[];
          const beforeOffer=JSON.stringify(s);
          const placement=reject(()=>worldPlaceConstructionContract(s,bid,args))&&beforeOffer===JSON.stringify(s);
          return {acceptance,completion,placement,reservation:phase7ReservedCash(s,bid)===r.amountLocal};
        }""",ids)
        assert len(reserved_construction)==4 and all(reserved_construction.values()),reserved_construction
        print("PASS Phase 6/7: reserved acquisition cash excluded from construction placement, acceptance and completion")
        page.evaluate("bid=>{VIEW_FIRM=bid;PAGE='worldInfrastructure';render()}",ids["bid"])
        target="|".join(["DR","JP-SHIMBASHI-YOKOHAMA",ids["bp"],ids["sid"],ids["sp"]])
        page.locator("#worldConstructionTarget").select_option(target)
        page.locator("#worldConstructionFee").fill("40000")
        page.locator('[data-world-build-contract="offer"]').click()
        page.evaluate("sid=>{VIEW_FIRM=sid;PAGE='worldInfrastructure';render()}",ids["sid"])
        page.locator('[data-world-build-contract="accept"]').click()
        result=page.evaluate("""async({bid,sid,bp,sp})=>{
          const c=S.worldExpansion.constructionContracts[0],id=c.id,first=S.monthCommitted;
          const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
          const add=(f,key,q,unit)=>{const amount=q*unit;post(f,{materials:amount},{cash:amount},'試験用有償調達','operating',S);const st=f.stock[key]??={q:0,v:0};st.q+=q;st.v+=amount};
          const place=()=>worldPlaceConstructionContract(S,bid,{kind:'DR',profileId:'JP-SHIMBASHI-YOKOHAMA',buyerPlantId:bp,sellerId:sid,sellerPlantId:sp,feeBase:40000});
          const accepted=c.status==='ACTIVE'&&c.dueAt===c.acceptedAt+1;
          const rev0=acc(company(sid,S),'serviceRevenue');
          await close();let x=S.worldExpansion.constructionContracts.find(x=>x.id===id);
          const wip=x.status==='ACTIVE'&&x.work.length===1&&x.bookCost>0&&acc(company(sid,S),'worldConstructionWip')===x.bookCost&&acc(company(sid,S),'serviceRevenue')===rev0&&Object.keys(S.worldExpansion.domesticRoutes??{}).length===0;
          const savedPartial=parsePayload(savePayload(S)).worldExpansion.constructionContracts[0].bookCost===x.bookCost;
          await close();x=S.worldExpansion.constructionContracts.find(x=>x.id===id);const rec=S.worldExpansion.constructionReceipts.find(y=>y.contractId===id),asset=S.worldExpansion.domesticRoutes[rec.assetId],g=consolidate(S);
          const complete=x.status==='COMPLETE'&&asset.capacityQty===10&&asset.ownerCompanyId===bid;
          const account=acc(company(sid,S),'worldConstructionWip')===0&&acc(company(sid,S),'serviceRevenue')===rev0-x.fee&&g.errors.length===0&&g.cf.reconciled&&g.pl.unrealizedProfit===x.fee-x.bookCost;
          const service=worldServiceActivity(S,'PRD-S11').some(y=>y.ref===rec.id&&y.providerId===sid);
          const forged=structuredClone(S);forged.worldExpansion.constructionContracts[0].work[0].items[0].quantity++;let tamper=false;try{parsePayload(savePayload(forged))}catch{tamper=true}
          const rev1=acc(company(sid,S),'serviceRevenue'),maintenance=asset.constructionMaintenance;
          add(company(sid,S),'PRD-M03',2,20);add(company(sid,S),'PRD-M09',2,10);
          const c2=place();worldAcceptConstructionContract(S,sid,c2.id);await close();const interim=S.worldExpansion.constructionContracts.find(y=>y.id===c2.id);const work=interim.status==='ACTIVE'&&interim.bookCost>0;await close();
          const fail=S.worldExpansion.constructionContracts.find(y=>y.id===c2.id),ff=company(sid,S),bb=company(bid,S);
          const failed=work&&fail.status==='FAILED'&&fail.lossJournal!=null&&acc(ff,'worldConstructionWip')===0&&acc(ff,'serviceRevenue')===rev1&&Object.keys(S.worldExpansion.domesticRoutes).length===1;
          const upkeep=bb.journals.some(j=>j.text.includes('請負建設インフラの固定維持費 '+asset.id)&&j.dr.some(y=>y[0]==='maintenance'&&y[1]===maintenance));
          const clean=check(S).length===0&&consolidate(S).errors.length===0&&parsePayload(savePayload(S)).worldExpansion.constructionContracts.length===2;
          return {accepted,wip,savedPartial,complete,account,service,tamper,failed,upkeep,clean,months:S.monthCommitted===first+4};
        }""",ids)
        assert len(result)==11 and all(result.values()),result
        investment=page.evaluate("""()=>{
          // Isolated ranking fixture; not a live save or fabricated economic event.
          const trial=structuredClone(S),w=trial.worldExpansion,month=ym(trial.year,trial.month);
          const c=w.constructionContracts[0],route=Object.values(w.domesticRoutes)[0];
          const buyer=company(c.buyerId,trial),terms=worldConstructionTerms(trial,c.kind,c.profileId);
          const maintenance=localFromBase(terms.maintenanceBase,buyer.country,trial);
          const gross=12*(maintenance+10000),fuel=12*1000;
          w.domesticShipments=[{sellerId:buyer.id,routeId:route.id,status:'DELIVERED',receivedAt:month-1,freightCost:gross,fuelBookCost:fuel}];
          const low={...c,fee:18000},high={...c,fee:36000};
          const ranked=worldRankInfrastructureInvestments(trial,[high,low]);
          const actual=ranked.length===2&&ranked[0].c===low&&ranked[0].payback.net===9000&&ranked[0].payback.months===2&&ranked[1].payback.months===4;
          const protectedBuyer=worldPlanAiInfrastructure(trial).length===0;
          w.domesticShipments[0].status='DISPATCHED';
          const noDelivery=worldRankInfrastructureInvestments(trial,[low]).length===0;
          w.domesticShipments[0].status='DELIVERED';w.domesticShipments[0].freightCost=fuel;
          const loss=worldRankInfrastructureInvestments(trial,[low]).length===0;
          return {actual,protectedBuyer,noDelivery,loss};
        }""")
        assert len(investment)==4 and all(investment.values()),investment
        print("PASS Phase 6 infrastructure investment ranking: actual margin, shortest payback, controlled buyer, non-delivery and loss rejection")
        page.evaluate("""({bid,sid})=>{
          const buyer=company(bid,S),seller=company(sid,S);
          buyer.research.tree.done=[...new Set([...buyer.research.tree.done,'energy-1'])];
          for(const [f,key,q,unit] of [[buyer,'PRD-E04',1,400],[buyer,'PRD-R04',5,20],
                                     [seller,'PRD-E04',1,300],[seller,'PRD-M03',4,20],[seller,'PRD-M09',4,10]]){
            const amount=q*unit;
            post(f,{materials:amount},{cash:amount},'試験用有償調達','operating',S);
            const stock=f.stock[key]??={q:0,v:0};stock.q+=q;stock.v+=amount;
          }
          VIEW_FIRM=bid;PAGE='worldInfrastructure';render();
        }""",ids)
        plant_target="|".join(["PG","JP-TOK",ids["bp"],ids["sid"],ids["sp"]])
        page.locator("#worldConstructionTarget").select_option(plant_target)
        page.locator("#worldConstructionFee").fill("40000")
        page.locator('[data-world-build-contract="offer"]').click()
        page.evaluate("sid=>{VIEW_FIRM=sid;PAGE='worldInfrastructure';render()}",ids["sid"])
        page.locator('[data-world-build-contract="accept"]').click()
        power=page.evaluate("""async({bid,sid,bp,sp})=>{
          const reject=fn=>{try{fn();return false}catch{return true}};
          const initial=S.worldExpansion.constructionContracts.find(c=>c.kind==='PG'),id=initial.id;
          const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
          const job=()=>S.worldExpansion.constructionContracts.find(c=>c.id===id);
          const gated=initial.status==='ACTIVE'&&reject(()=>worldSetGridPlan(S,bid,bp,'fuel',3))
            &&reject(()=>worldInstallGenerator(S,bid,bp))
            &&reject(()=>worldPlaceConstructionContract(S,bid,{kind:'PG',profileId:'JP-TOK',buyerPlantId:bp,sellerId:sid,sellerPlantId:sp,feeBase:40000}));
          await close();
          const partial=job().status==='ACTIVE'&&job().work.length===1&&!S.worldExpansion.powerGenerators[bp]
            &&job().work[0].items.every(x=>x.productId!=='PRD-E04')&&job().bookCost===acc(company(sid,S),'worldConstructionWip');
          await close();
          const asset=S.worldExpansion.powerGenerators[bp],receipt=S.worldExpansion.constructionReceipts.find(r=>r.id===job().receiptId);
          const delivered=job().status==='COMPLETE'&&asset?.id===receipt?.assetId&&asset.ownerCompanyId===bid
            &&company(sid,S).stock['PRD-E04'].q===0&&company(bid,S).stock['PRD-E04'].q===1
            &&job().work[1].items.some(x=>x.productId==='PRD-E04'&&x.quantity===1);
          const buyer=company(bid,S),seller=company(sid,S);
          const accounted=asset.assetValue===job().fee&&receipt.amount===job().fee&&receipt.bookCost===job().bookCost
            &&buyer.journals.some(j=>j.id===receipt.costReceipt.buyerJournal&&j.cr.some(([a,v])=>a==='cash'&&v===asset.assetValue))
            &&seller.journals.some(j=>j.id===receipt.costReceipt.sellerJournal&&j.dr.some(([a,v])=>a==='cash'&&v===asset.assetValue))
            &&acc(seller,'worldConstructionWip')===0&&consolidate(S).cf.reconciled;
          worldSetGridPlan(S,bid,bp,'fuel',3);
          await close();
          const w=S.worldExpansion,operating=w.energyReceipts.some(r=>r.plantId===bp&&r.fuelQty===3&&r.deliveredKwh===27)
            &&w.powerGenerators[bp].accumulatedDepreciation>0&&company(bid,S).stock['PRD-R04'].q===2;
          const restored=parsePayload(savePayload(S)),forged=structuredClone(restored);
          forged.worldExpansion.constructionReceipts.find(r=>r.contractId===id).assetId='GEN-other';
          const saved=restored.worldExpansion.powerGenerators[bp].constructionReceiptId===receipt.id
            &&!check(restored).length&&!consolidate(restored).errors.length&&reject(()=>parsePayload(savePayload(forged)));
          return {gated,partial,delivered,accounted,operating,saved};
        }""",ids)
        assert len(power)==6 and all(power.values()),power
        print("PASS Phase 6 contracted power generation: UI order, physical construction, settlement, fuel and restore")
        regions=page.evaluate("""({sid})=>{
          const f=company(sid,S),site=findSite('DE-BER');
          const local=SITE_CATALOG.find(x=>x.country===f.country&&worldPublicPowerDemand(S,x.id)>0&&!worldConstructionSiteAvailable(S,x.id));
          if(!local)throw Error('Missing power-only location');
          const noForeign=!factorySiteAvailable(f,site,S);
          const earlier={...S,year:1914,month:12};
          const dateGate=!worldConstructionSiteAvailable(earlier,local.id)&&!factorySiteAvailable(f,local,earlier);
          post(f,{cash:1000000000},{capital:1000000000},'試験用資金拠出','financing',S);
          VIEW_FIRM=sid;PAGE='facilityExpansion';render();
          const select=document.querySelector('#factorySite'),listed=[...select.options].some(x=>x.value===local.id);
          document.querySelector('#factoryName').value='Regional power facility';select.value=local.id;
          factoryBuild();
          const p=f.plants.find(x=>x.name==='Regional power facility');
          const built=p?.siteId===local.id&&!!p.construction&&worldConstructionTerms(S,'PG',local.id)?.site===p.siteId;
          return {noForeign,dateGate,listed,built,clean:!check(parsePayload(savePayload(S))).length};
        }""",ids)
        assert len(regions)==5 and all(regions.values()),regions
        print("PASS Phase 6 power-only construction site selection, date gate and save")
        port=page.evaluate("""async()=>{
          saveAuto=async()=>true;S=newWorldGame({country:'JP',name:'Port customer'});
          VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';PAGE='corporateSubsidiaries';render();
          document.querySelector('#subName').value='Port Builder';document.querySelector('#subCountry').value='JP';
          document.querySelector('#subIndustry').value='service';document.querySelector('#subCapital').value='650000';
          createSub();syncWorldIdentities(S);
          const bid=S.playerId,sid=S.firms.find(f=>f.name==='Port Builder').id;
          S.year=1935;S.month=1;S.monthCommitted=ym(S.year,S.month)-1;applyWorldHistory(S);syncWorldIdentities(S);
          for(const id of [bid,sid]){
            const f=company(id,S);post(f,{cash:1000000000},{capital:1000000000},'試験用資金拠出','financing',S);
            if(!f.research.tree.done.includes('production-1'))f.research.tree.done.push('production-1');
            f.auto=false;f.delegate.mode='manual';f.rnd.budgetBase=0;
            VIEW_FIRM=id;PAGE='facilityExpansion';render();
            document.querySelector('#factoryScale').value='small';document.querySelector('#factoryKind').value='assembly';
            document.querySelector('#factoryName').value='Yokohama';document.querySelector('#factorySite').value='JP-YOK';
            factoryBuild();if(!f.plants.some(p=>p.name==='Yokohama'))throw Error('facility not built '+id);
          }
          const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
          await close();await close();
          const buyer=company(bid,S),seller=company(sid,S),bp=buyer.plants.find(p=>p.name==='Yokohama').id,sp=seller.plants.find(p=>p.name==='Yokohama').id;
          seller.staff.production=20;seller.staffTarget.production=20;
          const add=(f,key,q,unit)=>{const amount=q*unit;post(f,{materials:amount},{cash:amount},'試験用有償調達','operating',S);const st=f.stock[key]??={q:0,v:0};st.q+=q;st.v+=amount};
          add(seller,'PRD-E14',1,300);add(seller,'PRD-E20',2,400);add(seller,'PRD-E21',1,120);add(seller,'PRD-E18',1,1000);add(seller,'PRD-M03',12,20);add(seller,'PRD-M09',12,10);
          worldInstallConstructionMachine(S,sid,sp);const results={};
          for(const [kind,profile,table] of [['DW','JP-YOKOHAMA-SHINKO','domesticWarehouses'],['IR','JP-US-SEATTLE-STEAM','internationalRoutes'],['IW','US-JP-SEATTLE-STEAM','internationalWarehouses']]){
            const c=worldPlaceConstructionContract(S,bid,{kind,profileId:profile,buyerPlantId:bp,sellerId:sid,sellerPlantId:sp,feeBase:40000});worldAcceptConstructionContract(S,sid,c.id);await close();await close();
            const row=S.worldExpansion.constructionContracts.find(x=>x.id===c.id),r=S.worldExpansion.constructionReceipts.find(x=>x.contractId===c.id),asset=S.worldExpansion[table]?.[r?.assetId];
            results[kind]=row.status==='COMPLETE'&&!!asset&&asset.ownerCompanyId===bid&&asset.profileId===profile;
          }
          const g=consolidate(S);results.clean=check(S).length===0&&g.errors.length===0&&g.cf.reconciled;
          results.restore=parsePayload(savePayload(S)).worldExpansion.constructionReceipts.length===3;
          const inbound=Object.values(S.worldExpansion.internationalWarehouses)[0];
          const cargo=WORLD_INTERNATIONAL_ROUTE_EVIDENCE[inbound.profileId].products?.[0]??'PRD-R22',client=company(sid,S);
          add(client,cargo,6,300);
          const storage=worldStartStorageService(S,sid,sp,inbound.id,cargo,6,1,80000);
          const inCustody=parsePayload(savePayload(S));
          results.custody=worldInternationalWarehouseReservations(inCustody.worldExpansion,inbound.id)===6
            &&acc(company(sid,inCustody),'worldStoredStock')===1800;
          await close();await close();
          const stored=S.worldExpansion.storageServices.find(x=>x.id===storage.id);
          const provider=company(bid,S),payback=worldConstructionPayback(S,S.worldExpansion.constructionContracts.find(x=>x.kind==='IW'));
          results.storage=stored.closedAt!==null&&worldInternationalWarehouseReservations(S.worldExpansion,inbound.id)===0
            &&acc(company(sid,S),'worldStoredStock')===0&&provider.journals.some(j=>j.id===stored.closeJournal+2&&j.amount===480000);
          results.warehousePayback=payback.gross===40000&&payback.fuel===0&&payback.months!==null&&consolidate(S).cf.reconciled;
          return results;
        }""")
        assert len(port)==8 and all(port.values()),port
        print("PASS Phase 6 construction: 8 checks for warehouse custody and fees, domestic warehouse and international logistics")
        funded=page.evaluate("""async()=>{
          S=newWorldGame({country:'JP',name:'Infrastructure sponsor'});saveAuto=async()=>true;
          const bid=S.playerId;
          const addSub=name=>{
            VIEW_FIRM=bid;VIEW_COUNTRY='JP';PAGE='corporateSubsidiaries';render();
            document.querySelector('#subName').value=name;
            document.querySelector('#subCountry').value='JP';
            document.querySelector('#subIndustry').value='service';
            document.querySelector('#subCapital').value='650000';
            createSub();
            return S.firms.find(f=>f.name===name).id;
          };
          const bankId=addSub('Infrastructure lender'),sid=addSub('Infrastructure contractor');
          S.year=2001;S.month=1;S.monthCommitted=ym(S.year,S.month)-1;applyWorldHistory(S);syncWorldIdentities(S);
          const sponsor=company(bid,S),partner=company(bankId,S),seller=company(sid,S);
          for(const f of [sponsor,partner,seller]){
            post(f,{cash:1000000000},{capital:1000000000},'試験用資金拠出','financing',S);
            f.auto=false;f.delegate.mode='manual';f.rnd.budgetBase=0;
          }
          const a0=acc(sponsor,'cash'),b0=acc(partner,'cash');
          const capitalBase=Math.max(650000,Math.round(450000*eraCostFactor(S.year)));
          const p=worldFormInfrastructureJointVenture(S,bid,bankId,'Rail infrastructure JV','JP-TOK',capitalBase);
          const pid=p.id,j=S.worldExpansion.infrastructureJvs[0];
          const shares=p.owners.map(o=>o.vote).join('|')==='0.6|0.4'
            &&a0-acc(sponsor,'cash')===j.capital*.6&&b0-acc(partner,'cash')===j.capital*.4
            &&-acc(p,'capital')===capitalBase*100&&j.projectId===pid;
          const history=!worldInfrastructurePolicy('JP',ym(1999,6))&&!!worldInfrastructurePolicy('JP',ym(1999,7))
            &&!!worldInfrastructurePolicy('UK',ym(1995,1))&&!worldInfrastructurePolicy('FR',ym(1995,1));
          const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
          const tax=20000000;
          post(sponsor,{taxExpense:tax},{taxDue:tax},'試験用法人税債務','operating',S);
          sponsor.payables.push({amount:tax,due:ym(S.year,S.month),account:'taxDue',note:'法人税'});
          await close();
          const buyer=company(pid,S),contractor=company(sid,S),sp=contractor.plants[0].id,bp=buyer.plants[0].id;
          for(const f of [buyer,contractor])if(!f.research.tree.done.includes('production-1'))f.research.tree.done.push('production-1');
          contractor.staff.production=15;contractor.staffTarget.production=15;
          const add=(key,q,unit)=>{const amount=q*unit;post(contractor,{materials:amount},{cash:amount},'試験用有償調達','operating',S);contractor.stock[key]={q,v:amount}};
          add('PRD-E14',1,300);add('PRD-E16',1,400);add('PRD-E17',1,120);add('PRD-M03',4,20);add('PRD-M09',4,10);
          worldInstallConstructionMachine(S,sid,sp);
          const ui=worldConstructionPanel(S,buyer,true).includes('worldConstructionGrant')
            &&worldConstructionPanel(S,buyer,true).includes('worldConstructionBank');
          const params={kind:'DR',profileId:'JP-SHIMBASHI-YOKOHAMA',buyerPlantId:bp,sellerId:sid,sellerPlantId:sp,feeBase:40000,grantRequested:true,bankId,loanBase:10000};
          const reject=fn=>{try{fn();return false}catch{return true}};
          const forbidden=reject(()=>worldPlaceConstructionContract(S,pid,{...params,bankId:sid}));
          const c=worldPlaceConstructionContract(S,pid,params);worldAcceptConstructionContract(S,sid,c.id);
          const reserved=c.funding.approval.grant===1000000&&c.funding.approval.loan===1000000&&c.funding.approval.own===2000000;
          await close();
          const current=()=>S.worldExpansion.constructionContracts.find(x=>x.id===c.id);
          const noPremature=current().status==='ACTIVE'&&current().funding.payment===null
            &&!company(pid,S).loans.length&&acc(company(bankId,S),'loanrec')===0
            &&parsePayload(savePayload(S)).worldExpansion.constructionContracts[0].status==='ACTIVE';
          await close();
          const done=current(),rec=S.worldExpansion.constructionReceipts[0],l=company(pid,S).loans.find(x=>x.id===rec.funding.loanId);
          const debit=company(pid,S),credit=company(bankId,S),g=consolidate(S);
          const grant=done.status==='COMPLETE'&&rec.funding.grant===1000000&&acc(debit,'otherRevenue')<=-1000000;
          const loan=l.outstanding===1000000&&l.parent===bankId&&l.due===done.finishedAt+36
            &&acc(credit,'loanrec')===1000000&&-acc(debit,'debt')===1000000;
          const lock=reject(()=>worldRetireDomesticAsset(S,pid,'route',rec.assetId))
            &&S.worldExpansion.domesticRoutes[rec.assetId].ownerCompanyId===pid;
          const restored=parsePayload(savePayload(S));
          const forged=structuredClone(restored);forged.worldExpansion.constructionContracts[0].funding.approval.grant++;
          const clean=!check(restored).length&&!g.errors.length&&g.cf.reconciled&&reject(()=>parsePayload(savePayload(forged)));
          const risk=worldBankCreditRisk(S,credit);
          const bankExposure=risk.total===1000000&&risk.sector[debit.industry]===1000000
            &&risk.liquid===Math.max(0,acc(credit,'cash'))&&risk.totalLimit===Math.floor(risk.equity*2)
            &&risk.sectorLimit===Math.floor(risk.equity*1.5);
          const boundary=structuredClone(S),lender=company(bankId,boundary),borrower=company(pid,boundary);
          const cap=worldBankCreditRisk(boundary,lender),room=cap.sectorLimit-cap.sector[borrower.industry];
          // Isolate the policy boundary from the unrelated liquidity and borrower-capital constraints.
          // The temporary quote fixture is not persisted or used as evidence of a real loan.
          post(lender,{cash:cap.totalLimit+100000000},{debt:cap.totalLimit+100000000},'審査境界の資金フィクスチャ','financing',boundary);
          post(borrower,{cash:cap.totalLimit+100000000},{capital:cap.totalLimit+100000000},'審査境界の資本フィクスチャ','financing',boundary);
          const concentration=room>0&&worldInfrastructureBankReady(boundary,lender,borrower,room)
            &&!worldInfrastructureBankReady(boundary,lender,borrower,room+1);
          const restoredRisk=worldBankCreditRisk(restored,company(bankId,restored));
          const riskRestore=restoredRisk.total===risk.total&&restoredRisk.sector[debit.industry]===1000000;
          const installment=Math.floor(l.outstanding/36)+(l.outstanding%36?1:0),principalBefore=l.outstanding;
          await close();
          const borrowerAfter=company(pid,S),bankAfter=company(bankId,S),after=borrowerAfter.loans.find(x=>x.id===l.id);
          const amortized=after?.outstanding===principalBefore-installment&&after.parentRemaining===after.outstanding
            &&acc(bankAfter,'loanrec')===after.outstanding&&worldBankCreditRisk(S,bankAfter).total===after.outstanding;
          const principalJournal=borrowerAfter.journals.some(j=>j.when===S.monthCommitted&&j.text==='借入元本返済'&&j.amount===installment)
            &&bankAfter.journals.some(j=>j.when===S.monthCommitted&&j.text.includes('貸付元本の回収')&&j.amount===installment);
          const repaymentRestore=parsePayload(savePayload(S)),loanRestored=company(pid,repaymentRestore).loans.find(x=>x.id===l.id);
          const repaymentClean=loanRestored?.outstanding===after.outstanding&&!check(S).length&&!consolidate(S).errors.length&&consolidate(S).cf.reconciled;
          const bankRow=repaymentRestore.worldExpansion.bankLoans.find(x=>x.id===l.id);
          const auditedLoan=bankRow.infrastructureContractId===c.id&&bankRow.remaining===after.outstanding
            &&bankRow.payments.some(x=>x.kind==='principal'&&x.amount===installment)&&bankRow.interestPaid>0
            &&worldServiceActivity(repaymentRestore,'PRD-S06').some(x=>x.ref===l.id&&x.providerId===bankId);
          const legacy=structuredClone(repaymentRestore);
          delete legacy.worldExpansion.bankLoans;
          delete company(pid,legacy).loans.find(x=>x.id===l.id).bankLoanId;
          const oldSavedContract=company(pid,parsePayload(savePayload(legacy))).loans.find(x=>x.id===l.id).outstanding===after.outstanding;
          const trial=repaymentRestore,trialBuyer=company(pid,trial),trialBank=company(bankId,trial),cash=acc(trialBuyer,'cash');
          post(trialBuyer,{otherExpense:cash},{cash},'支払不能検証用支出','operating',trial);
          phase7UpdateBankCreditLosses(trial);
          const provision=Math.ceil(after.outstanding/4),riskWithLoss=worldBankCreditRisk(trial,trialBank);
          const impaired=bankRow.allowance===provision&&-acc(trialBank,'bankLoanAllowance')===provision
            &&-acc(trialBuyer,'debt')===after.outstanding&&riskWithLoss.netExposure===after.outstanding-provision;
          const savedLoss=parsePayload(savePayload(trial));
          const invalidLoss=structuredClone(savedLoss);invalidLoss.worldExpansion.bankLoans[0].lossChanges[0].remaining++;
          const lossAudited=savedLoss.worldExpansion.bankLoans[0].allowance===provision&&reject(()=>parsePayload(savePayload(invalidLoss)));
          post(trialBuyer,{cash:500000000},{otherRevenue:500000000},'返済再開の営業収入','operating',trial);
          for(const f of trial.firms){f._profitStart=financials(f).profit;f._salesNow=0;f._unitsNow=0;}
          financeMonthly(trial,[]);
          const recovered=bankRow.allowance===0&&acc(trialBank,'bankLoanAllowance')===0&&bankRow.remaining===after.outstanding-installment
            &&bankRow.lossChanges.at(-1).delta===-provision&&!check(parsePayload(savePayload(trial))).length;
          return {history,shares,ui,forbidden,reserved,noPremature,grant,loan,lock,clean,bankExposure,concentration,riskRestore,amortized,principalJournal,repaymentClean,
            auditedLoan,oldSavedContract,impaired,lossAudited,recovered};
        }""")
        assert len(funded)==21 and all(funded.values()),funded
        print("PASS Phase 6/7 funded infrastructure: 21 checks including loan impairment, recovery and save evidence")
        autonomous=page.evaluate("""async()=>{
          S=newWorldGame({country:'JP',name:'Domestic freight customer'});saveAuto=async()=>true;
          S.year=1980;S.month=1;S.monthCommitted=ym(S.year,S.month)-1;applyWorldHistory(S);
          const buyer=company(S.playerId,S),bid=buyer.id,plant=buyer.plants[0],bp=plant.id;
          plant.siteId='JP-NGO';
          const carrier=initFirm(S,{name:'Autonomous road operator',country:'JP',industry:'service',seedBase:10000000});
          const builder=initFirm(S,{name:'Autonomous contractor',country:'JP',industry:'service',seedBase:10000000});
          const cid=carrier.id,sid=builder.id,sp=builder.plants[0].id;
          for(const f of [buyer,carrier,builder])if(!f.research.tree.done.includes('production-1'))f.research.tree.done.push('production-1');
          for(const f of [carrier,builder]){f.staff.production=20;f.staffTarget.production=20;}
          syncWorldIdentities(S);
          const add=(f,id,q,unit)=>{
            const amount=q*unit;post(f,{materials:amount},{cash:amount},'試験用有償調達','operating',S);f.stock[id]={q,v:amount};
          };
          add(buyer,'PRD-E20',1,400);add(carrier,'PRD-E15',1,800);
          add(carrier,'PRD-R22',100,100);add(carrier,'PRD-M16',50,20);
          add(builder,'PRD-E14',1,300);add(builder,'PRD-E15',1,800);
          add(builder,'PRD-M03',4,20);add(builder,'PRD-M09',4,10);
          const corridor='JP-TOMEI-TOKYO-KOMAKI';
          const route=worldRegisterDomesticRoute(S,cid,'JP-TOK','JP-NGO',347,'VERIFIED',corridor);
          const warehouse=worldInstallDomesticWarehouse(S,bid,bp,'JP-NAGOYA-SILO'),wid=warehouse.id;
          const order=(routeId,quantity)=>worldPlaceDomesticOrder(S,bid,{routeId,warehouseId:wid,
            productId:'PRD-R22',quantity,unitPrice:300,maxFreight:1000000});
          const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
          order(route.id,6);await close();
          order(route.id,6);for(let i=0;i<6;i++)await close();
          const w=S.worldExpansion,job=(w.constructionContracts??[]).find(x=>x.buyerId===cid&&x.sellerId===sid&&x.profileId===corridor);
          const historic=w.domesticOrders.filter(x=>x.routeId===route.id);
          const realDemand=historic.length===2&&historic.every(x=>x.status==='PARTIAL'&&x.acceptedQty<6)
            &&w.domesticShipments.filter(x=>x.routeId===route.id&&x.status==='DELIVERED').length===2;
          if(!job)return {realDemand,orders:historic.map(x=>[x.status,x.acceptedQty]),shipments:w.domesticShipments,
            payback:worldConstructionPayback(S,{buyerId:cid,kind:'DR',profileId:corridor,fee:100000}),events:S.lastReport.events};
          const receipt=w.constructionReceipts.find(x=>x.id===job.receiptId),newRoute=w.domesticRoutes[receipt?.assetId];
          const autoBuild=job.status==='COMPLETE'&&job.work.length===2&&newRoute?.ownerCompanyId===cid
            &&w.constructionMachines[sp].ownerCompanyId===sid&&company(sid,S).stock['PRD-E14'].q===0;
          const accepted=order(newRoute.id,1);
          await close();await close();await close();
          const used=S.worldExpansion.domesticShipments.some(t=>t.orderId===accepted.id&&t.routeId===newRoute.id&&t.status==='DELIVERED');
          const clean=!check(parsePayload(savePayload(S))).length&&consolidate(S).cf.reconciled;
          return {realDemand,autoBuild,used,clean};
        }""")
        assert len(autonomous)==4 and all(autonomous.values()),autonomous
        print("PASS Phase 6 autonomous infrastructure: prior partial orders, actual freight receipts, AI construction and operation")
        assert not errors,errors
        print("PASS Phase 6 construction: 11 checks, UI, real monthly work, completion, failed contract, fixed upkeep, accounting and restore")
        browser.close()

if __name__=="__main__":main()
