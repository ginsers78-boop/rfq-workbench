"use strict";
let config, record, busy = false, dirty = false, suppliers = [], editingSupplier = null, activeRFQ = null, privacyDirty = false;
const el = id => document.getElementById(id);
function notify(message, error = false) { el("message").textContent = message; el("message").className = error ? "error" : ""; el("message").hidden = false; }
async function request(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json", "X-Workbench-Token": config.token}, body: JSON.stringify(body)});
  let data;
  try { data = await response.json(); } catch { throw new Error("The local server returned an unreadable response."); }
  if (!response.ok) throw new Error(data.error || "The operation failed.");
  return data;
}
function markDirty() { dirty = true; el("dirty").hidden = false; el("rfq-preview").hidden = true; if (record?.document.used_ocr) el("source-verified").checked = false; el("coverage-verified").checked = false; }
function canLeave() { return (!dirty && !privacyDirty) || window.confirm("Discard your unsaved review or privacy edits?"); }
function field(label, value, key, type = "text", wide = false) {
  const wrapper = document.createElement("label"); wrapper.textContent = label; if (wide) wrapper.className = "wide";
  const input = document.createElement(type === "textarea" ? "textarea" : "input");
  if (type !== "textarea") input.type = type;
  if (type === "number") { input.step = key === "source_page" ? "1" : "any"; input.min = key === "source_page" ? "1" : "0"; if (key === "source_page") input.max = "50"; }
  input.dataset.key = key; input.value = value ?? ""; input.addEventListener("input", markDirty); wrapper.append(input); return wrapper;
}
function addLine(line, manual = false) {
  const card = document.createElement("article"); card.className = "line"; card.dataset.id = line.id; card.dataset.manual = String(manual);
  const heading = document.createElement("div"); heading.className = "line-head";
  const title = document.createElement("strong"); title.textContent = manual ? "Manually added position" : `Original line ${line.line_number}`; heading.append(title); card.append(heading);
  const pages = line.source_page ? [line.source_page] : record.analysis.line_pages?.[line.source_start ?? line.line_number] || []; if (pages.length) title.textContent += ` · source page ${pages.join(', ')}`;
  if (line.source_start != null && line.source_end != null) { const locate = document.createElement("button"); locate.type = "button"; locate.className = "secondary"; locate.textContent = "View source"; locate.addEventListener("click", () => { const source=record.document.text, mark=document.createElement("mark"); mark.textContent=source.slice(line.source_start,line.source_end); el("source").replaceChildren(document.createTextNode(source.slice(0,line.source_start)),mark,document.createTextNode(source.slice(line.source_end))); el("source").parentElement.open=true; mark.scrollIntoView({block:"center",behavior:"smooth"}); }); heading.append(locate); }
  const grid = document.createElement("div"); grid.className = "line-grid";
  if (manual) grid.append(field("Original line number", line.line_number, "line_number"));
  grid.append(field("Product description", line.description, "description", "text", true), field("Technical specification", line.specification, "specification", "textarea", true), field("Quantity", line.quantity, "quantity", "number"), field("Unit", line.unit, "unit"));
  const categoryLabel = document.createElement("label"); categoryLabel.textContent = "Category";
  const select = document.createElement("select"); select.dataset.key = "category";
  for (const category of config.categories) { const option = document.createElement("option"); option.value = category.id; option.textContent = category.id; select.append(option); }
  select.value = line.category; select.addEventListener("change", markDirty); categoryLabel.append(select); grid.append(categoryLabel); card.append(grid);
  if (manual) { card.append(field("Exact quotation from the original text", "", "source_quote", "textarea", true)); if (record.document.used_ocr) card.append(field("Image page number (for a line transcribed manually from an OCR preview)", null, "source_page", "number")); }
  else { const quote = document.createElement("p"); quote.className = "quote"; quote.textContent = `${line.source_kind === 'image_transcription' ? `Human transcription from image page ${line.source_page}: ` : ''}${line.source_quote}`; card.append(quote); }
  const approve = document.createElement("label"); approve.className = "approve"; const checkbox = document.createElement("input"); checkbox.type = "checkbox"; checkbox.dataset.key = "approved"; checkbox.checked = line.approved; checkbox.addEventListener("change", markDirty); approve.append(checkbox, document.createTextNode("I checked this line against the source")); card.append(approve); el("lines").append(card);
  const exclude = document.createElement("label"); exclude.className = "approve"; const excluded = document.createElement("input"); excluded.type = "checkbox"; excluded.dataset.key = "excluded"; excluded.checked = line.excluded || false;
  excluded.addEventListener("change", () => { if (excluded.checked) checkbox.checked = false; checkbox.disabled = excluded.checked; markDirty(); }); checkbox.disabled = excluded.checked;
  exclude.append(excluded, document.createTextNode("Exclude this position from RFQs")); card.append(exclude, field("Reason for exclusion (required when excluded)", line.exclusion_reason || "", "exclusion_reason"));
}
function showRecord(next) {
  record = next; dirty = false; el("dirty").hidden = true; el("review").hidden = false;
  el("status").textContent = record.status === "reviewed" ? "REVIEWED" : "NEEDS REVIEW";
  el("record-info").textContent = `${record.document.name} · revision ${record.revision} · ${record.lines.length} positions · model ${record.analysis.model} · ${record.analysis.elapsed_seconds}s`;
  el("source").textContent = record.document.text; el("lines").replaceChildren(); record.lines.forEach(line => addLine(line));
  el("findings").replaceChildren();
  for (const finding of record.analysis.validation_findings) { const p = document.createElement("p"); p.className = "finding"; p.textContent = `Original extraction warning, line ${finding.line_number}: ${finding.reason}`; el("findings").append(p); }
  el("export").href = `/api/requirements/${record.id}/export`; el("export").download = "requirement-review.json";
  el("rfq-preview").hidden = true; activeRFQ = null;
  showSourcePages();
  el("coverage-review").hidden = !(record.analysis.parts?.length > 1 || record.analysis.validation_findings.some(finding => 'source_start' in finding)); el("coverage-verified").checked = !!record.coverage_verified;
  loadProcurement().catch(error => notify(error.message, true));
}
async function history() {
  const records = await request("/api/requirements"); el("history").replaceChildren();
  if (!records.length) { const p = document.createElement("p"); p.className = "hint"; p.textContent = "Your saved requirements will appear here."; el("history").append(p); }
  for (const item of records) { const button = document.createElement("button"); button.type = "button"; button.className = "history-item"; button.textContent = item.name; const small = document.createElement("small"); small.textContent = `${item.status.replaceAll("_", " ")} · ${new Date(item.created).toLocaleDateString()}`; button.append(small); button.addEventListener("click", async () => { if (!canLeave()) return; try { showRecord(await request(`/api/requirements/${item.id}`)); } catch (error) { notify(error.message, true); } }); el("history").append(button); }
}
function fileBase64(file) { return new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(",")[1]); reader.onerror = () => reject(new Error("The browser could not read the selected file.")); reader.readAsDataURL(file); }); }
el("upload").addEventListener("submit", async event => {
  event.preventDefault(); if (busy || !canLeave()) return;
  const file = el("file").files[0], text = el("text").value;
  if (file && text.trim()) { notify("Choose one input: a file or pasted text. Clear the other input first.", true); return; }
  if (!file && !text.trim()) { notify("Select a document or paste a requirement first.", true); return; }
  if (file && (file.size > 10 * 1024 * 1024 || !/\.(txt|pdf|docx|xlsx|png|jpe?g|webp)$/i.test(file.name))) { notify("Choose a supported document or image up to 10 MB.", true); return; }
  const pageProcessing = el("ocr-storage").checked || (file && /\.(png|jpe?g|webp)$/i.test(file.name));
  if (pageProcessing && !el("ocr-storage").checked) { notify("Confirm local OCR file and page-preview storage before processing images.", true); return; }
  busy = true; el("analyze").disabled = true; el("progress").textContent = "Extracting locally… This can take up to four minutes."; notify("Reading the requirement and checking the model output…");
  try { const upload = file || (pageProcessing ? new File([text], "pasted-requirement.txt", {type:"text/plain"}) : null); const body = upload ? {file: {name: upload.name, base64: await fileBase64(upload)}} : {text}; if (pageProcessing) { await submitPageJob(body); } else { showRecord(await request("/api/analyze", body)); await history(); notify("Extraction saved. Check every position against the source before approving it."); el("review").scrollIntoView({behavior: "smooth", block: "start"}); } }
  catch (error) { notify(error.message, true); }
  finally { busy = false; el("analyze").disabled = false; el("progress").textContent = "Runs on your local Ollama model."; }
});
el("add-line").addEventListener("click", () => { addLine({id: crypto.randomUUID(), line_number: "", description: "", specification: null, quantity: null, unit: null, category: "Unclassified", source_quote: "", approved: false}, true); markDirty(); });
el("review-form").addEventListener("submit", async event => {
  event.preventDefault(); el("save").disabled = true;
  try {
    const lines = [...el("lines").children].map(card => {
      const original = record.lines.find(line => line.id === card.dataset.id);
      const line = original ? {...original} : {id: card.dataset.id};
      for (const input of card.querySelectorAll("[data-key]")) { const key = input.dataset.key; line[key] = ["approved", "excluded"].includes(key) ? input.checked : ["quantity", "source_page"].includes(key) ? (input.value === "" ? null : Number(input.value)) : ["specification", "unit"].includes(key) ? (input.value.trim() || null) : input.value.trim(); }
      return line;
    });
    showRecord(await request(`/api/requirements/${record.id}/review`, {revision: record.revision, lines, source_verified: el("source-verified").checked, coverage_verified: el("coverage-verified").checked})); await history(); notify(!el("coverage-review").hidden && !record.coverage_verified ? "Review saved. Compare the complete source and confirm coverage before RFQ preparation." : record.document.used_ocr && !record.source_verified ? "Review saved. Compare the OCR with source images and confirm it before RFQ preparation." : "Review saved on this computer.");
  } catch (error) { notify(error.message, true); }
  finally { el("save").disabled = false; }
});
el("delete").addEventListener("click", async () => { if (!window.confirm("Delete this saved requirement, its source text, history and RFQ packages? This cannot be undone in the application.")) return; try { await request(`/api/requirements/${record.id}/delete`, {}); record = null; dirty = false; el("review").hidden = true; el("procurement").hidden = true; await history(); notify("The local record was deleted."); } catch (error) { notify(error.message, true); } });
el("refresh").addEventListener("click", () => history().catch(error => notify(error.message, true)));
window.addEventListener("beforeunload", event => { if (dirty || privacyDirty) { event.preventDefault(); event.returnValue = ""; } });
