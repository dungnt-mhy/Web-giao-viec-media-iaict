"use strict";

/* Giao Việc IAICT — PWA frontend (vanilla JS, no build step).
   The server remains the only authority for permissions; this file
   only decides what to *show* based on /api/auth/me. */

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

const CHANNELS = [
  { key: "website", icon: "🌐", name: "Website", kind: "article" },
  { key: "facebook", icon: "📘", name: "Facebook", kind: "post" },
  { key: "instagram", icon: "📸", name: "Instagram", kind: "carousel" },
  { key: "video_vertical", icon: "🎬", name: "Video dọc", kind: "video" },
  { key: "video_horizontal", icon: "🎞", name: "Video ngang", kind: "video" },
];
const CHANNEL_MAP = Object.fromEntries(CHANNELS.map((c) => [c.key, c]));
const STATUS_LABELS = {
  DRAFT: "Nháp",
  PENDING: "Chờ duyệt",
  APPROVED_WAITING: "Đã duyệt, chờ đăng",
  PUBLISHED: "Đã đăng",
  REJECTED: "Bị trả lại",
  CANCELLED: "Đã hủy",
  RETRACTED: "Đã thu hồi",
};
const ROLE_OPTIONS = [
  ["admin", "Admin"],
  ["deputy_admin", "Phó Admin"],
  ["editor", "Biên tập viên"],
  ["writer", "Nhân viên viết bài"],
  ["contributor", "Cộng tác viên"],
];

/* Shown in the UI (Thông báo / Người dùng) so a stale cached shell is
   visible at a glance — TD-0009. Keep in step with the server VERSION. */
const APP_VERSION = "0.3.2";

/* Status filter chips on the Việc screen, in the owner's order. */
const STATUS_CHIPS = [
  ["", "🗂", "Tất cả"],
  ["DRAFT", "📝", "Nháp"],
  ["PENDING", "⏳", "Chờ duyệt"],
  ["APPROVED_WAITING", "✅", "Đã duyệt · chờ đăng"],
  ["PUBLISHED", "🚀", "Đã đăng"],
  ["REJECTED", "↩️", "Bị trả lại"],
  ["RETRACTED", "↩️", "Đã thu hồi"],
  ["CANCELLED", "🗑", "Đã hủy"],
];

const state = {
  me: null,
  route: "dashboard",
  taskCode: null,
  period: "all",
  taskStatus: "",
  wizard: null,
  usersCache: [],
};

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function fmtTime(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh", hour: "2-digit", minute: "2-digit",
    day: "2-digit", month: "2-digit", year: "numeric",
  }).format(date);
}

function fmtBytes(size) {
  if (!size && size !== 0) return "";
  const units = ["B", "KB", "MB", "GB"];
  let value = size, i = 0;
  while (value >= 1024 && i < units.length - 1) { value /= 1024; i++; }
  return `${value.toFixed(i ? 1 : 0)} ${units[i]}`;
}

function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.className = `toast show${isError ? " error" : ""}`;
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => el.classList.remove("show"), 3600);
}

async function api(path, options = {}) {
  const response = await fetch(path, { credentials: "same-origin", ...options });
  if (response.status === 401 && !path.startsWith("/api/auth/login")) {
    showLogin();
    throw new Error("Phiên đăng nhập đã hết hạn.");
  }
  const type = response.headers.get("Content-Type") || "";
  const data = type.includes("application/json")
    ? await response.json().catch(() => ({})) : {};
  if (!response.ok) {
    const err = new Error(data.error || `Lỗi ${response.status}`);
    err.status = response.status;
    err.data = data;
    throw err;
  }
  return data;
}

