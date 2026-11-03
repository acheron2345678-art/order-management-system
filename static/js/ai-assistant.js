/* Phase 12D — accessible, safe chat UI. Server remains the authority for reports and permissions. */
(() => {
    'use strict';

    const MAX_HISTORY = 8;
    const MAX_CHARS = 1200;

    // Pure extractor: highlights only reproduce numbers already present in a
    // single recognized report. They are never calculated from chat history.
    function extractHighlights(source) {
        if (typeof source !== 'string') return null;
        const recognized = /^Verified (?:Swiggy order-performance report|Swiggy order report|inventory) for /gm;
        if ([...source.matchAll(recognized)].length !== 1) return null;

        const inventory = source.match(/Products:\s*(\d+)\s*;\s*Total units:\s*(\d+)\s*;\s*Out of stock:\s*(\d+)\s*;\s*Low stock:\s*(\d+)/i);
        if (inventory) {
            return {
                kind: 'inventory',
                metrics: [
                    ['Products', inventory[1]],
                    ['Stock units', inventory[2]],
                    ['Low stock', inventory[4]],
                    ['Out of stock', inventory[3]],
                ],
            };
        }

        // Comparisons contain multiple windows. Don't display unlabeled cards
        // that could make one month's numbers look like the whole comparison.
        if ([...source.matchAll(/\bTotal orders:\s*\d+/gi)].length > 1) return null;

        const status = source.match(/Total orders:\s*(\d+)\s*;\s*Pending:\s*(\d+)\s*;\s*Processing:\s*(\d+)\s*;\s*Completed:\s*(\d+)\s*;\s*Cancelled:\s*(\d+)/i);
        const total = status ? Number(status[1]) : null;
        const counts = status ? [
            ['Pending', Number(status[2])],
            ['Processing', Number(status[3])],
            ['Completed', Number(status[4])],
            ['Cancelled', Number(status[5])],
        ] : null;
        const revenue = source.match(/Completed-order revenue:\s*(₹\s*[\d,]+(?:\.\d+)?)/i);
        const rate = source.match(/Completion rate:\s*([\d.]+%|N\/A)/i);
        if (status) {
            const metrics = [
                ['Total orders', String(total)],
                ['Completed', status[4]],
                ['Revenue', revenue ? revenue[1].replace(/\s+/g, '') : '—'],
                ['Completion', rate ? rate[1] : '—'],
            ];
            const goodCounts = counts.every(([, number]) => Number.isInteger(number) && number >= 0);
            return {
                kind: 'orders', metrics,
                statuses: goodCounts && total > 0 && counts.reduce((n, [, count]) => n + count, 0) === total ? counts : null,
                total,
            };
        }

        const recorded = source.match(/Total recorded orders:\s*(\d+)/i);
        const simpleRevenue = revenue || source.match(/Completed-order revenue:\s*(₹\s*[\d,]+(?:\.\d+)?)/i);
        if (recorded && simpleRevenue) {
            return { kind: 'revenue', metrics: [
                ['Recorded orders', recorded[1]],
                ['Completed revenue', simpleRevenue[1].replace(/\s+/g, '')],
            ] };
        }
        return null;
    }

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { extractHighlights };
    }
    if (typeof document === 'undefined') return;

    const messages = document.getElementById('om-ai-messages');
    const form = document.getElementById('om-ai-form');
    const input = document.getElementById('om-ai-question');
    const submit = document.getElementById('om-ai-submit');
    const status = document.getElementById('om-ai-status');
    const count = document.getElementById('om-ai-character-count');
    const reset = document.getElementById('om-ai-new-chat');
    const stop = document.getElementById('om-ai-stop');
    if (!messages || !form || !input || !submit || !status || !reset || !stop || !count) return;

    const history = [];
    let contextToken = null;
    let busy = false;
    let controller = null;
    let lastFailedQuestion = null;

    function scrollToLatest() { messages.scrollTop = messages.scrollHeight; }
    function setStatus(message) { status.textContent = message; }
    function updateCharacters() {
        count.textContent = `${input.value.length} / ${MAX_CHARS}`;
        input.style.height = 'auto';
        input.style.height = `${Math.min(input.scrollHeight, 170)}px`;
    }
    function busyState(value) {
        busy = value;
        submit.disabled = value;
        reset.disabled = value;
        stop.classList.toggle('d-none', !value);
        messages.setAttribute('aria-busy', String(value));
    }

    // All model text is inserted through text nodes, never innerHTML.
    function inline(target, raw) {
        const pattern = /(\*\*[^*\n]+\*\*|`[^`\n]+`|\[[^\]\n]+\]\(https?:\/\/[^\s)]+\)|\*[^*\n]+\*)/g;
        let from = 0;
        for (const match of raw.matchAll(pattern)) {
            const at = match.index;
            if (at > from) target.appendChild(document.createTextNode(raw.slice(from, at)));
            const token = match[0];
            if (token.startsWith('**')) {
                const strong = document.createElement('strong');
                strong.textContent = token.slice(2, -2);
                target.appendChild(strong);
            } else if (token.startsWith('`')) {
                const code = document.createElement('code');
                code.textContent = token.slice(1, -1);
                target.appendChild(code);
            } else if (token.startsWith('[')) {
                const split = token.indexOf('](');
                const label = token.slice(1, split);
                const href = token.slice(split + 2, -1);
                try {
                    const url = new URL(href);
                    if (url.protocol !== 'https:' && url.protocol !== 'http:') throw new Error('Unsafe link');
                    const link = document.createElement('a');
                    link.href = url.href;
                    link.target = '_blank';
                    link.rel = 'noopener noreferrer';
                    link.textContent = label;
                    target.appendChild(link);
                } catch (_) {
                    target.appendChild(document.createTextNode(token));
                }
            } else {
                const em = document.createElement('em');
                em.textContent = token.slice(1, -1);
                target.appendChild(em);
            }
            from = at + token.length;
        }
        if (from < raw.length) target.appendChild(document.createTextNode(raw.slice(from)));
    }

    function splitTable(line) {
        return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map(value => value.trim());
    }
    function tableSeparator(line) {
        return /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
    }
    function buildTable(header, rows) {
        const outer = document.createElement('div');
        outer.className = 'omai-table-scroll';
        const table = document.createElement('table');
        const thead = table.createTHead();
        const tr = thead.insertRow();
        header.forEach(value => { const th = document.createElement('th'); inline(th, value); tr.appendChild(th); });
        const tbody = table.createTBody();
        rows.forEach(values => {
            const row = tbody.insertRow();
            header.forEach((_, i) => { const td = row.insertCell(); inline(td, values[i] || ''); });
        });
        outer.appendChild(table);
        return outer;
    }

    function renderMarkdown(raw) {
        const container = document.createElement('div');
        container.className = 'omai-rich-text';
        const lines = String(raw || '').replace(/\r\n?/g, '\n').split('\n');
        let i = 0;
        const isList = line => /^\s*(?:[-*]|\d+[.)])\s+/.test(line);
        const isHeading = line => /^\s*#{1,4}\s+/.test(line);
        const isSpecial = (line, next) => isList(line) || isHeading(line) || /^\s*```/.test(line)
            || /^\s*>\s?/.test(line) || /^\s*(?:---|\*\*\*)\s*$/.test(line)
            || (line.includes('|') && tableSeparator(next || ''));

        while (i < lines.length) {
            const line = lines[i];
            if (!line.trim()) { i++; continue; }

            if (/^\s*```/.test(line)) {
                const language = line.trim().slice(3).trim().slice(0, 24);
                const body = [];
                i++;
                while (i < lines.length && !/^\s*```/.test(lines[i])) body.push(lines[i++]);
                if (i < lines.length) i++;
                const code = document.createElement('div'); code.className = 'omai-code';
                const header = document.createElement('div'); header.className = 'omai-code-head';
                const title = document.createElement('span'); title.textContent = language || 'Code';
                const copy = document.createElement('button'); copy.type = 'button'; copy.textContent = 'Copy code';
                const contents = body.join('\n');
                copy.addEventListener('click', () => copyText(contents, copy));
                header.append(title, copy);
                const pre = document.createElement('pre'); pre.textContent = contents;
                code.append(header, pre); container.appendChild(code);
                continue;
            }
            if (line.includes('|') && i + 1 < lines.length && tableSeparator(lines[i + 1])) {
                const header = splitTable(line); i += 2;
                const rows = [];
                while (i < lines.length && lines[i].includes('|') && lines[i].trim()) rows.push(splitTable(lines[i++]));
                container.appendChild(buildTable(header, rows));
                continue;
            }
            if (/^\s*(?:---|\*\*\*)\s*$/.test(line)) { container.appendChild(document.createElement('hr')); i++; continue; }
            if (isHeading(line)) {
                const depth = (line.trim().match(/^#+/) || ['#'])[0].length;
                const heading = document.createElement(depth <= 2 ? 'h3' : 'h4');
                inline(heading, line.replace(/^\s*#{1,4}\s+/, ''));
                container.appendChild(heading); i++; continue;
            }
            if (isList(line)) {
                const ordered = /^\s*\d+[.)]\s+/.test(line);
                const list = document.createElement(ordered ? 'ol' : 'ul');
                while (i < lines.length && isList(lines[i]) && (/^\s*\d+[.)]\s+/.test(lines[i])) === ordered) {
                    const li = document.createElement('li');
                    inline(li, lines[i].replace(/^\s*(?:[-*]|\d+[.)])\s+/, ''));
                    list.appendChild(li); i++;
                }
                container.appendChild(list); continue;
            }
            if (/^\s*>\s?/.test(line)) {
                const quote = document.createElement('blockquote');
                while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
                    if (quote.childNodes.length) quote.appendChild(document.createElement('br'));
                    inline(quote, lines[i++].replace(/^\s*>\s?/, ''));
                }
                container.appendChild(quote); continue;
            }
            if (line.trim().endsWith(':') && line.trim().length < 72 && i + 1 < lines.length && isList(lines[i + 1])) {
                const heading = document.createElement('h4');
                inline(heading, line.trim()); container.appendChild(heading); i++; continue;
            }
            const paragraph = document.createElement('p');
            while (i < lines.length && lines[i].trim() && (paragraph.childNodes.length === 0 || !isSpecial(lines[i], lines[i + 1]))) {
                if (paragraph.childNodes.length) paragraph.appendChild(document.createElement('br'));
                inline(paragraph, lines[i++]);
            }
            container.appendChild(paragraph);
        }
        return container;
    }

    function reportHighlights(source) {
        const info = extractHighlights(source);
        if (!info) return null;
        const box = document.createElement('div'); box.className = 'omai-report';
        const heading = document.createElement('div'); heading.className = 'omai-report-heading';
        heading.textContent = 'REPORT HIGHLIGHTS'; box.appendChild(heading);
        const metrics = document.createElement('div'); metrics.className = 'omai-metrics';
        info.metrics.forEach(([label, value]) => {
            const metric = document.createElement('div'); metric.className = 'omai-metric';
            const name = document.createElement('span'); name.className = 'omai-metric-label'; name.textContent = label;
            const number = document.createElement('strong'); number.className = 'omai-metric-value'; number.textContent = value;
            metric.append(name, number); metrics.appendChild(metric);
        });
        box.appendChild(metrics);
        if (info.statuses) {
            const label = document.createElement('p'); label.className = 'omai-status-title';
            label.textContent = 'Order status distribution'; box.appendChild(label);
            const track = document.createElement('div'); track.className = 'omai-status-track';
            track.setAttribute('role', 'img');
            track.setAttribute('aria-label', info.statuses.map(([name, value]) => `${name}: ${value}`).join(', '));
            const legend = document.createElement('div'); legend.className = 'omai-status-legend';
            info.statuses.forEach(([name, value]) => {
                if (value === 0) return;
                const cssName = name.toLowerCase();
                const segment = document.createElement('span'); segment.className = `omai-status-${cssName}`;
                segment.style.width = `${value / info.total * 100}%`; track.appendChild(segment);
                const item = document.createElement('span');
                const swatch = document.createElement('i'); swatch.className = `omai-status-${cssName}`;
                item.append(swatch, document.createTextNode(`${name} ${value}`)); legend.appendChild(item);
            });
            box.append(track, legend);
        }
        return box;
    }

    async function copyText(value, button) {
        try {
            await navigator.clipboard.writeText(value);
            const original = button.textContent;
            button.textContent = 'Copied';
            window.setTimeout(() => { if (button.isConnected) button.textContent = original; }, 1500);
        } catch (_) { setStatus('Clipboard access blocked by your browser.'); }
    }

    function bubble(kind, text, options = {}) {
        const article = document.createElement('article');
        article.className = `omai-message omai-message-${kind}`;
        if (options.error) article.classList.add('omai-message-error');
        const avatar = document.createElement('span');
        avatar.className = `omai-avatar omai-avatar-${kind === 'user' ? 'user' : 'ai'}`;
        avatar.setAttribute('aria-hidden', 'true');
        avatar.textContent = kind === 'user' ? 'YOU' : '✦';
        const content = document.createElement('div'); content.className = 'omai-message-content';
        const label = document.createElement('div'); label.className = 'omai-message-label';
        label.textContent = kind === 'user' ? 'You' : (options.denied ? 'Access restricted' : (options.error ? 'Unable to complete' : 'AI Assistant'));
        const surface = document.createElement('div'); surface.className = 'omai-message-surface';
        if (kind === 'user' || options.error || options.denied) surface.textContent = text;
        else {
            const summary = reportHighlights(text);
            if (summary) { article.classList.add('omai-message-report'); surface.appendChild(summary); }
            surface.appendChild(renderMarkdown(text));
        }
        content.append(label, surface);
        if (kind === 'assistant' && !options.pending && !options.denied) {
            const actions = document.createElement('div'); actions.className = 'omai-message-actions';
            if (!options.error) {
                const copy = document.createElement('button'); copy.type = 'button';
                copy.textContent = 'Copy response';
                copy.addEventListener('click', () => copyText(text, copy));
                actions.appendChild(copy);
            } else if (options.question) {
                const retry = document.createElement('button'); retry.type = 'button'; retry.textContent = '↻ Retry question';
                retry.addEventListener('click', () => sendMessage(options.question, false));
                actions.appendChild(retry);
            }
            if (actions.childNodes.length) content.appendChild(actions);
        }
        article.append(avatar, content); messages.appendChild(article);
        scrollToLatest();
        return article;
    }

    function makePending() {
        const article = document.createElement('article'); article.className = 'omai-message omai-message-assistant';
        const avatar = document.createElement('span'); avatar.className = 'omai-avatar omai-avatar-ai';
        avatar.textContent = '✦'; avatar.setAttribute('aria-hidden', 'true');
        const content = document.createElement('div'); content.className = 'omai-message-content';
        const label = document.createElement('div'); label.className = 'omai-message-label'; label.textContent = 'AI Assistant';
        const surface = document.createElement('div'); surface.className = 'omai-message-surface';
        const wrapper = document.createElement('div'); wrapper.className = 'omai-typing';
        wrapper.textContent = 'Preparing your response ';
        const dots = document.createElement('span'); dots.className = 'omai-typing-dots'; dots.setAttribute('aria-hidden', 'true');
        for (let i = 0; i < 3; i++) dots.appendChild(document.createElement('i'));
        wrapper.appendChild(dots); surface.appendChild(wrapper);
        content.append(label, surface); article.append(avatar, content); messages.appendChild(article);
        scrollToLatest(); return article;
    }

    function errorMessage(response, data) {
        if (response.status === 401) return 'Your session expired. Please sign in again.';
        const detail = data && data.detail;
        if (typeof detail === 'string' && detail.trim()) return detail;
        if (Array.isArray(detail)) return detail.map(item => item.msg || 'Invalid input').join('; ');
        return `Request failed (${response.status}).`;
    }

    async function sendMessage(question, showUser = true) {
        if (busy) return;
        question = question.trim();
        if (question.length < 3 || question.length > MAX_CHARS) {
            setStatus(`Please enter 3–${MAX_CHARS} characters.`); return;
        }
        const csrf = window.getCsrfToken?.();
        if (!csrf) { setStatus('Missing CSRF token. Please sign in again.'); return; }
        lastFailedQuestion = null;
        if (showUser) bubble('user', question);
        input.value = '';
        updateCharacters();
        busyState(true);
        setStatus('Processing your request...');
        const pending = makePending();
        let httpStatus = null;
        controller = new AbortController();
        try {
            const response = await fetch('/ai/ask', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
                signal: controller.signal,
                body: JSON.stringify({ question, history: history.slice(-MAX_HISTORY), context_token: contextToken }),
            });
            httpStatus = response.status;
            let data = {};
            try { data = await response.json(); } catch (_) { /* backend errors may be non-JSON */ }
            if (!response.ok) throw new Error(errorMessage(response, data));
            if (typeof data.answer !== 'string' || !data.answer.trim()) throw new Error('The assistant returned an empty response.');
            pending.remove();
            bubble('assistant', data.answer);
            contextToken = typeof data.context_token === 'string' ? data.context_token : null;
            history.push({ role: 'user', content: question });
            history.push({ role: 'assistant', content: data.answer.slice(0, MAX_CHARS) });
            while (history.length > MAX_HISTORY) history.shift();
            setStatus('Ready');
        } catch (error) {
            pending.remove();
            lastFailedQuestion = question;
            const cancelled = error && error.name === 'AbortError';
            const message = cancelled
                ? 'Stopped waiting for this response. The local server may still be processing the request.'
                : (error.message || 'Unable to reach the AI service.');
            const denied = httpStatus === 403;
            bubble('assistant', message, denied ? { denied: true } : { error: true, question });
            setStatus(denied ? 'Access restricted' : (cancelled ? 'Request stopped' : 'Request failed'));
        } finally {
            controller = null;
            busyState(false);
            input.focus();
        }
    }

    reset.addEventListener('click', () => {
        if (busy) return;
        if (history.length && !window.confirm('Start a new conversation? This will clear the visible chat and follow-up context.')) return;
        history.length = 0;
        contextToken = null;
        lastFailedQuestion = null;
        messages.replaceChildren();
        bubble('assistant', 'New conversation started. Ask about your orders, inventory, reports, or how the application works.');
        input.value = '';
        updateCharacters();
        setStatus('Ready');
        input.focus();
    });
    stop.addEventListener('click', () => { if (controller) controller.abort(); });
    document.querySelectorAll('[data-ai-question]').forEach(button => {
        button.addEventListener('click', () => {
            if (busy) return;
            input.value = button.dataset.aiQuestion || '';
            updateCharacters(); input.focus();
        });
    });
    input.addEventListener('input', updateCharacters);
    input.addEventListener('keydown', event => {
        if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
            event.preventDefault();
            if (!busy) form.requestSubmit();
        }
    });
    form.addEventListener('submit', event => {
        event.preventDefault();
        if (busy) return;
        sendMessage(input.value);
    });
    updateCharacters();
})();
