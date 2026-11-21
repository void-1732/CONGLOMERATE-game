# CONGLOMERATE 画面再編 — STEP 1 ベースライン・移設台帳

> 作成日: 2026-11-22 / 対象リポジトリ: `void-1732/CONGLOMERATE-game`

## 1. 目的と変更禁止事項

- 本STEPは **コード凍結時点のバックアップと既存機能の棚卸し** のみを行う。`index.html` の画面・ロジックを変更しない。
- 最終目標は左側の **8大分類** と各分類の上部タブ。既存コンテンツを移動し、スクロール量を減らす。
- 新しい経営・地図・地域・輸送・業種機能を作らない。未実装タブは案内テキストのみで構成する。
- **ユーザー追加指定: 車両設計を商品企画・設計・開発プロジェクトなどに分割しない。`productPage()` が生成する既存の車両設計画面を1ページに維持する。既存の画面内切替はそのまま。**
- 生産、調達、会計、月末処理、企業合併、M&A、株式、研究、人事、保存データスキーマに機能変更を加えない。

## 2. 再現可能なバックアップ基準

- ベースラインコミット: `4821bfce4d555d0d3327e770ee433d29bbe21f5d`
- ベースライン `index.html` blob SHA: `050d5a61aebad082a420fb8fbb8f4080ef7a6c26`
- ソース: `index.html` / 9663 行 / 921511 UTF-16文字（Unicode文字含む）
- GitHubバックアップブランチ: `backup/pre-8-section-ui-step1-2026-11-22`（作成時点の `main` と同一コミット）
- バックアップ検証: 同一 `index.html` 内容、同一 blob SHA、GitHub compare `identical / ahead 0 / behind 0`。
- バックアップ参照: https://github.com/void-1732/CONGLOMERATE-game/tree/backup/pre-8-section-ui-step1-2026-11-22
- 後続ステップが失敗した場合は、バックアップコミットとの差分を確認して、UIのみ安全にロールバックする。ゲームのセーブデータの削除・上書きは行わない。

## 3. 現在の画面定義・描画経路

- 既存左側メニュー: 6大分類（会社経営 / 製品・研究 / 工場・調達 / 市場・販売網 / 企業グループ / 財務・保存）。
- `SECTIONS`・`sectionOf(PAGE)`・`sectionTabs()` が左側分類と上部タブを生成する。
- `render()` の `PAGE -> renderer` に **21の経路** が登録されている。既存の `people` 経路も旧リンク互換用として残っている。
- 共通ヘッダーは会社選択・国選択・月末処理を表示する。再編成後も全ページ共通。

| 既存PAGE | 描画関数 |
|---|---|
| `dashboard` | `dashboard()` |
| `marketOverview` | `marketOverviewV025()` |
| `marketRegion` | `marketRegionV025()` |
| `marketRivals` | `marketRivalsV025()` |
| `marketOwn` | `groupMarketPage()` |
| `market` | `marketPage()` |
| `distribution` | `distributionPages()` |
| `product` | `productPage()` |
| `factory` | `factoryPage()` |
| `supply` | `supplyContractsPage()` |
| `people` | `peoplePage()` |
| `research` | `researchPageStep2()` |
| `hr` | `hrPageStep2()` |
| `finance` | `financePage()` |
| `group` | `groupPage()` |
| `automation` | `automationPage()` |
| `consolidated` | `consolidatedPage()` |
| `ma` | `maPage()` |
| `capital` | `capitalPage()` |
| `reports` | `reportsPage()` |
| `save` | `savePage()` |

## 4. 新8分類へのコンテンツ移設台帳（設計時の一次割当）

注意: 同一の入力フォームを2ページにそのまま複製しない。既存の「操作本体」を1か所に置き、他ページは既存の閲覧情報かリンクへ変更する。

