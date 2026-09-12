'use strict';
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const root = __dirname;
const cadHandler = require('./cad-server.cjs').createHandler(root);
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8' };
const files = new Set(['/index.html', '/styles.css', '/core.js', '/cad.js', '/snap.js', '/management.js', '/app.js']);
const server = http.createServer(async (req, res) => {
  if (await cadHandler(req, res)) return;
  let name;
  try { name = decodeURIComponent(new URL(req.url, 'http://localhost').pathname); } catch { res.writeHead(400); res.end(); return; }
  if (name === '/') name = '/index.html';
  if (name === '/favicon.ico') { res.writeHead(204); res.end(); return; }
  if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405); res.end(); return; }
  if (!files.has(name)) { res.writeHead(404); res.end('Not found'); return; }
  fs.readFile(path.join(root, name), (error, body) => {
    if (error) { res.writeHead(500); res.end('Cannot read file'); return; }
    res.writeHead(200, { 'Content-Type': types[path.extname(name)], 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
    res.end(req.method === 'HEAD' ? undefined : body);
  });
});
server.listen(Number(process.env.PORT || 4173), '127.0.0.1', () => console.log(`MEP-Manager: http://127.0.0.1:${server.address().port}`));
server.on('error', error => { console.error(error.code === 'EADDRINUSE' ? '端口被占用。请关闭已有服务，或设置 PORT 后重试。' : error.message); process.exitCode = 1; });
