import tempfile
import unittest
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from scripts.prepare_hn import extract

class HNPreparationTests(unittest.TestCase):
 def test_preserves_parent_and_provenance_and_filters(self):
  table=pa.table({"id":["100","101","102"],"deleted":[0,0,0],"type":[1,2,1],"by":["author","commenter","other"],"time":["2026-08-01T00:00:00Z"]*3,"text":[None,"A phishing incident exposed credentials; patch the affected service.",None],"dead":[0,0,0],"parent":[None,100,None],"poll":[None,None,None],"kids":[[101],[],[]],"url":[None,None,None],"score":[5,1,2],"title":["Security incident report",None,"Gardening tools"],"parts":[[],[],[]],"descendants":[1,0,0],"words":[[],[],[]]})
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"hn.parquet";pq.write_table(table,p);rows,total=extract(p)
  self.assertEqual(total,3);self.assertEqual(len(rows),2)
  comment=next(row for row in rows if row["parent_id"]==100)
  self.assertEqual(comment["author"],"commenter");self.assertIn("news.ycombinator.com/item?id=101",comment["source_url"])
  self.assertTrue(comment["license"].startswith("ODC-By 1.0"))
if __name__=="__main__":unittest.main()
