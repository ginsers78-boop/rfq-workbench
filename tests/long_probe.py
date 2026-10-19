"""Real local inference against long TXT and actual six-page PDF fixtures."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from rfq_workbench.extraction import extract, annotate_pages
from rfq_workbench.readers import read_document

root=Path(__file__).resolve().parent.parent
out=root/"data"/"long-inputs"
labels=json.loads((out/"expected.json").read_text())["expected"]
categories=json.loads((root/"categories.json").read_text())
reports=[]
for name in ["requirement.txt","requirement.pdf"]:
    document=read_document(name,(out/name).read_bytes())
    def record_evidence(item):
        (out/(name+"-part-"+item["part"].replace("/","of")+".json")).write_text(json.dumps(item,ensure_ascii=False,indent=2),encoding="utf-8")
    result=annotate_pages(extract(document["text"],categories,progress=lambda message: print(f"{name}: {message}",flush=True),evidence=record_evidence),document)
    findings=[]
    actual=result["extraction"]["lines"]
    if len(actual)!=len(labels):findings.append({"issue":"line_count","expected":len(labels),"actual":len(actual)})
    for index,(label,line) in enumerate(zip(labels,actual)):
        for key in ["line_number","quantity","unit","category"]:
            if line[key]!=label[key]:findings.append({"index":index,"field":key,"expected":label[key],"actual":line[key]})
        if label["tail"].casefold() not in (line["specification"] or "").casefold():findings.append({"index":index,"field":"end_of_section_specification","expected_contains":label["tail"],"actual":line["specification"]})
    if len({location["start"] for location in result["line_locations"]})!=len(actual):findings.append({"issue":"duplicate_source_anchor"})
    report={"file":name,"utf8_bytes":len(document["text"].encode()),"pages":document["pages"],"expected_positions":len(labels),"findings":findings,"result":result}
    (out/(name+"-report.json")).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({key:report[key] for key in ["file","utf8_bytes","pages","expected_positions","findings"]}),flush=True)
    if findings:raise AssertionError("Long-document quality gate failed; inspect the actual model report.")
    if result["validation_findings"]:raise AssertionError("Long-document validation needs review; inspect the actual model report.")
    reports.append({"file":name,"positions":len(actual),"parts":len(result["parts"]),"model_seconds":result["elapsed_seconds"]})
(out/"probe-report.json").write_text(json.dumps({"passed":True,"reports":reports},indent=2),encoding="utf-8")
print(json.dumps({"passed":True,"reports":reports}),flush=True)
