/* Full long-document workflow: real files, actual local model parts, persisted review. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..'),base=process.env.RFQ_BASE_URL||'http://127.0.0.1:8766';
const expected=JSON.parse(fs.readFileSync(path.join(root,'data/long-inputs/expected.json'),'utf8')).expected;
(async()=>{
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
  const reports=[],ids=[],errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  try{
    await page.goto(base);
    await page.waitForFunction(()=>document.querySelectorAll('#supplier-categories input').length===3);
    for(const extension of ['txt','pdf','docx','xlsx']){
      await page.locator('#ocr-storage').check();
      await page.locator('#file').setInputFiles(path.join(root,'data/long-inputs',`requirement.${extension}`));
      const pending=page.waitForResponse(res=>res.url()===`${base}/api/jobs`&&res.request().method()==='POST');
      await page.getByRole('button',{name:/Extract product/}).click();
      const response=await pending;assert.equal(response.status(),202,await response.text());
      const submitted=await response.json();let job=submitted,previous='';const deadline=Date.now()+900000;
      while(['queued','running'].includes(job.status)&&Date.now()<deadline){
        job=await(await page.request.get(`${base}/api/jobs/${submitted.id}`)).json();
        if(previous!==job.progress){console.log(`${extension}: ${job.progress}`);previous=job.progress;}
        if(['queued','running'].includes(job.status))await new Promise(resolve=>setTimeout(resolve,1000));
      }
      assert.equal(job.status,'completed',JSON.stringify(job));ids.push(job.result_id);
      const record=await(await page.request.get(`${base}/api/requirements/${job.result_id}`)).json();
      assert.ok(Buffer.byteLength(record.document.text,'utf8')>16000);
      assert.equal(record.lines.length,24);
      assert.equal(new Set(record.lines.map(line=>line.id)).size,24);
      assert.equal(new Set(record.lines.map(line=>line.source_start)).size,24);
      assert.ok(record.analysis.parts.length>1);
      for(let i=0;i<expected.length;i++){
        for(const key of ['line_number','quantity','unit','category'])assert.equal(record.lines[i][key],expected[i][key],`${extension} ${i} ${key}`);
        assert.ok((record.lines[i].specification||'').toLowerCase().includes(expected[i].tail.toLowerCase()));
        assert.equal(record.document.text.slice(record.lines[i].source_start,record.lines[i].source_end),record.lines[i].source_quote);
      }
      reports.push({extension,utf8_bytes:Buffer.byteLength(record.document.text,'utf8'),positions:24,parts:record.analysis.parts.length,seconds:record.analysis.elapsed_seconds,findings:record.analysis.validation_findings});
      if(extension==='txt'){
        await page.reload();
        await page.locator('#history .history-item').first().click();
        await page.waitForFunction(()=>document.querySelectorAll('#lines .line').length===24);
        await page.locator('#lines .line').nth(13).getByRole('button',{name:'View source',exact:true}).click();
        assert.equal(await page.locator('#source mark').textContent(),record.lines[13].source_quote);
        for(let i=0;i<24;i++){
          const card=page.locator('#lines .line').nth(i);
          if(record.lines[i].quantity===null){await card.locator('[data-key=excluded]').check();await card.locator('[data-key=exclusion_reason]').fill('Fictional QA: quantity awaiting customer clarification');}
          else await card.locator('[data-key=approved]').check();
        }
        await page.getByRole('button',{name:'Save review',exact:true}).click();
        await page.waitForFunction(()=>!document.getElementById('save').disabled);
        assert.equal(await page.locator('#status').textContent(),'NEEDS REVIEW');
        await page.locator('#coverage-verified').check();
        await page.getByRole('button',{name:'Save review',exact:true}).click();
        await page.waitForFunction(()=>document.getElementById('status').textContent==='REVIEWED');
        const downloadPromise=page.waitForEvent('download');await page.locator('#export').click();const download=await downloadPromise;
        const target=path.join(root,'data','long-review-export.json');await download.saveAs(target);
        const exported=JSON.parse(fs.readFileSync(target,'utf8'));assert.equal(exported.lines.length,24);assert.equal(exported.status,'reviewed');assert.equal(exported.lines[13].source_start,record.lines[13].source_start);
        await page.locator('#coverage-review').screenshot({path:path.join(root,'data','long-coverage-desktop.png')});
        await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.setViewportSize({width:1440,height:1000});
      }
    }
    assert.deepEqual(errors,[]);
    const config=await(await page.request.get(`${base}/api/config`)).json();
    for(const id of ids)assert.equal((await page.request.post(`${base}/api/requirements/${id}/delete`,{headers:{Origin:base,'X-Workbench-Token':config.token},data:{}})).status(),200);
    fs.writeFileSync(path.join(root,'data','long-browser-report.json'),JSON.stringify({passed:true,reports,full_source_review_required:true,highlight_matches_source:true,review_reload_export:true,mobile_overflow:false,page_errors:errors},null,2));
    console.log(fs.readFileSync(path.join(root,'data','long-browser-report.json'),'utf8'));
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
