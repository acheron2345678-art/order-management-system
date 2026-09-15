const API = "/api/v1";
const $ = (s) => document.querySelector(s);
const money = (v) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(Number(v));
const NEXT_ACTION = {
  PENDING: ["Accept", "CONFIRMED"],
  CONFIRMED: ["Start Preparing", "PREPARING"],
  PREPARING: ["Dispatch", "OUT_FOR_DELIVERY"],
  OUT_FOR_DELIVERY: ["Mark Delivered", "DELIVERED"],
};
const state = { stores: [], storeId: null, revenueChart: null, statusChart: null, socket: null };

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  if (!response.ok) { const data = await response.json().catch(() => ({})); throw new Error(data.detail || `Request failed (${response.status})`); }
  return response.json();
}
function toast(message){const node=$("#toast");node.textContent=message;node.classList.add("show");clearTimeout(toast.timer);toast.timer=setTimeout(()=>node.classList.remove("show"),1700)}

async function bootstrap() {
  state.stores = await api("/stores?open_only=false");
  if (!state.stores.length) return;
  $("#store-select").innerHTML = state.stores.map((store) => `<option value="${store.id}">${escapeHtml(store.name)}</option>`).join("");
  state.storeId = state.stores[0].id;
  await refreshAll();
  connectMerchantSocket();
}

async function refreshAll() {
  await Promise.all([loadAnalytics(), loadOrders()]);
}

async function loadAnalytics() {
  const data = await api(`/dashboard/analytics?store_id=${state.storeId}`);
  $("#metric-revenue").textContent = money(data.total_revenue);
  $("#metric-active").textContent = data.active_orders;
  $("#metric-orders").textContent = data.order_count;
  $("#metric-aov").textContent = money(data.average_order_value);
  renderRevenueChart(data.revenue_trend);
  renderStatusChart(data.status_breakdown);
  $("#top-items").innerHTML = data.top_items.length ? data.top_items.map((item, index) => `<div class="top-item"><span class="top-rank">${index + 1}</span><div><strong>${escapeHtml(item.name)}</strong><small>${item.quantity} sold</small></div><span>${money(item.revenue)}</span></div>`).join("") : `<div class="empty-row">Top items appear after orders are placed.</div>`;
}

async function loadOrders() {
  const orders = await api(`/dashboard/orders?store_id=${state.storeId}&limit=50`);
  $("#orders-empty").classList.toggle("hidden", orders.length > 0);
  $("#orders-body").innerHTML = orders.map((order) => {
    const next = NEXT_ACTION[order.status];
    const items = order.items.map((item) => `${item.quantity}× ${escapeHtml(item.item_name)}`).join(", ");
    return `<tr>
      <td><span class="order-id">#${order.id}</span><br><small>${new Date(order.created_at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</small></td>
      <td><strong>${escapeHtml(order.customer_name)}</strong><br><small>${escapeHtml(order.customer_email)}</small></td>
      <td title="${escapeAttr(items)}">${items.length > 42 ? items.slice(0, 42) + "…" : items}</td>
      <td><strong>${money(order.total_amount)}</strong></td>
      <td><span class="status ${order.status}">${order.status.replaceAll("_", " ")}</span></td>
      <td>${next ? `<button class="action-button" data-order="${order.id}" data-status="${next[1]}">${next[0]}</button>${["PENDING","CONFIRMED","PREPARING"].includes(order.status) ? `<button class="action-button cancel" data-order="${order.id}" data-status="CANCELLED">Cancel</button>` : ""}` : "—"}</td>
    </tr>`;
  }).join("");
}

async function updateStatus(orderId, status) {
  try {
    await api(`/orders/${orderId}/status`, { method: "PATCH", body: JSON.stringify({ status }) });
    toast(`Order #${orderId} → ${status.replaceAll("_", " ")}`);
    await refreshAll();
  } catch (error) { toast(error.message); }
}

function renderRevenueChart(points) {
  const labels = points.map((p) => new Date(`${p.date}T00:00:00`).toLocaleDateString([], { weekday: "short" }));
  const values = points.map((p) => Number(p.revenue));
  if (state.revenueChart) state.revenueChart.destroy();
  state.revenueChart = new Chart($("#revenue-chart"), { type: "line", data: { labels, datasets: [{ label: "Revenue", data: values, borderColor: "#ff6824", backgroundColor: "rgba(255,104,36,.10)", fill: true, tension: .35, pointRadius: 3 }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { grid: { display: false } }, y: { beginAtZero: true, ticks: { callback: (v) => `₹${v}` } } } } });
}
function renderStatusChart(rows) {
  const nonZero = rows.filter((row) => row.count > 0);
  if (state.statusChart) state.statusChart.destroy();
  state.statusChart = new Chart($("#status-chart"), { type: "doughnut", data: { labels: nonZero.map((r) => r.status.replaceAll("_", " ")), datasets: [{ data: nonZero.map((r) => r.count), backgroundColor: ["#e8a828", "#ff6824", "#f08b43", "#4777f5", "#1c9c69", "#d95542"], borderWidth: 0 }] }, options: { responsive: true, maintainAspectRatio: false, cutout: "68%", plugins: { legend: { position: "bottom", labels: { boxWidth: 9, usePointStyle: true, padding: 13 } } } } });
}

function connectMerchantSocket() {
  if (state.socket) state.socket.close();
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/ws/merchants/${state.storeId}`);
  state.socket = socket;
  socket.addEventListener("open", () => { $(".live-dot").classList.add("live"); $("#socket-label").textContent = "Realtime connected"; });
  socket.addEventListener("message", async (event) => { const payload = JSON.parse(event.data); if (["ORDER_CREATED","ORDER_STATUS_UPDATED"].includes(payload.type)) await refreshAll(); });
  socket.addEventListener("close", () => { $(".live-dot").classList.remove("live"); $("#socket-label").textContent = "Reconnecting…"; if (state.socket === socket) setTimeout(connectMerchantSocket, 1800); });
}
function escapeHtml(value){return String(value??"").replace(/[&<>'"]/g,(c)=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]))}function escapeAttr(value){return escapeHtml(value)}

$("#orders-body").addEventListener("click", (event) => { const button = event.target.closest("[data-order]"); if (button) updateStatus(button.dataset.order, button.dataset.status); });
$("#refresh-button").addEventListener("click", refreshAll);
$("#store-select").addEventListener("change", async (event) => { state.storeId = Number(event.target.value); await refreshAll(); connectMerchantSocket(); });
$("#theme-toggle").addEventListener("click", () => { const root=document.documentElement;const next=root.dataset.theme==="dark"?"light":"dark";root.dataset.theme=next;localStorage.setItem("nova-theme",next);$("#theme-toggle").textContent=next==="dark"?"☀":"☾"; });
const theme=localStorage.getItem("nova-theme")||"light";document.documentElement.dataset.theme=theme;$("#theme-toggle").textContent=theme==="dark"?"☀":"☾";
bootstrap().catch((error) => toast(error.message));
