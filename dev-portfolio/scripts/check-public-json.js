/* eslint-disable no-console */
// Fails the build if any published profile JSON still contains a TODO placeholder.
// Everything in public/profile is uploaded as-is, even entries React hides.
const fs = require('fs');
const path = require('path');

const profileDir = path.join(__dirname, '..', process.argv[2] || 'build', 'profile');

const offenders = fs.readdirSync(profileDir)
  .filter((file) => file.endsWith('.json'))
  .filter((file) => /TODO/i.test(fs.readFileSync(path.join(profileDir, file), 'utf8')));

if (offenders.length > 0) {
  console.error(`TODO placeholders found in public profile JSON: ${offenders.join(', ')}`);
  console.error('Remove the unfinished entries before publishing; these files are served publicly.');
  process.exit(1);
}
console.log(`Checked ${profileDir}: no TODO placeholders.`);
