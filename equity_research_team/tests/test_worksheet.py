import json
import sys
from pathlib import Path
from decimal import Decimal

import pytest

ROOT=Path(__file__).resolve().parents[2]
SCRIPT=ROOT/"skills"/"spinoff-worksheet"
sys.path.insert(0,str(SCRIPT))
from spinoff_worksheet_hook import validate_report
from worksheet import aligned_owner_cash_flow, persona_call, save_market_data, calculate_liquidity

def test_hook_passes_clean_and_refuses_seeded_amount_by_line(tmp_path):
    (tmp_path/"facts.json").write_text(json.dumps({"facts":{"net_income":{"current":{"val":10}}}}))
    (tmp_path/"worksheet.json").write_text(json.dumps({"computed":10}))
    clean=tmp_path/"clean.md"; clean.write_text("Owner cash flow is 10 USD millions.\n")
    assert validate_report(clean,tmp_path)
    seeded=tmp_path/"seeded.md"; seeded.write_text("Owner cash flow is 987654321 USD millions.\n")
    with pytest.raises(ValueError,match="line 1"):
        validate_report(seeded,tmp_path)

def test_owner_cash_flow_requires_matching_periods_and_accession():
    facts={"net_income":{"current":{"val":20,"start":"2025-01-01","end":"2025-12-31","accn":"A"}},
           "depreciation_and_amortization":{"current":{"val":5,"start":"2025-01-01","end":"2025-12-31","accn":"A"}},
           "property_additions":{"current":{"val":-8,"start":"2025-01-01","end":"2025-12-31","accn":"A"}},
           "diluted_shares":{"current":{"val":10,"start":"2025-01-01","end":"2025-12-31","accn":"A"}}}
    value,_,basis=aligned_owner_cash_flow({"worksheet_basis":"Form 10 comparable annual pro-forma","worksheet_facts":facts})
    assert value==Decimal("17")
    assert basis=="aligned reported annual figures"
    facts["diluted_shares"]["current"]["end"]="2025-09-30"
    value,_,_=aligned_owner_cash_flow({"worksheet_basis":"Form 10 comparable annual pro-forma","worksheet_facts":facts})
    assert value is None

def test_no_unidentified_annual_basis_is_not_computed():
    value,_,basis=aligned_owner_cash_flow({"facts":{}})
    assert value is None
    assert basis.startswith("not computed")

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
