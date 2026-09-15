const API = "/api/v1";
const CART_KEY = "nova-prototype-cart-v1";

const state = {
  stores: [],
  store: null,
  menu: [],
  category: "All",
  query: "",
  cart: loadCart(),
};

const $ = (selector) => document.querySelector(selector);
const money = (value) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(Number(value));

function loadCart() {
  try { return JSON.parse(localStorage.getItem(CART_KEY)) || {}; }
  catch { return {}; }
}
function saveCart() { localStorage.setItem(CART_KEY, JSON.stringify(state.cart)); }
function cartEntries() { return Object.values(state.cart).filter((item) => item.quantity > 0); }
function cartCount() { return cartEntries().reduce((sum, item) => sum + item.quantity, 0); }
function subtotal() { return cartEntries().reduce((sum, item) => sum + Number(item.price) * item.quantity, 0); }
function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("show"), 1800);
}

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

async function bootstrap() {
  try {
    state.stores = await api("/stores");
    if (!state.stores.length) throw new Error("No stores are available.");
    state.store = state.stores[0];
    $("#store-name").textContent = state.store.name;
    $("#store-description").textContent = state.store.description || "Browse the live menu.";
    await loadMenu();
    renderCart();
  } catch (error) {
    $("#catalog-grid").innerHTML = `<div class="empty-state"><h2>Could not load the prototype</h2><p>${escapeHtml(error.message)}</p></div>`;
  }
}

async function loadMenu() {
  state.menu = await api(`/stores/${state.store.id}/menu`);
  renderCategories();
  renderMenu();
}

function renderCategories() {
  const categories = ["All", ...new Set(state.menu.map((item) => item.category))];
  $("#category-tabs").innerHTML = categories.map((category) => `
    <button type="button" class="category-chip ${state.category === category ? "active" : ""}" data-category="${escapeHtml(category)}">
      ${category === "All" ? "★ " : ""}${escapeHtml(category)}
    </button>`).join("");
}

function filteredMenu() {
  const query = state.query.trim().toLowerCase();
  return state.menu.filter((item) => {
    const categoryMatch = state.category === "All" || item.category === state.category;
    const textMatch = !query || `${item.name} ${item.description || ""} ${item.category}`.toLowerCase().includes(query);
    return categoryMatch && textMatch;
  });
}

function renderMenu() {
  const items = filteredMenu();
  const grid = $("#catalog-grid");
  $("#empty-state").classList.toggle("hidden", items.length > 0);
  grid.innerHTML = items.map((item) => {
    const qty = state.cart[item.id]?.quantity || 0;
    return `<article class="food-card" data-id="${item.id}">
      <img class="food-image" src="${escapeAttr(item.image_url || "")}" alt="${escapeAttr(item.name)}" loading="lazy" />
      <div class="food-body">
        <div class="food-title-row"><strong>${escapeHtml(item.name)}</strong><span class="price">${money(item.price)}</span></div>
        <p class="food-description">${escapeHtml(item.description || item.category)}</p>
        <div class="food-footer">
          <div class="qty-control">
            <button type="button" data-action="minus" aria-label="Decrease ${escapeAttr(item.name)}">−</button>
            <span>${qty}</span>
            <button type="button" data-action="plus" aria-label="Increase ${escapeAttr(item.name)}">+</button>
          </div>
          <button type="button" class="add-button" data-action="add">Add item</button>
        </div>
      </div>
    </article>`;
  }).join("");
}

function setQuantity(item, quantity) {
  if (quantity <= 0) delete state.cart[item.id];
  else state.cart[item.id] = { id: item.id, name: item.name, price: Number(item.price), image_url: item.image_url, quantity };
  saveCart();
  renderMenu();
  renderCart();
}

function changeQuantity(id, delta) {
  const item = state.menu.find((entry) => entry.id === Number(id));
  if (!item) return;
  const current = state.cart[item.id]?.quantity || 0;
  setQuantity(item, Math.max(0, current + delta));
}

