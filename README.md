# Route-chan 🚚

ルート最適化Webアプリケーション — 1台の車両で複数の配達先を効率的に巡回する最短ルートを計算・視覚化するMVPツール

## 📋 概要

Route-chanは、複数の訪問地点（配送先）に対して、1台の車両がDepot（出発/帰着地点）から出発し、全ての地点を巡回してDepotに戻る**最短のルート**を計算し、Webアプリケーション上で視覚化します。

### 主な特徴

- 🗺️ **直感的な地図操作**: 地図上をクリックするだけで地点を登録
- 🚀 **高速計算**: 10地点の最適化を5秒以内に完了
- 📊 **視覚的な結果表示**: 最適化されたルートを地図上にポリラインで描画
- 💰 **コストゼロ**: 全てオープンソース技術を採用
- 🔒 **堅牢性**: エラーハンドリング、レート制限、入力検証を実装

### 技術スタック

| 領域           | 技術                               |
| :------------- | :--------------------------------- |
| 最適化エンジン | Google OR-Tools (Python)           |
| バックエンド   | Flask + Python 3.11                |
| フロントエンド | React + TypeScript + Vite          |
| 地図ライブラリ | Leaflet.js + OpenStreetMap         |
| 距離計算       | OSRM (Open Source Routing Machine) |

## 🚀 クイックスタート

### 前提条件

- **Node.js** 22.x / npm
- **Python** 3.11
- **Git**

### セットアップ

#### 1. リポジトリのクローン

```bash
git clone https://github.com/nob-ogura/route-chan.git
cd route-chan
```

#### 2. バックエンドのセットアップ

```bash
cd server

# 仮想環境の作成と有効化
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存パッケージのインストール
pip install -r requirements.txt
```

#### 3. フロントエンドのセットアップ

```bash
cd ../frontend

# 依存パッケージのインストール
npm install

# 環境変数の設定
cat > .env << 'EOF'
VITE_API_BASE_URL=http://localhost:5000
EOF
```

#### 4. 開発サーバーの起動

ルートディレクトリから以下のコマンドで、フロントエンドとバックエンドを同時に起動できます：

```bash
# macOS/Linux
chmod +x scripts/dev.sh
./scripts/dev.sh
```

起動後、以下のURLでアクセスできます：
- **フロントエンド**: http://localhost:5173
- **バックエンドAPI**: http://localhost:5000

> **Note**: Windowsの場合は、2つのターミナルを開いて `cd server && flask --app app.py run` と `cd frontend && npm run dev` をそれぞれ実行してください。

## 🧪 クイック検証

アプリケーションが正常に動作することを確認するための簡単なシナリオです。

### シナリオ: 東京駅周辺の配達ルート最適化（10地点）

#### 1. 出発点（Depot）の設定

1. ブラウザで http://localhost:5173 を開く
2. 地図上で「東京駅」の位置を探す（東京都千代田区丸の内）
3. 東京駅の位置をクリックして、出発点として登録する
   - マップ上に特別なマーカー（Depot）が表示されます

#### 2. 配達先9点の登録

1. 地図を東京駅中心に拡大表示する
2. 東京駅から徒歩圏内（おおよそ500m〜1km程度）の範囲で、地図上を**9回クリック**して地点を登録する
   - 各地点は、東京駅の北側・南側・東側・西側など、様々な方向に散らばるように登録するとより効果的です
   - 正確な位置にこだわらず、東京駅周辺の近距離エリア内であれば任意の地点でOKです
3. 各地点に訪問順序を示す番号が表示されます

#### 3. 最適化の実行

1. 画面右側のコントロールパネルで「最適化を実行」ボタンをクリック
2. **5秒以内**に結果が表示されることを確認：
   - 地図上に最適化されたルートがポリラインで描画される
   - サマリーパネルに総移動距離（km）と訪問順序が表示される

> **Note**: このシナリオの目的は、10点規模（出発点1点 + 配達先9点）での応答時間を評価することであり、地点の正確性には依存しません。地図上で直感的にクリックして登録できることを重視しています。

## 📖 使い方

### 地点の登録

1. **Depot（出発/帰着地点）**: 最初のクリックがDepotとして登録されます
2. **配達先**: 2回目以降のクリックが配達先として登録されます（最大9地点）
3. **削除**: 「全消去」ボタンですべての地点を削除できます

### ルート最適化

1. Depotと少なくとも1つの配達先を登録
2. 「最適化を実行」ボタンをクリック
3. 最適化されたルートが地図上に表示され、以下の情報が確認できます：
   - 最適な訪問順序
   - 総移動距離（km）
   - ルートのポリライン表示

### 制限事項

- **最大地点数**: 10地点（Depot + 配達先9点）
- **車両数**: 1台（TSP問題）
- **最適化目標**: 総移動距離の最小化

## 🔧 環境変数

### バックエンド（server/）

開発時のデフォルト値は `scripts/dev.sh` で設定されています。カスタマイズする場合は、`server/.env` ファイルを作成するか、環境変数を直接設定してください：

