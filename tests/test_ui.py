import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class UITests(unittest.TestCase):
 def test_ui_handlers_are_external_to_match_csp(self):
  page=(ROOT/"frontend/index.html").read_text();script=(ROOT/"frontend/app.js").read_text()
  self.assertIn('script src="/app.js"',page)
  self.assertNotIn("onclick=",page)
  for endpoint in ("/api/message","/api/url","/api/assistant","/api/incidents"):
   self.assertIn(endpoint,script)
if __name__=="__main__":unittest.main()
