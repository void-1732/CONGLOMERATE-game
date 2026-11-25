"""STEP 9 long-duration regression: 1,200 real month closes per start era.

Each trial executes the existing runMonth() pipeline, including factory,
AI, payroll, research, module inventories, debit/credit, and consolidated
accounting checks. Only DOM rerender and recurring browser autosave are
disabled to isolate simulation throughput; full JSON save/parse roundtrips
are exercised at 300, 600, 900, and 1,200 months.

Usage: python tests/test_step9_1200_months.py --era 1900
       python tests/test_step9_1200_months.py --era 2020
       python tests/test_step9_1200_months.py --era 1900 --world
"""
import argparse
import json
import os
import shutil
import time
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
MONTHS = 1200
CHUNK = 10
CHECKPOINT = 100
SAVE_CHECKPOINT = 300


WORLD_FREIGHT_FIXTURE = """() => {
  const buyer=company(S.playerId),plant=buyer.plants[0];
  plant.siteId='UK-LIV';
  const capital=Math.min(acc(buyer,'cash')-50000,3000000);
  if(capital<500000)throw Error('Insufficient fixture formation budget');
  const payer=S.seq;
  post(buyer,{investment:capital},{cash:capital},'長期回帰用・米国法人設立','investing',S);
  const seedBase=Math.round(baseFromLocal(capital,'UK')/100);
  const seller=initFirm(S,{name:'New Orleans freight fixture',country:'US',seedBase,publicOwnership:false});
  seller.owners=[{id:buyer.id,econ:1,vote:1}];
  registerEquityLink(S,{parentId:buyer.id,childId:seller.id,ratio:1,kind:'foundation',
    considerationLocal:capital,buyerJournal:payer,childJournal:seller.journals.find(j=>j.text==='創業資本').id,
    bookEquityBase:baseFromLocal(financials(seller).equity,'US'),
    cashAcquiredBase:baseFromLocal(acc(seller,'cash'),'US')});
  buyer.auto=false;seller.auto=false;
  // This fixture exercises the same asset, purchase, dispatch and accounting entry
  // points as the UI, isolating the long run from random AI stock availability.
  seller.plants[0].siteId='US-NEWORLEANS';
  for(const firm of [buyer,seller]){
    firm.research.tree.done=[...new Set([...firm.research.tree.done,'production-1'])];
    for(const model of firm.models)firm.plans[model.id]=0;
  }
  for(const [f,id,q,value] of [[seller,'PRD-E18',1,2500],[seller,'PRD-R04',10,200],
     [seller,'PRD-R20',5,200],[buyer,'PRD-E20',1,700],[buyer,'PRD-E21',1,900]]){
    post(f,{materials:value},{cash:value},'長期回帰用の有償現物調達','operating',S);
    f.stock[id]={q,v:value};
  }
  syncWorldIdentities(S);
  const profileId='US-UK-SEA-1900';
  const route=worldInternationalRegisterRoute(S,seller.id,profileId);
  const warehouse=worldInternationalInstallWarehouse(S,buyer.id,plant.id,profileId);
  const order=worldInternationalPlaceOrder(S,buyer.id,{routeId:route.id,warehouseId:warehouse.id,
    productId:'PRD-R20',quantity:5,unitPriceSeller:150,maxPaymentBuyer:100000,paymentDays:60});
  worldInternationalActOrder(S,seller.id,order.id,'approve');
  return {order:order.id,profileId,issues:check(S)};
}"""

