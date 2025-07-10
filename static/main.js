// Socket.IO init
const socket = io(location.origin.replace(/^http/, 'ws'));

// Elemen log
const logHome = document.getElementById("log_home");
const logMap = document.getElementById("log_map");
const logCollect = document.getElementById("log_collect");
const logRead = document.getElementById("logbook_log");

// Tombol
const startButton = document.getElementById("startButton");

// Navigasi halaman
function showPage(id) {
  document.querySelectorAll('.page').forEach(page => page.classList.remove('active'));
  document.getElementById(id).classList.add('active');

  document.querySelectorAll('.sidebar button').forEach(btn => btn.classList.remove('active'));
  document.getElementById(`btn${id.charAt(0).toUpperCase() + id.slice(1)}`).classList.add('active');
}
// Tambah log ke area <pre>
function appendLog(target, message) {
  target.innerHTML += message + "\n";
  target.scrollTop = target.scrollHeight;
}


/* ===== Loading Animation ===== */
function showLoading() {
  const overlay = document.getElementById("loadingOverlay");
  if (overlay) overlay.style.display = "flex";
}
function hideLoading() {
  const overlay = document.getElementById("loadingOverlay");
  if (overlay) overlay.style.display = "none";
  currentProcess = null;
}
function stopProcessGlobal() {
  if (currentProcess === "print") {
    document.getElementById("printStatus").innerText += "\n⛔ Proses print dihentikan (manual)";
  } else {
    socket.emit("stop");
  }
  hideLoading();
}

/* ===== CEK STOK LPG ===== */
function startProcess() {
  const index = parseInt(document.getElementById("sheetIndex").value);
  logHome.innerHTML = "⏳ Memulai proses...\n";
  startButton.disabled = true;
  socket.emit("start_check", { sheet_index: index });
  showLoading();
}
function stopProcess() {
  socket.emit("stop");
}
socket.on("checker_log", message => appendLog(logHome, message));
socket.on("checker_done", () => {
  appendLog(logHome, "✅ Proses selesai.");
  startButton.disabled = false;
});
socket.on("error", message => {
  appendLog(logHome, "❌ ERROR: " + message);
  startButton.disabled = false;
});

/* ===== INPUT MAP ===== */
function startMap() {
  const index = parseInt(document.getElementById("sheet_index").value);
  logMap.innerHTML = "⏳ Memulai proses map...\n";
  socket.emit("map", { sheet_index: index });
}
function stopMap() {
  socket.emit("stop");
}
socket.on("map_log", message => appendLog(logMap, message));
socket.on("map_done", () => appendLog(logMap, "✅ Proses map selesai."));

/* ===== COLLECT LOGBOOK ===== */
function startCollect() {
  const index = parseInt(document.getElementById("sheet_index_collect").value);
  const monthSelect = document.getElementById("month_select");
  const monthIndex = parseInt(monthSelect.value);
  const monthName = monthSelect.options[monthSelect.selectedIndex].text;

  logCollect.innerHTML = "⏳ Memulai proses collect...\n";
  socket.emit("collect", { sheet_index: index, bulan_index: monthIndex, bulan_nama: monthName });
}
function stopCollect() {
  socket.emit("stop");
}

socket.on("collect_log", message => appendLog(logCollect, message));
socket.on("collect_done", () => appendLog(logCollect, "✅ Proses collect selesai."));

/* ===== UNLOCK PDF ===== */
const fileInput = document.getElementById('pdfs');
const fileList = document.getElementById('fileList');
if (fileInput) {
  fileInput.addEventListener('change', function () {
    fileList.innerHTML = '';
    [...fileInput.files].forEach((file, i) => {
      const row = document.createElement('div');
      row.className = 'file-row';
      row.innerHTML = `
                <strong>${file.name}</strong><br>
                <input type="hidden" name="files" value="${i}">
                <input type="file" name="pdfs" style="display:none" data-index="${i}">
                Password: <input type="text" name="passwords" required><br><br>
            `;
      fileList.appendChild(row);
    });

    [...fileInput.files].forEach((file, i) => {
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      const input = document.querySelector(`input[name="pdfs"][data-index="${i}"]`);
      input.files = dataTransfer.files;
    });
  });
}


/* ===== READ LOGBOOK ===== */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("uploadForm");
  if (!form) {
    console.warn("⚠️ Form dengan id 'uploadForm' tidak ditemukan!");
    return;
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    showLoading();

    const formData = new FormData(this);
    const response = await fetch("/", { method: "POST", body: formData });
    const html = await response.text();

    const parser = new DOMParser();
    const doc = parser.parseFromString(html, "text/html");
    const newResult = doc.querySelector("#resultArea");

    if (newResult) {
      document.querySelector("#resultArea").innerHTML = newResult.innerHTML;
    }

    hideLoading();
  });
});
function clearLogbookData() {
  document.getElementById("resultArea").innerHTML = "";
  document.getElementById("loading").style.display = "none";
  document.querySelector("#uploadForm input[type='file']").value = "";
}