| 新しい大分類 | 上部タブ（予定） | 既存の移設元 | 移設時の制約 |
|---|---|---|---|
| **経営本部** | 経営概況 / 月次報告 / 経営AI / 通知・経営履歴 | dashboard, reports, automation; dashboardと研究系通知の既存表示 | 通知を複製せず元の状態管理を使用 |
| **製品・研究** | 車両設計 / 研究開発 / 人事・組織 | product（**画面一式**）, research, hr, people(旧経路) | 車両設計は分割禁止。商品企画・設計・開発進捗・原価・販売品質・既存の内部タブを1ページに保持 |
| **事業・施設** | 事業一覧 / 拠点管理 / 新設・拡張 / 生産・稼働 / 設備・保全 | factory, groupの業種・事業情報, 工場管理の既存パネル | 工場の検索・選択状態、建設・人員・保全操作を維持 |
| **物流・インフラ** | 供給網 / 調達契約 / 輸送網 / 物流拠点 / 配送計画 | supply, factory内の物流・ルート, distribution内の輸送中表示 | 既存の契約と輸送機能を移動。道路・鉄道・航空・海運は追加しない。物流拠点は専用機能が未実装なら案内のみ |
| **市場・販売** | 市場分析 / 競合企業 / 販売実績 / 販売網 / 輸出管理 | marketOverview, marketRivals, marketOwn, distribution | 販売実績と市場需要は区別。販売契約の保存ボタンは引き継ぐ |
| **世界・地域** | 世界地図 / 地域経済 / 人口・都市 / 政策・歴史 / インフラ | marketRegion, market; 地域別マクロ表、工場立地の既存情報 | 世界地図は未実装案内のみ。人口・都市や政策の既存項目だけを配置し、新しい行政区分等は作らない |
| **企業グループ** | グループ一覧 / 子会社経営 / M&A / 合併・再編 / 株式保有 | group, ma, capital内の株主・保有情報, reorganizationPanelと合併UI | 合併の進捗・株式承継・申請時状態を維持 |
| **財務・管理** | 単体財務 / 連結財務 / 資金調達 / 資本政策 / 保存・設定 | finance, consolidated, capital, save; group内の貸付画面 | 保存と復元・元帳・資本・借入の処理を変更しない |

### 未実装タブの扱い

- 「世界地図」「輸送網の道路・鉄道・海運・航空」「物流拠点の専用管理」など、現行コードに存在しないシステムには **未実装** と明示する。
- 「世界・地域」の人口・政策・インフラは、現在存在する国別マクロデータや工場立地情報に限って移動する。新規の地域階層や政策計算は作らない。
- 「事業一覧」は既存の会社・業種の閲覧情報のみ再配置する。事業ポートフォリオの新計算は作らない。

## 5. イベント・入力・画面状態の棚卸し

- `data-action` 属性の静的な異なる値: **86種類**（動的値や専用イベント属性は別途確認）。
- `actions(action, elem)` は単一の中央ディスパッチ。画面の移動後も `data-action`、`id`、期待される入力欄を保つ。
- 他にも `data-page`、`data-section`、`data-product-view`、`data-people-view`、`data-step2-hr-tab`、`data-factory-select`、`data-ai-command`、`data-mk-*`、`data-step7-*` のイベント導線がある。
- 工場ページは後段で `factoryPage` が再定義されているため **最終的に有効な生成関数** を移動元とする。
- 車両設計は後段で `productPage` がラップされている。分割せず `PRODUCT_VIEW` と既存のモデル設計・原価・ライフサイクルを保持する。
- 研究と人事は旧 `PEOPLE_VIEW` に加え研究専用・人事専用ページ、`STEP2_HR_VIEW` を持つ。旧リンク互換を残す。
- `render()` 自体が後段で互換ラップされている。画面ルーティング変更時はラップとイベント登録の順序を維持する。
- 通知の閉じた状態・工場選択・企業選択・地域選択・市場検索条件など、画面単位の状態はページ移動時にも意図せず初期化しない。
- 同一DOM `id` を同時に複数タブに挿入しない。非表示タブを含め複製しない実装が望ましい。

