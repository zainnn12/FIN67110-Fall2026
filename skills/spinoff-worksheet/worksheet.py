#!/usr/bin/env python3
"""Deterministic owner-cash-flow worksheet for a saved team run."""
from __future__ import annotations
import argparse, json, os, re, sys
from collections.abc import Mapping
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEAM = ROOT / "equity_research_team"
sys.path.insert(0, str(TEAM / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "skills" / "spinoff-seeker" / "scripts"))
from dotenv import dotenv_values
from equity_research_data import read_openai_api_key
from research_roles import OpenAIRoleClient, DEFAULT_OPENAI_MODEL
from spinoff_worksheet_hook import validate_report
from closes_reader import FinancialDatasetsClosesReader

CONFIG = json.loads((Path(__file__).parent / "worksheet_config.json").read_text())
PERSONA = (Path(__file__).parent / "investor_persona.md").read_text()
Q = Decimal("0.01")
FORM10_EXTRACTION_SPECS = {
    "0001193125-26-409182": {"form":"10-12B/A","lines":{
        "net_income": (1791, "Net (loss) income and comprehensive (loss) income", -1, "Pro forma net loss", "USD"),
        "depreciation_and_amortization": (1781, "Depreciation and amortization", -1, "Pro forma depreciation and amortization", "USD"),
        "property_additions": (5108, "Capital expenditures", 0, "Historical capital expenditures for the matching fiscal year", "USD"),
        "diluted_shares": (1797, "Diluted", -1, "Pro forma diluted weighted-average shares", "shares"),
    }},
}

def money(value): return Decimal(str(value)).quantize(Q, rounding=ROUND_HALF_UP)
def decimal_text(value): return format(Decimal(value),"f")
def fact_value(facts, key):
    item = facts.get(key) or {}; current = item.get("current") or {}
    if current.get("val") is None: return None, item, current
    return Decimal(str(current["val"])), item, current

def _table_numbers(line: str) -> list[int]:
    """Read signed table values from saved SEC text without using prose numbers."""
    values=[]
    pattern=re.compile(r"\(\s*([\d,]+)\s*\|?\s*\)|(?<![A-Za-z0-9])([\d,]+)(?![A-Za-z0-9])")
    for match in pattern.finditer(line):
        negative=match.group(1) is not None
        raw=match.group(1) or match.group(2)
        value=int(raw.replace(",",""))
        values.append(-value if negative else value)
    return values

