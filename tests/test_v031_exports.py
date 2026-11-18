"""v0.31: exports are recognized only against demand in their arrival month."""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / "index.html").read_text(encoding="utf-8")


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None,
            headless=True, args=["--no-sandbox"]
        )
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.set_content(HTML, wait_until="domcontentloaded")
        data = page.evaluate("""() => {
            S=newGame({era:1900,country:'JP',difficulty:'normal',history:'historical',name:'輸出需給検証'});
            const f=company(S.playerId,S),m=f.models[0];
            const cost=8000;
            post(f,{goods:cost},{cash:cost},'輸出テスト完成品原価','operating',S);
            f.goods[m.id].q+=8;f.goods[m.id].v+=cost;
            exportShipment(S,f,m.id,8,m.priceBase,'US',[],'mass');
            const costBefore=acc(f,'goodsTransit');
            const due=f.distribution.outbound[0].due;
            // Advance the calendar without doing an unrelated monthly production
            // cycle. A real monthly regression is covered by the demand test.
            S.year=Math.floor(due/12);S.month=due%12+1;
            S.world.US.demand=3;S.world.US.cycle=0;S.world.US.war=false;
            f._salesNow=0;f._unitsNow=0;f.modelEconomics={};f.marketThisMonth={};
            deliverExports(S,[]);
            const first={
                sold:f.marketThisMonth.US?.units||0,
                remaining:f.distribution.outbound[0]?.qty||0,
                inTransit:acc(f,'goodsTransit'),
                pendingCost:f.distribution.outbound.reduce((n,x)=>n+x.bookCost,0),
                accepted:S.marketDeliveryV031.markets.US?.units||0,
                err:check(S)
            };
            const next=ym(S.year,S.month)+1;
            S.year=Math.floor(next/12);S.month=next%12+1;
            S.world.US.demand=2;
            f._salesNow=0;f._unitsNow=0;f.modelEconomics={};f.marketThisMonth={};
            deliverExports(S,[]);
            const second={
                sold:f.marketThisMonth.US?.units||0,
                remaining:f.distribution.outbound[0]?.qty||0,
                inTransit:acc(f,'goodsTransit'),
                pendingCost:f.distribution.outbound.reduce((n,x)=>n+x.bookCost,0),
                err:check(S)
            };
            return {first,second,costBefore};
        }""")
        first, second = data["first"], data["second"]
        assert data["costBefore"] > 0, data
        assert (first["sold"], first["remaining"], first["accepted"]) == (3, 5, 3), data
        assert (second["sold"], second["remaining"]) == (2, 3), data
        for stage in (first, second):
            assert stage["inTransit"] == stage["pendingCost"], data
            assert not stage["err"], data
        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    run()
    print("PASS v0.31: cross-month export delivery cap, retained inventory book cost")
