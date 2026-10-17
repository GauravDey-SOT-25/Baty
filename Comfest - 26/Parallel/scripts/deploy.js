/**
 * Hardhat Deployment Script for TrustRegistry.sol
 * Deploys the contract to localhost or Hardhat in-memory network.
 */
const hre = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
  console.log("==================================================");
  console.log(" Deploying TrustRegistry.sol to Blockchain Network");
  console.log("==================================================");

  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying contract with account:", deployer.address);

  const balance = await hre.ethers.provider.getBalance(deployer.address);
  console.log("Account balance:", hre.ethers.formatEther(balance), "ETH");

  const TrustRegistry = await hre.ethers.getContractFactory("TrustRegistry");
  const registry = await TrustRegistry.deploy();
  await registry.waitForDeployment();

  const contractAddress = await registry.getAddress();
  console.log("\n[SUCCESS] TrustRegistry deployed at:", contractAddress);

  // Save deployed address for Python Backend consumption
  const deployInfo = {
    network: hre.network.name,
    contractAddress: contractAddress,
    deployer: deployer.address,
    timestamp: new Date().toISOString()
  };

  const outputPath = path.join(__dirname, "..", "contracts", "deployed_address.json");
  fs.writeFileSync(outputPath, JSON.stringify(deployInfo, null, 2));
  console.log("Deployment info written to:", outputPath);
  console.log("Set CONTRACT_ADDRESS in your .env or backend config to link to this instance.");
}

main().catch((error) => {
  console.error("Deployment failed:", error);
  process.exitCode = 1;
});
