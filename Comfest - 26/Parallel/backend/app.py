import os
import sys
from flask import Flask, request, jsonify, send_from_directory

# Ensure backend package can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from backend.hasher import (
    normalize_url,
    compute_url_hash,
    fetch_ssl_fingerprint
)
from backend.blockchain import BlockchainManager
from backend.threat_intel import get_threat_intelligence

# Initialize Flask app
frontend_dir = os.path.join(parent_dir, "frontend")
app = Flask(__name__, static_folder=frontend_dir, static_url_path="")

# Initialize Blockchain Manager
blockchain = BlockchainManager()


@app.after_request
def add_cors_headers(response):
    """Enable CORS for web frontends."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


# --- Static UI Serving ---

@app.route("/")
def index():
    """Serves the single-page frontend interface."""
    return send_from_directory(frontend_dir, "index.html")


# --- API Endpoints ---

@app.route("/api/status", methods=["GET"])
def api_status():
    """Returns blockchain health, network details, and verifier info."""
    return jsonify({
        "status": "online",
        "service": "Decentralized URL Trust Verifier API",
        "blockchain": blockchain.get_status()
    })


@app.route("/api/register", methods=["POST"])
def api_register():
    """
    Registers a URL and its SSL certificate fingerprint on the blockchain.
    JSON Payload:
      - url: Required (e.g. 'https://ethereum.org' or 'ethereum.org')
      - cert_fingerprint: Optional (if omitted, extracted live from the domain)
      - metadata: Optional descriptive label
    """
    data = request.get_json(silent=True) or {}
    raw_url = data.get("url", "").strip()
    custom_fingerprint = data.get("cert_fingerprint", "").strip()
    metadata = data.get("metadata", "").strip()

    if not raw_url:
        return jsonify({
            "success": False,
            "error": "Missing required field: 'url'"
        }), 400

    try:
        canonical_url, hostname, port = normalize_url(raw_url)
        url_hash = compute_url_hash(hostname)

        # If fingerprint not provided, extract live from target server
        cert_info = {}
        if not custom_fingerprint:
            cert_info = fetch_ssl_fingerprint(hostname, port)
            if cert_info.get("success"):
                cert_fingerprint = cert_info["fingerprint"]
            else:
                return jsonify({
                    "success": False,
                    "error": f"Failed to extract live SSL certificate for {hostname}: {cert_info.get('error')}. Please specify cert_fingerprint manually if testing offline domains.",
                    "url_hash": url_hash
                }), 400
        else:
            cert_fingerprint = custom_fingerprint

        ipfs_cid = data.get("ipfs_cid", "").strip()
        # Commit to blockchain
        descriptive_meta = metadata or f"{hostname} ({canonical_url})"
        tx_result = blockchain.add_trusted_link(
            url_hash=url_hash,
            cert_fingerprint=cert_fingerprint,
            ipfs_cid=ipfs_cid,
            metadata=descriptive_meta
        )

        return jsonify({
            "success": True,
            "message": "URL successfully registered on the decentralized ledger",
            "url": canonical_url,
            "domain": hostname,
            "url_hash": url_hash,
            "cert_fingerprint": cert_fingerprint,
            "live_cert_info": cert_info,
            "transaction": tx_result
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/check", methods=["GET"])
def api_check():
    """
    Takes a URL, hashes it, checks the smart contract, fetches live SSL certificate,
    and returns comprehensive Trust Score and verification verdict.
    Query parameter:
      - url: Target URL/domain to scan
    """
    raw_url = request.args.get("url", "").strip()
    if not raw_url:
        return jsonify({
            "success": False,
            "error": "Query parameter 'url' is required (e.g. /api/check?url=ethereum.org)"
        }), 400

    try:
        canonical_url, hostname, port = normalize_url(raw_url)
        url_hash = compute_url_hash(hostname)

        # 1. Query Blockchain Reader
        is_trusted_on_chain = blockchain.is_trusted(url_hash)
        chain_record = blockchain.get_trust_record(url_hash)

        # 2. Live SSL Certificate Inspection
        live_cert = fetch_ssl_fingerprint(hostname, port)

        # 3. Live Threat Intelligence (VirusTotal + Google Safe Browsing)
        threat_intel = get_threat_intelligence(canonical_url, hostname)

        # 4. Trust Scoring Engine
        verdict = evaluate_trust(
            url_hash=url_hash,
            chain_record=chain_record,
            is_trusted_on_chain=is_trusted_on_chain,
            live_cert=live_cert,
            threat_intel=threat_intel
        )

        return jsonify({
            "success": True,
            "query_url": raw_url,
            "canonical_url": canonical_url,
            "domain": hostname,
            "url_hash": url_hash,
            "trust_verdict": verdict["status"],
            "trust_score": verdict["score"],
            "summary": verdict["summary"],
            "explanation": verdict["explanation"],
            "indicators": verdict["indicators"],
            "blockchain_record": chain_record,
            "live_certificate": live_cert,
            "threat_intelligence": threat_intel
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def evaluate_trust(
    url_hash: str,
    chain_record: dict,
    is_trusted_on_chain: bool,
    live_cert: dict,
    threat_intel: dict = None
) -> dict:
    """
    Computes definitive Trust Score and category based on:
    1. Blockchain Proof-of-Trust (Smart Contract Ledger)
    2. Real-time SSL Certificate Fingerprint Matching
    3. Live Threat Intelligence (VirusTotal + Google Safe Browsing)
    """
    indicators = []
    threat_intel = threat_intel or {}
    vt = threat_intel.get("virustotal", {})
    gsb = threat_intel.get("google_safe_browsing", {})

    # Evaluate external threat intelligence alerts
    vt_flagged = vt.get("is_threat", False)
    gsb_flagged = gsb.get("is_threat", False)

    if vt_flagged:
        indicators.append(f"⚠️ VirusTotal Threat Alert: {vt.get('malicious_count')} of {vt.get('total_engines', 92)} security vendors flagged this domain as MALICIOUS.")
    elif vt.get("success"):
        indicators.append(f"🛡️ VirusTotal Reputation: {vt.get('status')}")

    if gsb_flagged:
        threat_str = ", ".join(gsb.get("threat_types", []))
        indicators.append(f"⚠️ Google Safe Browsing Alert: Threat category detected: {threat_str}")
    elif gsb.get("success"):
        indicators.append(f"🛡️ Google Safe Browsing: {gsb.get('status')}")
    elif gsb.get("activation_url"):
        indicators.append("ℹ️ Google Safe Browsing API Key configured (Requires 1-click activation in GCP Console)")

    # If active external threat detected, downgrade immediately
    if vt_flagged or gsb_flagged:
        return {
            "status": "Potential Threat (Needs Inspection)",
            "score": 10,
            "summary": "Active Security Threat Detected",
            "explanation": "SECURITY ALERT: External cyber-threat scanners (VirusTotal / Google Safe Browsing) have flagged this link as actively distributing malware or participating in social engineering / phishing campaigns.",
            "indicators": indicators
        }

    # Case 1: Not found on blockchain ledger
    if not chain_record:
        indicators.append("No record exists in the decentralized ledger.")
        return {
            "status": "Unverified",
            "score": 0,
            "summary": "No Record Found on Decentralized Ledger",
            "explanation": "This web link has not established Proof of Trust on the blockchain. Without decentralized ledger attestation, its authenticity cannot be verified cryptographically.",
            "indicators": indicators
        }

    # Case 2: Found on ledger, but revoked/inactive
    if not is_trusted_on_chain or not chain_record.get("is_trusted", False):
        indicators.append("Record exists on-chain, but trust has been explicitly REVOKED.")
        return {
            "status": "Potential Threat (Needs Inspection)",
            "score": 20,
            "summary": "Revoked Proof of Trust",
            "explanation": "This domain is registered on the ledger, but its trust status has been marked as REVOKED by the security verifier. This may indicate a known compromise or domain expiration.",
            "indicators": indicators
        }

    # Record is active on-chain. Now verify SSL fingerprint
    onchain_fingerprint = (chain_record.get("cert_fingerprint") or "").lower()
    live_fingerprint = (live_cert.get("fingerprint") or "").lower()

    if not live_cert.get("success"):
        indicators.append(f"Could not retrieve active SSL certificate: {live_cert.get('error')}")
        return {
            "status": "Potential Threat (Needs Inspection)",
            "score": 35,
            "summary": "SSL Connection Anomaly",
            "explanation": "Domain exists on the immutable ledger, but the server failed to provide a valid, verifiable SSL certificate during live inspection.",
            "indicators": indicators
        }

    # Compare Cryptographic Fingerprints
    if onchain_fingerprint == live_fingerprint:
        indicators.append("Domain SHA-256 matches blockchain ledger entry.")
        indicators.append("Live SSL certificate SHA-256 fingerprint exactly matches immutable on-chain record.")
        indicators.append(f"Attested by certified Verifier ID: {chain_record.get('primary_verifier') or chain_record.get('verifier_id')}")
        return {
            "status": "Verified Trust",
            "score": 100,
            "summary": "Matched Blockchain Record",
            "explanation": "Proof of Trust successfully established. The domain hash and active SSL certificate fingerprint match the immutable on-chain record attested by an authorized security verifier.",
            "indicators": indicators
        }
    else:
        indicators.append("Domain hash matched, BUT SSL certificate fingerprints DO NOT MATCH.")
        indicators.append(f"On-chain Fingerprint: {onchain_fingerprint}")
        indicators.append(f"Live Server Fingerprint: {live_fingerprint}")
        return {
            "status": "Potential Threat (Needs Inspection)",
            "score": 30,
            "summary": "Cryptographic Fingerprint Mismatch",
            "explanation": "SECURITY ALERT: The domain exists in the decentralized ledger, but the live server's SSL certificate fingerprint differs from the immutable ledger proof! This may indicate a Man-in-the-Middle (MITM) attack, DNS cache poisoning, or an unauthorized certificate reissuance.",
            "indicators": indicators
        }


@app.route("/api/links", methods=["GET"])
def api_links():
    """Returns all links recorded on the ledger for transparency."""
    records = blockchain.get_all_records()
    return jsonify({
        "total": len(records),
        "records": records
    })


@app.route("/api/revoke", methods=["POST"])
def api_revoke():
    """Revokes a link on-chain for security audit simulations."""
    data = request.get_json(silent=True) or {}
    raw_url = data.get("url", "").strip()
    reason = data.get("reason", "Administrative Security Revocation").strip()

    if not raw_url:
        return jsonify({"success": False, "error": "Missing 'url' parameter"}), 400

    _, hostname, _ = normalize_url(raw_url)
    url_hash = compute_url_hash(hostname)

    res = blockchain.revoke_trust(url_hash=url_hash, reason=reason)
    return jsonify(res)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n==================================================")
    print(f"  Decentralized URL Trust Verifier Server Online  ")
    print(f"  Local URL: http://127.0.0.1:{port}               ")
    print(f"==================================================\n")
    app.run(host="127.0.0.1", port=port, debug=False)
