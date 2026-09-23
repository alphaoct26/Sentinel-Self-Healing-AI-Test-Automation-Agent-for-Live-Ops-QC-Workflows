const http = require('http');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = process.env.PORT || 3001;
let CURRENT_DRIFT_MODE = (process.env.DRIFT_MODE || 'NORMAL').toUpperCase();

const server = http.createServer((req, res) => {
    const parsedUrl = url.parse(req.url, true);
    const pathname = parsedUrl.pathname;
    const method = req.method.toUpperCase();

    if (parsedUrl.query.drift) {
        const inputMode = parsedUrl.query.drift.toUpperCase();
        if (['NORMAL', 'SELECTOR_DRIFT', 'ASSERTION_DRIFT', 'REAL_BUG'].includes(inputMode)) {
            CURRENT_DRIFT_MODE = inputMode;
        }
    }

    if (method === 'GET' && (pathname === '/' || pathname === '/index.html')) {
        const viewPath = path.join(__dirname, 'views', 'index.html');
        fs.readFile(viewPath, 'utf8', (err, content) => {
            if (err) {
                res.writeHead(500, { 'Content-Type': 'text/plain' });
                return res.end('Error loading template');
            }

            let refreshBtnId = CURRENT_DRIFT_MODE === 'SELECTOR_DRIFT' ? 'reload-leaderboard-btn' : 'refresh-btn';
            let rankBadgeText = CURRENT_DRIFT_MODE === 'ASSERTION_DRIFT' ? 'Current Tier: Elite' : 'Top Rank: Elite';

            let rendered = content
                .replace(/{{DRIFT_MODE}}/g, CURRENT_DRIFT_MODE)
                .replace(/{{REFRESH_BTN_ID}}/g, refreshBtnId)
                .replace(/{{RANK_BADGE_TEXT}}/g, rankBadgeText);

            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
            res.end(rendered);
        });

    } else if (method === 'GET' && (pathname === '/api/drift' || pathname === '/api/drift-mode')) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ mode: CURRENT_DRIFT_MODE }));

    } else if (method === 'POST' && (pathname === '/api/drift' || pathname === '/api/drift-mode')) {
        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', () => {
            try {
                const data = JSON.parse(body);
                const inputMode = (data.mode || '').toUpperCase();
                if (['NORMAL', 'SELECTOR_DRIFT', 'ASSERTION_DRIFT', 'REAL_BUG'].includes(inputMode)) {
                    CURRENT_DRIFT_MODE = inputMode;
                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    return res.end(JSON.stringify({ status: 'updated', mode: CURRENT_DRIFT_MODE }));
                }
            } catch (e) {}
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Invalid drift mode' }));
        });

    } else if (method === 'POST' && pathname === '/api/export-pdf') {
        if (CURRENT_DRIFT_MODE === 'REAL_BUG') {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            return res.end(JSON.stringify({
                error: 'Internal Server Error: PDF generation engine crashed (Status 500)'
            }));
        }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            status: 'success',
            pdf_url: '/download/resume_optimized.pdf'
        }));

    } else {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('Not Found');
    }
});

server.listen(PORT, () => {
    console.log(`[Sentinel TargetApp] Server running on port ${PORT} (Initial Mode: ${CURRENT_DRIFT_MODE})`);
});
