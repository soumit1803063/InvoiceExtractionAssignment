---
name: accounting-api-contract
description: 会計システム API が受け付ける請求書データの形式・制約・エラーコード。登録は取り消せない。
license: proprietary
---

# 会計システム API の受け入れ条件

## 形式

- 日付は `YYYY-MM-DD` のみ。他の表記は拒否される。
- 金額は日本円の整数。小数は使えない。
- `currency` は `JPY` のみ。
- `partner_code` は `GET /partners` に存在するものだけが登録できる。取引先マスタに無い請求元は登録できない。
- 税は税コードで送る。`T10` は 10%、`T08` は 8%。税率そのものは送らない。
- 明細は 1 行以上必要。
- 明細の `quantity` と `unit_price` は null でよい。
- 明細の `amount` と `unit` は必須。`unit` が空だと登録できず、人が入力するまで進めない。

## 金額の再計算

送った金額はそのまま信用されず、明細から再計算して照合される。

- 小計 = 明細の金額の合計
- 税額 = 税コードごとに、そのコードの小計 × 税率 を切り捨てた値の合計
- 合計 = 小計 + 税額

一致しなければ `AMOUNT_MISMATCH` で拒否される。

## エラーコード

| コード | 意味 |
| --- | --- |
| `UNAUTHORIZED` | API キーが無いか誤っている |
| `PARTNER_NOT_FOUND` | 取引先マスタに無い `partner_code` |
| `UNKNOWN_TAX_CODE` | 未知の税コード |
| `DUE_DATE_BEFORE_ISSUE_DATE` | 支払期日が発行日より前 |
| `DUPLICATE_INVOICE` | 同じ取引先で同じ請求書番号が登録済み |
| `AMOUNT_MISMATCH` | 小計・税額・合計が明細と合わない |
| `VALIDATION_ERROR` | 型や書式の誤り |

## 登録は取り消せない

更新用の PATCH も、1 件ずつ消す DELETE も存在しない。誤った登録は残り続ける。
検証に通らないものは決して自動登録しない。