function apiJson(path, method, body) {
  return api(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

function statusPill(status) {
  const cls = status === "PUBLISHED" ? "ok"
    : status === "PENDING" || status === "APPROVED_WAITING" ? "warn"
    : status === "REJECTED" || status === "CANCELLED" ? "danger" : "info";
  return `<span class="pill ${cls}">${esc(STATUS_LABELS[status] || status)}</span>`;
}

function channelName(key) {
  return CHANNEL_MAP[key]?.name || key;
}

/* ============================ navigation ============================ */

function navItems() {
  const me = state.me;
  const items = [
    { route: "dashboard", icon: "🏠", label: "Tổng quan" },
    { route: "tasks", icon: "📋", label: "Việc" },
    { route: "create", icon: "➕", label: "Giao việc" },
  ];
  if (me.can_review) {
    items.push(
      { route: "review", icon: "⏳", label: "Chờ duyệt" },
      { route: "schedule", icon: "🕐", label: "Lịch đăng" },
      { route: "stats", icon: "📊", label: "Thống kê" },
    );
  }
  if (me.can_manage_users) {
    items.push({ route: "users", icon: "👥", label: "Người dùng" });
  }
  items.push({ route: "notifications", icon: "🔔", label: "Thông báo", badge: true });
  return items;
}

function renderNav(unread = null) {
  const items = navItems();
  const html = items.map((item) => `
    <button class="nav-btn ${state.route === item.route || (item.route === "tasks" && state.route === "detail") ? "active" : ""}"
      data-nav="${item.route}">
      <span>${item.icon}</span><span>${item.label}</span>
      ${item.badge ? `<span class="badge" data-unread-badge ${unread ? "" : "hidden"}>${unread || ""}</span>` : ""}
    </button>`).join("");
  $("#sideNav").innerHTML = html;
  $("#mobileNav").innerHTML = html;
  const bottomOrder = ["dashboard", "tasks", "create",
    state.me.can_review ? "review" : "notifications", "stats"];
  const bottomItems = items.filter((i) => bottomOrder.includes(i.route));
  if (!state.me.can_review) {
    bottomItems.push(...items.filter((i) => i.route === "schedule"));
  }
  $("#bottomNav").innerHTML = bottomItems.slice(0, 5).map((item) => `
    <button class="nav-btn ${state.route === item.route ? "active" : ""}" data-nav="${item.route}" aria-label="${item.label}">
      <span>${item.icon}</span><span>${item.label}</span>
      ${item.badge ? `<span class="badge" data-unread-badge ${unread ? "" : "hidden"}>${unread || ""}</span>` : ""}
    </button>`).join("");
  $$("[data-nav]").forEach((btn) =>
    btn.addEventListener("click", () => navigate(btn.dataset.nav)));
  if (unread !== null) updateBadges(unread);
}

function updateBadges(unread) {
  $("#bellBadge").hidden = !unread;
  $("#bellBadge").textContent = unread || "";
  $$("[data-unread-badge]").forEach((badge) => {
    badge.hidden = !unread;
    badge.textContent = unread || "";
  });
}

async function refreshBadge() {
  try {
    const data = await api("/api/notifications");
    updateBadges(data.unread);
    return data;
  } catch { return null; }
}

function navigate(route, taskCode = null) {
  state.route = route;
  state.taskCode = taskCode;
  renderNav();
  const screen = $("#screen");
  screen.innerHTML = `<div class="loading">⏳ Đang tải…</div>`;
  screen.focus({ preventScroll: true });
  const renderers = {
    dashboard: renderDashboard, tasks: renderTasks, create: renderCreate,
    detail: renderDetail, review: renderReview, schedule: renderSchedule,
    stats: renderStats, users: renderUsers,
    notifications: renderNotifications,
  };
  (renderers[route] || renderDashboard)().catch((err) => {
    screen.innerHTML = `<div class="empty">❌ ${esc(err.message)}</div>`;
  });
  refreshBadge();
}

/* ============================== auth ============================== */

function showLogin() {
  $("#appView").hidden = true;
  $("#loginView").hidden = false;
}

function showApp() {
  $("#loginView").hidden = true;
  $("#appView").hidden = false;
  const me = state.me;
  $("#sideAvatar").textContent = (me.display_name || "?").trim().charAt(0).toUpperCase();
  $("#sideUserName").textContent = me.display_name;
  $("#sideUserRole").textContent = `${me.role_title}${me.can_publish ? " · có quyền đăng" : ""}`;
  // Push notifications deep-link with ?task=CV-xxxx: open that task.
  const taskParam = new URLSearchParams(location.search).get("task");
  if (taskParam) navigate("detail", taskParam);
  else navigate("dashboard");
}

async function boot() {
  try {
    const data = await api("/api/auth/me");
    state.me = data.user;
    showApp();
  } catch {
    showLogin();
  }
}

$("#loginForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("#loginError").textContent = "";
  try {
    const data = await apiJson("/api/auth/login", "POST", {
      login: $("#loginInput").value.trim(),
      password: $("#passwordInput").value,
    });
    state.me = data.user;
    $("#passwordInput").value = "";
    showApp();
    toast(`Xin chào ${data.user.display_name}!`);
  } catch (err) {
    $("#loginError").textContent = err.message;
  }
});

async function logout() {
  await apiJson("/api/auth/logout", "POST").catch(() => {});
  state.me = null;
  showLogin();
}
$("#logoutBtn").addEventListener("click", logout);
$("#logoutBtnMobile").addEventListener("click", logout);
$("#bellBtn").addEventListener("click", () => navigate("notifications"));

/* ============================= modals ============================= */

function openModal(html) {
  $("#modalRoot").innerHTML = `<div class="modal-backdrop"><div class="modal" role="dialog" aria-modal="true">${html}</div></div>`;
  $(".modal-backdrop").addEventListener("click", (event) => {
    if (event.target.classList.contains("modal-backdrop")) closeModal();
  });
}
function closeModal() { $("#modalRoot").innerHTML = ""; }

function confirmModal(title, body, okLabel = "Xác nhận") {
  return new Promise((resolve) => {
    openModal(`
      <h3>${esc(title)}</h3><p>${esc(body)}</p>
      <div class="modal-actions">
        <button class="btn" data-close>Hủy</button>
        <button class="btn btn-danger" data-ok>${esc(okLabel)}</button>
      </div>`);
    $("[data-close]").addEventListener("click", () => { closeModal(); resolve(false); });
    $("[data-ok]").addEventListener("click", () => { closeModal(); resolve(true); });
  });
}

function reasonModal(title, label) {
  return new Promise((resolve) => {
    openModal(`
      <h3>${esc(title)}</h3>
      <label class="field">${esc(label)}
        <textarea id="reasonText" rows="4" required placeholder="Nhập nguyên văn nội dung cần sửa…"></textarea>
      </label>
      <div class="modal-actions">
        <button class="btn" data-close>Hủy</button>
        <button class="btn btn-primary" data-ok>Gửi</button>
      </div>`);
    $("#reasonText").focus();
    $("[data-close]").addEventListener("click", () => { closeModal(); resolve(null); });
    $("[data-ok]").addEventListener("click", () => {
      const value = $("#reasonText").value.trim();
      if (!value) { toast("Cần nhập nội dung.", true); return; }
      closeModal(); resolve(value);
    });
  });
}

function passwordModal() {
  openModal(`
    <h3>🔐 Đổi mật khẩu</h3>
    <form id="passwordForm" class="form-stack">
      <label>Mật khẩu hiện tại<input type="password" id="oldPassword" autocomplete="current-password" required></label>
      <label>Mật khẩu mới (ít nhất 8 ký tự)<input type="password" id="newPassword" autocomplete="new-password" required minlength="8"></label>
      <label>Nhập lại mật khẩu mới<input type="password" id="newPassword2" autocomplete="new-password" required minlength="8"></label>
      <p class="error-text" id="passwordError"></p>
      <div class="modal-actions">
        <button type="button" class="btn" data-close>Đóng</button>
        <button type="submit" class="btn btn-primary">Đổi mật khẩu</button>
      </div>
    </form>`);
  $("[data-close]").addEventListener("click", closeModal);
  $("#passwordForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    if ($("#newPassword").value !== $("#newPassword2").value) {
      $("#passwordError").textContent = "Mật khẩu mới nhập lại không khớp.";
      return;
    }
    try {
      await apiJson("/api/auth/change-password", "POST", {
        old_password: $("#oldPassword").value,
        new_password: $("#newPassword").value,
      });
      closeModal();
      toast("✅ Đã đổi mật khẩu. Các phiên đăng nhập khác đã bị đăng xuất.");
    } catch (err) {
      $("#passwordError").textContent = err.message;
    }
  });
}
$("#passwordBtn").addEventListener("click", passwordModal);
$("#passwordBtnMobile").addEventListener("click", passwordModal);

/* ============================ dashboard ============================ */

async function renderDashboard() {
  const me = state.me;
  const [tasks, notifications, review, scheduled, statsData, daily] = await Promise.all([
    api("/api/tasks?limit=100"),
    api("/api/notifications").catch(() => ({ items: [], unread: 0 })),
    me.can_review ? api("/api/review-queue").catch(() => ({ items: [] })) : Promise.resolve({ items: [] }),
    me.can_review ? api("/api/scheduled").catch(() => ({ items: [] })) : Promise.resolve({ items: [] }),
    me.can_review ? api("/api/stats/summary?period=all").catch(() => null) : Promise.resolve(null),
    api("/api/stats/daily-summary").catch(() => null),
  ]);
  updateBadges(notifications.unread);
  const working = tasks.items.filter((t) => ["DRAFT", "PENDING"].includes(t.status)).length;
  const nextSchedule = scheduled.items[0];
  $("#screen").innerHTML = `
    <div class="page-head">
      <div><h2>🏠 Tổng quan</h2><p>Xin chào ${esc(me.display_name)} · ${esc(me.role_title)}</p></div>
      <button class="btn btn-primary" id="dashCreate">📝 Giao việc mới</button>
    </div>
    <div class="grid grid-4">
      <div class="card metric"><span>📋 Tổng số việc</span><strong>${tasks.total}</strong><span>${working} việc Muse đang làm / chờ duyệt</span></div>
      <div class="card metric"><span>⏳ Thẻ kênh chờ duyệt</span><strong>${review.items.length}</strong><span>${me.can_review ? "Bạn có quyền duyệt" : "Chỉ người duyệt xem"}</span></div>
      <div class="card metric"><span>🕐 Bài đang đặt lịch</span><strong>${scheduled.items.length}</strong><span>${nextSchedule ? `Sắp nhất: ${fmtTime(nextSchedule.scheduled_at)}` : "Chưa có lịch"}</span></div>
      <div class="card metric"><span>✅ Đầu ra đã đăng</span><strong>${statsData ? statsData.published_total : "—"}</strong><span>${statsData ? `trên tổng ${statsData.outputs_total} đầu ra` : "Thống kê dành cho người duyệt"}</span></div>
    </div>
    ${daily ? `
    <section class="card" style="margin-top:1rem">
      <div class="row-item"><h3>🌆 Tổng kết hôm nay</h3><span class="pill info">${esc(daily.label)}</span></div>
      <p class="meta-line">🗂 Việc tạo mới: <strong>${daily.tasks_created}</strong> · 🚀 Đã đăng: <strong>${daily.published_today}</strong> · ⏳ Đang chờ duyệt: <strong>${daily.pending_review}</strong> đầu ra · 🕐 Đang chờ đăng: <strong>${daily.approved_waiting}</strong> đầu ra</p>
      <p class="meta-line">${Object.entries(daily.outputs_by_status || {}).map(([s, n]) => `<span class="channel-chip">${esc(STATUS_LABELS[s] || s)}: ${n}</span>`).join(" ") || "Chưa có đầu ra nào hôm nay."}</p>
    </section>` : ""}
    <div class="grid grid-2" style="margin-top:1rem">
      <section class="card">
        <div class="row-item"><h3>🕘 Việc gần đây</h3><button class="btn btn-small" data-go="tasks">Xem tất cả</button></div>
        <div class="list">${tasks.items.slice(0, 6).map(taskRow).join("") || `<p class="muted">Chưa có việc nào.</p>`}</div>
      </section>
      <section class="card">
        <div class="row-item"><h3>🔔 Hoạt động liên quan tới bạn</h3><button class="btn btn-small" data-go="notifications">Mở hộp thông báo</button></div>
        <div class="list">${notifications.items.slice(0, 6).map(notificationRow).join("") || `<p class="muted">Chưa có thông báo nào.</p>`}</div>
      </section>
    </div>`;
  $("#dashCreate").addEventListener("click", () => navigate("create"));
  $$("[data-go]").forEach((b) => b.addEventListener("click", () => navigate(b.dataset.go)));
  bindTaskCards();
  bindNotificationRows();
}

