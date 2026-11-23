"""Domestic acquisition costs survive partial processing, resale, and save restoration."""

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
        page.set_content((ROOT / "index.html").read_text(encoding="utf-8"))
        page.wait_for_function("STORAGE_READY")
        result = page.evaluate("""() => {
          S=newWorldGame({country:'JP',name:'Phase 2-K'});
          const parent=company(S.playerId);
          const subsidiary=name=>{
            const capital=60000000,parentJournal=S.seq;
            post(parent,{investment:capital},{cash:capital},'検証用の設立','investing',S);
            const f=initFirm(S,{name,country:'JP',seedBase:600000,publicOwnership:false});
            f.owners=[{id:parent.id,econ:1,vote:1}];
            registerEquityLink(S,{parentId:parent.id,childId:f.id,ratio:1,kind:'foundation',
              considerationLocal:capital,buyerJournal:parentJournal,
              childJournal:f.journals.find(j=>j.text==='創業資本').id,
              bookEquityBase:baseFromLocal(capital,'JP'),cashAcquiredBase:baseFromLocal(acc(f,'cash'),'JP')});
            return f;
          };
          const mill=subsidiary('Mill'),buyer=subsidiary('Reseller');
          const external=initFirm(S,{name:'External',country:'JP',seedBase:1000000});
          S.year=1970;S.month=1;S.monthCommitted=ym(1970,1)-1;
          const plant=parent.plants[0],receiving=mill.plants[0];
          plant.siteId='JP-TOK';
          for(const f of [mill,buyer,external])f.plants[0].siteId='JP-YOK';
          for(const f of [parent,mill,buyer,external]){
            for(const id of ['production-1','materials-1','materials-6','energy-1']){
              if(!f.research.tree.done.includes(id))f.research.tree.done.push(id);
            }
          }
          const put=(f,id,q,v)=>{
            post(f,{materials:v},{cash:v},'検証用現物仕入','operating',S);
            f.stock[id]={q,v};
          };
          put(parent,'PRD-E16',1,1200);put(parent,'PRD-E17',1,300);
          put(parent,'PRD-R04',6,30);put(parent,'PRD-R19',6,60);
          put(mill,'PRD-E20',1,120);put(mill,'PRD-R19',2,20);
          applyWorldHistory(S);syncWorldIdentities(S);
          const route=worldRegisterDomesticRoute(S,parent.id,'JP-TOK','JP-YOK',29,'VERIFIED','JP-SHIMBASHI-YOKOHAMA');
          worldInstallDomesticWarehouse(S,mill.id,receiving.id,'JP-YOKOHAMA-SHINKO');
          const dispatch=worldDispatchDomesticShipment(S,route.id,parent.id,plant.id,mill.id,receiving.id,'PRD-R19',6,20);
          const inTransit=consolidate(S).adjustments.domesticInventoryProfit===0;
          S.month++;
          worldReceiveDomesticShipments(S);
          const landed=mill.stock['PRD-R19'].domesticCostLayers[dispatch.id]===60
            &&consolidate(S).adjustments.domesticInventoryProfit===60;
          mill.staff.production=400;receiving.componentLines=[];receiving.lastProduced=0;receiving.wirePlan=0;
          worldPlanSave(mill,receiving,'PRD-M12',2);
          produceWorldSupplemental(S,[]);
          const production=mill.stock['PRD-M12']?.q===2&&mill.stock['PRD-M12']?.domesticCostLayers[dispatch.id]===30
            &&mill.stock['PRD-R19'].domesticCostLayers[dispatch.id]===30
            &&consolidate(S).adjustments.domesticInventoryProfit===60;
          const local=(seller,buyer,amount,price)=>worldLocalPhysicalDelivery(S,seller.id,seller.plants[0].id,
            buyer.id,buyer.plants[0].id,'PRD-R19',amount,price);
          const second=local(mill,buyer,2,35);
          const internalResale=buyer.stock['PRD-R19'].domesticCostLayers[dispatch.id+'|'+second.id]===15
            &&buyer.stock['PRD-R19'].domesticCostLayers[second.id]===34
            &&consolidate(S).adjustments.domesticInventoryProfit===94;
          const outside=local(buyer,external,1,55);
          const outsideSale=consolidate(S).adjustments.domesticInventoryProfit===69;
          const reentry=local(external,mill,1,60);
          const unchangedRoundtrip=mill.stock['PRD-R19'].domesticCostLayers[[dispatch.id,second.id,outside.id,reentry.id].join('|')]===8
            &&consolidate(S).adjustments.domesticInventoryProfit===69;
          const restored=parsePayload(savePayload(S));
          const final=consolidate(restored),legacy=structuredClone(restored);
          for(const f of legacy.firms)for(const item of Object.values(f.stock))delete item.domesticCostLayers;
          for(const t of [...legacy.worldExpansion.domesticShipments,...legacy.worldExpansion.physicalDeliveries])
            delete t.costReceipt;
          const legacyRestored=parsePayload(savePayload(legacy)),unadjusted=consolidate(legacyRestored);
          const financial=!check(restored).length&&!final.errors.length&&!unadjusted.errors.length
            &&unadjusted.adjustments.domesticInventoryProfit===0
            &&final.adjustments.domesticInventoryProfit===69&&final.adjustments.domesticInternalSales===190
            &&unadjusted.bs.assets-final.bs.assets===69&&unadjusted.pl.revenue-final.pl.revenue===190
            &&unadjusted.pl.expenses-final.pl.expenses===121&&unadjusted.pl.profit-final.pl.profit===69;
          const corrupt=structuredClone(restored);
          company(mill.id,corrupt).stock['PRD-M12'].domesticCostLayers[dispatch.id]+=60;
          let rejects=false;
          try{worldValidateDomesticLogistics(corrupt)}catch(e){rejects=e.message.includes('取得原価');}
          const coal=worldDispatchDomesticShipment(S,route.id,parent.id,plant.id,mill.id,receiving.id,'PRD-R04',2,10);
          S.month++;
          worldReceiveDomesticShipments(S);
          put(buyer,'PRD-E04',1,500);
          const equipment=worldLocalPhysicalDelivery(S,buyer.id,buyer.plants[0].id,mill.id,receiving.id,'PRD-E04',1,620);
          const generator=worldInstallGenerator(S,mill.id,receiving.id);
          const capitalization=generator.domesticCostLayers[equipment.id]===120
            &&consolidate(S).adjustments.domesticInventoryProfit===199;
          worldDepreciateInfrastructure(S);
          const depreciation=generator.domesticCostLayers[equipment.id]===119
            &&consolidate(S).adjustments.domesticInventoryProfit===198;
          put(mill,'PRD-R05',3,30);
          worldGeneratePower(S,mill.id,receiving.id,1);
          worldPlanSave(mill,receiving,'PRD-M15',1);
          produceWorldSupplemental(S,[]);
          const poweredManufacturing=mill.stock['PRD-M15']?.q===1
            &&mill.stock['PRD-M15']?.domesticCostLayers[coal.id]===2
            &&mill.stock['PRD-R04'].domesticCostLayers[coal.id]===5
            &&consolidate(S).adjustments.domesticInventoryProfit===195
            &&!check(parsePayload(savePayload(S))).length;
          return {inTransit,landed,production,internalResale,outsideSale,unchangedRoundtrip,financial,rejects,
            capitalization,depreciation,poweredManufacturing};
        }""")
        assert all(result.values()), result
        browser.close()
    print("PASS Phase 2-K cost: mixed stock, production, internal resale, external sale/re-entry, consolidated BS/PL, legacy save")


if __name__ == "__main__":
    main()
