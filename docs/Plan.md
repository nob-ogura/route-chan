# 実装計画（Implementation Plan）

本計画は `docs/Design.md` に基づき、MVP（TSP/車両1台）の実装手順・優先度・受入条件を整理する。段階的に小さく動かし、5秒以内の応答（10地点）と堅牢なエラーハンドリングの達成を目標とする。

## 0. 前提・体制
- 対象: Web フロント（React/TS/Leaflet）、API バックエンド（Flask/OR-Tools）、外部 OSRM。
- 環境バージョン（推奨）
  - Node.js 22.x / npm
  - Python 3.11 / pip
  - OR-Tools 9.x（Python）
- 開発ブランチ戦略: main（保護）+ feature ブランチ、PR ベース。
- DoD（Definition of Done）: セクション末尾の受入基準を満たすこと。

## 1. リポジトリ初期化とツール
1-1. 構成
- ルート
  - `frontend/`（Vite + React + TS）
  - `server/`（Flask API）
  - `docs/`（本書類）

1-2. 設定・整備
- `.editorconfig`, `.gitignore`（node_modules, .venv など）
- 依存管理
  - Frontend: `vite`, `react`, `react-dom`, `typescript`, `leaflet`
  - Backend: `flask`, `flask-cors`, `flask-limiter`, `pydantic`, `requests`, `ortools`
- `frontend` の lint/format（Biome）を導入。
- `server` 用 `requirements.txt` を追加。

受入基準
- `frontend`/`server` が起動可能（それぞれダミー画面/health のみ）。

## 2. バックエンド実装（Flask + OR-Tools）
2-0. TDD のサイクルを小さく回し、段階的に実装すること

2-1. スケルトン
- `server/app.py`: `/api/health` を返す最小 Flask。
- `server/config.py`: `MAX_LOCATIONS=10`, `OSRM_BASE_URL`, `TIMEOUTS`（接続/読み込み）等。
- `server/schemas.py`: `OptimizeRequest`, `OptimizeResponse` の Pydantic モデル。

2-2. OSRM クライアント
- `server/osrm_client.py`
  - table API: `GET /table/v1/driving/{lon,lat;...}?annotations=distance`
  - route API: `GET /route/v1/driving/{lon,lat;...}?overview=full&geometries=polyline6`
  - タイムアウト、HTTP エラー、構造検証、例外クラスの定義（`OsrmError`）。

2-3. ソルバ（OR-Tools）
- `server/solver.py`
  - Depot=0、訪問地点=1..N の距離行列を受け取り、`route`（locations のインデックス順）と `total_distance`（m）を返す。
  - 検索戦略: `PATH_CHEAPEST_ARC` + `GUIDED_LOCAL_SEARCH`、時間制限 ~3000ms。

2-4. 最適化 API
- `POST /api/optimize` 実装
  - 入力検証: 座標レンジ、Depot 有無、地点数（1..MAX_LOCATIONS）。
  - OSRM table → 距離行列取得。
  - OR-Tools で巡回順序算出。
  - 巡回順序に沿って OSRM route を呼び、`route_geometries` 取得（legs を抽出）。
  - エラーマッピング: 400/429/502/500。
- CORS 設定（`flask-cors`）。
- レート制限（`flask-limiter`、例: `60/minute`）。
- ロギング（INFO、エラー時に stack を抑制しユーザーには要約）。

2-5. テスト（優先）
- ユニット: `solver.py`（小規模行列で期待順序/距離）、`osrm_client.py`（正常/異常/タイムアウト）。
- 結合: `/api/optimize` を `responses` or `requests-mock` で OSRM モックし検証（境界: 0/1/10/11 地点）。

受入基準
- 10地点までで 3秒以内に最適化 API が応答（ローカル、OSRM 応答を含む目安）
- エラー時に JSON（`error`, `message`）で適切な HTTP ステータスを返却。
- Health, Optimize が CI 上でテスト緑。

## 3. フロントエンド実装（React + TypeScript + Leaflet）
3-1. スケルトン
- Vite で React/TS プロジェクトを作成。
- 画面: ヘッダー、MapView、Controls、Summary のラフ配置。

3-2. 地図・地点操作
- `MapView.tsx`
  - 初回クリックを Depot として登録、以降は訪問地点。
  - マーカー表示（Depot 用アイコン/色、訪問順番号）。
  - リセット（全削除）。
  - 上限 10 の UI バリデーション（超過時に警告・追加不可）。

3-3. API 連携
- `services/api.ts` に `optimize`, `health` 実装（fetch/axios）。
- `Controls.tsx`: 実行ボタン、処理中はボタン無効化/ローディング表示。
- 正常時: ポリライン描画、Summary に距離（km）と順序を表示。
- 異常時: スナック/トースト（シンプルなエリア）でエラー表示。

3-4. スタイル・体験
- マップ初期中心とズーム（日本中心）。
- レスポンシブ最小対応、キーボード操作は範囲外（MVP）。