function taskRow(task) {
  return `
    <article class="card task-card" data-task="${esc(task.code)}" style="box-shadow:none">
      <div class="row-item">
        <div class="row-main">
          <strong>🧾 ${esc(task.code)} — ${esc(task.hint || "(chưa có gợi ý)")}</strong>
          <p class="meta-line">👤 ${esc(task.creator_name || task.creator_id)} · ${fmtTime(task.created_at)}</p>
          <p class="meta-line">🎯 ${(task.destinations || []).map((d) => `<span class="channel-chip">${esc(CHANNEL_MAP[d]?.icon || "")} ${esc(channelName(d))}</span>`).join(" ")}</p>
        </div>${statusPill(task.status)}
      </div>
    </article>`;
}

function bindTaskCards(root = document) {
  $$("[data-task]", root).forEach((card) =>
    card.addEventListener("click", () => navigate("detail", card.dataset.task)));
}

/* ============================== tasks ============================== */

async function renderTasks() {
  const me = state.me;
  let users = [];
  if (me.can_manage_users) {
    users = (await api("/api/users").catch(() => ({ items: [] }))).items;
  }
  // TD-0009: the status filter survives leaving/returning to this
  // screen — kept in state, mirrored to the URL hash (#tasks?status=…).
  const hashParams = new URLSearchParams(location.hash.split("?")[1] || "");
  const hashStatus = hashParams.get("status");
  if (hashStatus !== null
      && STATUS_CHIPS.some(([code]) => code === hashStatus)) {
    state.taskStatus = hashStatus;
  }
  $("#screen").innerHTML = `
    <div class="page-head">
      <div><h2>📋 Danh sách việc</h2><p>Tìm kiếm và lọc theo trạng thái, kênh, người tạo.</p></div>
      <button class="btn btn-primary" id="tasksCreate">📝 Giao việc mới</button>
    </div>
    <form id="taskFilters" class="filters">
      <input name="q" placeholder="🔎 Tìm theo mã việc hoặc gợi ý…">
      <select name="channel"><option value="">Tất cả kênh</option>
        ${CHANNELS.map((c) => `<option value="${c.key}">${c.icon} ${c.name}</option>`).join("")}</select>
      <select name="creator"><option value="">Tất cả người tạo</option>
        <option value="${me.id}">Của tôi</option>
        ${users.filter((u) => u.id !== me.id).map((u) => `<option value="${u.id}">${esc(u.display_name)}</option>`).join("")}</select>
    </form>
    <div class="status-chips" id="statusChips" aria-label="Lọc theo trạng thái"></div>
    <div id="taskList" class="list"><div class="loading">⏳ Đang tải…</div></div>`;
  $("#tasksCreate").addEventListener("click", () => navigate("create"));
  let lastCounts = null;
  const paintChips = () => {
    const box = $("#statusChips");
    if (!box) return;
    const totalAll = lastCounts
      ? Object.values(lastCounts).reduce((sum, n) => sum + n, 0) : null;
    box.innerHTML = STATUS_CHIPS.map(([code, icon, label]) => {
      const n = code === "" ? totalAll
        : (lastCounts ? (lastCounts[code] || 0) : null);
      return `<button type="button" class="status-chip ${state.taskStatus === code ? "active" : ""}"
        data-status-chip="${code}">${icon} ${label}${n !== null ? ` <span class="chip-count">${n}</span>` : ""}</button>`;
    }).join("");
    $$("[data-status-chip]", box).forEach((btn) =>
      btn.addEventListener("click", () => {
        state.taskStatus = btn.dataset.statusChip;
        history.replaceState(null, "", state.taskStatus
          ? `#tasks?status=${state.taskStatus}` : "#tasks");
        paintChips();
        load().catch((e) => toast(e.message, true));
      }));
  };
  const load = async () => {
    const params = new URLSearchParams(new FormData($("#taskFilters")));
    for (const [key, value] of [...params.entries()]) if (!value) params.delete(key);
    if (state.taskStatus) params.set("status", state.taskStatus);
    params.set("limit", "100");
    const data = await api(`/api/tasks?${params}`);
    lastCounts = data.counts || null;
    paintChips();
    $("#taskList").innerHTML = data.items.length
      ? data.items.map(taskRow).join("")
      : `<div class="empty">${state.taskStatus
          ? "Không có việc nào ở trạng thái này."
          : "Không tìm thấy việc nào khớp bộ lọc."}</div>`;
    bindTaskCards($("#taskList"));
  };
  paintChips();
  $("#taskFilters").addEventListener("input", () => load().catch((e) => toast(e.message, true)));
  $("#taskFilters").addEventListener("submit", (e) => e.preventDefault());
  await load();
}

/* ============================== create ============================== */

function newWizard() {
  return {
    step: 1,
    files: [],
    hint: "",
    destinations: new Set(["website", "facebook", "instagram"]),
  };
}

async function renderCreate() {
  if (!state.wizard) state.wizard = newWizard();
  const w = state.wizard;
  const stepNames = ["1 · Tư liệu", "2 · Gợi ý", "3 · Chọn kênh"];
  let body = "";
  if (w.step === 1) {
    body = `
      <div class="drop-box">
        <p class="drop-icon">📎</p>
        <p><strong>Chọn ảnh, video hoặc tệp tư liệu</strong></p>
        <p class="muted drop-note">Tối đa 200MB mỗi file. File được lưu thẳng vào hồ sơ việc như tư liệu gửi qua Telegram.</p>
        <input type="file" id="wizardFiles" multiple accept="image/*,video/*,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.zip">
      </div>
      <div class="preview-grid">${w.files.map((file, i) => previewTile(file, i)).join("")}</div>`;
  } else if (w.step === 2) {
    body = `
      <label class="field">💡 Gợi ý cho Muse
        <textarea id="wizardHint" rows="7" placeholder="Ví dụ: Hội thảo nông nghiệp thông minh xã Chân Mộng, Phú Thọ — viết bài trang trọng, nhấn mạnh hiệu quả cho bà con.">${esc(w.hint)}</textarea>
      </label>
      <p class="muted">Gợi ý có thể sửa ngay tại bước này. Tư liệu đã chọn: <strong>${w.files.length} file</strong>.</p>`;
  } else {
    body = `
      <p><strong>🎯 Chọn kênh đăng bài</strong></p>
      <p class="muted">📌 Mặc định đang chọn cả 3 nơi đăng — chạm vào từng kênh để bỏ chọn nếu không cần. Kênh video chọn thêm thủ công.</p>
      <div class="channel-grid">
        ${CHANNELS.map((c) => {
          const selected = w.destinations.has(c.key);
          return `<button type="button" class="channel-choice ${selected ? "selected" : ""}" data-channel="${c.key}">
            ${selected ? c.icon : "❌"} ${c.name}<small>${c.key.startsWith("video") ? "Không nằm trong mặc định" : "Kênh chữ"}</small></button>`;
        }).join("")}
      </div>
      <div class="card" style="margin-top:1rem;box-shadow:none">
        <p class="meta-line">📎 Tư liệu: ${w.files.length} file</p>
        <p class="meta-line">💡 Gợi ý: ${esc(w.hint || "(không có)")}</p>
        <p class="meta-line">🎯 Kênh: ${[...w.destinations].map(channelName).join(", ") || "chưa chọn"}</p>
      </div>`;
  }
  $("#screen").innerHTML = `
    <div class="page-head"><div><h2>📝 Giao việc mới</h2><p>Tải tư liệu → gợi ý → chọn kênh → gửi Muse.</p></div></div>
    <div class="steps">${stepNames.map((name, i) => `<span class="step ${w.step === i + 1 ? "active" : w.step > i + 1 ? "done" : ""}">${name}</span>`).join("")}</div>
    <section class="card">${body}
      <div class="wizard-foot">
        <button class="btn" id="wizardBack" ${w.step === 1 ? "disabled" : ""}>← Quay lại</button>
        <span>
          <button class="btn" id="wizardCancel">🗑 Hủy việc</button>
          ${w.step < 3
            ? `<button class="btn btn-primary" id="wizardNext">Tiếp tục →</button>`
            : `<button class="btn btn-primary" id="wizardSubmit">🚀 Chốt! Gửi Muse</button>`}
        </span>
      </div>
    </section>`;
  const capture = () => {
    if (w.step === 2) w.hint = $("#wizardHint").value;
  };
  $("#wizardBack").addEventListener("click", () => { capture(); w.step--; renderCreate(); });
  $("#wizardCancel").addEventListener("click", () => { state.wizard = newWizard(); navigate("tasks"); });
  if (w.step === 1) {
    $("#wizardFiles").addEventListener("change", (event) => {
      const incoming = [...event.target.files];
      for (const file of incoming) {
        if (file.size > 200 * 1024 * 1024) { toast(`File ${file.name} vượt quá 200MB.`, true); continue; }
        w.files.push(file);
      }
      renderCreate();
    });
    $$("[data-remove-file]").forEach((btn) => btn.addEventListener("click", () => {
      w.files.splice(Number(btn.dataset.removeFile), 1); renderCreate();
    }));
  }
  if (w.step === 3) {
    $$("[data-channel]").forEach((btn) => btn.addEventListener("click", () => {
      const key = btn.dataset.channel;
      w.destinations.has(key) ? w.destinations.delete(key) : w.destinations.add(key);
      renderCreate();
    }));
    $("#wizardSubmit").addEventListener("click", submitWizard);
  }
  const next = $("#wizardNext");
  if (next) next.addEventListener("click", () => { capture(); w.step++; renderCreate(); });
}

