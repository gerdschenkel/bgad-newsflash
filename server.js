// BGAD News Flash static host. Zero dependencies, Node 18+.
// Railway sets PORT; everything under public/ is served.
// "/" redirects to the newest issue in public/issues.

const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, 'public');
const ISSUES = path.join(ROOT, 'issues');
const PORT = process.env.PORT || 3000;

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.pdf': 'application/pdf',
  '.ico': 'image/x-icon',
};

function issueList() {
  if (!fs.existsSync(ISSUES)) return [];
  return fs.readdirSync(ISSUES)
    .filter(f => f.endsWith('.html'))
    .sort()
    .reverse();
}

function send(res, code, body, type) {
  res.writeHead(code, {
    'Content-Type': type || 'text/plain; charset=utf-8',
    'Cache-Control': 'public, max-age=300',
    'X-Content-Type-Options': 'nosniff',
  });
  res.end(body);
}

const server = http.createServer((req, res) => {
  let urlPath;
  try {
    urlPath = decodeURIComponent(new URL(req.url, 'http://x').pathname);
  } catch (e) {
    return send(res, 400, 'Bad request');
  }

  if (urlPath === '/health') return send(res, 200, 'ok');

  if (urlPath === '/' || urlPath === '/latest') {
    const list = issueList();
    if (!list.length) return send(res, 404, 'No issues published yet.');
    res.writeHead(302, { Location: '/issues/' + list[0] });
    return res.end();
  }

  if (urlPath === '/archive.json') {
    return send(res, 200, JSON.stringify({ issues: issueList() }, null, 2), TYPES['.json']);
  }

  if (urlPath === '/archive') {
    const rows = issueList()
      .map(f => '<li><a href="/issues/' + f + '">' + f.replace('.html', '') + '</a></li>')
      .join('\n');
    const page = '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">' +
      '<meta name="viewport" content="width=device-width,initial-scale=1">' +
      '<title>BGAD News Flash archive</title><style>' +
      'body{font-family:Helvetica,Arial,sans-serif;max-width:640px;margin:40px auto;padding:0 20px;color:#232323}' +
      'h1{color:#024E8F;font-size:24px}a{color:#026EC9}li{margin:6px 0;font-size:17px}' +
      '</style></head><body><h1>BGAD News Flash archive</h1><ul>' + rows + '</ul></body></html>';
    return send(res, 200, page, TYPES['.html']);
  }

  // static files, path traversal guarded
  const target = path.normalize(path.join(ROOT, urlPath));
  if (!target.startsWith(ROOT)) return send(res, 403, 'Forbidden');

  fs.stat(target, (err, st) => {
    if (err || !st.isFile()) return send(res, 404, 'Not found');
    const type = TYPES[path.extname(target).toLowerCase()] || 'application/octet-stream';
    res.writeHead(200, {
      'Content-Type': type,
      'Content-Length': st.size,
      'Cache-Control': 'public, max-age=600',
    });
    fs.createReadStream(target).pipe(res);
  });
});

server.listen(PORT, () => console.log('News Flash site listening on ' + PORT));
