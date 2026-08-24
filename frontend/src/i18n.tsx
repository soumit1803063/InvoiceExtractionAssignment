import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';

export const DICTIONARY = {
  cancel: { en: 'Cancel', ja: 'キャンセル' },
  openFullSize: { en: 'Open full size', ja: '原寸で開く' },
  browserWillNotDisplayPdf: { en: 'This browser will not display the PDF inline.', ja: 'このブラウザーは PDF をページ内に表示できません。' },
  openInNewTab: { en: 'Open it in a new tab', ja: '新しいタブで開く' },
  scannedPageOf: { en: 'Scanned page of {0}', ja: '{0} のスキャン画像' },
  noLineItemsExtracted: { en: 'No line items were extracted. The accounting system needs at least one line.', ja: '明細が抽出されていません。会計システムには最低 1 行の明細が必要です。' },
  addLine: { en: 'Add a line', ja: '明細を追加' },
  noSubtotalToCompare: { en: 'no subtotal to compare with', ja: '比較する小計がありません' },
  matchesSubtotal: { en: 'matches the subtotal {0}', ja: '小計 {0} と一致' },
  doesNotMatchSubtotal: { en: 'does not match the subtotal {0}', ja: '小計 {0} と不一致' },
  ariaDescription: { en: 'Description for line {0}', ja: '明細 {0} の摘要' },
  ariaQuantity: { en: 'Quantity for line {0}', ja: '明細 {0} の数量' },
  ariaUnit: { en: 'Unit for line {0}', ja: '明細 {0} の単位' },
  ariaUnitPrice: { en: 'Unit price for line {0}', ja: '明細 {0} の単価' },
  ariaAmount: { en: 'Amount for line {0}', ja: '明細 {0} の金額' },
  ariaTaxCode: { en: 'Tax code for line {0}', ja: '明細 {0} の税区分' },
  ariaRemoveLine: { en: 'Remove line {0}', ja: '明細 {0} を削除' },
  checkCrossfoot: { en: 'Line amounts add up to the subtotal', ja: '明細金額の合計が小計と一致' },
  checkTax: { en: 'Tax matches the per-rate calculation', ja: '消費税が税率ごとの計算と一致' },
  checkTotal: { en: 'Subtotal plus tax equals the total', ja: '小計＋消費税が合計と一致' },
  checkPrintedTotal: { en: 'The total matches the amount printed on the page', ja: '合計が請求書に記載された金額と一致' },
  checkPartner: { en: 'The supplier exists in the accounting supplier master', ja: '取引先が取引先マスタに存在' },
  checkDuplicate: { en: 'This invoice is not a duplicate', ja: 'この請求書は重複していない' },
  checkRequired: { en: 'All required fields are filled in', ja: '必須項目がすべて入力済み' },
  detailLinesAddUp: { en: 'Lines add up to {0}; the subtotal says {1}.', ja: '明細の合計は {0}、小計の記載は {1} です。' },
  detailTaxDeclared: { en: 'The invoice declares {0} of tax.', ja: '請求書に記載の消費税は {0} です。' },
  detailTotalSum: { en: '{0} + {1} = {2}; the total says {3}.', ja: '{0} ＋ {1} ＝ {2}、合計の記載は {3} です。' },
  detailPrintedTotal: { en: 'Printed on the page: {0}; computed total: {1}.', ja: '記載金額: {0}、計算した合計: {1}。' },
  detailPartnerCode: { en: 'Partner code on this document: {0}.', ja: 'この書類の取引先コード: {0}。' },
  detailNoPartnerCode: { en: 'No partner code has been set on this document yet.', ja: 'この書類にはまだ取引先コードが設定されていません。' },
  detailNoDuplicate: { en: 'No other document in the queue carries the same invoice number for this supplier.', ja: '同じ取引先で同じ請求書番号の書類は一覧にありません。' },
  detailDuplicateOf: { en: 'Same invoice as {0}.', ja: '{0} と同じ請求書です。' },
  detailNothingMissing: { en: 'Nothing required is missing.', ja: '必須項目の不足はありません。' },
  detailStillMissing: { en: 'Still missing: {0}.', ja: '不足している項目: {0}。' },
  checksPassedOf: { en: '{0} of {1} checks passed', ja: '{1} 件中 {0} 件の検証に合格' },
  quantity: { en: 'Quantity', ja: '数量' },
  statusRegistered: { en: 'Registered', ja: '登録済' },
  mustBeWholeYen: { en: 'must be a whole number of yen.', ja: 'は円単位の整数で入力してください。' },
  mustBeIsoDate: { en: 'must be a real date in YYYY-MM-DD form.', ja: 'は YYYY-MM-DD 形式の日付で入力してください。' },
  lineNumber: { en: 'Line', ja: '明細' },
  upload: { en: 'Upload', ja: '追加' },
  needsReview: { en: 'Needs review', ja: '要確認' },
  readyRegister: { en: 'Ready to register', ja: '登録可' },
  rejected: { en: 'Rejected', ja: '却下' },
  reading: { en: 'Reading…', ja: '読取中' },
  readingTab: { en: 'Reading', ja: '読取中' },
  nothingBeingReadNow: { en: 'Nothing is being read right now', ja: '現在読み取り中の書類はありません' },
  uploadedInvoicesAppearHereWhileRead: { en: 'An uploaded invoice appears here while it is being read, then moves to the queue.', ja: 'アップロードした請求書は読み取り中ここに表示され、完了するとキューに移ります。' },
  stillReadingDocument: { en: 'This invoice is still being read', ja: 'この請求書はまだ読み取り中です' },
  fieldsAppearWhenReadingFinishes: { en: 'The extracted fields and the checks appear here once reading finishes. Only the original document is shown until then.', ja: '読み取りが終わると、抽出項目と検証結果がここに表示されます。それまでは元の書類のみを表示します。' },
  supplierName: { en: 'Supplier name', ja: '取引先名' },
  invoiceNumber: { en: 'Invoice number', ja: '請求書番号' },
  issueDate: { en: 'Issue date', ja: '発行日' },
  dueDate: { en: 'Due date', ja: '支払期日' },
  subtotal: { en: 'Subtotal', ja: '小計' },
  totalAmount: { en: 'Total', ja: '合計' },
  printedTotal: { en: 'Printed total', ja: '記載合計' },
  linesHaveNoUnit: { en: 'line(s) have no unit', ja: '件の明細に単位がありません' },
  unitsStillToFill: { en: 'unit(s) still to fill in', ja: '件の単位が未入力です' },
  acceptedSession: { en: 'Accepted this session', ja: '受付済' },
  acceptedTaxCodes: { en: 'Accepted tax codes', ja: '登録可能な税コード' },
  accountingId: { en: 'Accounting ID', ja: '会計ID' },
  accountingSystemReachableRegistrationPossible: { en: 'Accounting system reachable — registration is possible.', ja: '会計システムに接続できます。登録が可能です。' },
  accountingSystemRejectsRecordOutright: { en: 'The accounting system rejects the record outright if a required value is missing.', ja: '必須項目が欠けていると、会計システムはその記録をそのまま拒否します。' },
  accountingSystemRequiresUnitEvery: { en: 'The accounting system requires a unit on every line and rejects the whole invoice without it. Type what the page actually says. Nothing is filled in for you, because a guessed unit is a wrong unit.', ja: '会計システムは全明細に単位を要求し、無ければ請求書ごと拒否します。ページに印字されているとおりに入力してください。推測した単位は誤った単位なので、自動では埋めません。' },
  accountingSystemUnreachableReviewingWorks: { en: 'Accounting system unreachable — reviewing works, registration will fail until it is back.', ja: '会計システムに接続できません。確認は行えますが、復旧するまで登録は失敗します。' },
  amount: { en: 'Amount', ja: '金額' },
  arithmeticInvoiceItselfMustHold: { en: 'The arithmetic of the invoice itself must hold before anything is sent onward.', ja: '送信する前に、請求書自体の計算が合っている必要があります。' },
  backLoggedList: { en: 'Back to the logged list', ja: '登録済一覧へ戻る' },
  backQueue: { en: 'Back to the queue', ja: '一覧へ戻る' },
  blockingRegistration: { en: 'Blocking registration', ja: '登録を止めている理由' },
  checkingConnections: { en: 'Checking connections…', ja: '接続を確認しています…' },
  checks: { en: 'Checks', ja: '検証' },
  chooseInvoices: { en: 'Choose invoices', ja: 'ファイルを選ぶ' },
  correctionsSavedVerificationReRun: { en: 'Corrections saved and verification re-run', ja: '訂正を保存し、検証を再実行しました' },
  correctionsWereNotSaved: { en: 'The corrections were not saved', ja: '訂正を保存できませんでした' },
  created: { en: 'Created at', ja: '受付日時' },
  currency: { en: 'Currency', ja: '通貨' },
  description: { en: 'Description', ja: '摘要' },
  everyLineAmountAddedUp: { en: 'Every line amount was added up and compared with the subtotal on the invoice.', ja: '明細の金額をすべて合計し、請求書の小計と照合しました。' },
  failed: { en: 'Failed', ja: '不合格' },
  fixTheseBeforeSaving: { en: 'Fix these before saving', ja: '保存前に修正してください' },
  fromAccountingSystem: { en: 'From the accounting system', ja: '会計システムの登録内容' },
  goFirstMissingUnit: { en: 'Go to the first missing unit', ja: '最初の未入力の単位へ' },
  goQueue: { en: 'Go to the queue', ja: '一覧へ' },
  guardsAgainstReadingErrorComputed: { en: 'Guards against a reading error: the computed total must equal the total printed on the invoice.', ja: '読み取り誤りを防ぐため、計算した合計とページに印字された合計が一致する必要があります。' },
  invoice: { en: 'Invoice', ja: '請求書' },
  invoiceFields: { en: 'Invoice fields', ja: '請求書項目' },
  invoiceNotAccepted: { en: 'The invoice was not accepted', ja: '請求書を受け付けられませんでした' },
  invoiceReview: { en: 'Invoice review', ja: '請求書レビュー' },
  invoicesAppearHereOnceAccounting: { en: 'Invoices appear here once the accounting system has accepted them.', ja: '会計システムが受け付けた請求書がここに表示されます。' },
  lineItems: { en: 'Line items', ja: '明細' },
  linesAddUp: { en: 'Lines add up to', ja: '明細合計' },
  loading: { en: 'Loading…', ja: '読み込み中…' },
  loadingSourcePage: { en: 'Loading the source page…', ja: '原本を読み込んでいます…' },
  logged: { en: 'Registered', ja: '登録済み' },
  loggedIntoAccountingSystemThese: { en: 'Logged into the accounting system. These stay here permanently and are never read again unless you ask.', ja: '会計システムに登録済みです。ここに残り続け、指示がない限り再読取されません。' },
  noDocumentWithProcessId: { en: 'No document with that process id', ja: 'この処理IDは見つかりません' },
  noInvoicesYet: { en: 'No invoices yet', ja: 'まだ請求書がありません' },
  nothingHasBeenSentAccounting: { en: 'Nothing has been sent to the accounting system. Start the backend and try again.', ja: '会計システムには何も送信されていません。バックエンドを起動してから再試行してください。' },
  nothingLoggedYet: { en: 'Nothing logged yet', ja: '登録済の請求書はまだありません' },
  onlySuppliersAlreadyAccountingSystem: { en: 'Only suppliers already in the accounting system can be registered.', ja: '会計システムの取引先マスタにある取引先だけが登録できます。' },
  pageBeingTranscribedStructuredFields: { en: 'The page is being transcribed and structured. Fields, checks and registration appear here as soon as it finishes.', ja: 'ページを書き起こして構造化しています。完了すると項目・検証結果・登録がここに表示されます。' },
  partnerCode: { en: 'Partner code', ja: '取引先コード' },
  passed: { en: 'Passed', ja: '合格' },
  pdfJpgOrPngEach: { en: 'PDF, JPG or PNG. Each file is written into the invoices folder, given a process id, and read in the background. Reading a scanned page takes about half a minute.', ja: 'PDF・JPG・PNG に対応しています。ファイルは invoices フォルダに保存され、処理IDが付与され、背後で読み取られます。スキャン画像の読み取りには30秒ほどかかります。' },
  processId: { en: 'Process ID', ja: '処理ID' },
  qty: { en: 'Qty', ja: '数量' },
  queue: { en: 'Blocked', ja: '保留中' },
  queueCouldNotLoaded: { en: 'The queue could not be loaded', ja: '一覧を読み込めませんでした' },
  readLiveFrom: { en: 'read live from', ja: '取得元' },
  register: { en: 'Register', ja: '登録する' },
  registered: { en: 'Registered at', ja: '登録日時' },
  registration: { en: 'Registration', ja: '登録' },
  registrationNumber: { en: 'Registration number', ja: '登録番号' },
  registrationStaysBlockedUntilEvery: { en: 'Registration stays blocked until every line has a unit.', ja: 'すべての明細に単位が入るまで登録できません。' },
  required: { en: 'required', ja: '必須' },
  result: { en: 'Result', ja: '結果' },
  saveAndRevalidate: { en: 'Save & Revalidate', ja: '保存して再検証' },
  startOver: { en: 'Start over', ja: '最初からやり直す' },
  startingOver: { en: 'Starting over…', ja: 'やり直し中…' },
  startOverConfirm: { en: 'Unregister everything and start over?', ja: 'すべての登録を取り消してやり直しますか？' },
  startOverExplained: { en: 'This calls DELETE /invoices on the accounting system, so every invoice registered there is removed. Every uploaded file and everything read from it is deleted here as well. This cannot be undone.', ja: '会計システムに DELETE /invoices を送り、登録済みの請求書をすべて削除します。アップロードしたファイルと読み取り結果も当アプリからすべて削除します。取り消しはできません。' },
  yesStartOver: { en: 'Yes, start over', ja: 'はい、やり直します' },
  startOverFailed: { en: 'Nothing was deleted', ja: '削除できませんでした' },
  startOverDone: { en: 'Unregistered {0} invoices from the accounting system and cleared {1} documents from here.', ja: '会計システムから請求書 {0} 件の登録を取り消し、当アプリの書類 {1} 件を削除しました。' },
  startOverIncomplete: { en: 'The accounting system still reports {0} registered invoices.', ja: '会計システムには請求書がまだ {0} 件登録されています。' },
  otherFailures: { en: 'Other failures', ja: 'その他の失敗' },
  otherFailuresExplained: { en: 'These are not verification results. They happened before the invoice could be checked, or when it was sent to the accounting system.', ja: 'これらは検証結果ではありません。検証前、または会計システムへの送信時に発生した問題です。' },
  tokensUsed: { en: 'Tokens used', ja: '使用トークン' },
  inputTokens: { en: 'Input', ja: '入力' },
  outputTokens: { en: 'Output', ja: '出力' },
  modelUsed: { en: 'Model', ja: 'モデル' },
  revert: { en: 'Revert', ja: '元に戻す' },
  sameInvoiceNumberSameSupplier: { en: 'The same invoice number for the same supplier cannot be registered twice.', ja: '同じ取引先で同じ請求書番号を二重に登録することはできません。' },
  saving: { en: 'Saving…', ja: '保存中…' },
  screenCannotReachItsOwn: { en: 'This screen cannot reach its own server.', ja: 'この画面は自身のサーバーに接続できません。' },
  sourcePage: { en: 'Source page', ja: '原本' },
  sourcePageCouldNotLoaded: { en: 'The source page could not be loaded.', ja: '原本を読み込めませんでした。' },
  stillBeingRead: { en: 'Still being read', ja: 'この請求書はまだ読み取り中です' },
  subtotalOrTaxMissingSo: { en: 'The subtotal or the tax is missing, so the total cannot be checked.', ja: '小計または消費税がないため、合計を検証できません。' },
  supplier: { en: 'Supplier', ja: '取引先' },
  tax: { en: 'Tax', ja: '税区分' },
  taxRecalculatedPerTaxCode: { en: 'Tax is recalculated per tax code on the subtotal for that code and rounded down, then compared with the tax on the invoice.', ja: '税は税コードごとに、そのコードの小計に対して計算し切り捨てたうえで、請求書の消費税額と照合します。' },
  tryAgain: { en: 'Try again', ja: '再試行' },
  unit: { en: 'Unit', ja: '単位' },
  unitPrice: { en: 'Unit price', ja: '単価' },
  unsavedCorrections: { en: 'unsaved corrections', ja: '未保存の訂正' },
  uploadInvoiceFillQueue: { en: 'Upload an invoice to fill the queue.', ja: '請求書をアップロードすると一覧に表示されます。' },
  uploadInvoices: { en: 'Upload invoices', ja: '請求書を追加' },
  uploading: { en: 'Uploading…', ja: 'アップロード中…' },
  verification: { en: 'Verification', ja: '検証結果' },
  dashboard: { en: 'Dashboard', ja: 'ダッシュボード' },
  whatTheAccountingSystemAccepts: { en: 'What the accounting system accepts', ja: '会計システムが受け付ける内容' },
  readLiveFromTheAccountingSystem: { en: 'Read live from the accounting system every time this page opens.', ja: 'このページを開くたびに会計システムから直接読み込みます。' },
  livenessCheck: { en: 'Liveness check', ja: '死活監視' },
  livenessCheckEndpoint: { en: 'GET /health — no API key required', ja: 'GET /health — API キー不要' },
  supplierMaster: { en: 'Supplier master', ja: '取引先マスタ' },
  supplierMasterEndpoint: { en: 'GET /partners — only suppliers listed here can be registered', ja: 'GET /partners — ここに登録されている取引先のみ登録できます' },
  taxCodeList: { en: 'Tax code list', ja: '税コード一覧' },
  taxCodeListEndpoint: { en: 'GET /tax-codes — a line must carry one of these codes', ja: 'GET /tax-codes — 明細にはこれらのコードのいずれかが必要です' },
  aliases: { en: 'Aliases', ja: '別名' },
  reachable: { en: 'Reachable', ja: '接続可能' },
  unreachable: { en: 'Unreachable', ja: '接続不可' },
  taxCode: { en: 'Tax code', ja: '税コード' },
  rate: { en: 'Rate', ja: '税率' },
  suppliersRegisterable: { en: 'Suppliers that can be registered', ja: '登録可能な取引先' },
  taxCodesAccepted: { en: 'Tax codes accepted', ja: '受付可能な税コード' },
  referenceCouldNotBeRead: { en: 'The accounting system could not be read', ja: '会計システムを読み取れませんでした' },
  noSuppliersReturned: { en: 'The supplier master came back empty', ja: '取引先マスタが空でした' },
  noTaxCodesReturned: { en: 'The tax code list came back empty', ja: '税コード一覧が空でした' },
  refresh: { en: 'Refresh', ja: '再読み込み' },
} as const;