```bash
# OSRM API のベースURL
OSRM_BASE_URL=https://router.project-osrm.org

# 最大地点数（Depot含む）
MAX_LOCATIONS=10

# タイムアウト設定（秒）
TIMEOUT_CONNECT=2.5
TIMEOUT_READ=4.0

# レート制限
RATE_LIMIT_RULE=60/minute

# ソルバーの時間制限（ミリ秒）
SOLVER_TIME_LIMIT_MS=3000

# CORS設定（カンマ区切り）
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### フロントエンド（frontend/）

`frontend/.env` ファイルに設定：

```bash
# バックエンドAPIのベースURL
VITE_API_BASE_URL=http://localhost:5000
```

## 🧪 テスト

### バックエンドテスト

```bash
cd server
source .venv/bin/activate

# リポジトリルートに戻る
cd ..

# ユニットテスト
pytest tests/unit/ -v

# 統合テスト
pytest tests/integration/ -v

# パフォーマンステスト
pytest tests/performance/ -v

# 全テスト実行
pytest tests/ -v
```

### フロントエンドテスト

```bash
cd frontend

# リントチェック
npm run lint

# 型チェック
npm run type-check
```

## 🚢 デプロイ

本番デプロイの詳細な手順は `docs/tasks/05.md` を参照してください。

公開中のフロントエンド: https://route-chan-frontend.et-n-ogura.workers.dev

### フロントエンド（Cloudflare Pages）

```bash
cd frontend
npm run build
# dist/ ディレクトリの内容をデプロイ
```

環境変数の設定：
- `VITE_API_BASE_URL`: Cloud Run のAPIベースURL

### バックエンド（Google Cloud Run）

1. Dockerイメージのビルド
2. Google Cloud Run へデプロイ
3. 環境変数の設定（上記のバックエンド環境変数を参照）
4. `CORS_ALLOWED_ORIGINS` に Cloudflare Pages のオリジンを追加

## 📁 プロジェクト構造

```
route-chan/
├── frontend/              # React + TypeScript フロントエンド
│   ├── src/
│   │   ├── components/   # UI コンポーネント
│   │   │   ├── MapView.tsx       # 地図表示・地点登録
│   │   │   ├── Controls.tsx      # 最適化実行ボタン
│   │   │   └── Summary.tsx       # 結果サマリー表示
│   │   ├── services/     # API通信
│   │   │   └── api.ts
│   │   ├── types/        # 型定義
│   │   └── App.tsx
│   └── package.json
│
├── server/               # Flask バックエンド
│   ├── app.py           # Flask アプリケーション
│   ├── config.py        # 設定管理
│   ├── schemas.py       # Pydantic スキーマ
│   ├── osrm_client.py   # OSRM API クライアント
│   ├── solver.py        # OR-Tools ソルバー
│   └── requirements.txt
│
├── tests/               # テストコード
│   ├── unit/           # ユニットテスト
│   ├── integration/    # 統合テスト
│   └── performance/    # パフォーマンステスト
│
├── docs/               # ドキュメント
│   ├── Requirements.md # 要求仕様書
│   ├── Design.md       # 設計書
│   ├── Plan.md         # 実装計画
│   └── tasks/          # タスク詳細
│
└── scripts/            # 開発用スクリプト
    └── dev.sh          # 開発サーバー起動
```

## 🐛 トラブルシューティング

### OSRM APIのレート制限エラー

公開デモサーバー（https://router.project-osrm.org）はレート制限があります。エラーが発生した場合：

1. 少し時間を置いてから再試行
2. 自前のOSRMサーバーをDockerで立ち上げて `OSRM_BASE_URL` を変更

### 5秒以内に結果が表示されない

1. ネットワーク接続を確認
2. `SOLVER_TIME_LIMIT_MS` を調整（デフォルト: 3000ms）
3. 地点数を減らしてテスト

### ポートがすでに使用されている

別のアプリケーションがポート5000または5173を使用している場合：

```bash
# macOS/Linux でポートを使用しているプロセスを確認
lsof -i :5000
lsof -i :5173

# プロセスを終了（PIDは上記コマンドで確認）
kill -9 <PID>
```

## 📝 ライセンス

本プロジェクトで使用しているオープンソースコンポーネント：

- **OR-Tools**: Apache License 2.0
- **Flask**: BSD-3-Clause
- **React**: MIT License
- **Leaflet**: BSD-2-Clause
- **OpenStreetMap**: ODbL (Open Database License)
- **OSRM**: BSD-2-Clause

## 📚 参考リンク

- [Google OR-Tools ドキュメント](https://developers.google.com/optimization)
- [OSRM API ドキュメント](http://project-osrm.org/docs/v5.24.0/api/)
- [Leaflet.js ドキュメント](https://leafletjs.com/)
- [Flask ドキュメント](https://flask.palletsprojects.com/)

---

**Route-chan** — シンプルで高速なルート最適化ツール 🚚✨