### 既存の静的 `data-action` 値（機械抽出）

```text
activateSupportV026 / bomAssemblySave / borrow / buyBackSharesV0271 / buySpotV026 / cancelGroupMerger
cancelMonth / cancelTech / cancelTreasurySharesV0271 / changeBudget / createGrade / createSub
designPreview / develop / diagnoseStorage / engineeringPropose / engineeringTraining / establishSalesCorp
export / factoryBuild / factoryManageSelected / factoryManageV21 / factoryModeV21 / factoryRouteSaveOne
goProductionV023 / groupLoan / groupSale / hireStaff / hrNegotiate / hrSave
import / issueShares / loadAutoSlot / loadManual / maBuy / maCorpBuy
maCorpFill / maCorpQuote / maFillAvailable / maFilter / maIntegrate / maQuote
maSelect / maintainPlant / mergeParentSub / mergeSibling / moduleShipV21 / monthDiagnosticCopy
monthDiagnosticDismiss / monthDiagnosticDownload / monthDiagnosticJump / monthDiagnosticShow / newGame / openSupplyContracts
partBomOpen / partOrderPlace / partRepair / partsPlan / plantSettings / previewMonth
recallModel / renameCompany / renamePlant / renewModel / reorgIntegrate / reorgTransfer
researchFocusSave / roadmapAdd / roadmapRemove / roadmapToggle / runMonth / saveDelegate
saveDistribution / saveFactoryStaffV026 / saveManual / saveQualityPolicy / saveSupply / setPlan
shipParts / spendAd / staffToHrV023 / startSupportProductionV026 / startTech / v21RouteSave
wizardBack / wizardNext
```

## 6. 後続STEPで最も壊れやすい機能

| 優先 | 対象 | 検証すべき挙動 |
|---|---|---|
| 高 | 研究・車両設計 | 内部タブと開発状況・モデル改良・在庫原価・通知開閉を維持 |
| 高 | 合併・M&A | 統合元・存続先の選択、申請、進捗、取消、株式承継処理 |
| 高 | 供給網・調達 | `supplier_*`、`backup_*`、`autoOrder_*`、契約保存、入荷・在庫・見込み |
| 高 | 工場・設備 | 選択工場・工場別操作、建設と保全、部品と配送ルート |
| 高 | 財務・保存 | セーブ形式、旧セーブ読込、帳簿のチェック、連結計算、借入 |
| 中 | 市場・販売 | 検索条件、販売実績、輸出、販売網の保存 |
| 中 | 世界・地域 | `VIEW_COUNTRY`、国別データと選択の同期 |
| 共通 | 月末処理 | 全STEPでUI再編前後の同条件計算結果を比較 |

## 7. STEP 1 の受け入れ条件と結果

- [x] 既存の `main` と一致する退避ブランチを作成した。
- [x] バックアップと現行 `index.html` のSHAおよび内容が一致した。
- [x] 既存6大分類と21ページ描画経路を特定した。
- [x] 静的 `data-action` 値 86 種類を採集した。
- [x] 8分類への一次移設台帳を作成した。
- [x] **車両設計は単一ページ維持**と明記した。
- [x] 現行 HTML 内の JavaScript スクリプト 1 ブロックを構文チェックした。
- [x] 本STEPでは `index.html` の変更を行っていない。

## 8. STEP 2 への引き継ぎ

1. 先に8つの左側分類とそれぞれの上部タブを新しい設定テーブルから描画できるようにする。
2. 未移設の旧コンテンツは旧PAGEへのリンクまたは従来描画を残し、段階移行中にアクセス不能にしない。
3. 上部タブは最大5個程度で構成する。製品・研究は `車両設計 / 研究開発 / 人事・組織` を基準とし、車両設計画面内の既存タブは廃止しない。
4. STEP 2 の段階でゲームロジックを移動しない。動作確認後にSTEP 3（ページ枠と新旧ルート対応表）へ進む。
