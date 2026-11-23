import json
import sys
from pathlib import Path
from decimal import Decimal

import pytest

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/"skills"/"spinoff-worksheet"
sys.path.insert(0,str(SCRIPT))
from spinoff_worksheet_hook import validate_report
from worksheet import (aligned_owner_cash_flow, assemble, persona_call, save_market_data,
                       calculate_liquidity, parse_form10_comparable_annual_pro_forma)

def test_hook_passes_clean_and_refuses_seeded_amount_by_line(tmp_path):
    (tmp_path/"facts.json").write_text(json.dumps({"facts":{"net_income":{"current":{"val":10},"prior":{"val":-5}}}}))
    (tmp_path/"worksheet.json").write_text(json.dumps({"computed":10,"prior":-5}))
    clean=tmp_path/"clean.md"; clean.write_text("Owner cash flow is 10 USD millions; prior net income was (5).\n")
    assert validate_report(clean,tmp_path)
    seeded=tmp_path/"seeded.md"; seeded.write_text("Owner cash flow is 11 USD millions.\n")
    with pytest.raises(ValueError,match="line 1"):
        validate_report(seeded,tmp_path)

def test_hook_keeps_parenthetical_negative_sign(tmp_path):
    (tmp_path/"facts.json").write_text(json.dumps({"cash_flow":-5}))
    good=tmp_path/"good.md";good.write_text("Cash flow: (5)\n")
    bad=tmp_path/"bad.md";bad.write_text("Cash flow: 5\n")
    assert validate_report(good,tmp_path)
    with pytest.raises(ValueError,match="line 1"):
        validate_report(bad,tmp_path)

def test_owner_cash_flow_requires_matching_periods_and_accession():
    facts={"net_income":{"current":{"val":20,"start":"2025-01-01","end":"2025-12-31","accn":"A"}},
           "depreciation_and_amortization":{"current":{"val":5,"start":"2025-01-01","end":"2025-12-31","accn":"A"}},
           "property_additions":{"current":{"val":-8,"start":"2025-01-01","end":"2025-12-31","accn":"A"}},
           "diluted_shares":{"current":{"val":10,"start":"2025-01-01","end":"2025-12-31","accn":"A"}}}
    value,_,basis=aligned_owner_cash_flow({"worksheet_basis":"Form 10 comparable annual pro-forma","worksheet_facts":facts})
    assert value==Decimal("17")
    assert basis=="aligned Form 10 comparable annual pro-forma figures"
    facts["diluted_shares"]["current"]["end"]="2025-09-30"
    value,_,_=aligned_owner_cash_flow({"worksheet_basis":"Form 10 comparable annual pro-forma","worksheet_facts":facts})
    assert value is None

def test_ttm_is_preferred_and_single_quarter_is_rejected():
    def facts(amount):
        return {key:{"current":{"val":value,"start":"2025-01-01","end":"2025-12-31","accn":"TTM"}} for key,value in {
            "net_income":amount,"depreciation_and_amortization":5,"property_additions":-8,"diluted_shares":10}.items()}
    data={"reported_after_spin_ttm":{"facts":facts(20)},"form10_comparable_annual_pro_forma":{"facts":facts(100)}}
    value,_,basis=aligned_owner_cash_flow(data)
    assert value==Decimal("17")
    assert basis.startswith("aligned reported-after-spin trailing-twelve-month")
    one_quarter=facts(20)
    for item in one_quarter.values(): item["current"]["start"]="2025-10-01"
    value,_,basis=aligned_owner_cash_flow({"reported_after_spin_ttm":{"facts":one_quarter}})
    assert value is None and basis.startswith("not computed")

def test_no_unidentified_annual_basis_is_not_computed():
    value,_,basis=aligned_owner_cash_flow({"facts":{}})
    assert value is None
    assert basis.startswith("not computed")