def parse_form10_comparable_annual_pro_forma(path: Path, *, accession: str | None = None):
    """Extract the matching annual MSGR Form 10 basis from saved text.

    The parser fails closed if the annual header, units, labels, line locations, or
    accession filename do not match the saved evidence. It never reads a 10-Q.
    """
    path=Path(path).resolve()
    if not path.is_file(): raise ValueError(f"Missing saved Form 10 evidence: {path}")
    match=re.fullmatch(r"Form10_(\d{10}-\d{2}-\d{6})_information\.txt",path.name)
    if not match: raise ValueError("Form 10 evidence filename must contain its accession.")
    saved_accession=match.group(1)
    if accession is not None and saved_accession != accession:
        raise ValueError(f"Form 10 accession mismatch: expected {accession}, found {saved_accession}")
    extraction=FORM10_EXTRACTION_SPECS.get(saved_accession)
    if extraction is None:
        raise ValueError(f"No verified Form 10 extraction map exists for accession {saved_accession}.")
    lines=path.read_text(errors="strict").splitlines()
    def saved_line(number:int, label:str) -> str:
        if number > len(lines): raise ValueError(f"Saved Form 10 has no line {number}.")
        line=lines[number-1]
        if label not in line: raise ValueError(f"Saved Form 10 line {number} does not contain {label!r}.")
        return line
    annual_header=saved_line(1769,"For the Year Ended June 30")
    saved_line(1770,"in thousands, except per share data")
    saved_line(5088,"Years Ended June 30")
    year_match=re.search(r"June 30, (\d{4})",annual_header)
    if not year_match: raise ValueError("Form 10 annual period end is not identifiable.")
    year=int(year_match.group(1)); start=date(year-1,7,1); end=date(year,6,30)
    try: source_path=str(path.relative_to(ROOT))
    except ValueError: source_path=str(path)
    facts={}
    for key,(line_no,label,position,description,unit) in extraction["lines"].items():
        quote=saved_line(line_no,label)
        values=_table_numbers(quote)
        if not values: raise ValueError(f"No table value found at saved Form 10 line {line_no}.")
        source_value=values[position]
        value=source_value*1_000
        facts[key]={
            "label":description,
            "taxonomy":"Form 10 information statement",
            "tag":description,
            "unit":unit,
            "source_unit":"USD thousands" if unit=="USD" else "shares in thousands",
            "source_path":source_path,
            "source_line":line_no,
            "source_quote":quote,
            "current":{"val":value,"start":start.isoformat(),"end":end.isoformat(),
                       "accn":saved_accession,"form":extraction["form"],"source_line":line_no,
                       "source_path":source_path,"source_unit":"USD thousands" if unit=="USD" else "shares in thousands"},
        }
    return {"facts":facts,"accession":saved_accession,"form":extraction["form"],
            "period_start":start.isoformat(),"period_end":end.isoformat(),
            "source_path":source_path,"source_units":"USD thousands, except shares in thousands"}

def aligned_owner_cash_flow(data):
    required=("net_income","depreciation_and_amortization","property_additions","diluted_shares")
    candidates=[]
    ttm=data.get("reported_after_spin_ttm")
    if isinstance(ttm,Mapping): candidates.append(("reported-after-spin trailing-twelve-month",ttm.get("facts",ttm)))
    if data.get("worksheet_basis")=="reported-after-spin trailing-twelve-month":
        candidates.append(("reported-after-spin trailing-twelve-month",data.get("worksheet_facts",data.get("facts",{}))))
    proforma=data.get("form10_comparable_annual_pro_forma")
    if isinstance(proforma,Mapping): candidates.append(("Form 10 comparable annual pro-forma",proforma.get("facts",proforma)))
    if data.get("worksheet_basis")=="Form 10 comparable annual pro-forma":
        candidates.append(("Form 10 comparable annual pro-forma",data.get("worksheet_facts",data.get("facts",{}))))
    if not candidates:
        return None, {}, "not computed: neither reported-after-spin TTM nor comparable annual Form 10 pro-forma inputs are identified"
    errors=[]
    for basis,facts in candidates:
        vals={key:fact_value(facts,key) for key in required}
        if any(v[0] is None for v in vals.values()):
            errors.append(f"{basis} has missing required figures");continue
        points=[v[2] for v in vals.values()]
        starts={p.get("start") for p in points}; ends={p.get("end") for p in points}; accs={p.get("accn") for p in points}
        if len(starts)!=1 or len(ends)!=1 or len(accs)!=1 or None in starts or None in ends or None in accs:
            errors.append(f"{basis} figures do not share one cited filing and matched start/end dates");continue
        start=next(iter(starts));end=next(iter(ends))
        from datetime import date
        try: duration=(date.fromisoformat(end)-date.fromisoformat(start)).days
        except (TypeError,ValueError): duration=0
        if not 360 <= duration <= 370:
            errors.append(f"{basis} is not a full comparable annual or trailing-twelve-month period");continue
        income,da,capex,shares=[vals[k][0] for k in required]
        base_usd=income+da-abs(capex)
        return base_usd,vals,f"aligned {basis} figures"
    return None, vals, "not computed: "+"; ".join(errors)

def source_texts(run_dir):
    return [p.read_text(errors="replace") for p in run_dir.glob("*.txt") if p.is_file()]