/* ===== DOWNLOAD IMG ===== */
document.addEventListener("DOMContentLoaded", () => {
  // Kompres Foto
  const compressForm = document.getElementById("compressForm");
  if (compressForm) {
    compressForm.addEventListener("submit", async function (e) {
      e.preventDefault();

      showLoading();

      const formData = new FormData(this);
      const response = await fetch("/compress-photo", {
        method: "POST",
        body: formData
      });

      const html = await response.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, "text/html");
      const newResult = doc.querySelector("#compress");

      if (newResult) {
        document.querySelector("#compress").innerHTML = newResult.innerHTML;
      }

      hideLoading();
    });
  }
});

/* ===== MENU PENYALURAN ===== */
function submitPenyaluran(event) {
  event.preventDefault();

  const username = document.getElementById("penyaluran_username").value;
  const password = document.getElementById("penyaluran_password").value;
  const jenis = document.getElementById("penyaluran_jenis").value;
  const bulanOptions = document.getElementById("penyaluran_bulan").selectedOptions;

  const bulanData = Array.from(bulanOptions).map(opt => {
    const [tgl, namaBulan] = opt.value.split("|");
    return { tgl, namaBulan };
  });

  const payload = {
    username,
    password,
    jenis,
    bulan: bulanData
  };

  document.getElementById("log_penyaluran").textContent = "⏳ Memulai...";
  document.getElementById("loadingOverlay").style.display = "flex";

  socket.emit("penyaluran", payload);
}
socket.on("penyaluran_log", (msg) => {
  document.getElementById("log_penyaluran").textContent += `\n${msg}`;
});
socket.on("penyaluran_done", () => {
  document.getElementById("log_penyaluran").textContent += "\n✅ Selesai. Cek file unduhan di \\\\desktop-lg\\Downloads";
  document.getElementById("loadingOverlay").style.display = "none";
});

/* ===== MENU IN/OUT ===== */
let inoutButton = null;
function submitInOut(event) {
  event.preventDefault();

  const username = document.getElementById("inout_username").value;
  const password = document.getElementById("inout_password").value;
  const bulanOptions = document.getElementById("inout_bulan").selectedOptions;

  const bulanData = Array.from(bulanOptions).map(opt => {
    const [tgl, namaBulan] = opt.value.split("|");
    return { tgl, namaBulan };
  });

  const payload = {
    username,
    password,
    bulan: bulanData
  };

  document.getElementById("log_inout").textContent = "⏳ Memulai...";
  document.getElementById("loadingOverlay").style.display = "flex";
  inoutButton = event.target.querySelector("button[type='submit']");
  inoutButton.disabled = true;

  socket.emit("inout", payload);
}
socket.on("inout_log", (msg) => {
  document.getElementById("log_inout").textContent += `\n${msg}`;
});
socket.on("inout_done", () => {
  document.getElementById("log_inout").textContent += "\n✅ Selesai. Cek file unduhan di \\\\desktop-lg\\Downloads";
  document.getElementById("loadingOverlay").style.display = "none";
  inoutButton.disabled = false;
});

/* ===== PRINT PDF ===== */
function emitPrint(event, filename) {
  event.preventDefault();
  const printer = event.target.querySelector('select[name="printer"]').value;

  socket.emit("print_pdf", {
    pdf_path: filename,
    printer_name: printer
  });

  document.getElementById("printStatus").innerText = `🖨️ Mengirim ${filename} ke printer ${printer}...`;
}

/* ===== Pick Page ===== */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("ambil-halaman");
  if (!form) return;

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    showLoading();
    const formData = new FormData(this);
    const response = await fetch("/ambil-halaman", {
      method: "POST",
      body: formData
    });

    const html = await response.text();
    const doc = new DOMParser().parseFromString(html, "text/html");
    const newResult = doc.querySelector("#resultArea2");
    if (newResult) {
      document.querySelector("#resultArea2").innerHTML = newResult.innerHTML;
    }
    hideLoading();
  });
});

// Tambah event listener untuk drag & drop
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("mergeInput");
  const list = document.getElementById("mergeList");

  input.addEventListener("change", () => {
    list.innerHTML = "";
    [...input.files].forEach(file => {
      const li = document.createElement("li");
      li.textContent = file.name;
      li.draggable = true;
      li.className = "draggable";
      list.appendChild(li);
    });
  });

  // Drag and drop
  let dragged;
  list.addEventListener("dragstart", e => {
    dragged = e.target;
  });
  list.addEventListener("dragover", e => e.preventDefault());
  list.addEventListener("drop", e => {
    e.preventDefault();
    if (dragged && dragged !== e.target) {
      list.insertBefore(dragged, e.target);
    }
  });

  document.getElementById("gabungForm").addEventListener("submit", async e => {
    e.preventDefault();

    const formData = new FormData();
    const files = input.files;

    for (let i = 0; i < files.length; i++) {
      formData.append("pdfs", files[i]);
    }

    const order = [...list.children].map(li => li.textContent);
    order.forEach(name => formData.append("order[]", name));

    const res = await fetch("/gabung-pdf", {
      method: "POST",
      body: formData
    });

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "gabungan.pdf";
    a.click();
    URL.revokeObjectURL(url);
  });
});