import os
import urllib.error
import json
import threading
import tempfile
import urllib.request
import unittest
from pathlib import Path
from unittest.mock import patch

from src.research.parallel_client import (
    ConfigurationError,
    ParallelProvider,
    ProviderError,
    _map_task_status,
    _normalise_task_output,
)
from src.research.provider import MonitorRecord, ResearchTaskRecord
from src.research.ssrf_guard import SSRFError, validate_extract_url, validate_extract_urls
from src.research import service, task_store


class ParallelProviderTests(unittest.TestCase):
    def test_responses_quick_answer_parses_annotations_and_uses_bearer_auth(self):
        client = object.__new__(ParallelProvider)
        client._api_key = "test-key"
        payload = {"id": "resp_1", "output": [{"type": "message", "content": [{
            "type": "output_text", "text": "Patch the affected server.",
            "annotations": [
                {"type": "url_citation", "url": "https://vendor.example/advisory", "title": "Vendor"},
                {"type": "url_citation", "url": "javascript:alert(1)", "title": "bad"},
                {"type": "url_citation", "url": "https://vendor.example/advisory", "title": "duplicate"},
            ],
        }]}]}
        with patch.object(client, "_post", return_value=payload) as post:
            result = client.quick_answer("How to mitigate this?", "medium")
        self.assertEqual(post.call_args.args, ("/v1/responses", {
            "model": "parallel", "input": "How to mitigate this?", "reasoning": {"effort": "medium"}
        }))
        self.assertEqual(post.call_args.kwargs, {"bearer": True, "timeout": 120})
        self.assertEqual(result["answer"], "Patch the affected server.")
        self.assertEqual(result["citations"], [{"url": "https://vendor.example/advisory", "title": "Vendor"}])

    def test_responses_quick_answer_rejects_empty_provider_answer(self):
        client = object.__new__(ParallelProvider)
        with patch.object(client, "_post", return_value={"output": []}):
            with self.assertRaisesRegex(ProviderError, "no answer text"):
                client.quick_answer("question")

    def test_findall_endpoints_use_beta_contract_and_escape_run_id(self):
        client = object.__new__(ParallelProvider)
        with patch.object(client, "_post", side_effect=[{"entity_type": "vulnerabilities"}, {"findall_id": "fa_1"}]) as post, \
             patch.object(client, "_get", side_effect=[{"status": {"status": "completed"}}, {"candidates": []}]) as get:
            self.assertEqual(client.findall_ingest("Find vulnerabilities"), {"entity_type": "vulnerabilities"})
            self.assertEqual(client.findall_create({"objective": "Find vulnerabilities"}), {"findall_id": "fa_1"})
            status = client.findall_status("fa_1", include_result=True)
        self.assertEqual(post.call_args_list[0].args[0], "/v1beta/findall/ingest")
        self.assertEqual(post.call_args_list[1].args[0], "/v1beta/findall/runs")
        self.assertEqual(get.call_args_list[0].args[0], "/v1beta/findall/runs/fa_1")
        self.assertEqual(get.call_args_list[1].args[0], "/v1beta/findall/runs/fa_1/result")
        self.assertIn("result", status)

    def test_missing_credentials_are_clear(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "PARALLEL_API_KEY"):
                ParallelProvider()

    def test_search_uses_supported_request_fields_and_preserves_citations(self):
        client = object.__new__(ParallelProvider)
        with patch.object(client, "_post", return_value={
            "search_id": "search-1",
            "results": [
                {"title": "Vendor advisory", "url": "https://vendor.example/advisory", "publish_date": "2026-10-17", "excerpts": ["Patch released"]},
                {"title": "Second", "url": "https://second.example/", "excerpts": []},
            ],
        }) as post:
            response = client.search("latest product vulnerability", search_queries=["vendor product vulnerability"], max_results=1)
        body = post.call_args.args[1]
        self.assertEqual(set(body), {"objective", "search_queries", "max_chars_total"})
        self.assertEqual(len(response.results), 1)
        self.assertEqual(response.results[0].url, "https://vendor.example/advisory")
        self.assertEqual(response.results[0].publish_date, "2026-10-17")

    def test_task_result_uses_distinct_status_and_result_calls_without_blocking(self):
        client = object.__new__(ParallelProvider)
        record = ResearchTaskRecord(task_id="task_local", question="Research CVE", provider_run_id="trun_abc", status="pending")
        response = {"output": {"type": "text", "content": "A cited report.", "basis": [{"field": "finding", "citations": [{"title": "Vendor", "url": "https://vendor.example/report", "publish_date": "2026-10-17"}]}]}}
        with patch.object(client, "_get", side_effect=[{"status": "completed"}, response]) as get, \
             patch("src.research.parallel_client.task_store.update_task"):
            updated = client.get_task_result(record)
        self.assertEqual(get.call_args_list[0].args[0], "/v1/tasks/runs/trun_abc")
        self.assertEqual(get.call_args_list[1].args[0], "/v1/tasks/runs/trun_abc/result")
        self.assertEqual(updated.status, "completed")
        self.assertEqual(updated.result["sources"][0]["url"], "https://vendor.example/report")

    def test_transient_poll_failure_keeps_task_pollable(self):
        client = object.__new__(ParallelProvider)
        record = ResearchTaskRecord(task_id="task_local", question="Research CVE", provider_run_id="trun_abc", status="running")
        with patch.object(client, "_get", side_effect=ProviderError("timeout")), \
             patch("src.research.parallel_client.task_store.update_task"):
            updated = client.get_task_result(record)
        self.assertEqual(updated.status, "running")
        self.assertIn("unavailable", updated.error_message)

    def test_monitor_uses_current_create_and_cancel_contract(self):
        client = object.__new__(ParallelProvider)
        record = MonitorRecord(monitor_id="local-monitor", query="CVE advisories")
        with patch("src.research.parallel_client.task_store.create_monitor", return_value=record), \
             patch("src.research.parallel_client.task_store.update_monitor"), \
             patch.object(client, "_post", return_value={"monitor_id": "mon_remote", "status": "active"}) as post:
            created = client.create_monitor("CVE advisories")
        self.assertEqual(post.call_args.args[0], "/v1/monitors")
        self.assertEqual(post.call_args.args[1], {"type": "event_stream", "frequency": "1d", "settings": {"query": "CVE advisories"}})
        self.assertEqual(created.provider_monitor_id, "mon_remote")
        with patch("src.research.parallel_client.task_store.get_monitor", return_value=created), \
             patch("src.research.parallel_client.task_store.delete_monitor", return_value=True), \
             patch.object(client, "_post", return_value={}) as post:
            self.assertTrue(client.delete_monitor("local-monitor"))
        self.assertEqual(post.call_args.args[0], "/v1/monitors/mon_remote/cancel")

    def test_monitor_events_preserve_source_citations(self):
        client = object.__new__(ParallelProvider)
        monitor = MonitorRecord(monitor_id="monitor_" + "a" * 32, query="vendor advisory", provider_monitor_id="mon_remote")
        with patch.object(client, "_get", return_value={"events": [{
            "event_id": "evt1", "event_date": "2026-10-17", "event_type": "event_stream",
            "output": {"content": "A new vendor advisory.", "basis": [{"citations": [{"title": "Vendor notice", "url": "https://vendor.example/notice"}]}]},
        }]}) as get:
            result = client.get_monitor_events(monitor)
        self.assertEqual(get.call_args.args[0], "/v1/monitors/mon_remote/events?limit=20")
        self.assertEqual(result["events"][0]["sources"][0]["url"], "https://vendor.example/notice")

    def test_task_status_mapping_and_citation_normalization(self):
        self.assertEqual(_map_task_status("queued"), "pending")
        self.assertEqual(_map_task_status("completed"), "completed")
        result = _normalise_task_output({"content": "Summary", "basis": [{"field": "x", "citations": [{"url": "https://source.example/x", "title": "Source"}]}]}, "question")
        self.assertEqual(result["sources"][0]["url"], "https://source.example/x")

    def test_provider_translates_rate_limits_and_timeouts(self):
        client = object.__new__(ParallelProvider)
        req = __import__("urllib.request").request.Request("https://api.parallel.ai/v1/search")
        error = urllib.error.HTTPError(req.full_url, 429, "busy", {}, None)
        self.addCleanup(error.close)
        with patch("src.research.parallel_client.urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(ProviderError, "Rate limit"):
                client._send(req, "/v1/search")
        with patch("src.research.parallel_client.urllib.request.urlopen", side_effect=TimeoutError()):
            with self.assertRaisesRegex(ProviderError, "timed out"):
                client._send(req, "/v1/search")

    def test_provider_does_not_expose_invalid_credential_response_body(self):
        client = object.__new__(ParallelProvider)
        req = urllib.request.Request("https://api.parallel.ai/v1/search")
        error = urllib.error.HTTPError(req.full_url, 401, "unauthorized", {}, None)
        self.addCleanup(error.close)
        with patch("src.research.parallel_client.urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(ProviderError, "Invalid or missing API key") as raised:
                client._send(req, "/v1/search")
        self.assertNotIn("secret", str(raised.exception).lower())

    def test_provider_rejects_non_object_json_and_handles_unknown_task_status(self):
        client = object.__new__(ParallelProvider)
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size): return b'["unexpected"]'
        req = urllib.request.Request("https://api.parallel.ai/v1/search")
        with patch("src.research.parallel_client.urllib.request.urlopen", return_value=Response()):
            with self.assertRaisesRegex(ProviderError, "JSON object"):
                client._send(req, "/v1/search")
        self.assertEqual(_map_task_status(None), "running")

    def test_provider_normalizes_billing_forbidden_validation_and_server_errors(self):
        client = object.__new__(ParallelProvider)
        req = urllib.request.Request("https://api.parallel.ai/v1/search")
        expected = {
            402: "insufficient credits", 403: "rejected the request",
            408: "timed out", 422: "validation error", 500: "server error",
        }
        for status, message in expected.items():
            with self.subTest(status=status):
                error = urllib.error.HTTPError(req.full_url, status, "provider detail secret", {}, None)
                with patch("src.research.parallel_client.urllib.request.urlopen", side_effect=error):
                    with self.assertRaisesRegex(ProviderError, message) as raised:
                        client._send(req, "/v1/search")
                self.assertNotIn("secret", str(raised.exception).lower())
                error.close()


class ResearchServiceTests(unittest.TestCase):
    def tearDown(self):
        service._get_provider.cache_clear()

    def test_local_fallback_selected_without_credentials(self):
        service._get_provider.cache_clear()
        with patch.dict(os.environ, {}, clear=True):
            status = service.get_provider_status()
        self.assertEqual(status["mode"], "local-only")
        self.assertFalse(status["api_key_configured"])

    def test_quick_answer_requires_parallel_and_valid_effort(self):
        with patch("src.research.service._get_provider", return_value=type("Local", (), {"name": lambda self: "local"})()):
            self.assertIn("PARALLEL_API_KEY", service.quick_answer("Question")['error'])
        with patch("src.research.service._get_provider") as provider:
            self.assertIn("effort must", service.quick_answer("Question", "turbo")['error'])
        provider.assert_not_called()

    def test_quick_answer_passes_question_to_parallel_provider(self):
        class FakeProvider:
            def name(self): return "parallel"
            def quick_answer(self, question, effort):
                return {"answer": question, "citations": [], "effort": effort}
        with patch("src.research.service._get_provider", return_value=FakeProvider()):
            self.assertEqual(service.quick_answer("Explain MFA", "high"), {
                "answer": "Explain MFA", "citations": [], "effort": "high"
            })

    def test_findall_validates_preview_and_match_criteria(self):
        with patch("src.research.service._get_provider") as provider:
            bad = service.findall_create("Find candidates", "software", [{"name": "x", "description": "y"}], "preview", 2)
            self.assertIn("preview match_limit", bad["error"])
            self.assertIn("only name and description", service.findall_create("Find candidates", "software", [{"name": "x", "description": "y", "url": "https://x"}])["error"])
        provider.assert_not_called()

    def test_findall_ingest_and_run_call_parallel_provider(self):
        class FakeProvider:
            def name(self): return "parallel"
            def findall_ingest(self, objective): return {"entity_type": "products", "match_conditions": []}
            def findall_create(self, schema): return {"findall_id": "fa_123"}
            def findall_status(self, findall_id, include_result=False): return {"findall_id": findall_id, "include_result": include_result}
        with patch("src.research.service._get_provider", return_value=FakeProvider()):
            self.assertEqual(service.findall_ingest("Find vulnerable products")["entity_type"], "products")
            result = service.findall_create("Find vulnerable products", "products", [{"name": "active", "description": "Actively exploited"}])
            self.assertEqual(result["findall_id"], "fa_123")
            self.assertEqual(service.findall_status("fa_123", True)["include_result"], True)
            self.assertIn("Invalid FindAll run ID", service.findall_status("../../private")["error"])

    def test_task_ownership_rejects_other_and_unowned_records(self):
        record = ResearchTaskRecord(task_id="task1", question="q", owner_uid="alice")
        with patch("src.research.service.task_store.get_task", return_value=record):
            self.assertEqual(service.get_task_status("task1", poll=False, owner_uid="bob")["error"], "Task not found")
        record.owner_uid = None
        with patch("src.research.service.task_store.get_task", return_value=record):
            self.assertEqual(service.get_task_status("task1", poll=False, owner_uid="bob")["error"], "Task not found")

    def test_enrichment_uses_structured_task_schema_and_citations(self):
        class FakeProvider:
            def name(self): return "parallel"
            def create_research_task(self, question, processor, task_input, task_spec):
                self.question = question
                self.processor = processor
                self.task_input = task_input
                self.task_spec = task_spec
                return ResearchTaskRecord(task_id="task_enrich", question=question, provider="parallel", status="pending")
        provider = FakeProvider()
        with patch("src.research.service._get_provider", return_value=provider):
            result = service.create_enrichment_task(
                {"id": "CVE-2026-1234", "vendor": "Example", "source_url": "https://vendor.example/advisory"},
                ["severity", "mitigations"],
            )
        self.assertEqual(result["task_id"], "task_enrich")
        self.assertEqual(provider.task_input["security_record"]["source_url"], "https://vendor.example/advisory")
        schema = provider.task_spec["output_schema"]["json_schema"]
        self.assertEqual(set(schema["properties"]), {"severity", "mitigations"})

    def test_enrichment_rejects_unapproved_fields_and_private_source_urls(self):
        with patch("src.research.service._get_provider") as provider:
            self.assertIn("only id", service.create_enrichment_task({"message": "private body"}, ["severity"])["error"])
            self.assertIn("source_url", service.create_enrichment_task({"source_url": "https://127.0.0.1/"}, ["severity"])["error"])
        provider.assert_not_called()

    def test_research_task_store_uses_project_data_directory(self):
        from pathlib import Path
        from src.research import task_store as store
        self.assertEqual(store.ROOT, Path(__file__).resolve().parents[1])


class SSRFGuardTests(unittest.TestCase):
    def test_accepts_public_https_and_normalizes(self):
        self.assertEqual(validate_extract_url("https://example.com"), "https://example.com/")

    def test_rejects_private_metadata_internal_and_non_https(self):
        for url in [
            "https://127.0.0.1/admin",
            "https://169.254.169.254/latest/meta-data/",
            "https://metadata.google.internal/",
            "https://host.internal/",
            "http://example.com/",
            "https://user:pass@example.com/",
        ]:
            with self.subTest(url=url), self.assertRaises(SSRFError):
                validate_extract_url(url)

    def test_rejects_ipv4_ipv6_and_ambiguous_numeric_host_edges(self):
        for url in [
            "https://10.0.0.1/", "https://172.16.1.1/", "https://192.168.1.1/",
            "https://[::1]/", "https://[fc00::1]/", "https://[fe80::1]/",
            "https://[::ffff:127.0.0.1]/", "https://127.1/",
            "https://2130706433/", "https://0x7f000001/",
        ]:
            with self.subTest(url=url), self.assertRaises(SSRFError):
                validate_extract_url(url)

    def test_rejects_encoded_or_malformed_authorities_and_excessive_url_length(self):
        for url in [
            "https://%31%32%37.0.0.1/", "https://example.com:bad/",
            "https://example.com/" + "a" * 4100,
        ]:
            with self.subTest(url=url[:48]), self.assertRaises(SSRFError):
                validate_extract_url(url)

    def test_url_list_keeps_valid_entries_and_explains_rejections(self):
        valid, errors = validate_extract_urls(["https://example.com", "http://127.0.0.1", 123])
        self.assertEqual(valid, ["https://example.com/"])
        self.assertEqual(len(errors), 2)


class ResearchRateLimitTests(unittest.TestCase):
    def test_provider_cost_endpoints_have_per_client_limits(self):
        from src.api.server import _research_rate_allowed
        ip = "192.0.2.250"
        self.assertTrue(all(_research_rate_allowed(ip, "/api/research/tasks") for _ in range(3)))
        self.assertFalse(_research_rate_allowed(ip, "/api/research/tasks"))
        self.assertTrue(all(_research_rate_allowed(ip, "/api/research/responses") for _ in range(12)))
        self.assertFalse(_research_rate_allowed(ip, "/api/research/responses"))

    def test_loopback_routes_return_local_status_and_results_without_credentials(self):
        from src.api.server import create_server
        server = create_server("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = "http://127.0.0.1:" + str(server.server_port)
        try:
            with patch.dict(os.environ, {}, clear=True):
                service._get_provider.cache_clear()
                with urllib.request.urlopen(base + "/api/research/status", timeout=3) as response:
                    status = json.loads(response.read())
                request = urllib.request.Request(
                    base + "/api/research/search",
                    data=json.dumps({"query": "CVE-2026-102764 BeyondTrust"}).encode(),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=5) as response:
                    result = json.loads(response.read())
                answer_request = urllib.request.Request(
                    base + "/api/research/responses",
                    data=json.dumps({"question": "Explain MFA", "effort": "low"}).encode(),
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with urllib.request.urlopen(answer_request, timeout=5) as response:
                    answer_result = json.loads(response.read())
            self.assertEqual(status["mode"], "local-only")
            self.assertEqual(result["provider"], "local")
            self.assertIn("results", result)
            self.assertIn("PARALLEL_API_KEY", answer_result["error"])
        finally:
            service._get_provider.cache_clear()
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


class ResearchStorePrivacyTests(unittest.TestCase):
    def test_private_json_writer_uses_owner_only_permissions_and_atomic_content(self):
        from src.research.task_store import _atomic_private_json_write
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "research_tasks.json"
            _atomic_private_json_write(target, {"task": {"question": "private"}})
            self.assertEqual(target.read_text(encoding="utf-8"), '{\n  "task": {\n    "question": "private"\n  }\n}')
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(Path(directory).iterdir()), [target])


if __name__ == "__main__":
    unittest.main()