export function fill(template: string, ...values: string[]): string {
  return values.reduce((text, value, index) => text.split(`{${index}}`).join(value), template);
}

export type Language = 'en' | 'ja';
export type Words = Record<keyof typeof DICTIONARY, string>;

const STORAGE_KEY = 'invoice-review-language';
const LanguageContext = createContext<Language>('en');

function storedLanguage(): Language {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === 'ja' ? 'ja' : 'en';
  } catch {
    return 'en';
  }
}

export function useLanguage(): Language {
  return useContext(LanguageContext);
}

export function useWords(): Words {
  const language = useLanguage();
  return useMemo(
    () =>
      Object.fromEntries(
        Object.entries(DICTIONARY).map(([key, entry]) => [key, entry[language]])
      ) as Words,
    [language]
  );
}

export function LanguageProvider({ children }: { children: (toggle: ReactNode) => ReactNode }) {
  const [language, setLanguage] = useState<Language>(storedLanguage);

  useEffect(() => {
    document.documentElement.lang = language;
    try {
      window.localStorage.setItem(STORAGE_KEY, language);
    } catch {
      return;
    }
  }, [language]);

  const toggle = (
    <div className="language-toggle" role="group" aria-label="Language">
      <button
        type="button"
        className={`language-toggle__option${language === 'en' ? ' language-toggle__option--active' : ''}`}
        aria-pressed={language === 'en'}
        onClick={() => setLanguage('en')}
      >
        EN
      </button>
      <button
        type="button"
        className={`language-toggle__option${language === 'ja' ? ' language-toggle__option--active' : ''}`}
        aria-pressed={language === 'ja'}
        onClick={() => setLanguage('ja')}
      >
        日本語
      </button>
    </div>
  );

  return <LanguageContext.Provider value={language}>{children(toggle)}</LanguageContext.Provider>;
}
