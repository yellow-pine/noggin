// For each built page: every inline <script>/<style> body must have its sha256 in the CSP meta.
import fs from 'node:fs'; import crypto from 'node:crypto';
for (const f of process.argv.slice(2)) {
  const h = fs.readFileSync(f, 'utf8');
  const csp = h.match(/content-security-policy" content="([^"]*)"/)[1];
  for (const [, tag, attrs, body] of h.matchAll(/<(script|style)([^>]*)>([\s\S]*?)<\/\1>/g)) {
    if (/\ssrc=/.test(attrs)) continue;
    const d = 'sha256-' + crypto.createHash('sha256').update(body).digest('base64');
    console.log(f, tag, attrs.trim().slice(0, 40), csp.includes(d) ? 'hashed' : 'NOT HASHED', body.slice(0, 50).replace(/\s+/g, ' '));
  }
}
