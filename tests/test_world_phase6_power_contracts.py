"""Phase 6: physical inter-company power supply and accounting."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,args=["--no-sandbox"])
        page=browser.new_page()
        errors=[]
        page.on("pageerror",lambda e:errors.append(str(e)))
        page.set_content((ROOT/"index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result=page.evaluate("""async()=>{ S=newWorldGame({country:'JP',name:'Buyer'});VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';saveAuto=async()=>true;
const bid=S.playerId;PAGE='corporateSubsidiaries';render();
document.getElementById('subName').value='Generator';document.getElementById('subCountry').value='JP';document.getElementById('subIndustry').value='service';document.getElementById('subCapital').value='650000';
createSub();syncWorldIdentities(S);const seller=S.firms.find(x=>x.name==='Generator');const sid=seller.id;
VIEW_FIRM=bid;PAGE='facilityExpansion';render();document.getElementById('factoryScale').value='small';document.getElementById('factoryKind').value='integrated';document.getElementById('factoryName').value='Buyer factory';document.getElementById('factorySite').value='JP-NGO';factoryBuild();let b=company(bid,S),p=b.plants.find(x=>x.name==='Buyer factory');const pid=p.id;
const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};await close();await close();
S.year=1950;S.month=4;S.monthCommitted=ym(S.year,S.month)-1;applyWorldHistory(S);syncWorldIdentities(S);
b=company(bid,S);const a=company(sid,S);p=b.plants.find(x=>x.id===pid);const g=a.plants[0];for(const f of [a,b]){f.auto=false;f.delegate.mode='manual';f.staff.production=160;f.staffTarget.production=160;for(const key of ['energy-1','materials-1','production-1'])if(!f.research.tree.done.includes(key))f.research.tree.done.push(key);for(const m of f.models)f.plans[m.id]=0}
b.factoryOps.staffAssignments[pid]=20;
const add=(f,key,q,price)=>{const amount=q*price;post(f,{materials:amount},{cash:amount},'試験用実物購入','operating',S);const st=f.stock[key]??={q:0,v:0};st.q+=q;st.v+=amount};
add(a,'PRD-E04',1,300);add(a,'PRD-R04',5,19);add(b,'PRD-M06',6,20);add(b,'PRD-E29',1,150);add(b,'PRD-R30',4,5);
worldInstallGenerator(S,sid,g.id);worldSetGridPlan(S,sid,g.id,'fuel',5);worldPlanSave(b,p,'PRD-M43',2);
const reject=fn=>{try{fn();return false}catch{return true}},panel=worldPowerContractPanel(b,true);
const c=worldOfferPowerSupply(S,bid,{sellerId:sid,sourcePlantId:g.id,targetPlantId:pid,requestKwh:40,unitPriceBase:3});
const pending=c.status==='OFFERED'&&!S.worldExpansion.powerLines?.[pid]&&worldPowerContractPanel(a,true).includes('data-world-power-accept');
const unauthorized=reject(()=>worldAcceptPowerSupply(S,bid,c.id));
const ppe=acc(b,'ppe'),cash=acc(b,'cash');const l=worldAcceptPowerSupply(S,sid,c.id);
const installed=c.status==='ACTIVE'&&l.assetValue===270&&acc(b,'ppe')===ppe+270&&acc(b,'cash')===cash&&b.stock['PRD-M06'].q===0&&b.stock['PRD-E29'].q===0;
const limits=reject(()=>worldSetGridPlan(S,bid,pid,'request',41));
await close();const t=S.worldExpansion.powerTransfers.at(-1),budget=S.worldExpansion.powerAllocations[pid],out=company(bid,S).stock['PRD-M43'];const sav=parsePayload(savePayload(S));const co=consolidate(sav);
const metered=t.contractId===c.id&&t.sellerId===sid&&t.buyerId===bid&&t.sentKwh===40&&t.lossKwh===4&&t.deliveredKwh===36&&t.amount===10800&&company(sid,S).stock['PRD-R04'].q===0;
const product=out.q===2&&budget.capitalizedFuelCost===3000&&budget.usedKwh===10;
const journal=!!worldPowerCashPairs(sav).find(x=>x.seller===sid&&x.buyer===bid&&x.fromJournal===t.costReceipt.sellerJournal);
const tampered=structuredClone(sav);tampered.worldExpansion.powerTransfers.at(-1).amount++;
const tamper=reject(()=>parsePayload(savePayload(tampered)));
const clean=!check(sav).length&&!co.errors.length;
const n=S.worldExpansion.powerTransfers.length;await close();const shortage=S.worldExpansion.powerTransfers.length===n&&S.lastReport.events.some(x=>x.includes('停電'));
const supplier=company(sid,S),taxpayer=company(bid,S),tax=120000;
add(supplier,'PRD-M06',2,20);
const publicPanel=worldPublicPowerPanel(supplier,true).includes(g.id+'|JP-TOK');
const foreign=reject(()=>worldInstallPublicPowerLine(S,sid,g.id,'US-CHI'));
const publicLine=worldInstallPublicPowerLine(S,sid,g.id,'JP-TOK');
const publicAsset=publicLine.assetValue===40&&supplier.stock['PRD-M06'].q===0
 &&reject(()=>worldInstallPublicPowerLine(S,sid,g.id,'JP-TOK'));
