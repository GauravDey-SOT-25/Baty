import json
import os
import solcx

def compile_trust_registry():
    solc_version = "0.8.24"
    print(f"Ensuring solc {solc_version} is ready...")
    solcx.install_solc(solc_version)

    contract_path = os.path.join(os.path.dirname(__file__), "contracts", "TrustRegistry.sol")
    print(f"Compiling {contract_path}...")

    compiled = solcx.compile_files(
        [contract_path],
        output_values=["abi", "bin"],
        solc_version=solc_version
    )

    contract_id = f"{contract_path}:TrustRegistry"
    if contract_id not in compiled:
        # Try alternate key format
        matching_keys = [k for k in compiled.keys() if "TrustRegistry" in k]
        if not matching_keys:
            raise RuntimeError(f"Contract TrustRegistry not found in compiled output: {list(compiled.keys())}")
        contract_id = matching_keys[0]

    contract_data = compiled[contract_id]
    abi = contract_data["abi"]
    bytecode = contract_data["bin"]

    output_artifact = {
        "contractName": "TrustRegistry",
        "abi": abi,
        "bytecode": bytecode
    }

    output_path = os.path.join(os.path.dirname(__file__), "contracts", "TrustRegistry.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_artifact, f, indent=2)

    print(f"[SUCCESS] Compiled TrustRegistry.json saved to {output_path}")
    print(f"ABI functions count: {len([x for x in abi if x.get('type') == 'function'])}")
    print(f"Bytecode length: {len(bytecode)} characters")
    return output_path

if __name__ == "__main__":
    compile_trust_registry()
