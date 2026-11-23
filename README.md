# 穩穩存（GitHub 版）

台股存股記帳 App。

- 公開版：`https://loveyanglitw-coder.github.io/wenwencun/` — 任何人用 Google 帳號登入，每人一份自己的帳本。
- 個人版：`https://loveyanglitw-coder.github.io/wenwencun/me/` — 只限擁有者帳號。

## 運作方式
- **股價與除權息**：`.github/workflows/update-and-deploy.yml` 平日自動執行 `scripts/fetch_market.py`，從證交所、櫃買中心官方資料抓全部上市櫃股票（含 ETF）的收盤價與除權除息預告，存成 `data/market.json`。Actions 頁面按「Run workflow」可立即更新。
- **帳本資料**：存在 Firebase Firestore（`firebase-config.js` 設定、`firestore.rules` 權限）。
- **發布**：GitHub Pages，由同一個 workflow 發布；修改程式推上 main 也會自動重新發布。
