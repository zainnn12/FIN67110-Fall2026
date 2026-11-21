import json
from pathlib import Path

from equity_research_data import DownloadedResource
from save_sec_bundle import save_bundle


def test_sec_bundle_saves_raw_and_plain_text_without_model_call(tmp_path):
    class Client:
        calls=[]
        def fetch(self,url):
            self.calls.append(url)
            body=b'<html><body><p>Accepted: 2026-11-17</p><p>Revenue was 10.</p></body></html>'
            return DownloadedResource(url=url,content=body,content_type='text/html',encoding='utf-8')
    client=Client()
    result=save_bundle(ticker='TST',company='Test Corp',cik=123,accession='0000000123-26-000001',accepted='2026-11-17 16:00:00 ET',index_url='https://www.sec.gov/index.html',exhibit_url='https://www.sec.gov/exhibit.html',output=tmp_path,client=client)
    assert len(client.calls)==2
    assert result['ticker']=='TST'
    assert (tmp_path/'filing_index.txt').exists()
    assert 'Revenue was 10' in (tmp_path/'exhibit_99_1.txt').read_text()
    assert json.loads((tmp_path/'manifest.json').read_text())['accession']=='0000000123-26-000001'
