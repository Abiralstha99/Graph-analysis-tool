import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

const nginxConf = readFileSync(
  join(dirname(fileURLToPath(import.meta.url)), '../../nginx.conf'),
  'utf8',
);

function locationBlock(path: string): string {
  const match = nginxConf.match(
    new RegExp(`location\\s+${path.replace(/\//g, '\\/')}\\s*\\{([\\s\\S]*?)\\n\\s*\\}`),
  );
  if (!match) {
    throw new Error(`Missing nginx location ${path}`);
  }
  return match[1];
}

describe('frontend nginx reverse proxy', () => {
  it('forwards production /api/analysis POSTs to the backend analysis router', () => {
    const block = locationBlock('/api/analysis/');
    expect(block).toMatch(/proxy_pass\s+http:\/\/backend:8080\/analysis\//);
  });
});
