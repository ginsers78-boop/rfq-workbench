"""Actual multi-sheet Excel inference with reordered quantity/unit columns."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from rfq_workbench.extraction import extract
from rfq_workbench.readers import read_document

root=Path(__file__).resolve().parent.parent
out=root/"data"/"long-inputs"
labels=json.loads((out/"expected.json").read_text())["expected"][:6]*2
document=read_document("table-order.xlsx",(out/"table-order.xlsx").read_bytes())
categories=json.loads((root/"categories.json").read_text())
result=extract(document["text"],categories,progress=lambda text:print(text,flush=True))
findings=[]
actual=result["extraction"]["lines"]
if len(actual)!=12:findings.append({"issue":"line_count","actual":len(actual)})
for index,(label,line) in enumerate(zip(labels,actual)):
    for key in ["line_number","description","specification","quantity","unit","category"]:
        if line[key]!=label[key]:findings.append({"index":index,"field":key,"expected":label[key],"actual":line[key]})
report={"passed":not findings,"columns_reordered_between_sheets":True,"source_numbers_restart_per_sheet":True,"positions":len(actual),"findings":findings,"result":result}
(out/"table-order-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({key:report[key] for key in ["passed","columns_reordered_between_sheets","source_numbers_restart_per_sheet","positions","findings"]}),flush=True)
if findings:raise AssertionError("Reordered Excel columns failed; inspect actual output.")