def test_msgr_saved_form10_selects_matching_annual_inputs_and_zero_low_case():
    evidence=ROOT/"runs"/"lab07"/"MSGR_evidence"/"Form10_0001193125-26-409182_information.txt"
    parsed=parse_form10_comparable_annual_pro_forma(evidence,accession="0001193125-26-409182")
    facts=parsed["facts"]
    assert facts["net_income"]["current"]["val"] == -26_801_000
    assert facts["depreciation_and_amortization"]["current"]["val"] == 2_348_000
    assert facts["property_additions"]["current"]["val"] == -634_000
    assert facts["diluted_shares"]["current"]["val"] == 12_077_000
    assert {facts[key]["current"]["start"] for key in facts} == {"2025-07-01"}
    assert {facts[key]["current"]["end"] for key in facts} == {"2026-06-30"}
    assert {facts[key]["current"]["accn"] for key in facts} == {"0001193125-26-409182"}
    run=ROOT/"runs"/"desk"/"DESK_2026-11-22_13-31-53-865623"/"agent"/"MSG_Rangers_Corp_2026-11-22_13-31-54-793145"
    result=assemble(run,"MSGR",form10_evidence=evidence,form10_accession="0001193125-26-409182")
    assert Decimal(result["base_owner_cash_flow_usd_millions"]) == Decimal("-25.087")
    assert Decimal(result["diluted_shares_millions"]) == Decimal("12.077")
    assert Decimal(result["low_equity_value_usd_millions"]) == Decimal("0")
    assert Decimal(result["low_value_per_share_usd"]) == Decimal("0")
    assert result["period"] == "2025-07-01 to 2026-06-30"
    assert result["source_basis"] == "aligned Form 10 comparable annual pro-forma figures"
    assert result["inputs"]["net_income"]["source_line"] == 1791
    assert result["inputs"]["property_additions"]["source_line"] == 5108

def test_form10_parser_refuses_a_renamed_10q(tmp_path):
    path=tmp_path/"10-Q_000162828026071325.txt"
    path.write_text("For the Year Ended June 30, 2026\n")
    with pytest.raises(ValueError,match="filename"):
        parse_form10_comparable_annual_pro_forma(path)

def test_high_conviction_requires_all_five_known_inputs_and_liquidity(tmp_path):
    closes={"closes":[{"close":"10","volume":"100000","date":"2026-01-01"},{"close":"10","volume":"100000","date":"2026-01-02"}]}
    (tmp_path/"worksheet_closes.json").write_text(json.dumps(closes))
    (tmp_path/"facts.json").write_text(json.dumps({
        "owner_cash_flow_periods":[{"value":"10","period":"FY25","tag":"OCF25"},{"value":"12","period":"FY26","tag":"OCF26"}],
        "parent_burden":{"status":"no_material_obligations","source":"10-Q accession X","section":"Debt note","amount":"none stated","period":"FY26"},
        "insider_data_complete":True,"insider_purchases":[]
    }))
    known={"number":"known"}
    result={"base_owner_cash_flow_usd_millions":"10","diluted_shares_millions":"1","last_eligible_close_usd":"50","low_equity_value_usd_millions":"66.6666666667","criterion_scores":{k:dict(known) for k in ("margin_of_safety","owner_cash_flow","parent_burden","insider_alignment","liquidity")}}
    calculate_liquidity(result,tmp_path)
    assert result["conviction"]=="High"
    facts=json.loads((tmp_path/"facts.json").read_text());facts["parent_burden"]={"status":"not known"};(tmp_path/"facts.json").write_text(json.dumps(facts))
    calculate_liquidity(result,tmp_path)
    assert result["conviction"]=="Low"

def test_persona_call_occurs_once_and_liquidity_uses_saved_volume(tmp_path):
    class FakeClient:
        calls=0
        def call(self,**kwargs):
            self.calls+=1
            return {"analysis":"Evidence only.","insight":"not available"}
    client=FakeClient()
    (tmp_path/"facts.json").write_text(json.dumps({"facts":{}}))
    (tmp_path/"verified_report.md").write_text("Verified.")
    persona_call({"ticker":"TST"},tmp_path,client=client)
    assert client.calls==1
    class FakeReader:
        last_payloads=[{"prices":[{"time":"2026-11-18","volume":100,"close":10},{"time":"2026-11-19","volume":200,"close":10}]}]
        def daily_closes(self,*args):
            from closes_reader import DailyClose
            from datetime import date
            from decimal import Decimal
            return [DailyClose(date(2026,11,18),Decimal("10"),"TST","mock"),DailyClose(date(2026,11,19),Decimal("10"),"TST","mock")]
    result={"ticker":"TST","base_owner_cash_flow_usd_millions":None,"diluted_shares_millions":None}
    rows=save_market_data(result,tmp_path,reader=FakeReader())
    calculate_liquidity(result,tmp_path)
    assert len(rows)==2
    assert Decimal(result["median_daily_dollar_volume_usd"])==Decimal("1500")