受入基準
- 地図クリックで Depot/訪問地点が登録でき、順序番号表示。
- 実行でルートポリラインが描画され、距離と順序が表示。
- 上限超過や未入力時にユーザーに分かるエラー/警告。

## 4. 統合・開発体験
- ローカル開発: `frontend` dev サーバと `server` を同時起動、CORS か `vite` のプロキシで接続。
- 環境変数: `OSRM_BASE_URL`, `CORS_ALLOWED_ORIGINS`, `MAX_LOCATIONS`, `RATE_LIMIT_RULE`, `TIMEOUTS`, `SOLVER_TIME_LIMIT_MS`。
- 迅速な検証用シナリオ（東京駅を Depot、近隣9点）を README に記載。

受入基準
- ローカルで一連の操作（登録→実行→表示）が 5秒以内に完了。

## 5. デプロイ（MVP）
- フロントエンド: Cloudflare Pages
  - ビルド: `npm run build`、出力: `dist`
  - 設定: `VITE_API_BASE_URL` に Cloud Run の API ベースURLを設定（例: `https://<service>-<hash>-a.run.app`）
  - ドメイン: Pages のデフォルトドメイン（またはカスタムドメイン）
- バックエンド: Google Cloud Run
  - コンテナ: Python/Flask + Gunicorn（`$PORT` で起動）
  - 環境変数: `OSRM_BASE_URL`, `CORS_ALLOWED_ORIGINS`（Cloudflare Pages のオリジン）, `MAX_LOCATIONS`, `RATE_LIMIT_RULE`, `SOLVER_TIME_LIMIT_MS`
  - ヘルスチェック: `/api/health`
- CORS: Cloudflare Pages のオリジンをホワイトリストに追加。
- OSRM: 公開デモを利用（開発/検証用途）。安定運用は自前 OSRM を別検討。

受入基準
- Cloud Run の `GET /api/health` が 200。
- Cloudflare Pages から本番 API（Cloud Run）に対して最適化が成功し、CORS エラーがない。

## 6. リスクと対応
- OSRM デモのレート制限/不安定
  - UI に再試行・リトライ案内、バックエンドでタイムアウト/再試行（短回数）。
  - キャッシュ（短時間、座標セットキー）を検討。
- OR-Tools インストール問題
  - Python バージョン固定、`requirements.txt` 明記、CI でビルド検証。
- 5秒要件未達（10地点）
  - OR-Tools のタイムリミット調整、OSRM 呼び出しを最小化（table 1回, route 1回）。

## 7. マイルストーン（目安）
- M1: リポ初期化・Health（0.5日）
- M2: OSRM クライアント + ソルバ（1.5日）
- M3: 最適化 API 完成 + テスト（1日）
- M4: フロント地図/操作 + API 連携（1.5日）
- M5: 統合/パフォーマンス調整/デプロイ（1日）

## 8. タスク一覧（チェックリスト）
- [ ] repo 構成、共通設定（.gitignore 他）
- [ ] server: app.py（health, CORS, limiter）
- [ ] server: config.py, schemas.py
- [ ] server: osrm_client（table/route, 例外）
- [ ] server: solver（OR-Tools 設定/制限）
- [ ] server: POST /api/optimize（検証/エラー整備）
- [ ] server: テスト（ユニット/結合、CI）
- [ ] frontend: Vite 初期化、レイアウト
- [ ] frontend: MapView（クリック/マーカー/番号/リセット）
- [ ] frontend: API 連携（実行/ローディング/エラー表示）
- [ ] frontend: ポリライン描画/サマリー表示
- [ ] 統合検証（10地点/5秒、境界ケース）
- [ ] デプロイ: Cloud Run（Dockerfile, Gunicorn 起動, 環境変数設定, デプロイ）
- [ ] デプロイ: Cloudflare Pages（build 設定, 出力 `dist`, `VITE_API_BASE_URL` 設定）
- [ ] CORS: `CORS_ALLOWED_ORIGINS` に Cloudflare Pages のオリジンを登録

## 9. 受入基準（Definition of Done）
- 機能
  - 10地点まで登録、Depot→全訪問→Depot の最適順序と総距離を返し、地図に描画できる。
- 非機能
  - 10地点で 5秒以内にフロントへ結果表示（通常負荷、デモOSRM）。
  - 入力エラー・OSRM 失敗時にユーザーフレンドリーなメッセージと適切な HTTP ステータス。
  - セキュリティ: CORS 設定、レート制限、入力検証、タイムアウト。
  - コスト: 追加ライセンス費なし（OSS のみ）。

## 10. クイックスタート（開発）
```bash
# Backend
cd server
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OSRM_BASE_URL=https://router.project-osrm.org
export MAX_LOCATIONS=10
flask --app app.py run

# Frontend
cd ../frontend
npm i
npm run dev
```

以上で、設計に沿った最小構成の実装計画を提示した。進行に合わせて M3/M4 時点で性能・UX を再評価し、必要に応じてトレードオフを調整する。