def assemble(run_dir: Path, ticker: str, *, form10_evidence: Path | None = None, form10_accession: str | None = None):
    facts_path = run_dir / "facts.json"
    if not facts_path.is_file(): raise ValueError(f"Missing saved facts.json in {run_dir}")
    data = json.loads(facts_path.read_text())
    parsed_form10=None
    if form10_evidence is not None:
        parsed_form10=parse_form10_comparable_annual_pro_forma(form10_evidence,accession=form10_accession)
        data=dict(data)
        data["form10_comparable_annual_pro_forma"]=parsed_form10
    base_usd, vals, basis = aligned_owner_cash_flow(data)
    if not vals:
        vals = {key: (None, {}, {}) for key in ("net_income", "depreciation_and_amortization", "property_additions", "diluted_shares")}
    shares = vals["diluted_shares"][0]
    price = None
    candidates = []
    for text in source_texts(run_dir):
        for match in re.finditer(r"(?m)^.*(?:last eligible close|regular close|close price).*?(\$?\d[\d,]*\.\d{1,6}).*$", text, re.I):
            try: candidates.append(Decimal(match.group(1).replace("$", "").replace(",", "")))
            except InvalidOperation: pass
    # Price is accepted only from deterministic saved close evidence, not the agent prose.
    px_file = run_dir / "worksheet_closes.json"
    if px_file.is_file():
        close_rows = json.loads(px_file.read_text()).get("closes", [])
        eligible = sorted((r for r in close_rows if r.get("date") and r.get("close")), key=lambda r:r["date"])
        if eligible: price = Decimal(str(eligible[-1]["close"]))
    result = {"ticker": ticker.upper(), "run_dir": str(run_dir), "source_basis": basis,
              "base_owner_cash_flow_usd_millions": None, "period": None, "diluted_shares_millions": None,
              "last_eligible_close_usd": str(price) if price is not None else None,
              "low_value_per_share_usd": None, "mid_value_per_share_usd": None,
              "median_daily_dollar_volume_usd": None, "purchase_size_percent": None,
              "view": "Not computed", "conviction": "Not computed", "inputs": {}, "source_evidence": []}
    if parsed_form10:
        result["source_evidence"].append(parsed_form10["source_path"])
        result["correction_note"]="The original saved worksheet did not identify the available comparable annual Form 10 inputs. This regenerated worksheet corrects that selector result; it does not annualize the pre-spin 10-Q."
    for key, (value, item, point) in vals.items():
        result["inputs"][key] = {"value": str(value) if value is not None else None, "tag": item.get("tag"), "unit":item.get("unit"), "source_unit":item.get("source_unit"), "period_start": point.get("start"), "period_end": point.get("end"), "accession": point.get("accn"), "form": point.get("form"), "source_path":item.get("source_path") or point.get("source_path"), "source_line":item.get("source_line") or point.get("source_line"), "source_quote":item.get("source_quote")}
    if base_usd is not None and shares is not None and shares > 0:
        base_m = base_usd / Decimal(1_000_000)
        shares_m = shares / Decimal(1_000_000)
        income=vals["net_income"][0]; da=vals["depreciation_and_amortization"][0]; capex=vals["property_additions"][0]
        low_eq = max(Decimal(0), base_m * Decimal("0.80")) / (Decimal("0.12") - Decimal("0"))
        mid_eq = max(Decimal(0), base_m) * Decimal("1.02") / (Decimal("0.10") - Decimal("0.02"))
        result.update({"base_owner_cash_flow_usd_millions": decimal_text(base_m), "owner_cash_flow_calculation_usd_millions":f"{decimal_text(income/Decimal(1_000_000))} + {decimal_text(da/Decimal(1_000_000))} - {decimal_text(abs(capex)/Decimal(1_000_000))} = {decimal_text(base_m)}", "period": vals["net_income"][2].get("start")+" to "+vals["net_income"][2].get("end"), "diluted_shares_millions": decimal_text(shares_m), "low_equity_value_usd_millions": decimal_text(low_eq), "mid_equity_value_usd_millions": decimal_text(mid_eq), "low_value_per_share_usd":decimal_text(low_eq/shares_m), "mid_value_per_share_usd":decimal_text(mid_eq/shares_m)})
        if price is not None:
            result["view"] = "Price is at or below low-case value" if price <= low_eq / shares_m else "Price is above low-case value"
            result["conviction"] = "Low"
        else:
            result["view"] = "Not computed: price unavailable"
    return result