function previewTile(file, index) {
  const url = URL.createObjectURL(file);
  const media = file.type.startsWith("image/")
    ? `<img src="${url}" alt="">`
    : file.type.startsWith("video/")
      ? `<video src="${url}" muted preload="metadata"></video>`
      : `<div class="preview-ph">📄</div>`;
  return `<div class="preview">${media}<button class="remove" data-remove-file="${index}" aria-label="Bỏ file">✕</button><div class="fname">${esc(file.name)}<br><span class="muted">${fmtBytes(file.size)}</span></div></div>`;
}

async function submitWizard() {
  const w = state.wizard;
  if (!w.destinations.size) { toast("Hãy chọn ít nhất một kênh đăng.", true); return; }
  const btn = $("#wizardSubmit");
  btn.disabled = true; btn.textContent = "⏳ Đang gửi cho Muse…";
  try {
    const form = new FormData();
    form.append("hint", w.hint);
    for (const key of w.destinations) form.append("destinations", key);
    for (const file of w.files) form.append("files", file, file.name);
    const data = await api("/api/tasks", { method: "POST", body: form });
    state.wizard = newWizard();
    toast(`✅ Đã tạo việc ${data.task.code} và gửi cho Muse.`);
    navigate("detail", data.task.code);
  } catch (err) {
    btn.disabled = false; btn.textContent = "🚀 Chốt! Gửi Muse";
    toast(err.message, true);
  }
}

/* ============================== detail ============================== */

function isHttpUrl(value) {
  return /^https?:\/\//i.test(value || "");
}

function outputActions(output, task) {
  const me = state.me;
  const actions = [];
  if (["CANCELLED", "RETRACTED"].includes(output.status)) return actions;
  const isCreator = task.creator_id === me.id;
  if (output.pending_choice) {
    if (output.channel === "facebook" && output.status === "APPROVED_WAITING" && me.can_publish) {
      actions.push({ action: "publish", label: "🚀 Chọn nơi đăng", primary: true });
      actions.push({ action: "publish-abort", label: "🗑 Hủy đăng" });
    } else {
      actions.push({ label: "⏳ Đang chờ xử lý…", disabled: true });
    }
    return actions;
  }
  if (isCreator && me.role === "admin" && ["DRAFT", "REJECTED", "PENDING"].includes(output.status)) {
    if (output.draft_ref) {
      actions.push({ action: "publish", label: "🚀 Đăng", primary: true });
      actions.push({ action: "schedule", label: "🕐 Đặt lịch đăng" });
      actions.push({ action: "revise", label: "✏️ Sửa lại" });
    }
    actions.push({ action: "cancel", label: "🗑 Hủy bài", danger: true });
    return actions;
  }
  if (isCreator && ["DRAFT", "REJECTED"].includes(output.status)) {
    actions.push({ action: "submit", label: "📤 Gửi duyệt", primary: true, disabled: !output.draft_ref });
    if (output.draft_ref) actions.push({ action: "revise", label: "✏️ Sửa lại" });
  }
  if (me.can_review && output.status === "PENDING") {
    actions.push(
      { action: "approve", label: "✅ Duyệt", primary: true },
      { action: "reject", label: "↩️ Trả lại" },
      { action: "cancel", label: "🗑 Hủy bài", danger: true });
  }
  if (me.can_review && output.status === "DRAFT" && output.draft_ref) {
    actions.push(
      { action: "reject", label: "↩️ Trả lại" },
      { action: "cancel", label: "🗑 Hủy bài", danger: true });
  }
  if (output.status === "APPROVED_WAITING" && me.can_publish) {
    actions.push({ action: "publish", label: "🚀 Đăng", primary: true });
    if (output.scheduled_at) {
      actions.push({ action: "schedule", label: "🕐 Đổi lịch" });
      actions.push({ action: "unschedule", label: "❌ Hủy lịch" });
    } else {
      actions.push({ action: "schedule", label: "🕐 Đặt lịch đăng" });
    }
  }
  if (output.status === "PUBLISHED" && me.can_publish) {
    actions.push({ action: "retract", label: "↩️ Thu hồi" });
  }
  return actions;
}

function outputCard(output, task) {
  const meta = CHANNEL_MAP[output.channel] || { icon: "📄", name: output.channel, kind: "" };
  const creatorName = output.creator_name || task.creator_name || task.creator_id || "";
  let draft = "";
  if (output.draft_ref) {
    if (meta.kind === "video") {
      draft = `<p class="meta-line">🎬 Video nháp: xem ngay bên dưới</p>
        <video class="draft-video" controls preload="metadata" src="/api/outputs/${output.id}/draft-video"></video>`;
    } else if (isHttpUrl(output.draft_ref)) {
      draft = `<p class="meta-line">📄 Bản nháp: <a href="${esc(output.draft_ref)}" target="_blank" rel="noopener">Mở bản nháp</a></p>`;
    } else {
      draft = `<p class="meta-line">📄 Bản nháp: ${esc(output.draft_ref)}</p>`;
    }
  }
  return `
  <article class="card channel-card status-${esc(output.status)}">
    <div class="row-item">
      <div class="row-main">
        <strong>🧾 Thẻ kênh ${esc(meta.name)} — ${esc(STATUS_LABELS[output.status] || output.status)}</strong>
        <p class="meta-line">🗂 ${esc(output.task_code)}${meta.kind ? ` · ${esc(meta.kind)}` : ""}</p>
        <p class="meta-line">👤 ${esc(creatorName)} · ${fmtTime(output.created_at)}</p>
        <p class="meta-line">💡 ${esc(task.hint || output.task_hint || "(không có gợi ý)")}</p>
        ${draft}
        ${output.scheduled_at ? `<p class="meta-line">🕐 Lịch đăng: <span class="sched-time">${fmtTime(output.scheduled_at)}</span>${output.publish_target ? ` · ${output.publish_target === "page" ? "Fanpage Minhy" : "Trang cá nhân"}` : ""}</p>` : ""}
        ${output.public_url ? `<p class="meta-line">🔗 ${output.status === "RETRACTED" ? "Bài đã xóa" : "Đã đăng"}: <a href="${esc(output.public_url)}" target="_blank" rel="noopener">${esc(output.public_url)}</a></p>` : ""}
        ${output.status === "REJECTED" && output.reject_reason ? `<p class="meta-line">✏️ Yêu cầu chỉnh sửa: ${esc(output.reject_reason)}</p>` : ""}
        ${output.pending_choice ? `<p class="meta-line">⏳ Đang có lựa chọn/lệnh chưa hoàn tất — các nút khác tạm ẩn.</p>` : ""}
      </div>${statusPill(output.status)}
    </div>
    <div class="actions">
      ${outputActions(output, task).map((a) => `<button class="btn btn-small ${a.primary ? "btn-primary" : ""} ${a.danger ? "btn-danger" : ""}"
        data-output-action="${a.action || ""}" data-output-id="${output.id}" ${a.disabled ? "disabled" : ""}>${a.label}</button>`).join("")}
    </div>
  </article>`;
}

