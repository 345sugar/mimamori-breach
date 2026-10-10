# 開発への参加 / Contributing

操作しやすさ、通知のわかりやすさ、プライバシー、エラー処理の改善を歓迎します。

## 不具合・改善案

[Issues](https://github.com/345sugar/mimamori-breach/issues) に、次を含めてください。

- 何をしようとしたか、期待した結果、実際の結果。
- Windows、Python、アプリのバージョンまたはコミット。
- デモまたは架空データで再現できる操作。

実メールアドレス、API キー、個人の漏洩履歴を含む画面・ログを添付しないでください。セキュリティ上の問題には [SECURITY.md](SECURITY.md) の手順を使ってください。

## 開発環境

Windows、Python 3.11 以上、tkinter を用意します。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m mimamori_breach --demo
```

GUI とトレイには tkinter・pystray・Pillow を使います。通常の開発ではオフラインデモと、モックを使ったテストで挙動を確認してください。実アカウントの情報をテストデータに追加しないでください。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

単体テストは実メールアドレスや実 API キーを使わずに実行できます。Windows 用の暗号化・GUI の挙動は Windows 上で確認してください。

## 変更の方針

- 一つの Pull Request で扱う目的を明確にし、変更理由と確認した内容を書きます。
- 認証失敗・レート制限・オフラインを、照合成功や「該当なし」と区別します。
- API キー・登録アドレス・リクエスト URL をログやエラーメッセージへ出しません。
- ネットワーク送信や保存データを変える場合、同意表示・プライバシー文書も合わせて更新します。
- HIBP の出典表示を維持し、返却された文章・URL を実行可能な内容として扱いません。
- 新しい依存関係は用途を説明します。自動アップデートや起動登録を追加する場合は、利用者が選べる設計にします。

## English

Use the offline demo and synthetic test fixtures. Explain the purpose of your change and how you checked it. Never attach credentials, personal breach results or a real state file. Preserve the distinction between failed requests and successful empty results; update consent and privacy documentation when data flows change. Security reports follow [SECURITY.md](SECURITY.md).