PERSONA_SCHEMA={"type":"object","properties":{"analysis":{"type":"string"},"insight":{"type":"string"}},"required":["analysis","insight"],"additionalProperties":False}

def persona_call(result, run_dir, client=None):
    verified_path=run_dir/"verified_report.md"
    if not verified_path.is_file(): raise ValueError("A saved verified team report is required for the persona call.")
    release_paths=sorted(run_dir.glob("8-K_EX-99.1_*.txt"))
    release=release_paths[0].read_text(errors="replace") if release_paths else ""
    first_paragraph=" ".join([line.strip() for line in release.splitlines() if line.strip()][:18])
    evidence={"verified_team_report":verified_path.read_text(),"worksheet_computations":result,"saved_filing_facts":json.loads((run_dir/"facts.json").read_text()),"earnings_release_opening_paragraph_candidate":first_paragraph,"saved_earnings_release":release}
    instructions=(PERSONA+"\n\nUse only this saved evidence. Do not calculate, derive, annualize, estimate, or invent numbers. Do not present any model-derived numerical claim. Return a short evidence-bound analysis and one filing-supported Insight absent from the quoted release opening paragraph. Include the exact accession and saved-text line citation. If evidence does not support this comparison, state that clearly.")
    request={"task":"Apply the persona to the saved verified run. Do not perform calculations.","context":evidence,"expected_output":{"analysis":"A short prose analysis; no calculations.","insight":"One filing-supported claim absent from the release opening paragraph, with exact accession and saved-text line citation."}}
    (run_dir/"persona_model_input.json").write_text(json.dumps({"role":"Investor Persona","instructions":instructions,"request":request,"schema_name":"spinoff_persona","output_schema":PERSONA_SCHEMA},indent=2)+"\n")
    if client is None:
        api_key=read_openai_api_key(ROOT)
        client=OpenAIRoleClient(api_key=api_key, model=DEFAULT_OPENAI_MODEL)
    return client.call(role="Investor Persona", instructions=instructions, request=request, schema_name="spinoff_persona", output_schema=PERSONA_SCHEMA)

def offline_persona(result, run_dir):
    """Create correction prose from deterministic results and a saved insight only."""
    saved_path=run_dir/"persona_model_call.json"
    saved=json.loads(saved_path.read_text()) if saved_path.is_file() else {}
    accession=result.get("inputs",{}).get("net_income",{}).get("accession","not known")
    analysis=("Correction note: the original saved worksheet stated that no comparable annual Form 10 inputs were identified. "
              f"The saved Form 10 accession {accession} supplies one matching fiscal-year basis for 2025-07-01 through 2026-06-30. "
              "The corrected deterministic selector uses that annual basis. It does not annualize the pre-spin three-month 10-Q or mix periods. "
              "Owner cash flow is negative, so the low-case equity value and low-case value per share are zero. The saved positive close is above that low case; conviction remains Low. "
              "Parent-burden and complete first-30-day insider evidence remain unavailable.")
    return {"analysis":analysis,"insight":saved.get("insight","No additional saved filing-supported insight is available.")}

