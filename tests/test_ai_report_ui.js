/* Optional frontend regression checks: node tests/test_ai_report_ui.js */
'use strict';
const assert = require('node:assert/strict');
const { extractHighlights, normalizeAssistantText } = require('../static/js/ai-assistant.js');

const broken = 'Completed revenu&#x65;\\\nSeptember 2026:\nPending 2';
assert.equal(normalizeAssistantText(broken), 'Completed revenue\nSeptember 2026:\nPending 2');
assert.equal(normalizeAssistantText('safe &#60;script&#62;'), 'safe <script>');
assert.equal(normalizeAssistantText('bad &#xD800;'), 'bad &#xD800;');

const report = [
  'Verified Swiggy order-performance report for City Kitchen.',
  'September 2026:',
  '- Total orders: 6; Pending: 2; Processing: 0; Completed: 4; Cancelled: 0',
  '- Completion rate: 66.7%; Cancellation rate: 0.0%',
  '- Completed-order revenue: ₹994.00',
].join('\n');
const summary = extractHighlights(report);
assert.equal(summary.total, 6);
assert.deepEqual(summary.metrics[2], ['Completed revenue', '₹994.00']);
assert.deepEqual(summary.statuses, [
  ['Pending', 2], ['Processing', 0], ['Completed', 4], ['Cancelled', 0],
]);
assert.equal(extractHighlights(report + '\nTotal orders: 7'), null); // comparisons need context
console.log('AI report UI text/extraction checks passed');
