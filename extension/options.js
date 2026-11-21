const DEFAULTS = { apiUrl: "http://localhost:8766", apiKey: "", task: "", detonate: false, enabled: true };
const $ = (id) => document.getElementById(id);

chrome.storage.local.get(DEFAULTS).then((s) => {
  $("apiUrl").value = s.apiUrl;
  $("apiKey").value = s.apiKey; // type=password: shown masked
  $("task").value = s.task;
  $("detonate").checked = s.detonate;
  $("enabled").checked = s.enabled;
});

$("save").onclick = async () => {
  await chrome.storage.local.set({
    apiUrl: $("apiUrl").value.trim() || DEFAULTS.apiUrl,
    apiKey: $("apiKey").value.trim(),
    task: $("task").value.trim(),
    detonate: $("detonate").checked,
    enabled: $("enabled").checked,
  });
  $("saved").textContent = "Saved";
  setTimeout(() => ($("saved").textContent = ""), 1500);
};
