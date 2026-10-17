# 🛡️ Decentralized URL Trust Verifier (Web3 Security MVP)

> **Moving Beyond Blacklist Scanning to Cryptographic Proof-of-Trust via a Distributed Ledger.**

A functional, production-grade prototype demonstrating decentralized URL authenticity verification. Rather than relying on easily bypassed, reactive URL blacklists, this system establishes an immutable **Proof-of-Trust** using an Ethereum smart contract registry (`TrustRegistry.sol`), canonical domain SHA-256 hashing, and real-time SSL/TLS X.509 certificate fingerprint attestation.

---

## 📑 Table of Contents

1. [System Architecture & The Blueprint](#1-system-architecture--the-blueprint)
   - [Data Structure & JSON Schema](#data-structure--json-schema)
   - [Verification Flow](#verification-flow)
   - [Trust Scoring Engine](#trust-scoring-engine)
2. [Smart Contract Implementation (The Immutable Core)](#2-smart-contract-implementation)
   - [TrustRegistry.sol](#trustregistrysol)
   - [Local Blockchain Setup (Hardhat & Ganache)](#local-blockchain-setup)
3. [Backend Service (The Translator / API)](#3-backend-service)
   - [API Endpoints](#api-endpoints)
   - [Hashing & SSL Extraction Logic](#hashing--ssl-extraction-logic)
4. [Frontend Prototype (User Experience)](#4-frontend-prototype)
5. [Quickstart & Running Locally](#5-quickstart--running-locally)
6. [Automated Verification & Test Suite](#6-automated-verification--test-suite)

---

## 1. System Architecture & The Blueprint

### Data Structure & JSON Schema
Every record stored on the blockchain ledger or returned by the verification API adheres to this strictly typed specification:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "BlockchainTrustRecord",
  "type": "object",
  "required": ["url_hash", "cert_fingerprint", "timestamp", "verifier_id", "is_trusted"],
  "properties": {
    "url_hash": {
      "type": "string",
      "pattern": "^0x[a-fA-F0-9]{64}$",
      "description": "SHA-256 cryptographic digest of the canonical domain/URL"
    },
    "cert_fingerprint": {
      "type": "string",
      "pattern": "^0x[a-fA-F0-9]{64}$",
      "description": "SHA-256 fingerprint of the domain's X.509 SSL/TLS certificate"
    },
    "timestamp": {
      "type": "integer",
      "minimum": 0,
      "description": "Unix epoch block timestamp when the trust proof was registered"
    },
    "verifier_id": {
      "type": "string",
      "pattern": "^0x[a-fA-F0-9]{40}$",
      "description": "Ethereum address of the certified security verifier/auditor"
    },
    "is_trusted": {
      "type": "boolean",
      "description": "Active status: true if currently verified, false if revoked"
    },
    "metadata": {
      "type": "string",
      "description": "Optional human-readable label or domain description"
    }
  }
}
```

### Verification Flow
```
[ User Input URL ]
        │
        ▼
[ Frontend Interface ]
        │
        │ HTTP GET /api/check?url=...
        ▼
[ Backend Translator ] ────► Normalizes URL & Computes SHA-256 Domain Hash
        │
        ├───────────────────────────────────┬───────────────────────────────────┐
        ▼                                   ▼                                   ▼
 [ Blockchain Reader ]            [ Live SSL Inspector ]              [ Verifier Authority ]
 Calls isTrusted(urlHash)         Fetches X.509 DER Cert              Validates msg.sender /
 & getTrustRecord(urlHash)        Computes SHA-256 Fingerprint        authorized verifier list
        │                                   │                                   │
        └───────────────────────────────────┴───────────────────────────────────┘
                                            │
                                            ▼
                               [ Trust Scoring Engine ]
                                            │
                     ┌──────────────────────┼──────────────────────┐
                     ▼                      ▼                      ▼
             [ Verified Trust ]     [ Potential Threat ]     [ Unverified ]
               (Score: 100/100)       (Score: 20-35/100)     (Score: 0/100)
```

### Trust Scoring Engine

| Category | Score | Ledger Condition | Live SSL Condition | Security Significance |
| :--- | :---: | :--- | :--- | :--- |
| **Verified Trust** | **100** | Record exists, `isTrusted == true` | Live SSL fingerprint **matches** on-chain record | Cryptographically authentic domain attested by authorized verifier. |
| **Potential Threat (Needs Inspection)** | **30** | Record exists, `isTrusted == true` | Live SSL fingerprint **does not match** | **Critical Alert**: Possible Man-In-The-Middle (MITM), DNS spoofing, or hijacked SSL certificate. |
| **Potential Threat (Needs Inspection)** | **20** | Record exists, `isTrusted == false` | Any | Trust was explicitly revoked by security verifier due to known breach or domain expiration. |
| **Potential Threat (Needs Inspection)** | **35** | Record exists, `isTrusted == true` | Handshake failed / Self-signed / Invalid | Domain is registered, but active web host has broken/expired TLS. |
| **Unverified** | **0** | No record found on ledger | Any | No Proof of Trust established on-chain. Untrusted by default. |

---

## 2. Smart Contract Implementation

The immutable core is written in Solidity (`contracts/TrustRegistry.sol`):

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract TrustRegistry {
    struct TrustRecord {
        string urlHash;           // SHA-256 hash of canonical domain/URL
        string certFingerprint;   // SHA-256 fingerprint of the SSL/TLS certificate
        uint256 timestamp;        // Block timestamp when registered
        address verifierId;       // Ethereum address of certified security verifier
        bool isTrusted;           // Active status: true if verified, false if revoked
        string metadata;          // Descriptive metadata
    }

    address public owner;
    mapping(string => TrustRecord) private records;
    mapping(address => bool) public authorizedVerifiers;
    string[] private registeredHashes;

    event LinkRegistered(string urlHash, string certFingerprint, address indexed verifierId, uint256 timestamp);
    event LinkRevoked(string urlHash, address indexed verifierId, uint256 timestamp, string reason);

    modifier onlyVerifier() {
        require(msg.sender == owner || authorizedVerifiers[msg.sender], "Caller is not an authorized verifier");
        _;
    }

    function addTrustedLink(string memory urlHash, string memory certFingerprint) public onlyVerifier {
        addTrustedLinkWithMetadata(urlHash, certFingerprint, "");
    }

    function isTrusted(string memory urlHash) external view returns (bool) {
        return records[urlHash].isTrusted;
    }

    function getTrustRecord(string memory urlHash) external view returns (
        string memory, string memory, uint256, address, bool, string memory
    ) {
        TrustRecord memory rec = records[urlHash];
        return (rec.urlHash, rec.certFingerprint, rec.timestamp, rec.verifierId, rec.isTrusted, rec.metadata);
    }

    function revokeTrust(string memory urlHash, string memory reason) public onlyVerifier {
        require(records[urlHash].isTrusted, "Not active");
        records[urlHash].isTrusted = false;
        records[urlHash].timestamp = block.timestamp;
        emit LinkRevoked(urlHash, msg.sender, block.timestamp, reason);
    }
}
```

### Local Blockchain Setup

#### Option A: Zero-Friction Standalone Ledger (Built-in)
The Python backend contains an integrated cryptographic in-memory ledger engine. It starts immediately without requiring external daemons, so you can test the prototype instantly.

#### Option B: Hardhat Local Node
1. Launch local Ethereum RPC node:
   ```bash
   npx hardhat node
   ```
2. In another terminal, deploy the contract:
   ```bash
   npx hardhat run scripts/deploy.js --network localhost
   ```

#### Option C: Ganache Local Chain
1. Start Ganache on default port:
   ```bash
   ganache --port 8545 --chainId 1337
   ```
2. The backend connects automatically to `http://127.0.0.1:8545`.

---

## 3. Backend Service

Built with **Python + Flask + Web3.py**:

### API Endpoints

1. **`GET /api/check?url=<TARGET_URL>`**
   - Hashes canonical domain with SHA-256.
   - Queries `TrustRegistry.isTrusted(urlHash)` and `getTrustRecord(urlHash)`.
   - Inspects live server SSL certificate using Python's `ssl` module.
   - Returns Trust Score (100, 30, 20, 0), Verdict, and indicators.

2. **`POST /api/register`**
   - **Payload**: `{"url": "https://uniswap.org", "metadata": "Uniswap DEX"}`
   - Calls `TrustRegistry.addTrustedLink(urlHash, certFingerprint)` from verifier account.
   - Auto-extracts live SSL fingerprint if not provided.

3. **`GET /api/links`**
   - Returns all registered trust records on the ledger.

4. **`POST /api/revoke`**
   - **Payload**: `{"url": "uniswap.org", "reason": "Compromised DNS"}`
   - Marks link as untrusted on-chain for incident response simulation.

5. **`GET /api/status`**
   - Returns blockchain connection mode, block height, contract address, and verifier ID.

---

## 4. Frontend Prototype

A modern, responsive, cyber-security dashboard located in `frontend/`:
- **Trust Scanner**: Single-click URL inspection with real-time feedback and quick preset chips.
- **On-Chain Registry**: Form to register domains and certify SSL fingerprints.
- **Immutable Ledger Explorer**: Live audit table of all attested links with on-chain revocation buttons.
- **Architecture & Blueprint Tab**: Interactive diagram and JSON schema reference.

---

## 5. Quickstart & Running Locally

### Step 1: Install Python Requirements
```bash
python -m pip install -r backend/requirements.txt
```

### Step 2: Compile the Smart Contract
```bash
python compile_contract.py
```
*(This uses `py-solc-x` and automatically compiles `TrustRegistry.sol` to `contracts/TrustRegistry.json`)*.

### Step 3: Run the Application
```bash
python run_demo.py
```
Or directly:
```bash
python backend/app.py
```

### Step 4: Access the UI
Open your browser to:
👉 **`http://127.0.0.1:5000`**

---

## 6. Automated Verification & Test Suite

Run the full end-to-end test suite:
```bash
python -m unittest test_system.py -v
```

### Verified Test Results:
```
test_api_check_potential_threat_cert_mismatch ... ok (Score: 30, Potential Threat)
test_api_check_unverified .................... ok (Score: 0, Unverified)
test_api_check_verified_trust ................ ok (Score: 100, Verified Trust)
test_smart_contract_trust_registry_flow ...... ok (addTrustedLink, isTrusted, revokeTrust)
test_ssl_fingerprint_extraction .............. ok (Live SHA-256 DER extraction)
test_url_normalization_and_hashing ........... ok (Deterministic canonical SHA-256)

Ran 6 tests in 18.302s
OK (100% Pass Rate)
```

---

## 💡 Why This Solves Web3 Link Spoofing

Traditional security relies on centralized blacklists that are updated *hours or days after* phishing campaigns launch.

The **Decentralized URL Trust Verifier**:
1. **Shifts to Proof-of-Trust (Whitelist Model)**: Unknown links are treated as unverified (`Score 0`) until cryptographic proof is submitted.
2. **Defeats DNS Poisoning & BGP Hijacks**: Even if an attacker manipulates DNS records to point to a clone site, the live SSL certificate will not match the immutable on-chain fingerprint, immediately triggering a **Potential Threat** warning.
3. **Decentralized Censorship Resistance**: Ledger records cannot be quietly deleted or modified by a single compromised entity.