async function renderDetail() {
  const code = state.taskCode;
  const data = await api(`/api/tasks/${encodeURIComponent(code)}`);
  const { task, outputs, files } = data;
  $("#screen").innerHTML = `
    <div class="page-head">
      <div><h2>🧾 ${esc(task.code)}</h2><p>${esc(task.hint || "(chưa có gợi ý)")}</p></div>
      <button class="btn" id="backTasks">← Danh sách việc</button>
    </div>
    <section class="card">
      <p class="meta-line">🗂 Mã việc: ${esc(task.code)} · trạng thái tổng: ${esc(STATUS_LABELS[task.status] || task.status)}</p>
      <p class="meta-line">👤 Người tạo: ${esc(task.creator_name || task.creator_id)} · ${fmtTime(task.created_at)}</p>
      <p class="meta-line">💡 Gợi ý: ${esc(task.hint || "(không có)")}</p>
      <p class="meta-line">🎯 Kênh đăng: ${(task.destinations || []).map((d) => `${CHANNEL_MAP[d]?.icon || ""} ${channelName(d)}`).join(" · ")}</p>
      <p class="meta-line">📎 Tư liệu: ${files.length} file</p>
      <div class="files-grid" style="margin-top:.7rem">${files.map(fileTile).join("") || `<span class="muted">Chưa có tư liệu.</span>`}</div>
      ${(task.creator_id === state.me.id || state.me.role === "admin") ? `
        <form id="addFilesForm" style="margin-top:1rem">
          <label class="field">Thêm tư liệu<input type="file" id="addFiles" multiple></label>
          <button class="btn btn-soft btn-small" type="submit">⬆️ Tải thêm tư liệu</button>
        </form>` : ""}
    </section>
    <h3 style="margin:1.2rem 0 .7rem">Thẻ kênh (${outputs.length})</h3>
    <div class="list">${outputs.map((o) => outputCard(o, task)).join("") || `<div class="empty">Việc này chưa có thẻ kênh.</div>`}</div>`;
  $("#backTasks").addEventListener("click", () => navigate("tasks"));
  const addForm = $("#addFilesForm");
  if (addForm) addForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const chosen = [...$("#addFiles").files];
    if (!chosen.length) { toast("Hãy chọn file trước.", true); return; }
    const form = new FormData();
    form.append("task_code", task.code);
    for (const file of chosen) form.append("files", file, file.name);
    try {
      await api("/api/uploads", { method: "POST", body: form });
      toast("✅ Đã thêm tư liệu.");
      renderDetail();
    } catch (err) { toast(err.message, true); }
  });
  bindOutputActions(() => renderDetail());
}

function fileTile(file) {
  const isImage = (file.content_type || "").startsWith("image/");
  const isVideo = (file.content_type || "").startsWith("video/");
  const media = isImage ? `<img src="${esc(file.url)}" alt="">`
    : isVideo ? `<video src="${esc(file.url)}" controls preload="metadata"></video>`
    : `<div style="height:130px;display:grid;place-items:center;font-size:2.4rem;background:#f1f5f9">📄</div>`;
  return `<div class="file-tile">${media}<div class="file-name"><a href="${esc(file.url)}" target="_blank" rel="noopener">${esc(file.name)}</a><br><span class="muted">${fmtBytes(file.size)}</span></div></div>`;
}

function bindOutputActions(reload) {
  $$("[data-output-action]").forEach((btn) => {
    if (!btn.dataset.outputAction) return;
    btn.addEventListener("click", () =>
      handleOutputAction(Number(btn.dataset.outputId), btn.dataset.outputAction, reload));
  });
}

async function callOutput(id, action, body = {}) {
  return apiJson(`/api/outputs/${id}/${action}`, "POST", body);
}

async function handleOutputAction(id, action, reload) {
  try {
    if (action === "reject" || action === "revise") {
      const reason = await reasonModal(
        action === "reject" ? "↩️ Trả lại thẻ kênh" : "✏️ Sửa lại bản nháp",
        action === "reject" ? "Nội dung cần chỉnh sửa (người duyệt)" : "Nội dung cần sửa (người tạo)");
      if (reason === null) return;
      const data = await callOutput(id, action, { reason });
      toast(`✅ ${data.message}`);
    } else if (action === "cancel") {
      if (!await confirmModal("🗑 Hủy bài", "Hủy hẳn đầu ra này? Thao tác ghi vào nhật ký và không còn thao tác được nữa.", "Hủy bài")) return;
      const data = await callOutput(id, action);
      toast(`✅ ${data.message}`);
    } else if (action === "retract") {
      if (!await confirmModal("↩️ Thu hồi bài", "Nếu là Facebook, Muse sẽ xóa bài thật trên Facebook sau khi nhận lệnh.", "Thu hồi")) return;
      const data = await callOutput(id, action);
      toast(`✅ ${data.message}`);
    } else if (action === "publish") {
      await publishFlow(id, reload); return;
    } else if (action === "schedule") {
      await scheduleFlow(id, reload); return;
    } else {
      const data = await callOutput(id, action);
      toast(`✅ ${data.message}`);
      if (data.warnings?.length) toast(`${data.message} ⚠️ ${data.warnings.join(" ")}`);
    }
    await reload();
    refreshBadge();
  } catch (err) {
    if (err.data?.code === "target_required" && action === "publish") {
      await publishFlow(id, reload, true); return;
    }
    if (err.data?.code === "target_required" && action === "schedule") {
      await scheduleFlow(id, reload, true); return;
    }
    toast(err.message, true);
  }
}

async function publishFlow(id, reload, alreadyPending = false) {
  // Facebook needs its target chosen in this UI (owner's rule).
  const detail = state.route === "detail" ? await api(`/api/tasks/${state.taskCode}`).catch(() => null) : null;
  const output = detail?.outputs.find((o) => o.id === id);
  if (output && output.channel !== "facebook") {
    const data = await callOutput(id, "publish", {});
    toast(`✅ ${data.message}`); await reload(); return;
  }
  openModal(`
    <h3>📘 Chọn nơi đăng Facebook</h3>
    <p class="muted">Nơi đăng được chốt ngay tại đây, lệnh đăng sẽ ghi kèm lựa chọn này.</p>
    <div class="target-grid">
      <button class="target-choice" data-target="profile">👤 Trang cá nhân<br><small class="muted">Nguyễn Trọng Minh Huy</small></button>
      <button class="target-choice" data-target="page">📄 Fanpage Minhy</button>
    </div>
    <div class="modal-actions"><button class="btn btn-danger" data-abort>🗑 Hủy đăng</button></div>`);
  $$("[data-target]").forEach((btn) => btn.addEventListener("click", async () => {
    try {
      const data = await callOutput(id, "publish", { target: btn.dataset.target });
      closeModal(); toast(`✅ ${data.message}`); await reload(); refreshBadge();
    } catch (err) { toast(err.message, true); }
  }));
  $("[data-abort]").addEventListener("click", async () => {
    if (alreadyPending || output?.pending_choice) {
      try { await callOutput(id, "publish-abort", {}); } catch (err) { toast(err.message, true); return; }
    }
    closeModal(); toast("Đã hủy đăng."); if (alreadyPending) await reload();
  });
}