post(taxpayer,{taxExpense:tax},{taxDue:tax},'試験用法人税債務','operating',S);
taxpayer.payables.push({amount:tax,due:ym(S.year,S.month),account:'taxDue',note:'法人税'});
await close();
const publicOutage=!S.worldExpansion.publicPowerSales?.length&&S.lastReport.events.some(x=>x.includes('公共電力不足'));
const publicBudget=worldFiscalTaxWindow(S,'JP',S.monthCommitted)>=tax;
add(company(sid,S),'PRD-R04',5,19);
await close();
const pub=S.worldExpansion.publicPowerSales.at(-1),privateReceipt=S.worldExpansion.powerTransfers.at(-1);
const powerBalanced=pub.sentKwh===18&&pub.deliveredKwh===17&&pub.lossKwh===1&&pub.amount===5100
 &&privateReceipt.sentKwh===27&&privateReceipt.month===pub.month&&S.worldExpansion.powerAllocations[g.id].usedKwh===45;
const withPublic=parsePayload(savePayload(S)),cc=consolidate(withPublic);
const funded=withPublic.worldExpansion.publicPowerSales[0].amount===5100&&cc.cf.reconciled&&!cc.errors.length&&!check(withPublic).length;
const falsified=structuredClone(withPublic);falsified.worldExpansion.publicPowerSales[0].lossKwh++;
const publicTamper=reject(()=>parsePayload(savePayload(falsified)));
return {ui:panel.includes(sid+'|'+g.id+'|'+pid),pending,unauthorized,installed,limits,metered,product,journal,tamper,clean,shortage,persistent:sav.worldExpansion.powerSupplyContracts[0].status==='ACTIVE',
 publicPanel,foreign,publicAsset,publicOutage,publicBudget,powerBalanced,funded,publicTamper};}""")
        assert len(result)==20 and all(result.values()),result
        hospital=page.evaluate("""async()=>{
 S=newWorldGame({country:'JP',name:'Hospital priority acceptance'});VIEW_FIRM=S.playerId;VIEW_COUNTRY='JP';saveAuto=async()=>true;const root=S.playerId;
 const sub=name=>{VIEW_FIRM=root;PAGE='corporateSubsidiaries';render();document.getElementById('subName').value=name;document.getElementById('subCountry').value='JP';document.getElementById('subIndustry').value='service';document.getElementById('subCapital').value='650000';createSub();syncWorldIdentities(S);return S.firms.find(f=>f.name===name).id;};
 const genId=sub('Power provider'),medId=sub('Hospital');
 S.year=1949;S.month=12;S.monthCommitted=ym(S.year,S.month)-1;applyWorldHistory(S);syncWorldIdentities(S);
 let client=company(root,S),gen=company(genId,S),med=company(medId,S);
 const tax=120000;post(client,{taxExpense:tax},{taxDue:tax},'検証用法人税債務','operating',S);client.payables.push({amount:tax,due:ym(S.year,S.month),account:'taxDue',note:'法人税'});
 const close=async()=>{const m=S.monthCommitted;await runMonth();if(S.monthCommitted!==m+1)throw Error(JSON.stringify(LAST_MONTH_DIAGNOSTIC))};
 await close();client=company(root,S);gen=company(genId,S);med=company(medId,S);
 const g=gen.plants[0],hp=med.plants[0],lp=client.plants[0];
 for(const f of [gen,med,client]){f.auto=false;f.delegate.mode='manual';for(const key of ['energy-1','materials-1','production-1'])if(!f.research.tree.done.includes(key))f.research.tree.done.push(key);for(const m of f.models)f.plans[m.id]=0;}
 const add=(f,key,q,price)=>{const amount=q*price;post(f,{materials:amount},{cash:amount},'試験用実物購入','operating',S);const st=f.stock[key]??={q:0,v:0};st.q+=q;st.v+=amount;};
 add(gen,'PRD-E04',1,300);add(gen,'PRD-R04',3,19);add(gen,'PRD-M06',2,20);add(med,'PRD-M06',2,20);add(med,'PRD-E27',1,1500);add(client,'PRD-M06',2,20);
 worldInstallGenerator(S,genId,g.id);worldSetGridPlan(S,genId,g.id,'fuel',3);
 const clinic=worldInstallMedicalClinic(S,medId,hp.id,2);
 const contract=(f,p,qty)=>{const c=worldOfferPowerSupply(S,f.id,{sellerId:genId,sourcePlantId:g.id,targetPlantId:p.id,requestKwh:qty,unitPriceBase:3});worldAcceptPowerSupply(S,genId,c.id);return c;};
 contract(med,hp,10);contract(client,lp,18);
 worldInstallPublicPowerLine(S,genId,g.id,'JP-TOK');
 const genReceipt=worldGeneratePower(S,genId,g.id,3);
 const before=worldPowerAvailable(S,g.id),reject=(fn)=>{try{fn();return false}catch{return true}};
 const noLower=reject(()=>worldTransferPower(S,root,g.id,lp.id,18));
 const transfer=worldTransferPower(S,medId,g.id,hp.id,10);
 const req=worldRequestMedicalService(S,root,clinic.id,lp.id,3);const care=worldPerformMedicalService(S,medId,req.id,3);
 const metered=care.powerReceiptId===transfer.id&&care.powerKwh===3&&S.worldExpansion.powerAllocations[hp.id].usedKwh===3;
 const remaining=worldPowerAvailable(S,g.id),savedBefore=parsePayload(savePayload(S));const validBefore=!check(savedBefore).length&&!consolidate(savedBefore).errors.length;
 await close();
 const sales=S.worldExpansion.publicPowerSales??[],transfers=S.worldExpansion.powerTransfers??[];
 const pub=sales.find(x=>x.month===S.monthCommitted),low=transfers.find(t=>t.targetPlantId===lp.id&&t.month===S.monthCommitted);
 const order=pub&&pub.sentKwh===remaining&&!low,conserved=pub&&transfer.sentKwh+pub.sentKwh===genReceipt.deliveredKwh;
 const shortage=S.lastReport.events.some(x=>x.includes('停電')),co=consolidate(S);
 const saved=parsePayload(savePayload(S));const forged=structuredClone(saved);forged.worldExpansion.medicalTreatments[0].powerKwh++;
 const tamper=reject(()=>parsePayload(savePayload(forged)));
 return {noLower,priority:worldGridPriority(S,hp)===0&&worldGridPriority(S,lp)===4,metered,validBefore,order,conserved,shortage,tamper,clean:!check(saved).length&&!co.errors.length,cf:co.cf.reconciled,exact:before===27&&pub?.sentKwh===17&&transfer.sentKwh===10};
}""")
        assert len(hospital)==11 and all(hospital.values()),hospital
        ai_public=page.evaluate("""()=>{
 const s=newWorldGame({country:'JP',name:'Autonomous public power'});s.year=1950;s.month=1;s.monthCommitted=ym(s.year,s.month)-1;applyWorldHistory(s);syncWorldIdentities(s);
 const root=company(s.playerId,s),f=initFirm(s,{name:'Independent power',country:'JP',industry:'service',seedBase:650000,publicOwnership:true});
 syncWorldIdentities(s);ensureV20(s);f.auto=true;
 if(!f.research.tree.done.includes('energy-1'))f.research.tree.done.push('energy-1');
 const p=f.plants[0];p.capacity=Math.max(10,p.capacity);p.condition=100;
 const add=(id,q,unit)=>{post(f,{materials:q*unit},{cash:q*unit},'検証物品','operating',s);const st=f.stock[id]??={q:0,v:0};st.q+=q;st.v+=q*unit};
 add('PRD-E04',1,300);add('PRD-M06',2,20);add('PRD-R04',5,19);
 const noBudget=worldPlanAiPublicPower(s).length===0;
 const q=worldAiPublicPowerQuote(s,f,p,120000);
 const expensive=structuredClone(s),ef=company(f.id,expensive);ef.stock['PRD-R04'].v=100000000;
 const noProfit=worldAiPublicPowerQuote(expensive,ef,ef.plants[0],120000)===null;
 const controlled=structuredClone(s),cf=company(f.id,controlled);cf.owners=[{id:root.id,econ:1,vote:1}];
 const noPlayer=worldAiPublicPowerQuote(controlled,cf,cf.plants[0],120000)===null;
 s.year=1949;s.month=12;
 post(root,{taxExpense:120000},{taxDue:120000},'検証用税債務','operating',s);
 post(root,{taxDue:120000},{cash:120000},'検証用納税','operating',s);
 s.year=1950;s.month=1;
 const cash=acc(f,'cash'),ppe=acc(f,'ppe'),materials=acc(f,'materials');
 const made=worldPlanAiPublicPower(s),line=made[0],g=s.worldExpansion.powerGenerators?.[p.id];
 if(!line||!g)throw Error('AI investment failed: '+JSON.stringify(q));
 const assets=line.ownerCompanyId===f.id&&line.aiManaged===true&&acc(f,'cash')===cash&&acc(f,'ppe')===ppe+340&&acc(f,'materials')===materials-340;
 const duplicate=worldPlanAiPublicPower(s).length===0;
 worldDispatchGrid(s,[]);const sale=s.worldExpansion.publicPowerSales.at(-1);
 const paid=sale?.lineId===line.id&&sale.amount>sale.fuelBookCost&&sale.amount<=6000&&sale.deliveredKwh<=18;
 const loaded=parsePayload(savePayload(s)),clean=!check(loaded).length&&!consolidate(loaded).errors.length;
 const restore=loaded.worldExpansion.publicPowerLines[line.id].aiManaged===true;
 return {noBudget,profitable:q?.net>0&&q.months<=120,noProfit,noPlayer,assets,duplicate,paid,clean,restore};
}""")
        assert len(ai_public)==9 and all(ai_public.values()),ai_public
        print("PASS Phase 6 autonomous public power: funding, actual assets, profitability, dispatch and restore")
        assert not errors,errors
        print("PASS Phase 6 private and public power: 20 checks; 11 hospital, public, lower-priority, actual treatment, metering and save checks")
        browser.close()
if __name__=="__main__":
    main()
