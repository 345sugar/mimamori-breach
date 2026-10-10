"""Windows tray UI. Worker threads communicate through a queue, never Tk."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import queue
import re
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from urllib.parse import quote
import webbrowser

from .hibp import Breach, ClientError, HibpClient, normalize_email
from .model import apply_success
from .storage import Store, StorageError
from .instance import InstanceError, InstanceLock

DAY = 24 * 60 * 60
BG = "#f2f5f4"
INK = "#193e37"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def seconds_until_due(last_success, now=None):
    """A persisted success timestamp prevents an API call on every restart."""
    if not last_success:
        return 0
    try:
        previous = datetime.fromisoformat(last_success)
        if previous.tzinfo is None:
            return 0
        elapsed = ((now or datetime.now(timezone.utc)) - previous).total_seconds()
        return max(0, min(DAY, DAY - elapsed))
    except (ValueError, TypeError):
        return 0


def demo_breaches():
    return [Breach("ExampleGarden", "Example Garden（架空）", "example.test",
                   "2025-02-10", "2026-10-01T00:00:00Z",
                   ["Email addresses", "Passwords"]),
            Breach("ExampleLetters", "Example Letters（架空）", "example.test",
                   "2024-09-03", "2026-10-02T00:00:00Z", ["Email addresses"])]


class App:
    def __init__(self, root, *, demo=False, tray=True, store=None):
        self.root = root
        self.demo = demo
        self.store = store
        self.events = queue.Queue()
        self.tray = None
        self.tray_ready = False
        self.pending_notification = None
        self.closed = False
        self.busy = False
        self.generation = 0
        self.storage_failed = False
        self.last_error = False
        self.next_check = float("inf")
        self.payload = {"config": {}, "state": {}}
        self.status = tk.StringVar(value="メールアドレスを登録して、見守りを始めましょう。")
        self.detail = tk.StringVar(value="項目を選ぶと、次にできることを表示します。")
        self.last = tk.StringVar(value="最終確認：まだ確認していません")
        self.headline = tk.StringVar(value="準備をしましょう")
        self._layout()
        if demo:
            self.payload["state"], _ = apply_success({}, "demo@example.test", demo_breaches(), utc_now())
            self.headline.set("デモを体験中")
            self.status.set("架空の漏洩情報です。通信・設定保存・実際の監視は行いません。")
        else:
            try:
                if self.store is None:
                    self.store = Store()
                loaded = self.store.load()
                if loaded:
                    self._validate_payload(loaded)
                    self.payload = loaded
                if self.payload["config"].get("enabled"):
                    self.next_check = time.time() + seconds_until_due(self.payload["state"].get("last_success"))
                    self.status.set("起動中に1日1回確認します。画面を閉じてもトレイで動作します。")
            except (StorageError, ValueError, TypeError, KeyError):
                self.storage_failed = True
                self.status.set("保存データを読み込めません。監視を停止しています。データは上書きしません。")
        self._refresh()
        if tray:
            self._start_tray()
        self.root.protocol("WM_DELETE_WINDOW", self.hide)
        self.root.after(200, self._pump)

    @staticmethod
    def _validate_payload(payload):
        if not isinstance(payload, dict) or set(payload) != {"config", "state"}:
            raise ValueError
        config, state = payload["config"], payload["state"]
        if not isinstance(config, dict) or not isinstance(state, dict):
            raise ValueError
        if config:
            if normalize_email(config["email"]) != config["email"]:
                raise ValueError
            if not re.fullmatch(r"[0-9a-fA-F]{32}", config["api_key"]):
                raise ValueError
            if type(config.get("enabled")) is not bool or config.get("consent") is not True:
                raise ValueError
        if state:
            if state.get("account") != config.get("email") or not isinstance(state.get("items"), dict):
                raise ValueError
            if not isinstance(state.get("last_success"), str):
                raise ValueError
            for name, item in state["items"].items():
                if not isinstance(name, str) or not isinstance(item, dict):
                    raise ValueError
                breach = item["breach"]
                if not isinstance(breach, dict) or not all(isinstance(breach.get(k), str) for k in
                    ("name", "title", "domain", "breach_date", "added_date")):
                    raise ValueError
                if not isinstance(breach.get("data_classes"), list) or not all(isinstance(x, str) for x in breach["data_classes"]):
                    raise ValueError
                if type(item.get("acknowledged")) is not bool:
                    raise ValueError
                if not isinstance(item.get("first_seen"), str) or breach["name"] != name or not name:
                    raise ValueError

    def _layout(self):
        r = self.root
        r.title("Mimamori Breach — みまもり" + (" [デモ]" if self.demo else ""))
        r.geometry("850x680")
        r.minsize(740, 610)
        r.configure(bg=BG)
        style = ttk.Style(r)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=INK, font=("Yu Gothic UI", 10))
        style.configure("TButton", font=("Yu Gothic UI", 10), padding=(14, 8))
        style.configure("TCheckbutton", background=BG, font=("Yu Gothic UI", 10))
        style.configure("Treeview", rowheight=34, font=("Yu Gothic UI", 10))
        style.configure("Treeview.Heading", font=("Yu Gothic UI", 10, "bold"))
        frame = ttk.Frame(r, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="MIMAMORI  /  みまもり", font=("Yu Gothic UI", 12, "bold")).pack(anchor="w")
        ttk.Label(frame, textvariable=self.headline, font=("Yu Gothic UI", 25, "bold")).pack(anchor="w", pady=(12, 6))
        ttk.Label(frame, textvariable=self.status, wraplength=780).pack(anchor="w", pady=(0, 8))
        ttk.Label(frame, textvariable=self.last, foreground="#5b716b").pack(anchor="w")
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=18)
        self.check_button = ttk.Button(buttons, text="今すぐ確認", command=self.check)
        self.check_button.pack(side="left")
        self.settings_button = ttk.Button(buttons, text="見守り設定", command=self.settings)
        self.settings_button.pack(side="left", padx=8)
        ttk.Button(buttons, text="トレイへ", command=self.hide).pack(side="right")
        table = ttk.Frame(frame)
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("title", "date", "status"), show="headings", selectmode="browse", height=6)
        for col, title, width in (("title", "報告されたサービス", 310), ("date", "漏洩日", 140), ("status", "対応メモ", 110)):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, minwidth=80)
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._select)
        ttk.Label(frame, textvariable=self.detail, wraplength=770, justify="left").pack(anchor="w", fill="x", pady=(16, 8))
        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        ttk.Button(actions, text="対応済み / 未対応を切替", command=self.acknowledge).pack(side="left")
        ttk.Button(actions, text="HIBPの報告を見る", command=self.open_report).pack(side="left", padx=8)
        credit = ttk.Label(frame, text="情報提供：Have I Been Pwned ↗", foreground="#286556", cursor="hand2")
        credit.pack(anchor="w", pady=(16, 3))
        credit.bind("<Button-1>", lambda _event: webbrowser.open("https://haveibeenpwned.com/"))
        ttk.Label(frame, text="現在のパスワード流出や侵入を断定するものではありません。", foreground="#5b716b").pack(anchor="w")
        ttk.Button(frame, text="終了", command=self.quit).pack(anchor="e", pady=(8, 0))

    def _refresh(self):
        selected = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        items = self.payload["state"].get("items", {})
        for name, item in sorted(items.items(), key=lambda pair: (pair[1]["acknowledged"], pair[0])):
            breach = item["breach"]
            self.tree.insert("", "end", iid=name, values=(breach["title"], breach["breach_date"], "対応済み" if item["acknowledged"] else "要確認"))
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])
        elif items:
            self.tree.selection_set(self.tree.get_children()[0])
        self._select()
        last = self.payload["state"].get("last_success")
        if last:
            self.last.set("最終成功確認：" + last.replace("T", " "))
        else:
            self.last.set("最終確認：まだ確認していません")
        if not self.demo:
            count = sum(not item["acknowledged"] for item in items.values())
            if self.storage_failed:
                self.headline.set("保存データの確認が必要です")
            elif self.busy:
                self.headline.set("確認しています")
            elif self.last_error:
                self.headline.set("今回の確認はできませんでした")
            elif not self.payload["config"].get("enabled"):
                self.headline.set("見守りは停止中です")
            elif count:
                self.headline.set(f"確認してほしい情報が {count} 件")
            else:
                self.headline.set("次の確認を待っています")
        self.check_button.configure(state="disabled" if self.busy or self.storage_failed else "normal")
        self.settings_button.configure(state="disabled" if self.demo or self.storage_failed else "normal")

    def _select(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            self.detail.set("まだ表示する報告はありません。未確認や照合なしは、安全の保証ではありません。")
            return
        breach = self.payload["state"]["items"][selected[0]]["breach"]
        classes = "、".join(breach["data_classes"])[:180]
        action = ("当時のパスワードと使い回しを確認し、必要なら公式サイトで変更してください。\n"
                  "二段階認証・パスキーやログイン履歴も確認しましょう。") if "Passwords" in breach["data_classes"] else (
                  "不審なメールに注意し、対象サービスの公式案内を確認してください。")
        self.detail.set(f"報告に含まれる情報：{classes}\n{action}\n対応済みは自分用のメモです。漏洩記録やリスクを消す操作ではありません。")

    def _persist(self, payload):
        if self.demo:
            self.payload = payload
            return True
        try:
            self.store.save(payload)
            self.payload = payload
            return True
        except StorageError:
            self.storage_failed = True
            self.next_check = float("inf")
            self.status.set("暗号化保存に失敗しました。監視を停止しました。終了して保存先を確認してください。")
            self._notify("保存できないため見守りを停止しました。アプリを開いて確認してください。")
            return False

    def acknowledge(self):
        selection = self.tree.selection()
        if selection and not self.storage_failed:
            updated = deepcopy(self.payload)
            item = updated["state"]["items"][selection[0]]
            item["acknowledged"] = not item["acknowledged"]
            self._persist(updated)
            self._refresh()

    def open_report(self):
        selection = self.tree.selection()
        if selection:
            if self.demo:
                messagebox.showinfo("デモの報告", "これは架空のサービスです。実際の報告ページはありません。", parent=self.root)
            else:
                webbrowser.open("https://haveibeenpwned.com/breach/" + quote(selection[0], safe=""))

    def settings(self):
        if self.demo or self.storage_failed:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("見守り設定")
        dialog.transient(self.root)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=24)
        frame.pack(fill="both", expand=True)
        config = self.payload["config"]
        email = tk.StringVar(value=config.get("email", ""))
        key = tk.StringVar(value=config.get("api_key", ""))
        consent = tk.BooleanVar(value=config.get("consent", False))
        enabled = tk.BooleanVar(value=config.get("enabled", False))
        ttk.Label(frame, text="自分のメールアドレス", font=("Yu Gothic UI", 11, "bold")).pack(anchor="w")
        ttk.Entry(frame, textvariable=email, width=58).pack(fill="x", pady=(6, 14))
        ttk.Label(frame, text="HIBP APIキー（有料契約が必要）").pack(anchor="w")
        ttk.Entry(frame, textvariable=key, show="●", width=58).pack(fill="x", pady=(6, 12))
        ttk.Label(frame, text="登録したメールアドレス全体とAPIキーを、照合のために\nHave I Been PwnedへHTTPSで送信します。\n設定と履歴は、このWindowsユーザー用に暗号化して保存します。",
                  justify="left").pack(anchor="w", pady=(0, 12))
        ttk.Checkbutton(frame, text="自分のアドレスであり、上記の送信・保存に同意する", variable=consent).pack(anchor="w")
        ttk.Checkbutton(frame, text="起動中に1日1回、自動で確認する", variable=enabled).pack(anchor="w", pady=(8, 12))
        ttk.Button(frame, text="HIBPのAPI契約案内", command=lambda: webbrowser.open("https://haveibeenpwned.com/Subscription")).pack(anchor="w")

        def save():
            try:
                address = normalize_email(email.get())
                api_key = key.get().strip()
                if not re.fullmatch(r"[0-9a-fA-F]{32}", api_key) or not consent.get():
                    raise ValueError
            except ValueError:
                messagebox.showerror("設定を確認してください", "メールアドレス、32桁のAPIキー、同意のチェックが必要です。", parent=dialog)
                return
            state = self.payload["state"] if config.get("email") == address else {}
            updated = {"config": {"email": address, "api_key": api_key,
                       "consent": True, "enabled": enabled.get()}, "state": state}
            self.generation += 1  # Discard in-flight results for earlier settings.
            if self._persist(updated):
                self.last_error = False
                if config.get("api_key") != api_key:
                    self.retry_not_before = 0
                self.next_check = time.time() if enabled.get() else float("inf")
                self.status.set("設定を保存しました。" if enabled.get() else "自動確認を停止しました。手動で確認できます。")
                key.set("")
                dialog.destroy()
            self._refresh()

        ttk.Button(frame, text="保存", command=save).pack(anchor="e", pady=(18, 0))

    def check(self):
        if self.busy or self.storage_failed:
            return
        if self.demo:
            self._notify("デモ通知：確認してほしい漏洩情報があります。アプリを開いて確認してください。")
            self.status.set("デモの確認が完了しました。実際の通信は行っていません。")
            return
        config = self.payload["config"]
        if not config.get("consent"):
            self.settings()
            return
        if time.time() < getattr(self, "retry_not_before", 0):
            self.status.set("サービスへの再確認を少し待っています。しばらくしてからお試しください。")
            return
        self.busy = True
        generation = self.generation
        address, api_key = config["email"], config["api_key"]
        self.status.set("HIBPの既知の漏洩情報を確認しています。")
        self._refresh()

        def worker():
            try:
                breaches = HibpClient(api_key).breaches(address)
                result = ("result", generation, address, breaches)
            except ClientError as error:
                result = ("error", generation, error.kind, error.retry_after)
            except Exception:
                result = ("error", generation, "service", 300)
            self.events.put(result)
        threading.Thread(target=worker, daemon=True, name="breach-check").start()

    def _handle_result(self, event):
        self.busy = False
        if event[1] != self.generation:
            self._refresh()
            return
        if event[0] == "result":
            _, _, address, breaches = event
            state, new = apply_success(self.payload["state"], address, breaches, utc_now())
            if self._persist({"config": self.payload["config"], "state": state}):
                self.last_error = False
                self.next_check = time.time() + DAY if self.payload["config"].get("enabled") else float("inf")
                self.retry_not_before = time.time() + 30
                self.status.set("確認が完了しました。新しく確認した報告を表示しています。" if new else
                                "確認が完了しました。今回、新しい報告は見つかりませんでした。")
                if new:
                    self._notify(f"確認してほしい情報が {len(new)} 件あります。アプリを開いて確認してください。")
        else:
            first_failure = not self.last_error
            self.last_error = True
            kind, delay = event[2:]
            messages = {"auth": "APIキーまたは契約を確認してください。今回の照合はできませんでした。",
                        "rate_limit": "HIBPの利用上限に達しました。時間をおいて再確認します。",
                        "network": "通信できませんでした。以前の確認結果を表示しています。"}
            self.status.set(messages.get(kind, "今回の確認に失敗しました。以前の確認結果を表示しています。"))
            delay = max(60, min(86400, delay or 300))
            self.retry_not_before = time.time() + delay
            self.next_check = (float("inf") if kind == "auth" or not self.payload["config"].get("enabled")
                               else self.retry_not_before)
            if first_failure:
                self._notify("漏洩情報の確認ができませんでした。アプリを開いて状態を確認してください。")
        self._refresh()

    def _pump(self):
        if self.closed:
            return
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] in ("result", "error"):
                    self._handle_result(event)
                elif event[0] == "show":
                    self.root.deiconify()
                    self.root.lift()
                elif event[0] == "quit":
                    self.quit()
                elif event[0] == "check":
                    self.check()
                elif event[0] == "tray_ready":
                    self.tray_ready = True
                    if self.pending_notification:
                        self._notify(self.pending_notification)
                elif event[0] == "tray_error":
                    self.tray_ready = False
                    self.root.deiconify()
                    self.status.set("トレイを開始できませんでした。このウィンドウを開いてご利用ください。")
        except queue.Empty:
            pass
        if self.closed:
            return
        if not self.demo and not self.busy and not self.storage_failed and time.time() >= self.next_check:
            self.check()
        self.root.after(250, self._pump)

    def _start_tray(self):
        import pystray
        from PIL import Image, ImageDraw
        picture = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(picture)
        draw.rounded_rectangle((2, 2, 62, 62), radius=18, fill=INK)
        draw.polygon([(32, 12), (49, 18), (46, 40), (32, 53), (18, 40), (15, 18)], fill="#c6efd5")
        draw.ellipse((23, 26, 27, 30), fill=INK)
        draw.ellipse((37, 26, 41, 30), fill=INK)
        draw.arc((25, 29, 39, 41), 0, 180, fill=INK, width=2)
        menu = pystray.Menu(
            pystray.MenuItem("みまもりを開く", lambda *_: self.events.put(("show",)), default=True),
            pystray.MenuItem("今すぐ確認", lambda *_: self.events.put(("check",))),
            pystray.MenuItem("終了", lambda *_: self.events.put(("quit",))))
        self.tray = pystray.Icon("MimamoriBreach", picture, "Mimamori Breach" + (" [デモ]" if self.demo else ""), menu)

        def run():
            try:
                def setup(icon):
                    icon.visible = True
                    self.events.put(("tray_ready",))
                self.tray.run(setup=setup)
            except Exception:
                self.events.put(("tray_error",))
        threading.Thread(target=run, daemon=True, name="tray").start()

    def _notify(self, text):
        self.pending_notification = text
        if self.tray and self.tray_ready:
            try:
                self.tray.notify(text, "Mimamori Breach" + (" [デモ]" if self.demo else ""))
                self.pending_notification = None
            except Exception:
                pass  # The persistent in-app finding remains available.

    def hide(self):
        if self.tray_ready:
            self.root.withdraw()
        elif messagebox.askyesno("みまもりを終了", "トレイは準備できていません。アプリを終了しますか？", parent=self.root):
            self.quit()

    def quit(self):
        self.closed = True
        self.generation += 1
        if self.tray:
            self.tray.stop()
        self.root.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mimamori Breach — Windows breach alerts")
    parser.add_argument("--demo", action="store_true", help="Offline, in-memory demonstration")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if sys.platform != "win32":
        parser.error("This desktop application supports Windows only.")
    root = tk.Tk()
    if args.smoke_test:
        root.withdraw()
    lock = None
    try:
        if not args.demo and not args.smoke_test:
            try:
                lock = InstanceLock()
                if not lock.acquire():
                    messagebox.showinfo("起動済みです", "みまもりは既に起動しています。トレイから開いてください。", parent=root)
                    root.destroy()
                    return 0
            except InstanceError:
                messagebox.showerror("起動できません", "二重起動の確認ができませんでした。", parent=root)
                root.destroy()
                return 1
        app = App(root, demo=args.demo or args.smoke_test, tray=not args.smoke_test)
        if args.smoke_test:
            try:
                root.update_idletasks()
                assert len(app.tree.get_children()) == 2
                app.tree.selection_set("ExampleGarden")
                app.acknowledge()
                assert app.payload["state"]["items"]["ExampleGarden"]["acknowledged"]
                app.check()
            finally:
                app.quit()
            return 0
        root.mainloop()
    finally:
        if lock is not None:
            lock.close()
    return 0
