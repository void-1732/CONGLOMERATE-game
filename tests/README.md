# テスト

- **現行v0.20:** `python tests/test_v020_smoke.py`（v0.19テストは旧版の履歴として保持）
- **旧版の回帰記録:** `test_v014_*.py` 等、旧バージョン名を含むファイルは当時の仕様を固定検証するためのものです。最新`index.html`で実行すると旧技術件数などの前提が異なり失敗する場合があります。
- 実行環境：Python + `pip install playwright` + `python -m playwright install chromium`。ローカルChromiumがある場合`CHROMIUM_EXECUTABLE`を指定可能。
- 現行版の本体は単一HTMLで動作します。厳密な長期・全OSブラウザのIndexedDB永続復旧テストは未完了です。
