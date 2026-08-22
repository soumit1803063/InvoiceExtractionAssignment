from pydantic import BaseModel, Field
from .fields import RawAmount, RawText


class AiLineItem(BaseModel):
    description: RawText = Field(
        None, description="品名・摘要 列に印字された品名。印字が無ければ null"
    )
    quantity: RawAmount = Field(
        None, description="数量 列の整数。印字が無ければ null。推測して埋めない"
    )
    unit: RawText = Field(
        None,
        description="単位 列に印字された文字をそのまま写す。例: 個 式 箱 本 袋 件 時間 セット。印字が無ければ null。推測して埋めない",
    )
    unit_price: RawAmount = Field(
        None, description="単価 列の整数。印字が無ければ null。推測して埋めない"
    )
    amount: RawAmount = Field(
        None,
        description="金額 列の整数。カンマや ¥ は取り除く。△ または ▲ が付く行は負の数にする",
    )
    tax_code: RawText = Field(
        None, description="税率 10% の行は T10、8% の行は T08。判断できなければ null"
    )


class AiTaxRow(BaseModel):
    percent: RawAmount = Field(
        None, description="消費税の行に印字された税率の数値。10% なら 10、8% なら 8"
    )
    taxable_amount: RawAmount = Field(
        None, description="消費税の行の（対象 ...）に印字された、その税率の対象金額"
    )
    tax_amount: RawAmount = Field(None, description="その税率で計算された消費税額")


class AiInvoice(BaseModel):
    registration_number: RawText = Field(
        None, description="登録番号。T で始まる13桁の数字。無ければ null"
    )
    supplier_name: RawText = Field(
        None, description="請求元の会社名。御中 が付く受取側の会社名ではない"
    )
    invoice_number: RawText = Field(
        None, description="請求書番号の値だけ。ラベルは含めない"
    )
    issue_date: RawText = Field(
        None, description="発行日。YYYY-MM-DD。令和N年は西暦 N+2018 年に直す"
    )
    due_date: RawText = Field(
        None, description="お支払期日。YYYY-MM-DD。令和N年は西暦 N+2018 年に直す"
    )
    subtotal: RawAmount = Field(None, description="小計。税抜の合計金額")
    tax_amount: RawAmount = Field(
        None, description="消費税額。消費税の行が複数ある場合はその合算値"
    )
    total_amount: RawAmount = Field(None, description="合計。税込の合計金額")
    printed_total: RawAmount = Field(
        None, description="御請求金額 などの枠に印字された税込金額"
    )
    notes_excluded: RawText = Field(
        None,
        description="手書きの書き込みや欄外の注記など、構造化データに含めなかった内容をそのまま書き写す。無ければ null",
    )
    tax_rows: list[AiTaxRow] = Field(
        default_factory=list,
        description="消費税の行を税率ごとに書き出す。例: 消費税 8%（対象 103,200） 8,256",
    )
    lines: list[AiLineItem] = Field(
        default_factory=list,
        description="明細行。小計・消費税・合計 の行は含めない",
    )
