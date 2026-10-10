# プライバシー / Privacy

## 送信する情報

メールアドレスと自分の API キーを設定し、送信への同意と、自分の API 契約・費用負担の確認を行った後に、手動確認を行うか自動監視を有効にすると、アプリは登録された 1 件のメールアドレスを HIBP の照合 API に送ります。費用負担の確認がない従来の保存設定では、手動・自動ともに照合を停止します。

| 項目 | 送信先・用途 |
| --- | --- |
| 登録メールアドレス全体 | `https://haveibeenpwned.com` への HTTPS リクエストの URL に含め、漏洩記録を照合 |
| HIBP API キー | 同じリクエストの認証ヘッダー |
| アプリを識別する User-Agent | API 利用元の明示 |
| 通常の接続情報 | 通信に伴い HIBP 側で接続元 IP などを確認可能 |

この初期版ではメールアドレスの部分ハッシュ照合を利用しません。送信先サービスの扱いは [HIBP のプライバシーポリシー](https://haveibeenpwned.com/Privacy) と [API 仕様](https://haveibeenpwned.com/API/v3) を確認してください。

本プロジェクト独自のクラウドへのアップロード、利用状況の解析、広告用トラッキングはありません。画面の外部リンクを開く場合は、通常のブラウザーでリンク先へ接続します。依存パッケージのインストールや GitHub からのダウンロードは、アプリの照合通信とは別です。

## API キーと費用

利用者本人のキーを使い（BYOK）、端末から HIBP へ直接照合します。作者のキーの同梱・共有や、作者が運営する有料 API の中継はなく、他の利用者の API 利用料金が作者へ集まる構成ではありません。実際の照合には利用者自身の HIBP 有料契約が必要で、その費用は利用者が負担します。アプリが自動で契約・購入することはありません。

キーを設定せず無料デモを使う場合、通信・契約は不要で、このアプリから課金対象の API 利用は発生しません。アプリの停止・削除は、別途結んだ HIBP の契約の解約にはなりません。

## 端末に残る情報

メールアドレス、API キー、送信への同意・費用負担の確認・監視設定、取得した漏洩記録、確認日時、対応済みの状態を、次のファイルにまとめて保存します。

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

After setup, disclosure consent and confirmation that you use your own API subscription and bear its costs, manual checks and enabled automatic monitoring send the full configured email address in an HTTPS URL and your API key in a header directly to HIBP. Saved settings without the cost confirmation cannot make either kind of lookup. Each user brings their own key (BYOK); no maintainer key is bundled or shared, and there is no maintainer-operated paid API relay. Other users' API usage does not accrue charges to the maintainer through this app. Users are responsible for their own HIBP subscription costs; the app makes no purchases or subscriptions. Stopping or deleting it does not cancel a separate HIBP subscription.

The app uses no project-operated analytics or cloud backend. Settings, consent, cost confirmation and history are encrypted with current-user Windows DPAPI in `%LOCALAPPDATA%\MimamoriBreach\state.bin`; this does not protect them from malware running as your Windows user. Quit the app before deleting that file to reset all local data. The free offline demo uses synthetic in-memory state only, requires no key or subscription and makes no billable API requests. No passwords, browser credentials or browsing history are collected.
