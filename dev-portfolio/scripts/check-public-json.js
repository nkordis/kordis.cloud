/* eslint-disable no-console */
// Fails the build if any published JSON file still contains a TODO placeholder.
// Everything in public/ (profile JSON included) is uploaded as-is, even entries React hides.
const fs = require('fs');
const path = require('path');

// Every JSON file anywhere in the build output, including nested folders
const buildDir = path.join(__dirname, '..', process.argv[2] || 'build');

function jsonFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) return jsonFiles(full);
    return entry.name.endsWith('.json') ? [full] : [];
  });
}

const offenders = jsonFiles(buildDir)
  .filter((file) => /TODO/i.test(fs.readFileSync(file, 'utf8')))
  .map((file) => path.relative(buildDir, file));

if (offenders.length > 0) {
  console.error(`TODO placeholders found in published JSON: ${offenders.join(', ')}`);
  console.error('Remove the unfinished entries before publishing; these files are served publicly.');
  process.exit(1);
}
console.log(`Checked JSON under ${buildDir}: no TODO placeholders.`);