function renderCart() {
  const items = cartEntries();
  const sub = subtotal();
  const tax = sub * 0.10;
  const total = sub + tax;
  $("#cart-badge").textContent = cartCount();
  $("#cart-empty").classList.toggle("hidden", items.length > 0);
  $("#cart-items").classList.toggle("hidden", items.length === 0);
  $("#cart-items").innerHTML = items.map((item) => `<div class="cart-line">
    <img src="${escapeAttr(item.image_url || "")}" alt="" />
    <div class="cart-line-main"><strong>${escapeHtml(item.name)}</strong><span>${money(item.price)} each</span></div>
    <div class="cart-line-actions">
      <button type="button" data-cart-action="minus" data-id="${item.id}">−</button>
      <b>${item.quantity}</b>
      <button type="button" data-cart-action="plus" data-id="${item.id}">+</button>
    </div>
  </div>`).join("");
  $("#subtotal").textContent = money(sub);
  $("#tax").textContent = money(tax);
  $("#total").textContent = money(total);
  $("#modal-total").textContent = money(total);
  $("#checkout-button").disabled = !items.length;
}

function openCart() { $("#cart-panel").classList.add("open"); $("#cart-overlay").classList.add("show"); }
function closeCart() { $("#cart-panel").classList.remove("open"); $("#cart-overlay").classList.remove("show"); }

async function placeOrder(event) {
  event.preventDefault();
  const button = $("#place-order-button");
  const errorBox = $("#checkout-error");
  errorBox.classList.add("hidden");
  button.disabled = true;
  button.textContent = "Placing order…";
  try {
    const form = new FormData(event.currentTarget);
    const payload = {
      store_id: state.store.id,
      customer_name: form.get("customer_name"),
      customer_email: form.get("customer_email"),
      customer_phone: form.get("customer_phone") || null,
      delivery_address: form.get("delivery_address"),
      notes: form.get("notes") || null,
      items: cartEntries().map((item) => ({ menu_item_id: item.id, quantity: item.quantity })),
    };
    const order = await api("/orders", { method: "POST", body: JSON.stringify(payload) });
    state.cart = {};
    saveCart();
    renderCart();
    toast(`Order #${order.id} created`);
    window.setTimeout(() => { window.location.href = `/track/${order.id}`; }, 450);
  } catch (error) {
    errorBox.textContent = error.message;
    errorBox.classList.remove("hidden");
  } finally {
    button.disabled = false;
    button.textContent = "Place Order";
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}
function escapeAttr(value) { return escapeHtml(value); }

$("#category-tabs").addEventListener("click", (event) => {
  const button = event.target.closest("[data-category]");
  if (!button) return;
  state.category = button.dataset.category;
  renderCategories();
  renderMenu();
});
$("#catalog-grid").addEventListener("click", (event) => {
  const card = event.target.closest("[data-id]");
  const action = event.target.closest("[data-action]")?.dataset.action;
  if (!card || !action) return;
  const delta = action === "minus" ? -1 : 1;
  changeQuantity(card.dataset.id, delta);
  if (action === "add") toast("Added to cart");
});
$("#cart-items").addEventListener("click", (event) => {
  const button = event.target.closest("[data-cart-action]");
  if (!button) return;
  changeQuantity(button.dataset.id, button.dataset.cartAction === "minus" ? -1 : 1);
});
$("#search-input").addEventListener("input", (event) => { state.query = event.target.value; renderMenu(); });
$("#checkout-button").addEventListener("click", () => $("#checkout-modal").showModal());
$("#checkout-close").addEventListener("click", () => $("#checkout-modal").close());
$("#checkout-form").addEventListener("submit", placeOrder);
$("#mobile-cart-button").addEventListener("click", openCart);
$("#close-cart").addEventListener("click", closeCart);
$("#cart-overlay").addEventListener("click", closeCart);
$("#theme-toggle").addEventListener("click", () => {
  const root = document.documentElement;
  const next = root.dataset.theme === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  localStorage.setItem("nova-theme", next);
  $("#theme-toggle").textContent = next === "dark" ? "☀" : "☾";
});

const savedTheme = localStorage.getItem("nova-theme") || "light";
document.documentElement.dataset.theme = savedTheme;
$("#theme-toggle").textContent = savedTheme === "dark" ? "☀" : "☾";
bootstrap();
