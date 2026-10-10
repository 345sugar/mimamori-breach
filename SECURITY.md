# セキュリティ / Security

## 保守対象

初期開発版のため、現時点ではデフォルトブランチの最新コードを対象に修正します。安定版の長期サポート期間、応答時間、報奨金制度は設けていません。

メンテナーは [345sugar](https://github.com/345sugar) です。AI による実装支援を利用しています。独立したセキュリティ監査や第三者認証は受けていません。

## 問題の連絡

本プロジェクトのセキュリティ上の問題に気づいた場合は、GitHub の [非公開の脆弱性報告](https://github.com/345sugar/mimamori-breach/security/advisories/new) を使ってメンテナーへ連絡してください。非公開報告機能を有効にしています。

公開 Issue、Pull Request、添付ファイルに以下を載せないでください。

- 実際の API キー、メールアドレス、漏洩記録。
- 暗号化されていても、実利用中の `state.bin`。
- 未修正の問題を使って他人の情報へアクセスできる詳細。

非公開の報告にも、必要最小限の情報だけを含めてください。バージョンまたはコミット、Windows/Python のバージョン、想定と実際の挙動、架空データで再現する手順が役立ちます。API キーなどの秘密情報を送る必要はありません。

他者のアカウントや実データで試す必要はありません。HIBP 自体の問題は、本プロジェクトではなく HIBP の窓口へ連絡してください。

## 保護の範囲

- API キー・メールアドレス・履歴の保存には Windows DPAPI を使います。同じ Windows ユーザー権限で実行される悪意あるプログラムへの対策にはなりません。
- 設定と同意の後、手動確認または有効にした自動監視で HIBP への照合を行います。公開 API から返ったデータの表示と、アプリの固定リンクを使用します。
- このアプリは漏洩情報を知らせる補助ツールです。侵入防止ソフトや、PC 全体の安全性を確認するスキャナーではありません。
- Windows 配布物は現時点で署名付きインストーラーではありません。

データの扱いは [PRIVACY.md](PRIVACY.md) を参照してください。

## English

Only the latest default-branch code is currently maintained. Report suspected security issues through [GitHub private vulnerability reporting](https://github.com/345sugar/mimamori-breach/security/advisories/new), which is enabled for this repository. Do not publish exploit details, real email addresses, API keys, breach histories or your state file. Share only the information needed to reproduce the issue, using synthetic records. There is no guaranteed response time or bug bounty.
