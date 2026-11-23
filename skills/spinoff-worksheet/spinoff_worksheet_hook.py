"""Fail-closed numerical claim hook for saved worksheet and report text."""
from __future__ import annotations
import json,re
from decimal import Decimal,InvalidOperation
from pathlib import Path

NUMBER=re.compile(r"(?<![A-Za-z0-9])(?:\(\s*\$?\s*\d[\d,]*(?:\.\d+)?\s*\)|-?\$?\d[\d,]*(?:\.\d+)?)(?:\s*(?:%|x|million|billion|thousand))?",re.I)

def normalize(value):
    raw=value.strip().casefold()
    negative=raw.startswith("(") or raw.startswith("-")
    raw=re.sub(r"[,$()\s]", "", raw)
    raw=raw.removesuffix("million").removesuffix("billion").removesuffix("thousand")
    is_percent=raw.endswith("%")
    raw=raw.removesuffix("%")
    try:
        number=Decimal(raw)
        if negative: number=-abs(number)
        return str((number/100 if is_percent else number).normalize())
    except InvalidOperation: return None

def evidence_numbers(run_dir:Path, supplemental_paths=()):
    texts=[]
    for path in run_dir.iterdir():
        if path.is_file() and (path.suffix.lower()==".txt" or path.name in {"facts.json","worksheet.json","worksheet_closes.json","manifest.json","verification_summary.json","live_record.json"}):
            try:texts.append(path.read_text(errors="replace"))
            except OSError:pass
    config=Path(__file__).with_name("worksheet_config.json")
    if config.exists(): texts.append(config.read_text())
    supplemental=[]
    for item in supplemental_paths:
        path=Path(item)
        if path.is_file():
            supplemental.append(path)
            texts.append(path.read_text(errors="replace"))
    values=set()
    for text in texts:
        for match in NUMBER.finditer(text):
            token=normalize(match.group(0))
            if token is not None: values.add(token)
    return values

def is_source_line_locator(line:str,start:int) -> bool:
    """Allow explicit citation locators without treating every line number as evidence."""
    prefix=line[max(0,start-24):start]
    return re.search(r"(?:saved-text\s+line|lines?|L)\s*$",prefix,re.I) is not None

def validate_report(report_path:Path,run_dir:Path,supplemental_paths=()):
    report_path=Path(report_path); run_dir=Path(run_dir)
    allowed=evidence_numbers(run_dir,supplemental_paths=supplemental_paths)
    text=report_path.read_text(errors="replace")
    for line_no,line in enumerate(text.splitlines(),1):
        for match in NUMBER.finditer(line):
            token=normalize(match.group(0))
            if is_source_line_locator(line,match.start()):
                continue
            if token is not None and token not in allowed:
                raise ValueError(f"Numerical claim refused at line {line_no}: {match.group(0).strip()}")
    return True

def main():
    import argparse
    parser=argparse.ArgumentParser(description="Validate report numbers against saved run evidence.")
    parser.add_argument("report",type=Path)
    parser.add_argument("--evidence",type=Path,required=True)
    parser.add_argument("--supplemental-evidence",type=Path,action="append",default=[])
    args=parser.parse_args()
    try:
        validate_report(args.report,args.evidence,supplemental_paths=args.supplemental_evidence)
    except ValueError as exc:
        print(str(exc)); return 1
    print("HOOK PASS")
    return 0

if __name__=="__main__": raise SystemExit(main())