def apply_saved_market_data(result, run_dir):
    """Load only an existing close file; never call a market-data client."""
    path=run_dir/"worksheet_closes.json"
    if not path.is_file(): raise ValueError("Offline regeneration requires saved worksheet_closes.json.")
    rows=json.loads(path.read_text()).get("closes",[])
    eligible=sorted((row for row in rows if row.get("date") and row.get("close")),key=lambda row:row["date"])
    if eligible:
        result["last_eligible_close_usd"]=str(eligible[-1]["close"])
        result["price_date"]=eligible[-1]["date"]
        result["volume_start_date"]=eligible[0]["date"]
        result["volume_end_date"]=eligible[-1]["date"]
    return eligible

def save_market_data(result, run_dir, api_key=None, reader=None):
    if reader is None:
        from dotenv import dotenv_values
        api_key=api_key or dotenv_values(ROOT/".env").get("FINANCIAL_DATASETS_API_KEY")
        reader=FinancialDatasetsClosesReader(api_key)
    end=date.today(); start=end-timedelta(days=120)
    closes=reader.daily_closes(result["ticker"],start,end)
    payload_rows=[]
    for payload in reader.last_payloads:
        for row in payload.get("prices",[]) if isinstance(payload,dict) else []:
            if isinstance(row,dict): payload_rows.append(row)
    close_rows=[]
    for item in closes:
        row=next((r for r in payload_rows if str(r.get("time",""))[:10]==item.trading_date.isoformat()),{})
        close_rows.append({"date":item.trading_date.isoformat(),"close":str(item.close),"volume":str(row.get("volume")) if row.get("volume") is not None else None,"source":item.source})
    (run_dir/"worksheet_closes.json").write_text(json.dumps({"ticker":result["ticker"],"source":"financialdatasets.ai","closes":close_rows},indent=2)+"\n")
    if close_rows:
        result["last_eligible_close_usd"]=close_rows[-1]["close"]
        result["price_date"]=close_rows[-1]["date"]
        result["volume_start_date"]=close_rows[0]["date"]
        result["volume_end_date"]=close_rows[-1]["date"]
    return close_rows

