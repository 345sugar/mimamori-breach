# Mimamori Breach

A small Windows tray app that helps you follow breach records associated with your own email address. Breach data is provided by [Have I Been Pwned](https://haveibeenpwned.com/) (HIBP).

[日本語](README.md) · [Privacy](PRIVACY.md) · [Security](SECURITY.md) · [Contributing](CONTRIBUTING.md)

## Initial feature set

- Monitor one email address, approximately daily while the app is running and the PC is awake.
- Check manually and distinguish failed checks from successful checks with no known matches.
- See breach titles, dates and affected data classes; mark records as acknowledged.
- Receive generic tray notifications that omit the email address and breached service names.
- Store settings and history with current-user Windows DPAPI encryption.
- Try an offline demo using synthetic, in-memory records.

The first successful check may show historical records. A newly displayed record means it is new to the app, not that a new attack just occurred. Acknowledging a record only changes your local checklist.

## Run from source

Use Windows with Python 3.11 or later, including tkinter. From the repository directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m mimamori_breach --demo
```

The demo makes no API requests and does not read or write real settings. Start without `--demo` to configure your own account:

```powershell
.\.venv\Scripts\python.exe -m mimamori_breach
```

Normal email lookups require your own [paid HIBP API key](https://haveibeenpwned.com/API/Key). Enter the email and key in Settings, accept the disclosure that the full email address is sent to HIBP, confirm that you use your own API subscription and bear its costs, and enable monitoring. Both manual and automatic lookups require the key, disclosure consent and cost confirmation. Existing saved settings also require the new cost confirmation before lookups resume. Automatic checks additionally require monitoring to be enabled. This version uses direct email lookup, not email hash ranges. See the [HIBP API documentation](https://haveibeenpwned.com/API/v3).

Closing the window keeps the app in the tray when a tray icon is available. Use the explicit Quit command to stop it. Disabling monitoring keeps your history. The app does not register itself to start when you sign in to Windows.

### Who pays for the API?

Each user brings their own API key (BYOK), and their device connects directly to HIBP. No maintainer key is bundled or shared, and there is no maintainer-operated paid API relay. Other users' API usage therefore does not accrue charges to the maintainer through this app.

The user who configures a key is responsible for their own paid HIBP subscription. The app does not automatically purchase or subscribe to anything. **The free demo needs no key, network requests or subscription, and generates no billable API usage from this app.** Stopping or deleting the app does not cancel a separate HIBP subscription.

## Scope and privacy

This app checks known breach records. It cannot block attacks, detect all leaks or prove that your current password is compromised. HIBP coverage is incomplete; sensitive, retired and unverified records are excluded from this app's lookup. See the [HIBP FAQ](https://haveibeenpwned.com/FAQs) and [API documentation](https://haveibeenpwned.com/API/v3).

The app collects no passwords or browser history. Its encrypted local state is stored at `%LOCALAPPDATA%\MimamoriBreach\state.bin`. DPAPI does not protect against malware running as the same Windows user. Read [PRIVACY.md](PRIVACY.md) for the data flow and deletion instructions.

## Windows builds

The Windows GitHub Actions build produces an artifact ZIP. Extract it and run `MimamoriBreach.exe` inside the `MimamoriBreach` directory. Keep the bundled files together. This early build is not a signed installer.

Double-click `Demo.cmd` in the same directory to try synthetic data without an API key or network requests.

When rebuilding, run `python scripts/collect_bundle_materials.py` in the build environment after PyInstaller to include documentation, licenses and the pystray source used by that build. See [rebuild instructions](THIRD_PARTY_NOTICES.md).

## Project status and attribution

Maintained by [345sugar](https://github.com/345sugar), with AI implementation assistance. This is an early development project; no independent security audit or certification is claimed. Report bugs using synthetic examples, without email addresses, API keys or personal breach histories.

Source code: [MIT](LICENSE). Dependency licenses and rebuild instructions: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Breach data: [Have I Been Pwned](https://haveibeenpwned.com/), under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). This project is not an official HIBP product.
