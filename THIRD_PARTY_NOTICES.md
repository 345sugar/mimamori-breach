# Third-party notices

Mimamori Breach のソースコードには [MIT License](LICENSE) が適用されます。依存ソフトウェアには、それぞれのライセンスが適用されます。ライセンス原文と著作権表示は [`licenses/`](licenses/) に同梱しています。

以下は、2026-10-10 にローカルの Windows 配布物を作成した環境で確認したバージョンです。パッケージ情報と同梱ライセンスから記録しています。依存ソフトウェアや Python を更新して再配布する場合は、そのビルドに対応する原文も更新してください。

| ソフトウェア | 確認した版 | ライセンス原文 | ソース |
| --- | --- | --- | --- |
| pystray | 0.19.5 | [LGPLv3](licenses/pystray-COPYING.LGPL) と [GPLv3](licenses/pystray-COPYING)。ソースの通知は LGPLv3 またはそれ以降 | [moses-palmer/pystray](https://github.com/moses-palmer/pystray) |
| Pillow | 12.3.0 | [MIT-CMU と wheel 内ライブラリのライセンス](licenses/Pillow-LICENSE.txt) | [python-pillow/Pillow](https://github.com/python-pillow/Pillow) |
| six | 1.17.0 | [MIT](licenses/six-LICENSE.txt) | [benjaminp/six](https://github.com/benjaminp/six) |
| Python | 3.12.14 | [PSF と配布元が添付する関連通知](licenses/Python-LICENSE.txt) | [python/cpython](https://github.com/python/cpython) |
| Tcl | 8.6.12 | [license.terms](licenses/Tcl-license.terms) | [tcltk/tcl](https://github.com/tcltk/tcl/tree/core-8-6-12) |
| Tk | 8.6.12 | [license.terms](licenses/Tk-license.terms) | [tcltk/tk](https://github.com/tcltk/tk/tree/core-8-6-12) |
| PyInstaller | 6.22.3 | [GPLv2-or-later、Bootloader Exception、実行時フック等の条件](licenses/PyInstaller-COPYING.txt) | [pyinstaller/pyinstaller](https://github.com/pyinstaller/pyinstaller) |

pystray: Copyright (C) 2016–2022 Moses Palmér.

PIL/Pillow: Copyright © 1997–2011 Secret Labs AB; Copyright © 1995–2011 Fredrik Lundh and contributors; Copyright © 2010 Jeffrey 'Alex' Clark and contributors. Pillow の wheel に含まれる追加ライブラリの通知は、[原文全体](licenses/Pillow-LICENSE.txt)に収録しています。このソフトウェアは、一部に FreeType Team と Independent JPEG Group の成果を使用しています。

six: Copyright (c) 2010–2024 Benjamin Peterson.

Python、Tcl/Tk、PyInstaller と各ライブラリのその他の著作権表示・条件・免責事項は、それぞれの同梱原文を参照してください。PyInstaller の原文には、配布実行ファイルへ組み込む bootloader に関する例外、および実行時フック等の Apache 2.0 条件が含まれています。

## ソースの入手と変更版による再ビルド

アプリのソースとビルド定義は [345sugar/mimamori-breach](https://github.com/345sugar/mimamori-breach) にあります。Windows のフル版 Python 3.11 以上と tkinter を用意し、リポジトリのフォルダーで実行します。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install '.[build]'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --windowed --onedir --name MimamoriBreach --paths src launcher.py
.\.venv\Scripts\python.exe scripts/collect_bundle_materials.py
```

この PyInstaller コマンドは [Windows ビルド定義](.github/workflows/checks.yml) と同じです。結果は `dist\MimamoriBreach\` に作成されます。最後のスクリプトで説明書・ライセンス・使用した pystray の Python ソースとメタデータを同梱します。ビルドに使った Python 環境で実行してください。実行ファイルだけでなく、隣のファイルもまとめて使用します。

### ZIP に同梱する pystray ソース

配布 ZIP の `MimamoriBreach/third_party_sources/pystray/` は、ビルド環境で使った pystray の `.py` ファイルをサブフォルダーごとコピーしたものです。`__pycache__` は含めません。`third_party_sources/pystray-METADATA.txt` にパッケージ情報、`recorded-versions.json` に実際のパッケージバージョンと各ソースファイルの SHA-256 を記録します。

この同梱ソースを変更して再ビルドする場合は、アプリのリポジトリ内に `replacement_sources/pystray/` としてコピーし、編集してください。依存関係をインストールした後、次の例で変更したソースを仮想環境へコピーします。下のコマンドはリポジトリのフォルダーで実行します。

```powershell
.\.venv\Scripts\python.exe -c "from importlib import metadata; from pathlib import Path; import shutil; source=Path('replacement_sources/pystray'); assert (source/'__init__.py').is_file(); target=Path(metadata.distribution('pystray').locate_file('pystray')); shutil.copytree(source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))"
```

その後、上記のテスト・PyInstaller・`collect_bundle_materials.py` を再実行してください。モジュールを削除する変更をした場合は、仮想環境側の対応するモジュールも取り除いてからビルドしてください。

### 上流のソース配布物

pystray 0.19.5 のソース配布物は、上記リポジトリまたは次のコマンドで取得できます。

```powershell
.\.venv\Scripts\python.exe -m pip download --no-binary=:all: --no-deps pystray==0.19.5 --dest vendor-sources
```

展開した pystray を変更して組み込む場合は、アプリの依存関係をインストールした**後**に、変更版を同じ仮想環境へインストールし、上記 PyInstaller コマンドを再実行します。

```powershell
# 実際に変更した pystray のソースフォルダーを指定してください。
.\.venv\Scripts\python.exe -m pip install --no-deps --force-reinstall 'C:\path\to\modified-pystray'
```

元のアプリのソースを変更する場合も同じ方法でビルドできます。配布パッケージは起動時に元のライブラリの署名やハッシュ一致を要求しません。変更内容・ライセンス原文・この文書を、変更版と一緒に保存してください。

## 原文の取得元

- pystray: インストール済み `pystray-0.19.5.dist-info/COPYING` と `COPYING.LGPL`。
- Pillow: `pillow-12.3.0.dist-info/licenses/LICENSE`。MIT-CMU 本文を含め、同梱された追加ライブラリの通知を省略せずにコピー。
- six: `six-1.17.0.dist-info/LICENSE`。
- PyInstaller: `pyinstaller-6.22.3.dist-info/licenses/COPYING.txt`。
- Python: ビルドに使った Python 配布物の `LICENSE.txt`。
- Tk: 同じ Python 配布物の `tcl/tk8.6/license.terms`。
- Tcl: 対応する [公式ソースの 8.6.12 ライセンス](https://raw.githubusercontent.com/tcltk/tcl/core-8-6-12/license.terms)。

## Breach data

漏洩情報の提供元は [Have I Been Pwned](https://haveibeenpwned.com/) です。データには [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) が適用されます。アプリはデータの一部を選択して表示し、表示用の状態・対応メモを追加します。デモの記録は本プロジェクトが作成した架空データです。