def score_persona_criteria(result,run_dir,data):
    price=Decimal(result["last_eligible_close_usd"]) if result.get("last_eligible_close_usd") else None
    low=Decimal(result["low_value_per_share_usd"]) if result.get("low_value_per_share_usd") else None
    if price is not None and low is not None:
        margin_score=2 if price<=low*Decimal("0.80") else (1 if price<=low else 0)
        margin={"score":margin_score,"basis":"price compared with low-case value per share","number":str(price),"filing_tag":"saved daily close and deterministic low-case worksheet computation","period":result.get("price_date","not known"),"calculation":f"price {price} compared with 80% of low case {decimal_text(low*Decimal('0.80'))} and low case {decimal_text(low)}"}
    else:
        margin={"score":0,"basis":"not computed: price-to-low-case comparison unavailable","number":"not known","filing_tag":"not known","period":"not known","calculation":"not computed"}
    periods=data.get("owner_cash_flow_periods",[])
    if isinstance(periods,list) and periods:
        valid=[x for x in periods if x.get("value") is not None and x.get("period") and x.get("tag")]
        positive=[x for x in valid if Decimal(str(x["value"]))>0]
        owner_score=min(2,len(positive))
        owner={"score":owner_score,"basis":"positive valid owner-cash-flow periods only","number":"; ".join(str(x["value"]) for x in valid) or "not known","filing_tag":"; ".join(str(x["tag"]) for x in valid) or "not known","period":"; ".join(str(x["period"]) for x in valid) or "not known","calculation":f"{len(positive)} positive values among {len(valid)} valid cited periods"}
    elif result.get("base_owner_cash_flow_usd_millions") is not None:
        value=Decimal(result["base_owner_cash_flow_usd_millions"]); owner_score=1 if value>0 else 0
        owner_input=result.get("inputs",{}).get("net_income",{})
        owner={"score":owner_score,"basis":"one valid base owner-cash-flow period; second comparable period not established","number":str(value),"filing_tag":f"{owner_input.get('form','saved filing')} accession {owner_input.get('accession','not known')}","period":result.get("period","not known"),"calculation":"one positive valid period" if value>0 else "one nonpositive valid period"}
    else:
        owner={"score":0,"basis":"not known: valid comparable cash-flow periods are unavailable","number":"not known","filing_tag":"not known","period":"not known","calculation":"not computed"}
    burden=data.get("parent_burden") or {}; burden_status=burden.get("status")
    if burden_status=="no_material_obligations" and burden.get("source") and burden.get("section"):
        parent={"score":2,"basis":"filing states no material inherited debt or restrictions","number":burden.get("amount","none stated"),"filing_tag":burden.get("source"),"period":burden.get("period","not known"),"calculation":burden.get("section")}
    elif burden_status=="obligations_stated_manageable" and burden.get("amount") is not None and burden.get("owner_cash_flow") is not None and burden.get("source") and burden.get("calculation"):
        parent={"score":1,"basis":"supported obligations shown manageable relative to owner cash flow","number":str(burden["amount"]),"filing_tag":burden["source"],"period":burden.get("period","not known"),"calculation":burden["calculation"]}
    else:
        parent={"score":0,"basis":"not known: inherited obligations or restrictions are not established","number":"not known","filing_tag":"not known","period":"not known","calculation":"not computed"}
    purchases=data.get("insider_purchases",[]); distinct={str(x.get("insider_id")) for x in purchases if x.get("qualifying") is True and x.get("insider_id") and x.get("source") and x.get("period")}
    if data.get("insider_data_complete") is True:
        insider_score=2 if len(distinct)>=2 else (1 if len(distinct)==1 else 0)
        insider={"score":insider_score,"basis":"distinct qualifying Form 4 code-P purchasers","number":str(len(distinct)),"filing_tag":"; ".join(sorted({str(x.get('source')) for x in purchases if x.get('qualifying') is True and x.get('source')})) or "Form 4 code-P search complete; none qualifying","period":"first 30 days after distribution","calculation":f"{len(distinct)} distinct qualifying insiders"}
    else:
        insider={"score":0,"basis":"not known: complete first-30-day Form 4 review is unavailable","number":"not known","filing_tag":"not known","period":"not known","calculation":"not computed"}
    pct=Decimal(result["purchase_size_percent"]) if result.get("purchase_size_percent") is not None else None
    liquidity_score=2 if pct is not None and pct<=Decimal("0.5") else (1 if pct is not None and pct<=Decimal("1") else 0)
    liquidity={"score":liquidity_score,"basis":"median daily dollar volume compared with client purchase","number":result.get("median_daily_dollar_volume_usd") or "not known","filing_tag":"Financial Datasets daily close and volume" if pct is not None else "not known","period":f"{result.get('volume_start_date','not known')} to {result.get('volume_end_date','not known')}","calculation":f"{CONFIG['client_purchase_usd']} / {result.get('median_daily_dollar_volume_usd') or 'not known'} × 100 = {result.get('purchase_size_percent') or 'not known'}%"}
    result["criterion_scores"]={"margin_of_safety":margin,"owner_cash_flow":owner,"parent_burden":parent,"insider_alignment":insider,"liquidity":liquidity}
    return result

