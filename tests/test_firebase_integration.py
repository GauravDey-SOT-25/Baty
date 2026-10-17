import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FirebaseIntegrationTests(unittest.TestCase):
    def test_database_policy_is_private_and_uid_scoped(self):
        policy = json.loads((ROOT / "database.rules.json").read_text())['rules']
        self.assertIs(policy['.read'], False)
        self.assertIs(policy['.write'], False)
        history = policy['users']['$uid']['assistantHistory']
        self.assertIn('auth.uid === $uid', history['.read'])
        self.assertIn('auth.uid === $uid', history['.write'])
        self.assertEqual(history['.validate'], 'newData.numChildren() <= 200')
        entry = history['$entryId']['.validate']
        for field, limit in (("question", 8000), ("answer", 12000), ("answerBasis", 80)):
            self.assertIn(f"child('{field}').val().length <= {limit}", entry)

    def test_web_client_is_opt_in_and_uses_only_user_scoped_qa_history(self):
        client = (ROOT / "frontend/firebase-app.js").read_text()
        page = (ROOT / "frontend/index.html").read_text()
        self.assertIn("users/${currentUser.uid}/assistantHistory", client)
        self.assertIn("if (!currentUser || !cloudSyncEnabled) return false", client)
        self.assertRegex(page, r'<input id="cloud-sync" type="checkbox"[^>]*disabled')
        self.assertIn("message text, sender details, URLs, incident searches, and research activity are not synced", page)
        self.assertNotIn("getAnalytics", client)

    def test_public_firebase_config_matches_project_files(self):
        client = (ROOT / "frontend/firebase-app.js").read_text()
        cli = json.loads((ROOT / ".firebaserc").read_text())
        firebase = json.loads((ROOT / "firebase.json").read_text())
        self.assertEqual(cli['projects']['default'], 'baty-ac397')
        self.assertEqual(firebase['database']['rules'], 'database.rules.json')
        self.assertIn("databaseURL: 'https://baty-ac397-default-rtdb.firebaseio.com'", client)
        self.assertRegex(client, r"apiKey: 'AIza[^']+'")


if __name__ == '__main__':
    unittest.main()
