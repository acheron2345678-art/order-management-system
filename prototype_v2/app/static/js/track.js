const API = "/api/v1";
const orderId = Number(document.body.dataset.orderId);
const FLOW = ["PENDING", "PREPARING", "OUT_FOR_DELIVERY", "DELIVERED"];
const LABELS = { PENDING: "Pending", CONFIRMED: "Confirmed", PREPARING: "Preparing", OUT_FOR_DELIVERY: "Out for delivery", DELIVERED: "Delivered", CANCELLED: "Cancelled" };
const DESCRIPTIONS = { PENDING: "We received your order.", CONFIRMED: "The store accepted your order.", PREPARING: "Your order is being prepared.", OUT_FOR_DELIVERY: "Your order is on the way.", DELIVERED: "Delivered. Enjoy your meal!", CANCELLED: "This order was cancelled." };
const $ = (s) => document.querySelector(s);
const money = (v) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(Number(v));

function renderTimeline(status) {
  const effective = status === "CONFIRMED" ? "PENDING" : status;
  const index = FLOW.indexOf(effective);
  $("#timeline").innerHTML = FLOW.map((step, i) => `<div class="step ${status !== "CANCELLED" && i < index ? "done" : ""} ${status !== "CANCELLED" && i === index ? "active" : ""}">
    <div class="step-dot">${i + 1}</div><strong>${LABELS[step]}</strong><span>${i === index ? "Current" : i < index ? "Completed" : "Upcoming"}</span>
  </div>`).join("");
}

function renderOrder(order) {
  renderTimeline(order.status);
  $("#status-copy").textContent = DESCRIPTIONS[order.status] || "Order status updated.";
  $("#order-status").textContent = LABELS[order.status] || order.status;
  $("#order-items").innerHTML = order.items.map((item) => `<div class="order-item"><div><strong>${escapeHtml(item.item_name)}</strong><span>${item.quantity} × ${money(item.unit_price)}</span></div><strong>${money(item.line_total)}</strong></div>`).join("");
  $("#subtotal").textContent = money(order.subtotal);
  $("#tax").textContent = money(order.tax_amount);
  $("#total").textContent = money(order.total_amount);
  $("#customer").textContent = order.customer_name;
  $("#address").textContent = order.delivery_address;
  $("#placed").textContent = new Date(order.created_at).toLocaleString();
}

async function loadOrder() {
  const response = await fetch(`${API}/orders/${orderId}`);
  if (!response.ok) throw new Error("Order not found");
  const order = await response.json();
  renderOrder(order);
}

function connectSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/ws/orders/${orderId}`);
  socket.addEventListener("open", () => { $(".connection-pill").classList.add("live"); $("#connection-label").textContent = "Live"; });
  socket.addEventListener("message", async (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "ORDER_STATUS_UPDATED") await loadOrder();
  });
  socket.addEventListener("close", () => {
    $(".connection-pill").classList.remove("live"); $("#connection-label").textContent = "Reconnecting";
    setTimeout(connectSocket, 1800);
  });
}

function escapeHtml(value) { return String(value ?? "").replace(/[&<>'"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c])); }
$("#theme-toggle").addEventListener("click", () => { const root=document.documentElement; const next=root.dataset.theme==="dark"?"light":"dark"; root.dataset.theme=next; localStorage.setItem("nova-theme",next); $("#theme-toggle").textContent=next==="dark"?"☀":"☾"; });
const theme=localStorage.getItem("nova-theme")||"light";document.documentElement.dataset.theme=theme;$("#theme-toggle").textContent=theme==="dark"?"☀":"☾";
loadOrder().then(connectSocket).catch((error) => { $("#status-copy").textContent = error.message; });
