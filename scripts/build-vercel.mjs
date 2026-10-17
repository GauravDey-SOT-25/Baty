import {cpSync, copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outputDirectory = path.join(projectRoot, 'dist', 'vercel');
const siteDirectory = path.join(projectRoot, 'Comfest - 26');

const publicFiles = [
  'styles.css', 'script.js', 'ai-workspace.css', 'ai-workspace.js',
  'blockchain.html', 'blockchain.css', 'blockchain.js',
  'assistant.html', 'assistant.css', 'assistant.js', 'research-not-available.html',
];

if (!existsSync(path.join(projectRoot, 'index.html'))) throw new Error('Missing public file: root index.html');
for (const name of publicFiles) {
  if (!existsSync(path.join(siteDirectory, name))) throw new Error(`Missing public file: ${name}`);
}

rmSync(outputDirectory, {recursive: true, force: true});
mkdirSync(outputDirectory, {recursive: true});
for (const name of publicFiles) copyFileSync(path.join(siteDirectory, name), path.join(outputDirectory, name));
const homepage = readFileSync(path.join(projectRoot, 'index.html'), 'utf8')
  .replaceAll('./Comfest%20-%2026/', './')
  .replaceAll('./frontend/trust.js', './trust.js');
writeFileSync(path.join(outputDirectory, 'index.html'), homepage);
cpSync(path.join(siteDirectory, 'assets'), path.join(outputDirectory, 'assets'), {recursive: true});
copyFileSync(path.join(projectRoot, 'frontend', 'trust.js'), path.join(outputDirectory, 'trust.js'));
copyFileSync(path.join(projectRoot, 'frontend', 'trust.css'), path.join(outputDirectory, 'trust.css'));

console.log(`Prepared the public site and assistant assets in ${path.relative(projectRoot, outputDirectory)}.`);
