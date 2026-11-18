"""Monthly resource ledger and save round trips through 24, 60, 120 and 240 months."""

import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright


HTML = Path(__file__).resolve().parents[1] / "index.html"

SCENARIOS = (
    (1900, "normal", (24, 60, 120, 240)),
    (1960, "hard", (24, 60)),
    (2010, "easy", (24,)),
)


def run_scenario(page, era, difficulty, checkpoints):
    page.evaluate("""([era, difficulty]) => {
        saveAuto = async () => true;
        render = () => {};
        S = newGame({era, country:'JP', difficulty, history:'historical',
            name:'資源業の長期検証'});
        VIEW_FIRM = S.playerId;
    }""", [era, difficulty])
    last = 0
    for checkpoint in checkpoints:
        for first in range(last, checkpoint, 12):
            months = min(12, checkpoint - first)
            result = page.evaluate("""async months => {
                for (let i = 0; i < months; i++) {
                    const previous = S.monthCommitted;
                    await runMonth();
                    if (S.monthCommitted !== previous + 1) {
                        return {month:previous + 1, diagnostic:LAST_MONTH_DIAGNOSTIC?.message};
                    }
                    for (const f of S.firms.filter(f => f.industry === 'resource')) {
                        const bins = RAW_TYPES_V032.map(t => rawBinV032(f, t));
                        if (bins.reduce((sum, x) => sum + x.v, 0) !== acc(f, 'goods') ||
                            f._produced > f._factoryCapacity) {
                            return {month:S.monthCommitted, firm:f.name, ledger:acc(f, 'goods'), bins};
                        }
                    }
                }
                const restored = parsePayload(savePayload(S));
                const errors = check(restored);
                if (errors.length || restored.monthCommitted !== S.monthCommitted) return {errors};
                S = restored;
                return null;
            }""", months)
            assert result is None, (era, difficulty, first + 1, result)
        print(f"PASS {era} {difficulty} {checkpoint} months", flush=True)
        last = checkpoint


if __name__ == "__main__":
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=os.getenv("CHROMIUM_EXECUTABLE") or shutil.which("chromium"),
            args=["--no-sandbox"],
        )
        page = browser.new_page()
        page.context.set_offline(True)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.set_content(HTML.read_text(encoding="utf-8"), wait_until="domcontentloaded")
        for scenario in SCENARIOS:
            run_scenario(page, *scenario)
        assert not errors, errors
        browser.close()