WORLD_DOCUMENTED_FREIGHT_FIXTURE = """profileId => {
  const root=company(S.playerId);
  const isAir=profileId==='UK-FR-HOUNSLOW-LEATHER';
  function form(name,country,seedBase){
    const capital=localFromBase(seedBase,root.country),payer=S.seq;
    if(acc(root,'cash')<capital)throw Error('Insufficient freight fixture formation budget');
    post(root,{investment:capital},{cash:capital},'長期回帰用・国際売買法人設立','investing',S);
    const firm=initFirm(S,{name,country,seedBase,size:isAir ? 0.25 : 0.6,publicOwnership:false});
    firm.owners=[{id:root.id,econ:1,vote:1}];
    registerEquityLink(S,{parentId:root.id,childId:firm.id,ratio:1,kind:'foundation',
      considerationLocal:capital,buyerJournal:payer,childJournal:firm.journals.find(j=>j.text==='創業資本').id,
      bookEquityBase:baseFromLocal(financials(firm).equity,country),
      cashAcquiredBase:baseFromLocal(acc(firm,'cash'),country)});
    firm.auto=false;firm.research.tree.done=[...new Set([...firm.research.tree.done,'production-1'])];
    for(const model of firm.models)firm.plans[model.id]=0;
    return firm;
  }
  const buyer=isAir?form('Le Bourget leather buyer','FR',240000):form('London remittance buyer','UK',480000);
  const seller=isAir?form('Hounslow leather seller','UK',240000):form('Wellington wool seller','NZ',480000);
  const profile=worldInternationalProfile(profileId);
  const plant=buyer.plants[0],origin=seller.plants[0];
  plant.siteId=profile.to;origin.siteId=profile.from;
  const equipment=[[seller,profile.vehicles[0],2400],
    ...profile.terminals.map((id,i)=>[buyer,id,700+200*i])];
  for(const [firm,id,value] of equipment){
    post(firm,{materials:value},{cash:value},'長期回帰用の有償現物設備','operating',S);
    firm.stock[id]={q:1,v:value};
  }
  syncWorldIdentities(S);
  const goods=worldBuyRegionalSupply(S,seller.id,origin.id,isAir?'UK-HOUNSLOW-LEATHER':'NZ-WLG-WOOL',isAir?5:10);
  worldBuyRegionalSupply(S,seller.id,origin.id,isAir?'UK-HOUNSLOW-PETROL':'NZ-WLG-BUNKER-COAL',isAir?10:25);
  const route=worldInternationalRegisterRoute(S,seller.id,profileId);
  const warehouse=worldInternationalInstallWarehouse(S,buyer.id,plant.id,profileId);
  const order=worldInternationalPlaceOrder(S,buyer.id,{routeId:route.id,warehouseId:warehouse.id,
    productId:goods.productId,quantity:isAir?2:10,cargoLitres:isAir?18:24,
    unitPriceSeller:isAir?goods.unitPrice+20:12,maxPaymentBuyer:100000,paymentDays:30});
  worldInternationalActOrder(S,seller.id,order.id,'approve');
  return {order:order.id,profileId,issues:check(S)};
}"""


