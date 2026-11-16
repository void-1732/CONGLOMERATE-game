"""CONGLOMERATE v0.19 current-release smoke test.

Run: python tests/test_v019_smoke.py
Requires: pip install playwright; python -m playwright install chromium
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parents[1] / 'index.html').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path=os.getenv('CHROMIUM_EXECUTABLE') or shutil.which('chromium') or None,
        args=['--no-sandbox'],
    )
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.set_content(HTML, wait_until='domcontentloaded')
    for _ in range(4):
        page.locator('[data-action="wizardNext"]').click()
    assert page.evaluate('TECH_NODES.length') == 800
    assert page.evaluate('check(S)') == []

    # Research can start repeatedly, without a monthly tick.
    page.evaluate('''() => {
      S.year=2020; S.month=1; S.monthCommitted=ym(2020,1)-1;
      current().staff.research=80; current().rnd.budgetBase=1000000;
      PAGE='people'; render();
    }''')
    slots = page.evaluate('techSlotLimit(current())')
    assert slots >= 2
    for i in range(2):
        page.locator('.tech-quick-list [data-action="startTech"]:not([disabled])').first.click()
        assert page.evaluate('current().research.tree.active.length') == i + 1
    assert page.evaluate('S.month') == 1

    # Every market view can be selected independently.
    page.locator('[data-section="markets"]').click()
    for key in ('marketOwn', 'market', 'distribution'):
        assert page.locator(f'[data-page="{key}"]').count() == 1
        page.locator(f'[data-page="{key}"]').click()

    # Parent company rename preserves identity and accounting validation.
    page.locator('[data-section="corporate"]').click()
    original_id = page.evaluate('S.playerId')
    page.locator('#renameCompanyName').fill('新・統合モータース')
    page.locator('[data-action="renameCompany"]').click()
    assert page.evaluate('company(S.playerId).name') == '新・統合モータース'
    assert page.evaluate('S.playerId') == original_id
    assert page.evaluate('check(S)') == []
    assert not errors, errors
    browser.close()
print('PASS v0.19: 800-node research, multiple starts, markets, rename, accounting')