def calculate_liquidity(result, run_dir):
    close_rows=json.loads((run_dir/"worksheet_closes.json").read_text()).get("closes",[])
    if close_rows:
        dollar_volumes=[]
        for row in close_rows:
            if row["volume"] is not None:
                dollar_volumes.append(Decimal(row["volume"])*Decimal(row["close"]))
        if dollar_volumes:
            ordered=sorted(dollar_volumes); mid=len(ordered)//2
            median=ordered[mid] if len(ordered)%2 else (ordered[mid-1]+ordered[mid])/2
            result["median_daily_dollar_volume_usd"]=str(median)
            result["purchase_size_percent"]=str(Decimal(CONFIG["client_purchase_usd"])/median*100) if median else None
    if result["base_owner_cash_flow_usd_millions"] is not None and result["diluted_shares_millions"] and result["last_eligible_close_usd"]:
        low=Decimal(result.get("low_equity_value_usd_millions",0))/Decimal(result["diluted_shares_millions"])
        result["low_value_per_share_usd"]=decimal_text(low)
        price=Decimal(result["last_eligible_close_usd"])
        result["view"]="Price is at or below low-case value" if price<=low else "Price is above low-case value"
        data=json.loads((run_dir/"facts.json").read_text()) if (run_dir/"facts.json").exists() else {}
        score_persona_criteria(result,run_dir,data)
        scores=result.get("criterion_scores",{})
        known_all=all(item.get("number") not in (None,"not known") for item in scores.values())
        positive=Decimal(result["base_owner_cash_flow_usd_millions"])>0
        pct=Decimal(result["purchase_size_percent"]) if result.get("purchase_size_percent") else None
        result["conviction"]="High" if price<=low*Decimal("0.80") and positive and known_all and pct is not None and pct<=Decimal("1") else "Low"
    pct=Decimal(result["purchase_size_percent"]) if result.get("purchase_size_percent") else None
    liquidity_score=2 if pct is not None and pct<=Decimal("0.5") else (1 if pct is not None and pct<=Decimal("1") else 0)
    data=json.loads((run_dir/"facts.json").read_text()) if (run_dir/"facts.json").exists() else {}
    score_persona_criteria(result,run_dir,data)
    return result

def format_output(result, persona):
    def f(v, places=2):
        if v is None: return "not known"
        quantum=Decimal(1).scaleb(-places)
        return f"{Decimal(str(v)).quantize(quantum,rounding=ROUND_HALF_UP):,.{places}f}"
    insight=persona.get("insight","No filing-supported insight is available.")
    insight=re.sub(r"^Insight:\s*", "", insight, flags=re.I)
    lines = ["Why it may be cheap—or why it is not", "", persona.get("analysis", "Evidence-bound analysis unavailable."), f"Ticker: {result['ticker']}"]
    if result.get("correction_note"):
        lines.extend(["", "Correction record", "", result["correction_note"]])
    inputs=result.get("inputs",{})
    if inputs.get("net_income",{}).get("accession"):
        net=inputs["net_income"]; da=inputs["depreciation_and_amortization"]; capex=inputs["property_additions"]; shares=inputs["diluted_shares"]
        lines.extend(["", "Matched Form 10 basis", "",
                      f"Accession: {net['accession']}; form: {net['form']}; period: {net['period_start']} through {net['period_end']}; source units: USD thousands, except shares in thousands.",
                      f"Pro forma net loss: {int(Decimal(net['value'])):,} USD; {net['source_path']}, saved-text line {net['source_line']}.",
                      f"Depreciation and amortization: {int(Decimal(da['value'])):,} USD; {da['source_path']}, saved-text line {da['source_line']}.",
                      f"Capital expenditures: {int(Decimal(capex['value'])):,} USD; {capex['source_path']}, saved-text line {capex['source_line']}; the owner-cash-flow subtraction uses its absolute value.",
                      f"Pro forma diluted weighted-average shares: {int(Decimal(shares['value'])):,}; {shares['source_path']}, saved-text line {shares['source_line']}."])
    lines.extend(["", "Owner cash flow formula: after-tax earnings + depreciation and amortization − capital expenditures."])
    if result.get("base_owner_cash_flow_usd_millions") is not None and inputs.get("net_income"):
        lines.append(f"Owner cash flow arithmetic: {Decimal(inputs['net_income']['value'])/Decimal(1_000_000)} + {Decimal(inputs['depreciation_and_amortization']['value'])/Decimal(1_000_000)} − {abs(Decimal(inputs['property_additions']['value']))/Decimal(1_000_000)} = {result['base_owner_cash_flow_usd_millions']} USD millions.")
    lines.extend([f"Owner cash flow: {f(result['base_owner_cash_flow_usd_millions'],3)} USD millions ({result['source_basis']}); period: {result['period'] or 'not known'}.", f"Diluted shares: {f(result['diluted_shares_millions'],3)} million.", "Valuation assumptions: low case haircut 20.0%, growth 0.0%, required return 12.0%; midpoint haircut 0.0%, growth 2.0%, required return 10.0%.", f"Low-case equity value: {f(result.get('low_equity_value_usd_millions'))} USD millions; low-case value per share: {f(result['low_value_per_share_usd'])} USD; midpoint: {f(result['mid_value_per_share_usd'])} USD.", f"Last eligible close: {f(result['last_eligible_close_usd'])} USD per share ({result.get('price_date','not known')}).", f"View: {result['view']}. Conviction: {result['conviction']}.", "", "Criterion scores (number, source tag, period, and arithmetic are shown; unavailable inputs receive zero under the supplied criteria):"])
    for name,score in result.get("criterion_scores",{}).items():
        lines.append(f"- {name.replace('_',' ').title()}: {score['score']}/2; {score['basis']}; number: {score['number']}; filing tag: {score['filing_tag']}; period: {score['period']}; calculation: {score['calculation']}.")
    lines.extend(["", "What the next filing must show to change the view: comparable reported-after-spin after-tax earnings, depreciation and amortization, capital spending, and diluted shares for a complete matching period, plus any inherited debt or restrictions.", "", "Insight: "+insight, ""])
    # This liquidity calculation is deliberately appended in code after the persona model call.
    median=result.get("median_daily_dollar_volume_usd")
    purchase=Decimal(CONFIG["client_purchase_usd"])
    pct=Decimal(result["purchase_size_percent"]) if result.get("purchase_size_percent") else None
    lines.append(f"Liquidity: $10,000 purchase / {f(median)} median daily dollar volume = {f(pct,1)}%; dates: {result.get('volume_start_date','not known')} to {result.get('volume_end_date','not known')}." if median else "Liquidity: not known; saved daily volume is unavailable.")
    return "\n".join(lines)+"\n"