async function scheduleFlow(id, reload, alreadyPending = false) {
  const detail = state.route === "detail" ? await api(`/api/tasks/${state.taskCode}`).catch(() => null) : null;
  const output = detail?.outputs.find((o) => o.id === id);
  const isFacebook = output?.channel === "facebook";
  openModal(`
    <h3>🕐 Đặt lịch đăng</h3>
    ${isFacebook ? `<label class="field">📘 Nơi đăng Facebook
      <select id="schedTarget"><option value="">— Chọn nơi đăng —</option><option value="profile">👤 Trang cá nhân</option><option value="page">📄 Fanpage Minhy</option></select></label>` : ""}
    <div class="target-grid">
      <button class="target-choice" data-preset="60">⏱ Sau 1 giờ</button>
      <button class="target-choice" data-preset="120">⏱ Sau 2 giờ</button>
      <button class="target-choice" data-preset="eve">🌆 Tối nay 20:00</button>
      <button class="target-choice" data-preset="mor">🌅 Sáng mai 8:00</button>
    </div>
    <label class="field">⌨️ Hoặc nhập giờ khác (giờ Việt Nam)
      <input id="schedCustom" placeholder="16:30 hoặc 24/10 16:30"></label>
    <div class="modal-actions">
      <button class="btn" data-cancel>🗑 Hủy đặt lịch</button>
      <button class="btn btn-primary" data-custom-submit>Dùng giờ đã nhập</button>
    </div>`);
  const submit = async (body) => {
    if (isFacebook) {
      const target = $("#schedTarget").value;
      if (!target) { toast("Hãy chọn nơi đăng Facebook trước.", true); return; }
      body.target = target;
    }
    try {
      const data = await callOutput(id, "schedule", body);
      closeModal();
      toast(`✅ ${data.message}${data.warnings?.length ? ` ⚠️ ${data.warnings.join(" ")}` : ""}`);
      await reload();
    } catch (err) { toast(err.message, true); }
  };
  $$("[data-preset]").forEach((btn) => btn.addEventListener("click", () => submit({ preset: btn.dataset.preset })));
  $("[data-custom-submit]").addEventListener("click", () => {
    const value = $("#schedCustom").value.trim();
    if (!value) { toast("Hãy nhập giờ hoặc chọn giờ nhanh.", true); return; }
    submit({ scheduled_at: value });
  });
  $("[data-cancel]").addEventListener("click", async () => {
    if (alreadyPending || output?.pending_choice) {
      try { await callOutput(id, "schedule-abort", {}); } catch {}
    }
    closeModal(); if (alreadyPending) await reload();
  });
}

/* ============================== review ============================== */

async function renderReview() {
  const data = await api("/api/review-queue");
  $("#screen").innerHTML = `
    <div class="page-head"><div><h2>⏳ Chờ duyệt</h2><p>${data.items.length} thẻ kênh đang chờ người duyệt xử lý.</p></div></div>
    <div class="list">${data.items.map((o) => outputCard(o, {
      code: o.task_code, creator_id: o.creator_id, creator_name: o.creator_name,
      hint: o.task_hint || "",
    })).join("") || `<div class="empty">🎉 Không có thẻ kênh nào đang chờ duyệt.</div>`}</div>`;
  // Clicking a queue card (outside its buttons) opens the task.
  $$("[data-task]").forEach(() => {});
  $$(".channel-card").forEach((card, i) => {
    card.style.cursor = "pointer";
    card.addEventListener("click", (event) => {
      if (event.target.closest("button,a,video")) return;
      navigate("detail", data.items[i].task_code);
    });
  });
  bindOutputActions(() => renderReview());
}

/* ============================= schedule ============================= */

async function renderSchedule() {
  const data = await api("/api/scheduled");
  $("#screen").innerHTML = `
    <div class="page-head"><div><h2>🕐 Lịch đăng</h2><p>Tất cả bài đang đặt lịch, xếp theo giờ tăng dần.</p></div></div>
    <div class="list">${data.items.map((o) => outputCard(o, {
      code: o.task_code, creator_id: o.creator_id, creator_name: o.creator_name,
      hint: o.task_hint || "",
    })).join("") || `<div class="empty">Chưa có bài nào đang đặt lịch.</div>`}</div>`;
  $$(".channel-card").forEach((card, i) => {
    card.style.cursor = "pointer";
    card.addEventListener("click", (event) => {
      if (event.target.closest("button,a,video")) return;
      navigate("detail", data.items[i].task_code);
    });
  });
  bindOutputActions(() => renderSchedule());
}

/* ============================== stats ============================== */

function barChartSVG(pairs) {
  const max = Math.max(1, ...pairs.map((p) => p[1]));
  const width = 560, height = 230, base = 190, gap = width / Math.max(pairs.length, 1);
  const bars = pairs.map(([label, value], i) => {
    const h = Math.round((value / max) * 140);
    const x = i * gap + gap * 0.22, w = gap * 0.56;
    return `<rect x="${x}" y="${base - h}" width="${w}" height="${h}" rx="6" fill="#0f766e"></rect>
      <text x="${x + w / 2}" y="${base - h - 7}" text-anchor="middle" font-size="13" font-weight="700">${value}</text>
      <text x="${x + w / 2}" y="${base + 20}" text-anchor="middle" font-size="11" fill="#64748b">${esc(label)}</text>`;
  }).join("");
  return `<svg viewBox="0 0 ${width} ${height}" width="100%" role="img" aria-label="Biểu đồ cột"><line x1="8" y1="${base}" x2="${width - 8}" y2="${base}" stroke="#cbd5e1"/>${bars}</svg>`;
}

function donutSVG(pairs) {
  const total = Math.max(1, pairs.reduce((s, p) => s + p[1], 0));
  const colors = ["#0f766e", "#2563eb", "#e11d63", "#f59e0b", "#7c3aed"];
  let offset = 25;
  const circles = pairs.map(([label, value], i) => {
    const frac = (value / total) * 100;
    const segment = `<circle r="15.9" cx="21" cy="21" fill="none" stroke="${colors[i % colors.length]}" stroke-width="7"
      stroke-dasharray="${Math.max(frac - 1, 0)} ${100 - Math.max(frac - 1, 0)}" stroke-dashoffset="${offset}"></circle>`;
    offset -= frac;
    return segment;
  }).join("");
  const legend = pairs.map(([label, value], i) =>
    `<p class="meta-line"><span style="color:${colors[i % colors.length]}">●</span> ${esc(label)}: <strong>${value}</strong></p>`).join("");
  return `<div class="row-item"><svg viewBox="0 0 42 42" width="150" height="150" role="img" aria-label="Biểu đồ tròn">${circles}<text x="21" y="23" text-anchor="middle" font-size="7" font-weight="800">${total}</text></svg><div>${legend}</div></div>`;
}

