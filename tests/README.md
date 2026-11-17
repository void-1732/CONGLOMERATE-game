- **現行v0.27.1:** `python tests/test_v0271_smoke.py`。開発版v0.27と以前のスモークテストは回帰記録として保持。
# テスト

- **現行v0.27:** `python tests/test_v027_gate.py`（G0〜G5）。旧Ver.0.26のHTMLはGit履歴のコミット `17c73e9343bb2eba9f3a6226caaea41c7856b75d` から抽出して基準にします。旧版のテストは履歴として保持します。
- **旧版の回帰記録:** `test_v014_*.py` 等、旧バージョン名を含むファイルは当時の仕様を固定検証するためのものです。最新`index.html`で実行すると旧技術件数などの前提が異なり失敗する場合があります。
- 実行環境：Python + `pip install playwright` + `python -m playwright install chromium`。ローカルChromiumがある場合`CHROMIUM_EXECUTABLE`を指定可能。
- 現行版の本体は単一HTMLで動作します。厳密な長期・全OSブラウザのIndexedDB永続復旧テストは未完了です。
