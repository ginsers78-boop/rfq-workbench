/* Real files, persistent queue, local vision and browser review. No route mocks. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname,'..');
const base = process.env.RFQ_BASE_URL || 'http://127.0.0.1:8766';
const expected = JSON.parse(fs.readFileSync(path.join(root,'data/ocr-inputs/expected.json'),'utf8'));
const files = process.env.RFQ_OCR_FILES ? process.env.RFQ_OCR_FILES.split(',') : ['requirement.png','requirement.jpg','requirement.webp','scanned.pdf','mixed.pdf','blank.png'];
const reportName = process.env.RFQ_OCR_FILES ? 'ocr-selected-browser-report.json' : 'ocr-browser-report.json';
(async()=>{
  const browser = await chromium.launch({headless:true});
  const page = await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[], reports=[], ids=[];
  page.on('pageerror',error=>errors.push(error.message));
  try {
    await page.goto(base);
    await page.waitForFunction(()=>document.querySelectorAll('#supplier-categories input').length===3);
    await page.locator('#file').setInputFiles(path.join(root,'data/ocr-inputs/requirement.png'));
    await page.getByRole('button',{name:/Extract product/}).click();
    assert.match(await page.locator('#message').textContent(),/Confirm local OCR/);
    await page.locator('#ocr-storage').check();
    for(const filename of files) {
      await page.locator('#ocr-storage').check();
      await page.locator('#file').setInputFiles(path.join(root,'data/ocr-inputs',filename));
      const pending=page.waitForResponse(res=>res.url()===`${base}/api/jobs`&&res.request().method()==='POST');
      await page.getByRole('button',{name:/Extract product/}).click();
      const response=await pending;
      assert.equal(response.status(),202,await response.text());
      const submitted=await response.json();
      let job=submitted, previous='', deadline=Date.now()+720000;
      while(['queued','running'].includes(job.status)&&Date.now()<deadline) {
        job=await (await page.request.get(`${base}/api/jobs/${submitted.id}`)).json();
        if(job.progress!==previous){ console.log(`${filename}: ${job.progress}`); previous=job.progress; }
        if(['queued','running'].includes(job.status)) await new Promise(resolve=>setTimeout(resolve,1000));
      }
      if(filename==='blank.png') {
        assert.equal(job.status,'failed',JSON.stringify(job));
        assert.match(job.error,/no readable text/i);
        reports.push({filename,status:job.status,error:job.error}); continue;
      }
      assert.equal(job.status,'completed',JSON.stringify(job));
      const record=await (await page.request.get(`${base}/api/requirements/${job.result_id}`)).json();
      ids.push(record.id);
      assert.equal(record.document.used_ocr,true);
      const labels=filename==='mixed.pdf' ? [
        {line_number:'1',quantity:200,unit:'m',category:'Electrical'},
        {line_number:'2',quantity:40,unit:'pcs',category:'Pipes and fittings'},
        {line_number:'3',quantity:120,unit:'pcs',category:'Fasteners'}] : expected.image_lines;
      assert.equal(record.lines.length,labels.length);
      for(const label of labels){const line=record.lines.find(value=>value.line_number===label.line_number);assert.ok(line,JSON.stringify(record.lines));for(const key of ['quantity','unit','category']) assert.equal(line[key],label[key],`${filename} ${label.line_number} ${key}`);}
      const ocrPages=record.document.page_details.filter(value=>value.method==='local_vision');
      if(filename==='mixed.pdf'){assert.equal(record.document.page_details[0].method,'text_layer');assert.equal(ocrPages[0].page,2);}
      for(const source of ocrPages) assert.equal((await page.request.get(`${base}/api/requirements/${record.id}/pages/${source.page}`)).status(),200);
      reports.push({filename,status:job.status,positions:record.lines.length,ocr_pages:ocrPages.map(value=>({page:value.page,seconds:value.elapsed_seconds,uncertainties:value.uncertain_regions})),model_seconds:record.analysis.elapsed_seconds});
      if(filename==='requirement.png') {
        await page.reload();
        await page.waitForFunction(()=>document.querySelectorAll('#history .history-item').length>0);
        await page.locator('#history .history-item').first().click();
        await page.locator('#ocr-source').waitFor({state:'visible'});
        await page.locator('#source-pages summary').first().click();
        await page.locator('#source-pages img').first().waitFor({state:'visible'});
        await page.waitForFunction(()=>{const image=document.querySelector('#source-pages img');return image&&image.complete&&image.naturalWidth>0;});
        const cards=page.locator('#lines .line');
        for(let i=0;i<3;i++) await cards.nth(i).locator('[data-key=approved]').check();
        await cards.nth(3).locator('[data-key=excluded]').check();
        await cards.nth(3).locator('[data-key=exclusion_reason]').fill('Customer omitted this position in fictional OCR QA');
        await page.getByRole('button',{name:'Save review',exact:true}).click();
        await page.waitForFunction(()=>!document.getElementById('save').disabled);
        assert.equal(await page.locator('#status').textContent(),'NEEDS REVIEW');
        await page.locator('#source-verified').check();
        await page.getByRole('button',{name:'Save review',exact:true}).click();
        await page.waitForFunction(()=>document.getElementById('status').textContent==='REVIEWED');
        await page.locator('#source-pages summary').first().click();
        await page.waitForFunction(()=>{const image=document.querySelector('#source-pages img');return image&&image.complete&&image.naturalWidth>0;});
        await page.locator('#ocr-source').screenshot({path:path.join(root,'data','ocr-review-desktop.png')});
        await page.setViewportSize({width:390,height:844});
        assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
        await page.locator('#ocr-source').screenshot({path:path.join(root,'data','ocr-review-mobile.png')});
        await page.setViewportSize({width:1440,height:1000});
        // Exercise explicit human image transcription without altering raw OCR.
        await page.getByRole('button',{name:'Add a missed line',exact:true}).click();
        const added=page.locator('#lines .line').last();
        await added.locator('[data-key=line_number]').fill('10-qa-split');
        await added.locator('[data-key=description]').fill('Fictional QA manual split of visible valve row');
        await added.locator('[data-key=source_quote]').fill('10. Brass ball valve 1/2 inch BSP, PN16, 12 pcs');
        await added.locator('[data-key=source_page]').fill('1');
        await added.locator('[data-key=excluded]').check();
        await added.locator('[data-key=exclusion_reason]').fill('UI QA entry, excluded from supplier requests');
        await page.locator('#source-verified').check();
        await page.getByRole('button',{name:'Save review',exact:true}).click();
        await page.waitForFunction(()=>!document.getElementById('save').disabled);
        assert.match(await page.locator('#lines .line').last().locator('.quote').textContent(),/Human transcription from image page 1/);
        const reviewed=await (await page.request.get(`${base}/api/requirements/${record.id}`)).json();
        assert.equal(reviewed.document.text,record.document.text);
        assert.equal(reviewed.lines.at(-1).source_kind,'image_transcription');
      }
    }
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(root,'data',reportName),JSON.stringify({passed:true,reports,consent_required:true,visual_review_required:true,manual_image_transcription:true,source_preview_after_reload:true,mobile_overflow:false,page_errors:errors},null,2));
    const config=await (await page.request.get(`${base}/api/config`)).json();
    for(const id of ids) await page.request.post(`${base}/api/requirements/${id}/delete`,{headers:{Origin:base,'X-Workbench-Token':config.token},data:{}});
    console.log(fs.readFileSync(path.join(root,'data',reportName),'utf8'));
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