async function renderStats() {
  const data = await api(`/api/stats/summary?period=${state.period}`);
  const statusTotals = {};
  const channelTotals = [];
  for (const [channel, perStatus] of Object.entries(data.output_channel_status)) {
    let total = 0;
    for (const [status, n] of Object.entries(perStatus)) {
      statusTotals[status] = (statusTotals[status] || 0) + n;
      total += n;
    }
    channelTotals.push([channelName(channel), total]);
  }
  const statusPairs = Object.keys(STATUS_LABELS)
    .filter((s) => statusTotals[s]).map((s) => [STATUS_LABELS[s], statusTotals[s]]);
  $("#screen").innerHTML = `
    <div class="page-head">
      <div><h2>📊 Thống kê</h2><p>${esc(data.label)}</p></div>
      <div>
        <a class="btn" href="/api/stats/export?format=csv&period=${state.period}">📥 Xuất CSV</a>
        <a class="btn" href="/api/stats/export?format=xlsx&period=${state.period}">📗 Xuất Excel</a>
      </div>
    </div>
    <div class="periods" style="margin-bottom:1rem">
      ${[["today", "📅 Hôm nay"], ["week", "🗓 Tuần này"], ["month", "📆 Tháng này"], ["all", "♾ Tất cả"]]
        .map(([key, label]) => `<button class="btn ${state.period === key ? "active" : ""}" data-period="${key}">${label}</button>`).join("")}
    </div>
    <div class="grid grid-4">
      <div class="card metric"><span>📋 Việc trong kỳ</span><strong>${data.tasks_total}</strong></div>
      <div class="card metric"><span>🧩 Đầu ra trong kỳ</span><strong>${data.outputs_total}</strong></div>
      <div class="card metric"><span>✅ Đã đăng</span><strong>${data.published_total}</strong></div>
      <div class="card metric"><span>🎬 Video đã dựng / đã đăng</span><strong>${data.video.drafted} / ${data.video.published}</strong><span>dọc ${data.video.published_vertical} · ngang ${data.video.published_horizontal}</span></div>
    </div>
    <div class="chart-wrap" style="margin-top:1rem">
      <section class="card"><h3>Đầu ra theo trạng thái</h3>${statusPairs.length ? barChartSVG(statusPairs) : `<p class="muted">Chưa có dữ liệu.</p>`}</section>
      <section class="card"><h3>Đầu ra theo kênh</h3>${channelTotals.length ? donutSVG(channelTotals) : `<p class="muted">Chưa có dữ liệu.</p>`}</section>
    </div>
    <div class="grid grid-2" style="margin-top:1rem">
      <section class="card"><h3>Theo kênh · trạng thái</h3><div class="table-wrap"><table>
        <tr><th>Kênh</th><th>Trạng thái</th><th>Số lượng</th></tr>
        ${Object.entries(data.output_channel_status).flatMap(([ch, per]) =>
          Object.entries(per).map(([s, n]) => `<tr><td>${esc(channelName(ch))}</td><td>${esc(STATUS_LABELS[s] || s)}</td><td>${n}</td></tr>`)).join("") || `<tr><td colspan="3">Chưa có dữ liệu</td></tr>`}
      </table></div></section>
      <section class="card"><h3>Theo người tạo</h3><div class="table-wrap"><table>
        <tr><th>Người tạo</th><th>Việc</th><th>Đã đăng</th></tr>
        ${data.per_creator.map((r) => `<tr><td>${esc(r.name)}</td><td>${r.tasks}</td><td>${r.published}</td></tr>`).join("") || `<tr><td colspan="3">Chưa có dữ liệu</td></tr>`}
      </table></div></section>
    </div>`;
  $$("[data-period]").forEach((btn) => btn.addEventListener("click", () => {
    state.period = btn.dataset.period; renderStats();
  }));
}

/* ============================== users ============================== */

function grantableRoles(actorRole) {
  if (actorRole === "admin") return ROLE_OPTIONS;
  if (actorRole === "deputy_admin") return ROLE_OPTIONS.filter(([k]) => ["writer", "contributor"].includes(k));
  return [];
}

async function renderUsers() {
  const data = await api("/api/users");
  state.usersCache = data.items;
  const allowed = grantableRoles(state.me.role);
  $("#screen").innerHTML = `
    <div class="page-head"><div><h2>👥 Người dùng & phân quyền</h2><p>Tài khoản do Admin/Phó Admin tạo và cấp quyền ngay tại đây.</p></div></div>
    <section class="card">
      <h3>➕ Tạo tài khoản mới</h3>
      <form id="createUserForm" class="grid grid-3">
        <label class="field">Tên hiển thị<input name="name" required></label>
        <label class="field">Email<input name="email" type="email" placeholder="co-the-de-trong"></label>
        <label class="field">Số điện thoại<input name="phone" placeholder="co-the-de-trong"></label>
        <label class="field">Mật khẩu tạm (≥ 8 ký tự)<input name="password" type="text" required minlength="8" autocomplete="off"></label>
        <label class="field">Vai trò<select name="role">${allowed.map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select></label>
        <label class="field">Quyền đăng bài<select name="can_publish"><option value="">Mặc định theo vai trò</option><option value="1">Bật</option><option value="0">Tắt</option></select></label>
        <div><button class="btn btn-primary" type="submit">Tạo tài khoản</button></div>
      </form>
      <p class="muted small">Người được tạo dùng mật khẩu tạm đăng nhập lần đầu rồi tự đổi trong mục 🔐.</p>
    </section>
    <div class="user-grid" style="margin-top:1rem">
      ${data.items.map(userCard).join("")}
    </div>
    <p class="muted small center" style="margin-top:1rem">Phiên bản ${APP_VERSION}</p>`;
  $("#createUserForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = new FormData(event.target);
    const body = {
      name: form.get("name"), email: form.get("email") || undefined,
      phone: form.get("phone") || undefined, password: form.get("password"),
      role: form.get("role"),
    };
    if (form.get("can_publish")) body.can_publish = form.get("can_publish") === "1";
    try {
      const created = await apiJson("/api/users", "POST", body);
      toast(`✅ Đã tạo tài khoản cho ${created.user.display_name}.`);
      renderUsers();
    } catch (err) { toast(err.message, true); }
  });
  $$("[data-save-role]").forEach((btn) => btn.addEventListener("click", async () => {
    const id = btn.dataset.saveRole;
    const select = $(`[data-role-select="${id}"]`);
    const publish = $(`[data-publish-select="${id}"]`);
    try {
      await apiJson(`/api/users/${id}/role`, "PATCH", {
        role: select.value, can_publish: publish.value === "1",
      });
      toast("✅ Đã cập nhật vai trò.");
      renderUsers();
    } catch (err) { toast(err.message, true); }
  }));
  $$("[data-revoke]").forEach((btn) => btn.addEventListener("click", async () => {
    if (!await confirmModal("Thu hồi quyền", "Người này sẽ trở về trạng thái chờ cấp quyền và bị đăng xuất khỏi Web App.", "Thu hồi")) return;
    try {
      await apiJson(`/api/users/${btn.dataset.revoke}/revoke`, "POST", {});
      toast("✅ Đã thu hồi quyền.");
      renderUsers();
    } catch (err) { toast(err.message, true); }
  }));
}

function userCard(user) {
  const allowed = grantableRoles(state.me.role);
  const isSelf = user.id === state.me.id;
  return `<article class="card">
    <div class="row-item"><div class="row-main">
      <strong>👤 ${esc(user.display_name)}</strong>
      <p class="meta-line">🏷 ${esc(user.role_title)}${user.can_publish ? " · 🚀 có quyền đăng" : ""}</p>
      <p class="meta-line">✉️ ${esc(user.email || "—")} · 📱 ${esc(user.phone || "—")}</p>
      <p class="meta-line">🕘 Tạo: ${fmtTime(user.created_at)}</p>
    </div>${user.role ? `<span class="pill info">${esc(user.role_title)}</span>` : `<span class="pill warn">Chờ cấp quyền</span>`}</div>
    <div class="user-actions">
      <select data-role-select="${user.id}" ${isSelf ? "disabled" : ""}>
        ${allowed.map(([k, v]) => `<option value="${k}" ${user.role === k ? "selected" : ""}>${v}</option>`).join("")}
      </select>
      <select data-publish-select="${user.id}" title="Quyền đăng">
        <option value="1" ${user.can_publish ? "selected" : ""}>🚀 Được đăng</option>
        <option value="0" ${!user.can_publish ? "selected" : ""}>Không đăng</option>
      </select>
      <span>
        <button class="btn btn-small" data-save-role="${user.id}" ${isSelf ? "disabled" : ""}>Lưu vai trò</button>
        <button class="btn btn-small btn-danger" data-revoke="${user.id}" ${isSelf || !user.role ? "disabled" : ""}>Thu hồi</button>
      </span>
    </div>
  </article>`;
}

