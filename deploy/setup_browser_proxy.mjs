// Temporary, localhost-only workaround for agent-browser 0.34.0 keyboard input.
// Keep credentials and input out of logs; forward only to the existing dashboard.
import http from 'node:http';
import net from 'node:net';
import {pathToFileURL} from 'node:url';

export const BUGGY_KEY_CODE = 'i=r?.keyCode??(1===e.key.length?e.key.charCodeAt(0):0)';

export function patchKeyboardBundle(source) {
  if (source.split(BUGGY_KEY_CODE).length !== 2) {
    throw new Error('Unexpected dashboard keyboard implementation');
  }
  return source.replace(BUGGY_KEY_CODE, 'i=e.keyCode||r?.keyCode||0');
}

async function start() {
  const upstream = 'http://127.0.0.1:4849';
  const read = async path => {
    const response = await fetch(upstream + path, {signal: AbortSignal.timeout(10000)});
    if (!response.ok) throw new Error('Dashboard asset unavailable');
    return response.text();
  };
  let html = await read('/');
  const patches = new Map();
  const paths = new Set([...html.matchAll(/<script src="([^"]+)"/g)].map(m => m[1]));
  for (const path of paths) {
    if (!path.startsWith('/_next/static/')) continue;
    const source = await read(path);
    if (source.includes(BUGGY_KEY_CODE)) patches.set(path, patchKeyboardBundle(source));
  }
  if (patches.size !== 1) throw new Error('Expected one dashboard keyboard bundle');
  for (const path of patches.keys()) {
    html = html.replaceAll(`"${path}"`, `"${path}?recover_keyboard=1"`);
  }
  const server = http.createServer((req, res) => {
    const path = new URL(req.url, upstream).pathname;
    const asset = path === '/' ? html : patches.get(path);
    if (asset !== undefined) {
      res.writeHead(200, {
        'Content-Type': path === '/' ? 'text/html; charset=utf-8' : 'text/javascript; charset=utf-8',
        'Cache-Control': 'no-store',
      });
      res.end(req.method === 'HEAD' ? undefined : asset);
      return;
    }
    const proxy = http.request({
      hostname: '127.0.0.1', port: 4849, path: req.url,
      method: req.method, headers: req.headers,
    }, response => {
      res.writeHead(response.statusCode, response.headers);
      response.pipe(res);
    });
    proxy.on('error', () => {
      if (!res.headersSent) res.writeHead(502);
      res.end('Setup browser unavailable');
    });
    req.on('aborted', () => proxy.destroy());
    req.pipe(proxy);
  });
  server.on('upgrade', (req, socket, head) => {
    const proxy = net.connect(4849, '127.0.0.1', () => {
      const headers = [];
      for (let i = 0; i < req.rawHeaders.length; i += 2) {
        headers.push(`${req.rawHeaders[i]}: ${req.rawHeaders[i + 1]}`);
      }
      proxy.write(`${req.method} ${req.url} HTTP/1.1\r\n${headers.join('\r\n')}\r\n\r\n`);
      if (head.length) proxy.write(head);
      socket.pipe(proxy).pipe(socket);
    });
    proxy.on('error', () => socket.destroy());
    socket.on('error', () => proxy.destroy());
    socket.on('close', () => proxy.destroy());
    proxy.on('close', () => socket.destroy());
  });
  server.listen(4850, '127.0.0.1');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  start().catch(() => {
    console.error('Setup browser proxy failed its startup check');
    process.exitCode = 1;
  });
}