def run(era, scenario='baseline', world=False, months=MONTHS):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1280, "height": 800}, offline=world)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(HTML, wait_until="domcontentloaded")
        started = time.monotonic()
        initial = page.evaluate(
            """({era, scenario, world}) => {
              // Do not replace runMonth(), its CHECK_BEFORE/CHECK_AFTER, or
              // its CONSOLIDATION stage. Avoid DOM and IDB work only.
              saveAuto = async () => true;
              render = () => {};
              const setup={era,country:world?'UK':'JP',difficulty:'normal',
                history:'historical',name:'STEP9_1200_'+era};
              S=world?newWorldGame(setup):newGame(setup);
              VIEW_FIRM = S.playerId;
              PAGE = 'dashboard';
              if (scenario === 'specialists') {
                const f = company(S.playerId, S);
                // Seed valid completed prerequisites as a deterministic test
                // fixture. Actual formation, payroll and month-close use
                // original game functions and their accounting journals.
                const ids = ['materials-1'];
                if (era >= 1990) ids.push('energy-5');
                f.research.tree.done = [...new Set([...f.research.tree.done, ...ids])];
                step5OpenDepartment(f, S, 'materials_evaluation');
                step5SetTraining(f, 'materials_evaluation', 120);
                if (era >= 1990) {
                  step5OpenDepartment(f, S, 'energy_storage_research');
                  step5SetTraining(f, 'energy_storage_research', 120);
                }
                if (step5Allocation(f).list.some(x => x.state !== 'active'))
                  throw Error('Test fixture did not create staffed specialists');
              }
              return {
                year: S.year, month: S.month, committed: S.monthCommitted,
                worldMarkets:S.worldExpansion?WORLD_MARKETS.length:null,
                firms: S.firms.length, technologies: TECH_NODES.length,
                departments: STEP4_CATALOG.length,
                notifications: S.step7LinksV1?.entries.length,
                activeDepartments: company(S.playerId,S).step4OrgV1?.departments.length,
                checks: check(S)
              };
            }""",
            {"era": era, "scenario": scenario, "world":world},
        )
        assert initial["year"] == era and initial["month"] == 1, initial
        assert initial["technologies"] == 800 and initial["departments"] == 22, initial
        assert initial["notifications"] == 0 and not initial["checks"], initial
        assert initial["worldMarkets"] == (40 if world else None), initial
        expected_departments = (2 if era >= 1990 else 1) if scenario == 'specialists' else 0
        assert initial["activeDepartments"] == expected_departments, initial
        print("START", json.dumps({"era": era, **initial}, ensure_ascii=False), flush=True)
        count = 0
        try:
            for _ in range(months // CHUNK):
                batch = page.evaluate(
                    """async batchSize => {
                      const first = S.monthCommitted;
                      let completed = 0;
                      for (let i = 0; i < batchSize; i++) {
                        const previous = S.monthCommitted;
                        await runMonth();
                        if (S.monthCommitted !== previous + 1 ||
                            LAST_MONTH_DIAGNOSTIC || MONTH_DIAGNOSTIC_OPEN) {
                          return {
                            completed, failure: 'monthly close failed',
                            prior: previous, now: S.monthCommitted,
                            stage: LAST_MONTH_DIAGNOSTIC?.stage,
                            why: LAST_MONTH_DIAGNOSTIC?.message
                          };
                        }
                        if (S.worldExpansion?.internationalShipments.some(t=>t.credit?.paidAt===S.monthCommitted
                              ||t.credit?.remittance?.sentAt===S.monthCommitted)
                            &&!S.consoHistory.at(-1).cf.reconciled) {
                          return {completed, failure:'international payment cash flow did not reconcile',
                            cashFlow:S.consoHistory.at(-1).cf};
                        }
                        completed++;
                      }
                      return {
                        completed, advanced: S.monthCommitted - first,
                        now: S.monthCommitted
                      };
                    }""",
                    CHUNK,
                )
                assert batch.get("completed") == CHUNK and batch.get("advanced") == CHUNK, {
                    "era": era, "completed_total": count, **batch
                }
                count += CHUNK
                if world and count == 120:
                    freight = page.evaluate(WORLD_FREIGHT_FIXTURE)
                    assert not freight["issues"], freight
                    print("FREIGHT", json.dumps(freight, ensure_ascii=False), flush=True)
                if world and count == 160:
                    remittance = page.evaluate(WORLD_DOCUMENTED_FREIGHT_FIXTURE, "NZ-UK-WELLINGTON-WOOL")
                    assert not remittance["issues"], remittance
                    print("REMITTANCE", json.dumps(remittance, ensure_ascii=False), flush=True)
                if world and count == 240:
                    air_freight = page.evaluate(WORLD_DOCUMENTED_FREIGHT_FIXTURE, "UK-FR-HOUNSLOW-LEATHER")
                    assert not air_freight["issues"], air_freight
                    print("AIR FREIGHT", json.dumps(air_freight, ensure_ascii=False), flush=True)
                if count % CHECKPOINT != 0 and count != months and (not world or count not in (130, 170, 250)):
                    continue
                checkpoint = page.evaluate(
                    """saveCheck => {
                      const prior = S, issues = check(S);
                      const accounting = consolidate(S);
                      const journalIds=new Set();let duplicateJournalIds=0;
                      for(const f of S.firms)for(const j of f.journals){if(journalIds.has(j.id))duplicateJournalIds++;journalIds.add(j.id)}
                      const out = {
                        duplicateJournalIds,
                        committed: S.monthCommitted, year: S.year, month: S.month,
                        firmCount: S.firms.length, plantCount: S.firms.reduce(
                          (n, f) => n + (f.plants||[]).length, 0),
                        journalEntries: S.firms.reduce(
                          (n, f) => n + (f.journals||[]).length, 0),
                        stateIssues: issues.slice(0, 10),
                        consoIssues: accounting.errors.slice(0, 10),
                        cfReconciled: accounting.cf.reconciled,
                        cfDifference: accounting.cf.unreconciled || null,
                        noticeCount: S.step7LinksV1?.entries.length ?? null,
                        departmentCount: S.firms.reduce(
                          (n, f) => n + (f.step4OrgV1?.departments||[]).length, 0),
                        playerDepartments: company(S.playerId,S).step4OrgV1?.departments.map(
                          d => ({id:d.id,level:d.level,actual:d.actualHeadcount,
                                 state:d.state,skill:d.skill})),
                        saveChecked: false,
                        worldMarkets:S.worldExpansion?Object.values(S.worldExpansion.openMarkets)
                          .filter(m=>m!==null).length:null,
                        international:S.worldExpansion?.internationalShipments.map(t=>({
                          id:t.id,status:t.status,orderId:t.orderId,dutyBuyer:t.dutyBuyer,paidAt:t.credit?.paidAt??null,
                          sentAt:t.credit?.remittance?.sentAt??null,bankId:t.credit?.remittance?.bankId??null,
                          quantity:t.quantity,loadKg:t.loadKg??t.quantity,
                          profileId:S.worldExpansion.internationalRoutes[t.routeId].profileId
                        }))??[]
                      };
                      if (saveCheck) {
                        const raw = savePayload(S);
                        const loaded = parsePayload(raw);
                        const restored = consolidate(loaded);
                        const same =
                          loaded.year === S.year &&
                          loaded.month === S.month &&
                          loaded.monthCommitted === S.monthCommitted &&
                          JSON.stringify(accounting.bs) === JSON.stringify(restored.bs) &&
                          JSON.stringify(accounting.cf) === JSON.stringify(restored.cf) &&
                          JSON.stringify(loaded.step7LinksV1) ===
                            JSON.stringify(S.step7LinksV1) &&
                          JSON.stringify(loaded.worldExpansion?.internationalShipments) ===
                            JSON.stringify(S.worldExpansion?.internationalShipments) &&
                          check(loaded).length === 0;
                        out.saveBytes = raw.length;
                        out.saveChecked = true;
                        out.saveConsistent = same;
                        // Continue from deserialized state, verifying it is runnable.
                        if (same) S = loaded;
                      }
                      return out;
                    }""",
                    count % SAVE_CHECKPOINT == 0 or count == months,
                )
                assert len(checkpoint["playerDepartments"]) == expected_departments, {
                    "era": era, "scenario": scenario, "month": count, **checkpoint
                }
                if scenario == 'specialists':
                    assert all(d["actual"] >= 1 and 0 <= d["skill"] <= 100
                               for d in checkpoint["playerDepartments"]), checkpoint
                assert checkpoint["duplicateJournalIds"] == 0, checkpoint
                assert not checkpoint["stateIssues"], {"era": era, "month": count, **checkpoint}
                assert not checkpoint["consoIssues"], {"era": era, "month": count, **checkpoint}
                assert checkpoint["cfReconciled"], {"era": era, "month": count, **checkpoint}
                assert checkpoint["year"] == era + count // 12, checkpoint
                assert checkpoint["month"] == 1 + count % 12, checkpoint
                if world and count >= 130:
                    assert any(t["orderId"] == freight["order"] and t["status"] == "DELIVERED"
                               and t["quantity"] == 5 and t["dutyBuyer"] > 0 and t["paidAt"] is not None
                               and t["profileId"] == freight["profileId"]
                               for t in checkpoint["international"]), checkpoint
                if world and count >= 170:
                    assert any(t["orderId"] == remittance["order"] and t["status"] == "DELIVERED"
                               and t["quantity"] == 10 and t["bankId"] == "BANK-BNZ-GBP"
                               and t["paidAt"] == t["sentAt"] + 1
                               and t["profileId"] == remittance["profileId"]
                               for t in checkpoint["international"]), checkpoint
                if world and count >= 250:
                    assert any(t["orderId"] == air_freight["order"] and t["status"] == "DELIVERED"
                               and t["quantity"] == 2 and t["loadKg"] == 3 and t["paidAt"] is not None
                               and t["profileId"] == air_freight["profileId"]
                               for t in checkpoint["international"]), checkpoint
                if checkpoint["saveChecked"]:
                    assert checkpoint["saveConsistent"], {"era": era, "month": count, **checkpoint}
                assert not errors, {"era": era, "month": count, "page_errors": errors}
                print(
                    "CHECKPOINT",
                    json.dumps({
                        "era": era, "scenario": scenario,
                        "months": count,
                        "elapsedSeconds": round(time.monotonic() - started, 1),
                        **checkpoint,
                    }, ensure_ascii=False),
                    flush=True,
                )
            assert count == months, {"era": era, "count": count}
            assert not errors, errors
            print("PASS", json.dumps({
                "era": era, "scenario": scenario, "months": count,
                "endYear": era + count // 12, "endMonth": 1 + count % 12, "world": world,
                "elapsedSeconds": round(time.monotonic() - started, 1)
            }, ensure_ascii=False), flush=True)
        finally:
            page.close()
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--era", type=int, choices=(1900, 2020), required=True)
    parser.add_argument("--scenario", choices=("baseline", "specialists"), default="baseline")
    parser.add_argument("--world", action="store_true")
    parser.add_argument("--months", type=int, default=MONTHS, help="Shorter local smoke trials")
    opts = parser.parse_args()
    if opts.months < 10 or opts.months > MONTHS or opts.months % CHUNK:
        parser.error("months must be a multiple of ten between 10 and 1200")
    if opts.world and (opts.era != 1900 or opts.months < 130):
        parser.error("the world freight scenario starts in 1900 and needs at least 130 months")
    run(opts.era, opts.scenario, opts.world, opts.months)
