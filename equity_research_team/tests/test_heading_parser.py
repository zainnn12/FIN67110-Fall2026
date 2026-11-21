import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from research_roles import extract_ten_k_sections

def test_ten_k_split_item_heading_is_detected():
    text="""ITEM 1.\nBUSINESS\nBusiness facts.\nITEM 1A.\nRISK FACTORS\nRisks.\nITEM 7.\nMANAGEMENT'S DISCUSSION AND ANALYSIS, (continued)\nThe MD&A text.\nITEM 7A.\nQUANTITATIVE AND QUALITATIVE DISCLOSURES ABOUT MARKET RISK\nMarket risk."""
    sections=extract_ten_k_sections(text)
    assert "The MD&A text." in sections["md_and_a"]["text"]
    assert "Business facts." in sections["business"]["text"]
