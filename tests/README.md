# CONGLOMERATE テスト

## STEP 10: 最終画面分割の統合回帰

- 実行: `python tests/test_step10_37_pages.py`
- GitHub Actions: `.github/workflows/step10-final-regression.yml` （`main` への `index.html` またはテストファイル更新で自動起動、手動実行も可）
- 対象: 8大分類・37タブの画面描画、実際のタブ切替、子会社設立と会計検算、販売網／輸出画面の分離、調達契約・配送操作の接続、1900年と2020年から各12か月の月次計算、連結検算とCF整合、JSON保存・復元、HTTP上のIndexedDB保存と即時再読込。
- 実行環境: Python + Playwright + Chromium。準備: `python -m pip install playwright`、`python -m playwright install chromium`。ローカルChromiumは `CHROMIUM_EXECUTABLE` で指定可。
- 注意: テストコードが追加されたことは実ブラウザ試験の成功を意味しません。GitHub Actionsの結果（ログ・成否）を別途確認してください。全OS・複数ブラウザ・障害注入・1200か月の長期耐久試験は、STEP 10 テスト単体の対象外です。

## 既存の回帰試験

- 保存・再読込: `python tests/test_reload_autosave_v034dev3.py`
- 工場停止・再開: `python tests/test_factory_idle_recovery_v034dev3.py`
- 1200か月耐久: `python tests/test_step9_1200_months.py`
- 長期保存: `python tests/test_step9_real_indexeddb_longsave.py`
- 現行以前のバージョン名を冠したテストは、当時の画面構成・旧モデル件数等を前提とする場合があります。最新の37ページ構成の受入判定には STEP 10 の統合テストを使ってください。

ゲーム本体は `index.html` の単一ファイルで、稼働中に外部マーケットデータを取得しません。
