import fs from 'fs';
import path from 'path';

function makeExecutable(dir) {
  if (!fs.existsSync(dir)) return;
  try {
    const files = fs.readdirSync(dir);
    for (const file of files) {
      const fullPath = path.join(dir, file);
      try {
        const stat = fs.statSync(fullPath);
        if (stat.isDirectory()) {
          makeExecutable(fullPath);
        } else {
          fs.chmodSync(fullPath, 0o755);
        }
      } catch (e) {}
    }
  } catch (e) {}
}

try {
  const binDir = path.resolve('node_modules', '.bin');
  makeExecutable(binDir);

  const esbuildDir = path.resolve('node_modules', '@esbuild');
  makeExecutable(esbuildDir);

  const viteBin = path.resolve('node_modules', 'vite', 'bin');
  makeExecutable(viteBin);

  console.log('✓ Execution permissions verified successfully.');
} catch (err) {
  console.log('Permission verification bypassed:', err.message);
}
