#!/usr/bin/env python3
"""Deterministic one-desk pipeline and network-free replay."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, time
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
SEEKER=ROOT/"skills"/"spinoff-seeker"/"scripts"/"seeker.py"
WORKSHEET=ROOT/"skills"/"spinoff-worksheet"/"worksheet.py"
TEAM_PROJECT=ROOT/"equity_research_team"
TEAM_SOURCE=TEAM_PROJECT/"src"
sys.path.insert(0, str(WORKSHEET.parent))
EASTERN=ZoneInfo("America/New_York")

class DeskRunError(RuntimeError): pass

def create_run_dir(root:Path=ROOT/"runs"/"desk") -> Path:
    stamp=datetime.now(EASTERN).strftime("%Y-%m-%d_%H-%M-%S-%f")
    path=root/f"DESK_{stamp}"
    path.mkdir(parents=True,exist_ok=False)
    return path

def run_command(name,command,run_dir,*,cwd=ROOT,env=None):
    started=time.monotonic()
    proc=subprocess.run(command,cwd=cwd,env=env,text=True,capture_output=True)
    elapsed=time.monotonic()-started
    (run_dir/f"{name}_stdout.txt").write_text(proc.stdout,encoding="utf-8")
    (run_dir/f"{name}_stderr.txt").write_text(proc.stderr,encoding="utf-8")
    (run_dir/f"{name}_timing.json").write_text(json.dumps({"part":name,"elapsed_seconds":round(elapsed,6),"return_code":proc.returncode},indent=2)+"\n")
    print(f"Part {name}: {elapsed:.3f} seconds")
    if proc.returncode:
        failure={"part":name,"return_code":proc.returncode,"stdout":proc.stdout,"stderr":proc.stderr,"elapsed_seconds":elapsed}
        (run_dir/"failure.json").write_text(json.dumps(failure,indent=2)+"\n")
        exact=(proc.stderr.strip().splitlines() or proc.stdout.strip().splitlines() or [f"exit code {proc.returncode}"])[-1]
        print(f"Run folder: {run_dir}")
        raise DeskRunError(exact)
    return proc.stdout

def find_team_run(stdout:str) -> Path:
    match=re.search(r"(?m)^Run folder: (.+)$",stdout)
    if not match: raise DeskRunError("Agent team completed without printing its run folder.")
    path=Path(match.group(1).strip()).resolve()
    if not (path/"verified_report.md").is_file(): raise DeskRunError("Agent team run has no mandatory verified report.")
    return path

def registry_row(ticker:str,registry_path:Path|None):
    if registry_path is None or not registry_path.is_file(): return None
    ticker = str(ticker or "")
    rows=json.loads(registry_path.read_text()).get("records",[])
    return next((x for x in rows if str(x.get("ticker","")).upper()==ticker.upper()),None)

def assemble_final(run_dir:Path,team_dir:Path|None,worksheet_path:Path|None,ticker:str,spinoff:dict|None):
    filing_items=[]
    if team_dir and (team_dir/"manifest.json").is_file():
        filing_items=json.loads((team_dir/"manifest.json").read_text()).get("documents",[])
    first="Filings read: "+("; ".join(f"{x.get('label','filing')} (accession {x.get('accession_number','not known')})" for x in filing_items) if filing_items else "none; no issuer filing was read")
    ticker = str(ticker or "not applicable")
    lines=[first,"","# Joined desk report","",f"Ticker: {ticker.upper()}","", "## Spinoff screen", "not applicable" if spinoff is None else f"Registry record: {spinoff.get('company','not known')} ({ticker.upper()}); stage {spinoff.get('stage','not known')}. See the saved registry row for source citations.","", "## Verified team report", f"Saved report: {team_dir/'verified_report.md' if team_dir else 'not applicable'}", "", "## Worksheet view"]
    if worksheet_path and worksheet_path.is_file():
        lines.extend([worksheet_path.read_text().rstrip(),""])
    else:
        lines.append("not applicable: screen has no ranked ticker.")
    lines.extend(["", "The final assembler quotes saved files. It does not recalculate a skill output."])
    return "\n".join(lines)+"\n"

def finalize_outputs(run_dir:Path,team_dir:Path,worksheet_path:Path,ticker:str,spinoff:dict|None):
    from spinoff_worksheet_hook import validate_report
    started=time.monotonic()
    validate_report(worksheet_path,team_dir)
    worksheet_hook_elapsed=time.monotonic()-started
    (run_dir/"worksheet_hook_timing.json").write_text(json.dumps({"part":"worksheet_hook","elapsed_seconds":round(worksheet_hook_elapsed,6),"return_code":0},indent=2)+"\n")
    print(f"Part worksheet_hook: {worksheet_hook_elapsed:.3f} seconds")
    started=time.monotonic()
    report=assemble_final(run_dir,team_dir,worksheet_path,ticker,spinoff)
    final=run_dir/"final_report.md"
    final.write_text(report,encoding="utf-8")
    assembler_elapsed=time.monotonic()-started
    (run_dir/"final_assembler_timing.json").write_text(json.dumps({"part":"final_assembler","elapsed_seconds":round(assembler_elapsed,6),"return_code":0},indent=2)+"\n")
    print(f"Part final_assembler: {assembler_elapsed:.3f} seconds")
    started=time.monotonic()
    validate_report(final,team_dir)
    final_hook_elapsed=time.monotonic()-started
    (run_dir/"final_report_hook_timing.json").write_text(json.dumps({"part":"final_report_hook","elapsed_seconds":round(final_hook_elapsed,6),"return_code":0},indent=2)+"\n")
    print(f"Part final_report_hook: {final_hook_elapsed:.3f} seconds")
    proof={"status":"PASS","worksheet":str(worksheet_path),"final_report":str(final)}
    (run_dir/"hook_result.json").write_text(json.dumps(proof,indent=2)+"\n")
    return final

def run_desk(ticker:str,*,run_root:Path|None=None,registry_path:Path|None=None) -> Path:
    run_dir=create_run_dir((run_root or ROOT/"runs"/"desk").resolve())
    ticker=ticker.strip().upper()
    screen=ticker=="SCREEN"
    env=dict(os.environ)
    env["CREWAI_STORAGE_DIR"]=str(run_dir/".crewai")
    env["EQUITY_DESK_SEC_CACHE_DIR"]=str(run_dir/"sec_cache")
    current_registry=registry_path
    selected=ticker
    if screen:
        out=run_command("seeker",[sys.executable,str(SEEKER),"run","--start-date","2025-11-18","--end-date",date.today().isoformat(),"--output-root",str(run_dir/"seeker")],run_dir,env=env)
        start=time.monotonic()
        seeker_match=re.search(r"(?m)^Run folder: (.+)$",out)
        if not seeker_match: raise DeskRunError("Seeker completed without printing its run folder.")
        seeker_dir=Path(seeker_match.group(1).strip())
        current_registry=seeker_dir/"registry.json"
        manifest=json.loads((seeker_dir/"manifest.json").read_text())
        ranked=json.loads((seeker_dir/"evaluation_final.json").read_text()).get("ranked",[])
        pick=next((str(x.get("ticker","")) for x in ranked if x.get("ticker")),"")
        (run_dir/"picker.json").write_text(json.dumps({"source_registry":str(current_registry),"ranked_count":manifest.get("ranked_count",0),"selected_ticker":pick or None,"status":"picked" if pick else "not applicable"},indent=2)+"\n")
        picker_elapsed=time.monotonic()-start
        (run_dir/"deterministic_picker_timing.json").write_text(json.dumps({"part":"deterministic_picker","elapsed_seconds":round(picker_elapsed,6),"return_code":0},indent=2)+"\n")
        print(f"Part deterministic_picker: {picker_elapsed:.3f} seconds")
        if not pick:
            for part in ("agent_team","worksheet","worksheet_hook","final_report_hook"):
                (run_dir/f"{part}_timing.json").write_text(json.dumps({"part":part,"elapsed_seconds":0,"status":"not applicable: no ranked ticker"},indent=2)+"\n")
                print(f"Part {part}: 0.000 seconds (not applicable: no ranked ticker)")
            assembler_start=time.monotonic()
            report=assemble_final(run_dir,None,None,"not applicable",None)
            final=run_dir/"final_report.md"; final.write_text(report)
            assembler_elapsed=time.monotonic()-assembler_start
            (run_dir/"final_assembler_timing.json").write_text(json.dumps({"part":"final_assembler","elapsed_seconds":round(assembler_elapsed,6),"return_code":0},indent=2)+"\n")
            print(f"Part final_assembler: {assembler_elapsed:.3f} seconds")
            timings={"seeker":"recorded in seeker_timing.json","deterministic_picker":"recorded in deterministic_picker_timing.json","agent_team":"not applicable","worksheet":"not applicable","worksheet_hook":"not applicable","final_report_hook":"not applicable","final_assembler":"recorded in final_assembler_timing.json"}
            (run_dir/"hook_result.json").write_text(json.dumps({"status":"not applicable: no ranked ticker"},indent=2)+"\n")
            (run_dir/"timings.json").write_text(json.dumps(timings,indent=2)+"\n")
            (run_dir/"run_manifest.json").write_text(json.dumps({"ticker":None,"screen":True,"seeker_run":str(seeker_dir),"team_run":None,"worksheet":None,"registry_path":str(current_registry),"final_report":str(final)},indent=2)+"\n")
            print(f"Run folder: {run_dir}\nFinal report: {final}")
            return final
        selected=pick
    record=registry_row(selected,current_registry)
    team_out=run_command("agent_team",[sys.executable,"-u","-m","equity_research_team.main",selected,"--run-root",str(run_dir/"agent")],run_dir,cwd=TEAM_PROJECT,env=env)
    team_dir=find_team_run(team_out)
    worksheet_out=run_command("worksheet",[sys.executable,str(WORKSHEET),str(team_dir),selected],run_dir,env=env)
    match=re.search(r"(?m)^Worksheet: (.+)$",worksheet_out)
    if not match: raise DeskRunError("Worksheet completed without printing its saved path.")
    worksheet_path=Path(match.group(1).strip())
    started=time.monotonic()
    final=finalize_outputs(run_dir,team_dir,worksheet_path,selected,record)
    print(f"Part hook_and_assembler: {time.monotonic()-started:.3f} seconds")
    (run_dir/"run_manifest.json").write_text(json.dumps({"ticker":selected,"screen":screen,"seeker_run":str(seeker_dir) if screen else None,"team_run":str(team_dir),"worksheet":str(worksheet_path),"registry_path":str(current_registry) if current_registry else None,"final_report":str(final)},indent=2)+"\n")
    print(f"Run folder: {run_dir}\nFinal report: {final}")
    return final

def replay(run_dir:Path) -> bool:
    """Reassemble from saved text only; no network client is called."""
    run_dir=run_dir.resolve(); manifest=json.loads((run_dir/"run_manifest.json").read_text())
    team_dir=Path(manifest["team_run"]) if manifest.get("team_run") else None
    worksheet=Path(manifest["worksheet"]) if manifest.get("worksheet") else None
    registry=registry_row(manifest["ticker"],Path(manifest["registry_path"]) if manifest.get("registry_path") else None)
    expected=(run_dir/"final_report.md").read_bytes()
    actual=assemble_final(run_dir,team_dir,worksheet,manifest.get("ticker"),registry).encode()
    target=run_dir/"replay"/"final_report.md"; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(actual)
    passed=hashlib.sha256(expected).digest()==hashlib.sha256(actual).digest()
    report={"status":"PASS" if passed else "FAIL","network_calls":0,"networking":"disabled by file-only implementation","model_calls":0,"modeling":"disabled by file-only implementation","byte_identical":passed,"sha256_saved":hashlib.sha256(expected).hexdigest(),"sha256_replay":hashlib.sha256(actual).hexdigest()}
    (target.parent/"replay_proof.json").write_text(json.dumps(report,indent=2)+"\n")
    print(f"Replay: {report['status']}; network calls: 0")
    return passed

def main(argv=None):
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True)
    run=sub.add_parser("run"); run.add_argument("ticker",help="A ticker or SCREEN")
    run.add_argument("--run-root",type=Path,default=ROOT/"runs"/"desk"); run.add_argument("--registry",type=Path,default=ROOT/"lab06_runs/SEEKER_2026-11-20_22-29-06-302032/registry.json")
    rp=sub.add_parser("replay"); rp.add_argument("run_dir",type=Path)
    a=p.parse_args(argv)
    if a.command=="replay": return 0 if replay(a.run_dir) else 1
    try: run_desk(a.ticker,run_root=a.run_root,registry_path=a.registry)
    except Exception as exc:
        print(f"ERROR: {exc}",file=sys.stderr); return 1
    return 0
if __name__=="__main__": raise SystemExit(main())
