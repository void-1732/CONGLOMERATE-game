"""Phase 8 SPEC-122 competitive quote selection (actual browser game function)."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads("[[[{\"buyerId\":\"A\",\"targetId\":\"T\",\"total\":100,\"score\":90,\"accepted\":true,\"available\":1000},{\"buyerId\":\"B\",\"targetId\":\"T\",\"total\":120,\"score\":20,\"accepted\":true,\"available\":1000}],\"B\"],[[{\"buyerId\":\"A\",\"targetId\":\"T\",\"total\":100,\"score\":90,\"accepted\":true,\"available\":1000},{\"buyerId\":\"B\",\"targetId\":\"T\",\"total\":120,\"score\":20,\"accepted\":false,\"available\":1000}],\"A\"],[[{\"buyerId\":\"A\",\"targetId\":\"T\",\"total\":100,\"score\":90,\"accepted\":true,\"available\":1000},{\"buyerId\":\"B\",\"targetId\":\"T\",\"total\":120,\"score\":20,\"accepted\":true,\"available\":200}],\"A\"],[[{\"buyerId\":\"B\",\"targetId\":\"T\",\"total\":100,\"score\":90,\"accepted\":true,\"available\":1000},{\"buyerId\":\"A\",\"targetId\":\"T\",\"total\":100,\"score\":20,\"accepted\":true,\"available\":1000}],\"A\"],[[{\"buyerId\":\"A\",\"targetId\":\"T\",\"total\":100,\"score\":90,\"accepted\":false,\"available\":1000}],null],[[{\"buyerId\":\"A\",\"targetId\":\"T\",\"total\":100,\"score\":90,\"accepted\":true,\"available\":1000},{\"buyerId\":\"B\",\"targetId\":\"U\",\"total\":120,\"score\":20,\"accepted\":true,\"available\":1000}],\"A\"]]")

def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto((ROOT / "index.html").as_uri(), wait_until="load")
        for proposals, expected in CASES:
            actual = page.evaluate("(rows) => phase8SelectCompetitiveBid(rows)?.buyerId ?? null", proposals)
            assert actual == expected, (proposals, actual, expected)
        browser.close()
    print(f"Phase 8 competitive quotes: {len(CASES)}/{len(CASES)} passed")

if __name__ == "__main__":
    main()
