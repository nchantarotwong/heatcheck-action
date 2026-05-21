# macOS release signing & notarization

The `release.yml` workflow signs and notarizes the macOS build so that
people can download and run `heatcheck` on a Mac without Gatekeeper
blocking it. This is a **one-time setup** of an Apple Developer ID
identity plus repository secrets; after that, every tagged release is
signed automatically.

## What gets produced

Each tagged release publishes, for `darwin-arm64`:

| Asset | Signed | Notarized | Stapled | Who uses it |
|---|---|---|---|---|
| `heatcheck-darwin-arm64` (bare binary) | ✅ Developer ID Application | ✅ | ❌ (can't staple a bare Mach-O) | the GitHub Action + `curl`/script installs |
| `heatcheck-darwin-arm64.pkg` (installer) | ✅ Developer ID Installer | ✅ | ✅ | humans who download from the Releases page in a browser |

Why two artifacts:

- **The GitHub Action and `curl` installers keep using the bare
  binary** — unchanged. Those download paths don't set the
  `com.apple.quarantine` xattr, so Gatekeeper never blocks them. The
  binary is still signed + notarized (cheap, strictly better; the
  online notarization check passes if quarantine ever does apply).
- **A browser download of the bare binary IS quarantined**, and a bare
  Mach-O can't be stapled, so a fully-offline Mac could still see a
  warning. The **`.pkg` is stapled**, so double-clicking it installs
  `heatcheck` to `/usr/local/bin` with zero Gatekeeper friction, online
  or offline. That's the artifact to hand a design partner.

## Where each step runs

The build and the signing both happen **in CI** — on the `macos-14`
GitHub Actions runner, automatically, on every tagged release. You do
not build or sign anything locally.

The **only** local work is a one-time *minting* of the signing
certificate, because a code-signing cert is bound to a private key that
must originate on a machine you control, and Apple issues it through an
interactive portal flow tied to your account. You mint it once on your
Mac, export it as a `.p12`, and store it (base64) as a GitHub secret.
From then on CI imports that secret and does all the actual signing
itself — the cert is valid ~5 years and reused for every release.

```
  YOU, once, on your Mac           CI, every release (macos-14 runner)
  ----------------------           -----------------------------------
  generate CSR → get certs
  export .p12 (cert + key)   ─────►  import .p12 from secret
  base64 → GitHub secrets             codesign + notarize binary
                                      pkgbuild + productsign + staple .pkg
                                      upload signed assets
```

## Prerequisites

- A paid Apple Developer account ($99/yr).
- A Mac (to mint the cert once via Keychain Access). The release
  *builds* run on GitHub's macOS runners, not your machine.

## One-time setup (local — minting the credential)

### 1. Create the two certificates

In the [Apple Developer portal](https://developer.apple.com/account/resources/certificates/list)
→ Certificates → **+**:

1. **Developer ID Application** — signs the binary.
2. **Developer ID Installer** — signs the `.pkg`.

What matters is the certificate **type** — pick exactly those two.
Do *not* pick *Apple Distribution*, *Mac App Distribution*, *Mac
Installer Distribution*, or *Apple Development*; those are for the App
Store / dev provisioning and the notary service rejects them for
Developer-ID-distribution-outside-the-store.

When the portal offers a **profile / Sub-CA** choice, use the **G2
Sub-CA** ("Developer ID Certification Authority (G2)"). It's Apple's
current default intermediate for newly-issued Developer ID certs and is
the forward-looking pick. The only caveat: certs chained through G2
require that intermediate in the verifying Mac's trust store — modern
macOS (12+) ships it, and the notarized + stapled `.pkg` embeds the
full chain, so it's a non-issue for the install path partners use.

Each cert is issued from a **Certificate Signing Request (CSR)** you
generate on your Mac. **Apple enforces one CSR per certificate** — you
cannot reuse a CSR (the portal rejects it with "The uploaded CSR file
has already been used to generate another certificate"), so generate a
**separate CSR for each** of the two certs.

For each cert:

1. Open **Keychain Access** → menu **Certificate Assistant → Request a
   Certificate From a Certificate Authority…**
2. **User Email Address** = your Apple ID; **Common Name** = something
   that tells the two apart (e.g. `… Developer ID Application` vs `…
   Developer ID Installer`); **CA Email Address** = *blank*; **Request
   is** = **Saved to disk**.
3. Save the `.certSigningRequest` file.
4. In the portal, upload that `.csr`, download the issued `.cer`, and
   import it into your **login** keychain.

Importing reliably — double-clicking the `.cer` can fail with
`-25294` (`errSecNoSuchKeychain`) even on a healthy setup; the explicit
CLI import sidesteps that GUI quirk:

```bash
security import ~/Downloads/<the>.cer -k ~/Library/Keychains/login.keychain-db
```

Each CSR creates its own private key in your keychain, and each issued
cert pairs with the key from its CSR. The private keys stay in your
keychain; they're what you export as the `.p12` next (which is why you
must export each cert *with its private key* — see step 2). After both
imports, verify:

```bash
security find-identity -v -p codesigning | grep "Developer ID Application"
security find-identity -v | grep "Developer ID Installer"
```

### 2. Export each as a `.p12`

In **Keychain Access** → login keychain → My Certificates: select the
certificate **with its private key disclosure triangle expanded**
(you must export cert + key together), right-click → *Export*, choose
`.p12`, set an export password. Do this for **both** certs.

```bash
# base64-encode each .p12 for storage as a GitHub secret
base64 -i DeveloperID_Application.p12 | pbcopy   # → MACOS_CERT_P12_BASE64
base64 -i DeveloperID_Installer.p12  | pbcopy   # → MACOS_INSTALLER_CERT_P12_BASE64
```

### 3. Create an app-specific password for notarization

At [appleid.apple.com](https://appleid.apple.com) → Sign-In and
Security → App-Specific Passwords → **+**. Label it e.g.
`heatcheck-notary`. Copy the generated password (`xxxx-xxxx-xxxx-xxxx`).

### 4. Find your Team ID

Apple Developer portal → Membership → **Team ID** (10-char string like
`A1B2C3D4E5`). Or:

```bash
xcrun notarytool store-credentials --help   # the team id is shown in any notarytool example
# or, from an installed cert:
security find-identity -v -p codesigning | grep "Developer ID"
# → the (XXXXXXXXXX) suffix on the identity name is the Team ID
```

### 5. Add the repository secrets

On **github.com/nchantarotwong/heatcheck-action** → Settings → Secrets
and variables → Actions → New repository secret. Add all seven:

| Secret | Value |
|---|---|
| `MACOS_CERT_P12_BASE64` | base64 of the Developer ID **Application** `.p12` |
| `MACOS_CERT_PASSWORD` | export password for that `.p12` |
| `MACOS_INSTALLER_CERT_P12_BASE64` | base64 of the Developer ID **Installer** `.p12` |
| `MACOS_INSTALLER_CERT_PASSWORD` | export password for that `.p12` |
| `MACOS_NOTARY_APPLE_ID` | your Apple ID email |
| `MACOS_NOTARY_PASSWORD` | the app-specific password from step 3 |
| `MACOS_NOTARY_TEAM_ID` | your 10-char Team ID |

Until these exist, `release.yml` ships the **unsigned** bare binary and
no `.pkg` (it logs a `::warning::` and continues — releases don't
break). The moment all seven are set, the next tagged release is
signed end to end.

## Re-release the current version

The signing only applies to builds that run *after* the secrets exist.
To sign the version you already shipped, re-run the release for its
tag:

```bash
# Option A — re-run the existing tag's release workflow from the UI:
#   Actions → release → Run workflow → set release-tag to the version,
#   heat-ref to the same Heat commit that version was built from.

# Option B — delete + re-push the tag (forces a fresh release.yml run):
git -C <heatcheck-action> push origin :refs/tags/vX.Y.Z   # delete remote tag
git -C <heatcheck-action> tag -d vX.Y.Z                    # delete local
git -C <heatcheck-action> tag vX.Y.Z <commit>              # re-create
git -C <heatcheck-action> push origin vX.Y.Z               # re-trigger build
```

The release upload uses `--clobber`, so re-running overwrites the
existing assets in place with the signed versions.

## Verify a release

After a signed release, download the assets and check:

```bash
# Bare binary — signed + notarized (online check)
codesign -dvvv ./heatcheck-darwin-arm64 2>&1 | grep -E 'Authority|TeamIdentifier|flags'
spctl -a -vvv -t install ./heatcheck-darwin-arm64    # may report "no usable signature" for a bare CLI — expected; the .pkg is the Gatekeeper-clean artifact

# .pkg — signed + notarized + stapled (fully offline-clean)
pkgutil --check-signature ./heatcheck-darwin-arm64.pkg
xcrun stapler validate ./heatcheck-darwin-arm64.pkg   # → "The validate action worked!"
spctl -a -vvv -t install ./heatcheck-darwin-arm64.pkg # → "accepted; source=Notarized Developer ID"
```

## Notes & gotchas

- **A bare Mach-O cannot be stapled** (`stapler` only handles
  `.app` / `.dmg` / `.pkg`). The binary's notarization ticket lives on
  Apple's servers; Gatekeeper fetches it on first run *if* the file is
  quarantined. For a fully-offline + browser-quarantined Mac, hand them
  the `.pkg` (stapled) or have them run
  `xattr -dr com.apple.quarantine ./heatcheck` once.
- **Notarization is asynchronous**; `notarytool ... --wait` blocks
  until Apple finishes (typically 1–5 min, occasionally longer). The
  release job will sit on that step.
- **Hardened runtime** (`--options runtime`) is required for
  notarization to accept the binary. It's already set in the workflow.
- **Cert expiry**: Developer ID certs are valid 5 years. When one
  expires, re-do steps 1–2 and update the two `*_P12_BASE64` /
  `*_PASSWORD` secrets. The app-specific password and Team ID don't
  expire.
- The Linux assets and the container image are **not** signed — they
  don't need it (no Gatekeeper).
