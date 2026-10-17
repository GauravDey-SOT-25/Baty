# Firebase Google sign-in and optional assistant backup

The local app includes Google sign-in through Firebase Authentication, an explicitly opt-in Realtime Database backup for assistant exchanges, and an optional path to authenticate requests to the separate Modal inference preview. The app still binds to `127.0.0.1`; Firebase does not move the local model or security-record corpus to the cloud.

## Data flow and privacy

- Signing in identifies the user with Firebase Authentication. Local message analysis, passive URL checks, local retrieval, and model inference remain available without an account.
- Cloud sync is unchecked and disabled until sign-in. After sign-in, the user must check the consent box. Only subsequent Learning assistant questions, answers, answer-basis labels, and Firebase timestamps are saved under `users/{Firebase UID}/assistantHistory`.
- Message text, sender details, submitted URLs, incident searches, and Web Research activity are not saved by this integration.
- The Account & sync panel reads at most the 25 most recent saved exchanges. “Delete my cloud assistant history” removes that user's entire history. Cloud copies persist until the user deletes them; a new device/session may see them after opting into sync.
- Firebase browser configuration is client-visible project metadata, not an Admin credential. Never put a service-account key or Firebase Admin credential in this browser app.
- When **Use the Modal cloud model** is selected, the local API sends the question and Firebase ID token to Modal. Modal verifies the signed token and checks that it belongs to project `baty-ac397` and a verified Google sign-in. The Modal Proxy Token remains on the local server and is never exposed to the browser. Cloud model use is independent of Realtime Database backup consent.

The behavior follows Firebase's [Google sign-in for web](https://firebase.google.com/docs/auth/web/google-signin), [Realtime Database web read/write](https://firebase.google.com/docs/database/web/read-and-write), and [Realtime Database security rules](https://firebase.google.com/docs/database/security) guidance. Authentication and rule deployment were not verified against the live Firebase Console in this workspace.

## Firebase Console setup

In project `baty-ac397`:

1. In **Authentication → Sign-in method**, enable **Google** and select the support email.
2. In **Authentication → Settings → Authorized domains**, make sure the browser's host is listed. The live project config currently lists `localhost` but not `127.0.0.1`; use `http://localhost:8765` with this app, or add `127.0.0.1` in Firebase Console before using that address. The local server accepts both exact loopback Hostnames while still binding only to `127.0.0.1`.
3. Confirm that Realtime Database exists at `https://baty-ac397-default-rtdb.firebaseio.com`.
4. Review the currently deployed database rules before changing them. Merge any required existing rules; do not blindly replace remote rules.

The local Firebase project files are `.firebaserc`, `firebase.json`, and `database.rules.json`. The checked-in rules deny access at the root and grant each authenticated UID access only to their own assistant-history path, validate field types/lengths, and cap each user's exchanges at 200. A deploy replaces the remote database rules, so after reviewing and merging any existing rules, deploy intentionally with:

```sh
firebase deploy --only database --project baty-ac397
```

The Firebase CLI is not installed in the inspected environment, and no remote rules were read or deployed. Google provider/domain settings are required for sign-in. Compatible database rules are required only for the optional database backup. The supplied API key is a public web-app key; rely on Firebase Authentication and database rules for data access control and apply suitable API restrictions in Google Cloud where supported.

## Local verification

Run the local app as documented in the README, open the account panel, and verify the following only after completing the Console setup:

1. The app loads with local features available while signed out.
2. Google sign-in succeeds for an authorized local host.
3. No data is saved while the consent box is unchecked.
4. After opting in, one harmless assistant question appears in the signed-in user's history and is visible only to that UID.
5. Turning sync off stops later writes; deletion removes that user's history.

Do not use private incident details or sensitive prompts in cloud-sync checks. Tests in this repository validate static wiring and local HTTP serving; they do not authenticate with Google or prove the deployed Firebase rules.