/* =========================== notifications =========================== */

function notificationRow(item) {
  const icons = {
    review_pending: "⏳", rejected: "↩️", revision_requested: "✏️",
    draft_ready: "📄", published: "✅", retracted: "🗑",
    daily_summary: "🌆",
  };
  return `<button class="card notification ${item.read ? "" : "unread"}" data-notification="${esc(item.key)}" data-code="${esc(item.task_code || "")}">
    <span class="dot"></span>
    <span class="row-main"><strong>${icons[item.kind] || "🔔"} ${esc(item.title)}</strong>
    <br><span class="muted">${esc(item.body)}</span>
    <br><span class="muted small">${fmtTime(item.created_at)}</span></span>
  </button>`;
}

function bindNotificationRows(root = document) {
  $$("[data-notification]", root).forEach((el) => el.addEventListener("click", async () => {
    try {
      await apiJson("/api/notifications/read", "POST", { keys: [el.dataset.notification] });
    } catch {}
    if (el.dataset.code) navigate("detail", el.dataset.code);
    else if (state.route === "notifications") renderNotifications();
    else refreshBadge();
  }));
}

/* --------------------- Web Push (GĐ3) --------------------- */

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const raw = atob((base64String + padding).replaceAll("-", "+").replaceAll("_", "/"));
  return Uint8Array.from([...raw].map((ch) => ch.charCodeAt(0)));
}

async function initPushPanel() {
  const box = $("#pushState");
  const enableBtn = $("#pushEnable");
  const disableBtn = $("#pushDisable");
  const testBtn = $("#pushTest");
  if (!box || !enableBtn || !disableBtn || !testBtn) return;
  // TD-0009: the panel must ALWAYS end in a clear, visible state —
  // never leave every button hidden looking like the feature is gone.
  // Each step is guarded separately and failures say so in the card.
  const setButtons = (enable, disable, test) => {
    if (enableBtn) enableBtn.hidden = !enable;
    if (disableBtn) disableBtn.hidden = !disable;
    if (testBtn) testBtn.hidden = !test;
  };
  const fail = (message) => {
    box.textContent = `⚠️ ${message}`;
    setButtons(false, false, false);
  };
  const supported = "serviceWorker" in navigator && "PushManager" in window
    && "Notification" in window;
  if (!supported) {
    box.textContent = "Trình duyệt này không hỗ trợ thông báo đẩy (cần HTTPS và trình duyệt hiện đại; trên iPhone hãy mở app từ biểu tượng ở màn hình chính).";
    setButtons(false, false, false);
    return;
  }
  let registration;
  try {
    registration = await Promise.race([
      navigator.serviceWorker.ready,
      new Promise((_, reject) => setTimeout(
        () => reject(new Error("quá thời gian chờ")), 6000)),
    ]);
  } catch {
    fail("Chưa kết nối được với nền tảng thông báo của trình duyệt (service worker chưa sẵn sàng). Hãy tải lại trang rồi mở lại mục này.");
    return;
  }
  if (!registration.pushManager) {
    box.textContent = "Trình duyệt này không hỗ trợ thông báo đẩy.";
    setButtons(false, false, false);
    return;
  }
  const refresh = async () => {
    let sub;
    try {
      sub = await registration.pushManager.getSubscription();
    } catch (err) {
      fail(`Không kiểm tra được trạng thái thông báo đẩy: ${err.message}`);
      return;
    }
    if (Notification.permission === "denied") {
      box.innerHTML = "⚠️ Bạn đã chặn thông báo cho trang này — hãy mở cài đặt trình duyệt, cho phép thông báo cho <strong>post.iaict-platform.com</strong> rồi quay lại bật.";
      setButtons(false, false, false);
      return;
    }
    if (sub) {
      box.textContent = "✅ Đang bật trên thiết bị này — việc mới, chờ duyệt, đã đăng… sẽ hiện ngay cả khi đóng app.";
      setButtons(false, true, true);
    } else {
      box.textContent = "Đang tắt trên thiết bị này. Bật để nhận việc mới, thẻ chờ duyệt, bài đã đăng… ngay cả khi đóng app.";
      setButtons(true, false, false);
    }
  };
  enableBtn.addEventListener("click", async () => {
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") { await refresh(); return; }
      const { public_key } = await api("/api/push/vapid-public-key");
      const sub = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(public_key),
      });
      await apiJson("/api/push/subscribe", "POST", sub.toJSON());
      toast("Đã bật thông báo đẩy trên thiết bị này.");
    } catch (err) {
      toast(`Không bật được thông báo đẩy: ${err.message}`, true);
    }
    await refresh();
  });
  disableBtn.addEventListener("click", async () => {
    try {
      const sub = await registration.pushManager.getSubscription();
      if (sub) {
        await apiJson("/api/push/unsubscribe", "POST", { endpoint: sub.endpoint }).catch(() => {});
        await sub.unsubscribe();
      }
      toast("Đã tắt thông báo đẩy trên thiết bị này.");
    } catch (err) {
      toast(`Không tắt được: ${err.message}`, true);
    }
    await refresh();
  });
  testBtn.addEventListener("click", async () => {
    try {
      const data = await apiJson("/api/push/test", "POST", {});
      toast(data.sent ? "Đã gửi thông báo thử — kiểm tra khay thông báo của máy."
                       : "Chưa gửi được thông báo thử nào.", !data.sent);
    } catch (err) {
      toast(err.message, true);
    }
  });
  await refresh();
}

async function renderNotifications() {
  const data = await api("/api/notifications");
  updateBadges(data.unread);
  $("#screen").innerHTML = `
    <div class="page-head"><div><h2>🔔 Thông báo</h2><p>${data.unread} thông báo chưa đọc.</p>
      <p class="muted small">Phiên bản ${APP_VERSION}</p></div>
      <button class="btn" id="markAll">Đánh dấu tất cả đã đọc</button></div>
    <section class="card" style="margin-bottom:1rem">
      <div class="row-item"><h3>📲 Thông báo đẩy</h3></div>
      <p class="muted" id="pushState">Đang kiểm tra trạng thái…</p>
      <div>
        <button class="btn btn-primary" id="pushEnable" hidden>Bật thông báo đẩy</button>
        <button class="btn" id="pushTest" hidden>Gửi thử</button>
        <button class="btn btn-danger" id="pushDisable" hidden>Tắt thông báo đẩy</button>
      </div>
    </section>
    <div class="list">${data.items.map(notificationRow).join("") || `<div class="empty">Chưa có thông báo nào.</div>`}</div>`;
  $("#markAll").addEventListener("click", async () => {
    await apiJson("/api/notifications/read", "POST", { all: true });
    renderNotifications();
  });
  bindNotificationRows();
  initPushPanel().catch((err) => {
    const box = $("#pushState");
    if (box) box.textContent = `⚠️ Không khởi tạo được mục thông báo đẩy: ${err.message}`;
  });
}

/* =============================== boot =============================== */

if ("serviceWorker" in navigator) {
  // TD-0009: check for a newer worker on every launch, and when a new
  // worker takes control (skipWaiting in sw.js), reload ONCE so an
  // installed PWA never stays stuck on a stale cached shell. The very
  // first install has no previous controller — no reload then.
  const hadController = Boolean(navigator.serviceWorker.controller);
  let reloading = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (!hadController || reloading) return;
    reloading = true;
    location.reload();
  });
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js")
      .then((registration) => registration.update().catch(() => {}))
      .catch(() => {});
  });
}
boot();
