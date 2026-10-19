"use strict";
function choice(label, value, checked = false) {
  const wrapper = document.createElement("label"); wrapper.className = "approve";
  const box = document.createElement("input"); box.type = "checkbox"; box.value = value; box.checked = checked; wrapper.append(box, document.createTextNode(label)); return wrapper;
}
function resetSupplier() { editingSupplier = null; el("supplier-heading").textContent = "Add supplier"; el("supplier-name").value = ""; el("supplier-email").value = ""; el("supplier-active").checked = true; for (const box of el("supplier-categories").querySelectorAll("input")) box.checked = false; }
async function loadSuppliers() {
  suppliers = await request("/api/suppliers"); el("supplier-list").replaceChildren();
  if (!suppliers.length) { const p = document.createElement("p"); p.className = "hint"; p.textContent = "No suppliers yet. Add a supplier before preparing an RFQ."; el("supplier-list").append(p); }
  for (const supplier of suppliers) {
    const button = document.createElement("button"); button.type = "button"; button.className = "history-item"; button.textContent = `${supplier.name} · ${supplier.email} · ${supplier.active ? 'active' : 'inactive'}`;
    const small = document.createElement("small"); small.textContent = `${supplier.categories.join(', ')} · permanent ID ${supplier.id}`; button.append(small);
    button.addEventListener("click", () => { editingSupplier = supplier; el("supplier-heading").textContent = "Edit supplier"; el("supplier-name").value = supplier.name; el("supplier-email").value = supplier.email; el("supplier-active").checked = supplier.active; for (const box of el("supplier-categories").querySelectorAll("input")) box.checked = supplier.categories.includes(box.value); }); el("supplier-list").append(button);
  }
  renderSelection();
}
function renderSelection() {
  el("supplier-selection").replaceChildren(); if (!record) return;
  const categories = [...new Set(record.lines.filter(line => !line.excluded).map(line => line.category))];
  for (const category of categories) {
    const group = document.createElement("fieldset"); group.dataset.category = category; const title = document.createElement("legend"); title.textContent = category; group.append(title);
    const matching = suppliers.filter(supplier => supplier.active && supplier.categories.includes(category));
    if (!matching.length) { const p = document.createElement("p"); p.className = "hint"; p.textContent = "No active suppliers for this category. Add one in Supplier directory."; group.append(p); }
    for (const supplier of matching) group.append(choice(`${supplier.name} · ${supplier.email}`, supplier.id)); group.addEventListener("change", () => { el("rfq-preview").hidden = true; activeRFQ = null; }); el("supplier-selection").append(group);
  }
}
async function loadProcurement() {
  const identifier = record.id, revisionNumber = record.revision;
  const [privacy, revisions, rfqs] = await Promise.all([request(`/api/requirements/${identifier}/privacy`), request(`/api/requirements/${identifier}/history`), request(`/api/requirements/${identifier}/rfqs`)]);
  if (!record || record.id !== identifier || record.revision !== revisionNumber) return;
  el("procurement").hidden = false; el("privacy-markers").value = privacy.markers.join('\n'); el("privacy-confirm").checked = privacy.confirmed; privacyDirty = false;
  el("audit-history").replaceChildren();
  for (const revision of revisions) { const details = document.createElement("details"), summary = document.createElement("summary"), pre = document.createElement("pre"); summary.textContent = `Revision ${revision.revision} · ${revision.event.replaceAll('_',' ')} · ${new Date(revision.recorded).toLocaleString()}`; pre.textContent = JSON.stringify(revision.record, null, 2); details.append(summary, pre); el("audit-history").append(details); }
  el("saved-rfqs").replaceChildren();
  for (const rfq of rfqs) { const button = document.createElement("button"); button.type = "button"; button.className = "history-item"; button.textContent = `Saved RFQ · revision ${rfq.revision} · ${rfq.status.replaceAll('_',' ')}${rfq.revision !== record.revision ? ' · outdated' : ''}`; button.addEventListener("click", async () => { if (dirty) { notify("Save your review edits before opening an RFQ.", true); return; } try { showRFQ(await request(`/api/rfqs/${rfq.id}`)); } catch (error) { notify(error.message, true); } }); el("saved-rfqs").append(button); }
  renderSelection();
}
function showRFQ(rfq) {
  activeRFQ = rfq; el("rfq-preview").hidden = false; el("rfq-confirm").checked = false; el("download-rfq").hidden = true; el("rfq-messages").replaceChildren();
  for (const message of rfq.messages) { const article = document.createElement("article"); article.className = "rfq-message"; const heading = document.createElement("h3"); heading.textContent = message.subject; const bcc = document.createElement("p"); bcc.className = "hint"; bcc.textContent = `BCC: ${message.bcc.map(supplier => `${supplier.name} <${supplier.email}>`).join('; ')}`; const pre = document.createElement("pre"); pre.textContent = message.body; const attachment = document.createElement("p"); attachment.className = "hint"; attachment.textContent = `Excel reply template: ${message.lines.length} positions. Reference and permanent line IDs are included; source quotations and customer headers are excluded.`; article.append(heading, bcc, pre, attachment); el("rfq-messages").append(article); }
}
el("supplier-reset").addEventListener("click", resetSupplier);
el("privacy-markers").addEventListener("input", () => { privacyDirty = true; el("privacy-confirm").checked = false; el("rfq-preview").hidden = true; });
el("privacy-confirm").addEventListener("change", () => { privacyDirty = true; el("rfq-preview").hidden = true; });
el("supplier-form").addEventListener("submit", async event => { event.preventDefault(); const button = event.submitter; button.disabled = true; try { await request("/api/suppliers", {id: editingSupplier?.id || null, revision: editingSupplier?.revision || 0, name: el("supplier-name").value, email: el("supplier-email").value, categories: [...el("supplier-categories").querySelectorAll("input:checked")].map(box => box.value), active: el("supplier-active").checked}); resetSupplier(); await loadSuppliers(); el("rfq-preview").hidden = true; notify("Supplier saved. Its permanent ID is preserved when edited."); } catch (error) { notify(error.message, true); } finally { button.disabled = false; } });
el("privacy-form").addEventListener("submit", async event => { event.preventDefault(); if (dirty) { notify("Save your product review before saving the privacy checklist.", true); return; } const button = event.submitter; button.disabled = true; try { showRecord(await request(`/api/requirements/${record.id}/privacy`, {revision: record.revision, markers: el("privacy-markers").value.split('\n').map(value => value.trim()).filter(Boolean), confirmed: el("privacy-confirm").checked})); await history(); notify("Privacy checklist saved. Prepare and inspect the RFQ preview next."); } catch (error) { notify(error.message, true); } finally { button.disabled = false; } });
el("rfq-form").addEventListener("submit", async event => { event.preventDefault(); if (dirty || privacyDirty) { notify("Save your review and privacy edits before preparing RFQs.", true); return; } el("prepare-rfq").disabled = true; try { const selection = {}; for (const group of el("supplier-selection").querySelectorAll("fieldset")) selection[group.dataset.category] = [...group.querySelectorAll("input:checked")].map(box => box.value); const rfq = await request(`/api/requirements/${record.id}/rfqs`, {revision: record.revision, selection}); showRFQ(rfq); notify("RFQ preview prepared locally. Inspect all messages and recipients; nothing has been sent."); } catch (error) { notify(error.message, true); } finally { el("prepare-rfq").disabled = false; } });
el("approve-rfq").addEventListener("click", async () => { if (dirty || privacyDirty || !el("rfq-confirm").checked) { notify("Check the exact preview and confirm it before approving the export.", true); return; } try { activeRFQ = await request(`/api/rfqs/${activeRFQ.id}/approve`, {confirmed: true}); el("download-rfq").href = `/api/rfqs/${activeRFQ.id}/download`; el("download-rfq").download = "rfq-preparation-package.zip"; el("download-rfq").hidden = false; notify("Local export approved. Download the internal ZIP and follow its dispatch instructions. No email was sent."); } catch (error) { notify(error.message, true); } });
(async () => { try { config = await request("/api/config"); for (const category of config.categories.filter(item => item.id !== "Unclassified")) el("supplier-categories").append(choice(category.id, category.id)); await Promise.all([history(), loadSuppliers()]); } catch (error) { notify(`Could not open the local workspace: ${error.message}`, true); el("analyze").disabled = true; } })();