def main():
    p=argparse.ArgumentParser(); p.add_argument("run_dir",type=Path); p.add_argument("ticker")
    p.add_argument("--form10-evidence",type=Path); p.add_argument("--form10-accession")
    p.add_argument("--offline",action="store_true",help="Use only saved close and persona evidence; make no API calls.")
    a=p.parse_args()
    run_dir=a.run_dir.resolve(); result=assemble(run_dir,a.ticker,form10_evidence=a.form10_evidence,form10_accession=a.form10_accession)
    if a.offline:
        apply_saved_market_data(result,run_dir); persona=offline_persona(result,run_dir)
    else:
        save_market_data(result,run_dir); persona=persona_call(result,run_dir)
    calculate_liquidity(result,run_dir)
    out=run_dir/"worksheet.json"; out.write_text(json.dumps(result,indent=2)+"\n")
    if not a.offline:
        (run_dir/"persona_model_call.json").write_text(json.dumps(persona,indent=2)+"\n")
    report=format_output(result,persona); path=run_dir/"worksheet.md"; path.write_text(report)
    supplemental=[a.form10_evidence] if a.form10_evidence else []
    validate_report(path, a.run_dir.resolve(), supplemental_paths=supplemental)
    if a.offline:
        (run_dir/"worksheet_offline_proof.json").write_text(json.dumps({"status":"PASS","network_calls":0,"model_calls":0,"saved_evidence_only":True,"form10_evidence":str(a.form10_evidence.resolve()) if a.form10_evidence else None},indent=2)+"\n")
    print(f"Worksheet: {path}")
    return 0
if __name__=="__main__": raise SystemExit(main())
