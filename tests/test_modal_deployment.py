import ast
import re
import unittest
from pathlib import Path


DEPLOYMENT = Path(__file__).resolve().parents[1] / "deploy" / "modal_app.py"


class ModalDeploymentConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = DEPLOYMENT.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source)

    def test_model_revision_is_pinned(self):
        assignments = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in self.tree.body
            if isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
        }
        self.assertEqual(assignments["MODEL_ID"], "Qwen/Qwen2.5-1.5B-Instruct")
        self.assertRegex(assignments["MODEL_REVISION"], re.compile(r"^[0-9a-f]{40}$"))

    def test_cpu_deployment_selects_cpu_only_pytorch_wheel(self):
        self.assertIn('"torch==2.14.1+cpu"', self.source)
        self.assertIn('extra_index_url="https://download.pytorch.org/whl/cpu"', self.source)

    def test_web_endpoint_requires_modal_proxy_auth(self):
        self.assertIn("@modal.asgi_app(requires_proxy_auth=True)", self.source)
        self.assertIn('"google-auth==2.62.0"', self.source)
        self.assertIn("verify_firebase_id_token(token, FIREBASE_PROJECT_ID)", self.source)
        self.assertIn("MAX_REQUESTS_PER_UID_PER_MINUTE = 3", self.source)

    def test_remote_image_does_not_package_local_artifacts(self):
        forbidden = ("add_local_dir", "adapters/", "data/processed", "Secret.from_dotenv")
        for value in forbidden:
            with self.subTest(value=value):
                self.assertNotIn(value, self.source)

    def test_cloud_inference_is_resource_bounded(self):
        self.assertIn("max_containers=1", self.source)
        self.assertIn("MAX_BODY_BYTES = 16 * 1024", self.source)
        self.assertIn("MAX_NEW_TOKENS = 128", self.source)

    def test_model_cache_volume_is_created_only_by_modal_deployment(self):
        self.assertIn('modal.Volume.from_name("cyber-qwen-hf-cache", create_if_missing=True)', self.source)
        self.assertNotIn("modal.Volume.from_name(\"cyber-qwen-hf-cache\", create_if_missing=False)", self.source)

    def test_deploy_helper_checks_auth_without_printing_token_details(self):
        helper = DEPLOYMENT.with_name("post_to_modal.sh").read_text(encoding="utf-8")
        self.assertIn('"$PYTHON" -m modal token info >/dev/null 2>&1', helper)
        self.assertIn('exec "$PYTHON" -m modal deploy deploy/modal_app.py', helper)

    def test_fastapi_request_body_is_parsed_explicitly(self):
        self.assertIn("question_request = Question.model_validate(body)", self.source)
        self.assertIn('answer.__annotations__["request"] = Request', self.source)
        self.assertIn('api.post("/api/assistant")(answer)', self.source)


if __name__ == "__main__":
    unittest.main()
