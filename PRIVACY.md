# プライバシー / Privacy

## 送信する情報

メールアドレスと API キーの設定・同意後に、手動確認を行うか自動監視を有効にすると、アプリは登録された 1 件のメールアドレスを HIBP の照合 API に送ります。

| 項目 | 送信先・用途 |
| --- | --- |
| 登録メールアドレス全体 | `https://haveibeenpwned.com` への HTTPS リクエストの URL に含め、漏洩記録を照合 |
| HIBP API キー | 同じリクエストの認証ヘッダー |
| アプリを識別する User-Agent | API 利用元の明示 |
| 通常の接続情報 | 通信に伴い HIBP 側で接続元 IP などを確認可能 |

この初期版ではメールアドレスの部分ハッシュ照合を利用しません。送信先サービスの扱いは [HIBP のプライバシーポリシー](https://haveibeenpwned.com/Privacy) と [API 仕様](https://haveibeenpwned.com/API/v3) を確認してください。

本プロジェクト独自のクラウドへのアップロード、利用状況の解析、広告用トラッキングはありません。画面の外部リンクを開く場合は、通常のブラウザーでリンク先へ接続します。依存パッケージのインストールや GitHub からのダウンロードは、アプリの照合通信とは別です。

## 端末に残る情報

メールアドレス、API キー、同意・監視設定、取得した漏洩記録、確認日時、対応済みの状態を、次のファイルにまとめて保存します。

```text
%LOCALAPPDATA%\MimamoriBreach\state.bin
```

ファイルは Windows DPAPI の現在のユーザー範囲で暗号化されます。別の PC や別の Windows ユーザーへコピーして設定を移す仕組みではありません。同じユーザー権限を持つプログラムやマルウェアからデータを守ることはできません。起動中は設定・結果がアプリのメモリーにあります。

通知にはメールアドレスやサービス名を載せません。アプリ本体には詳細を表示するため、画面共有やスクリーンショットには注意してください。

## 止める・消す

- **一時停止:** 設定で監視を無効にします。保存済みの履歴は残ります。既に送信済みのリクエストは取り消せません。
- **終了:** 画面またはトレイメニューの「終了」を選びます。ウィンドウを閉じるだけでは、トレイ常駐が続く場合があります。
- **ローカルデータの削除:** アプリを終了してから、エクスプローラーで `%LOCALAPPDATA%\MimamoriBreach` を開き、`state.bin` を削除します。次回は未設定で起動します。通常の削除であり、ストレージ上の完全消去を保証するものではありません。
- **API キーの失効:** 必要な場合は HIBP 側でキーを管理してください。ローカルファイルを削除しても API 契約は解約されません。

削除は自分の端末の保存情報に対して行われ、HIBP が持つ漏洩記録を変更しません。

## デモ

`--demo` は架空のデータのみをメモリー内で使用します。HIBP に問い合わせず、実際の設定ファイルにアクセスしません。終了するとデモ中の状態は破棄されます。

## 読み取らない情報

パスワード、ブラウザーの認証情報・閲覧履歴、メール本文、他アプリの通信、任意のファイル内容は収集しません。

## English summary

After setup and consent, manual checks and enabled automatic monitoring send the full configured email address in an HTTPS URL and your API key in a header directly to HIBP. The app uses no project-operated analytics or cloud backend. Settings and history are encrypted with current-user Windows DPAPI in `%LOCALAPPDATA%\MimamoriBreach\state.bin`; this does not protect them from malware running as your Windows user. Quit the app before deleting that file to reset all local data. The offline demo uses synthetic in-memory state only. No passwords, browser credentials or browsing history are collected.
