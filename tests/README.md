# CONGLOMERATE 回帰試験

## STEP 13 — 長期耐久と保存復旧

- ワークフロー: `.github/workflows/step13-longrun.yml`。現行の`main`で実行
- 120か月: `python tests/test_step13_120_months.py --era 1900` と `--era 2020`。工場新設、月次計算・会計・JSON検証、経過後の16画面表示、セーブ容量と月次処理時間を確認
- 1,200か月: `python tests/test_step9_1200_months.py --era 1900 --scenario baseline`。1900/2020、baseline/specialistsの4組み合わせ。月末処理、100か月区切り会計検算、300か月区切りJSON保存復元を実施
- 実IndexedDB: `python tests/test_step9_real_indexeddb_longsave.py`。300か月後、2世代保存・再読込・最新スナップショット破損から前世代復旧を検証
- 高速耐久区間では画面再描画と各月のIndexedDB自動保存のみ抑止し、実際の`runMonth()`と仕訳・連結処理を省略しません
- テスト成功はブラウザ全種、実デバイス強制終了時の復旧、全画面の長期操作性能を保証しません

## STEP 12 — 経営取引

`python tests/test_step12_transactions.py`（`.github/workflows/step12-transactions.yml`）

## STEP 11 — 画面操作・権限

`python tests/test_step11_ui_permissions.py`

## STEP 10 — 37タブと基本会計

`python tests/test_step10_37_pages.py`（`.github/workflows/step10-final-regression.yml`）

## 旧版の補助回帰

`tests/test_reload_autosave_v034dev3.py`、`tests/test_factory_idle_recovery_v034dev3.py`

ゲーム本体は外部マーケットデータなしの単一`index.html`です。
