"use strict";
let jobsLoading = false;
const pendingOpen = new Set();
async function submitPageJob(body) {
  const job = await request("/api/jobs", {...body, local_storage_consent: el("ocr-storage").checked});
  pendingOpen.add(job.id); await loadJobs(); notify("Document queued for background processing. You can close this tab; keep the local application and Ollama on.");
}
async function loadJobs() {
  if (jobsLoading || !config) return;
  jobsLoading = true;
  try {
    const jobs = await request("/api/jobs"); el("processing-panel").hidden = !jobs.length; el("processing-jobs").replaceChildren();
    for (const job of jobs) {
      const card = document.createElement("article"); card.className = "queue-job"; card.dataset.job = job.id;
      const heading = document.createElement("strong"); heading.textContent = `${job.name} · ${job.status}`;
      const status = document.createElement("p"); status.className = job.error ? "finding" : "hint"; status.textContent = job.error || job.progress; card.append(heading, status);
      if (["queued", "running"].includes(job.status)) { const cancel = document.createElement("button"); cancel.type = "button"; cancel.className = "secondary"; cancel.textContent = "Cancel processing"; cancel.addEventListener("click", async () => { try { await request(`/api/jobs/${job.id}/cancel`, {}); await loadJobs(); } catch (error) { notify(error.message, true); } }); card.append(cancel); }
      if (job.status === "completed" && job.result_id) { const open = document.createElement("button"); open.type = "button"; open.className = "secondary"; open.textContent = "Open processed requirement"; open.addEventListener("click", async () => { if (!canLeave()) return; try { showRecord(await request(`/api/requirements/${job.result_id}`)); } catch (error) { notify(error.message, true); } }); card.append(open);
        if (pendingOpen.has(job.id)) { pendingOpen.delete(job.id); await history(); if (!record && !dirty && !privacyDirty) { const completed=await request(`/api/requirements/${job.result_id}`); showRecord(completed); notify(completed.document.used_ocr ? "Local OCR processing completed. Compare the transcript and product lines with source images before approval." : "Document processing completed. Compare the complete source with the product lines before approval."); } }
      }
      el("processing-jobs").append(card);
    }
  } catch (error) { notify(`Processing status unavailable: ${error.message}`, true); }
  finally { jobsLoading = false; }
}
function showSourcePages() {
  const required = !!record.document.used_ocr; el("ocr-source").hidden = !required; el("source-pages").replaceChildren(); el("source-verified").checked = !!record.source_verified;
  if (!required) return;
  for (const page of record.document.page_details || []) {
    const details = document.createElement("details"), summary = document.createElement("summary"); summary.textContent = `Page ${page.page} · ${page.method === 'local_vision' ? 'local OCR' : 'text layer'} · ${page.characters} characters`; details.append(summary);
    if (page.method === 'local_vision') { const image = document.createElement("img"); image.src = `/api/requirements/${record.id}/pages/${page.page}`; image.alt = `Source preview of page ${page.page}`; image.loading = "lazy"; image.className = "source-preview"; const zoom = document.createElement("a"); zoom.href = image.src; zoom.target = "_blank"; zoom.rel = "noopener"; zoom.className = "button secondary"; zoom.textContent = "Open full-size source page"; details.append(zoom, image); }
    for (const uncertainty of page.uncertain_regions || []) { const p = document.createElement("p"); p.className = "finding"; p.textContent = uncertainty; details.append(p); }
    el("source-pages").append(details);
  }
}
el("source-verified").addEventListener("change", () => { dirty = true; el("dirty").hidden = false; el("rfq-preview").hidden = true; });
el("coverage-verified").addEventListener("change", () => { dirty = true; el("dirty").hidden = false; el("rfq-preview").hidden = true; });
setInterval(loadJobs, 2000);
loadJobs();
