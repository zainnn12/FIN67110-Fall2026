#!/usr/bin/env python3
"""Save a filing index and exhibit using SEC_USER_AGENT only."""
import argparse,hashlib,json,sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from equity_research_data import SecClient,read_sec_user_agent,resource_to_plain_text

def save_bundle(*,ticker,company,cik,accession,accepted,index_url,exhibit_url,output,client=None):
    if client is None: client=SecClient(read_sec_user_agent(ROOT))
    output=Path(output);output.mkdir(parents=True,exist_ok=True); docs=[]
    for label,url in (("filing_index",index_url),("exhibit_99_1",exhibit_url)):
        response=client.fetch(url); suffix=Path(url.split('?',1)[0]).suffix or '.html'
        raw_path=output/f'{label}_raw{suffix}'; raw_path.write_bytes(response.content)
        text=resource_to_plain_text(response); text_path=output/f'{label}.txt';text_path.write_text(text,encoding='utf-8')
        docs.append({'label':label,'url':url,'raw_file':raw_path.name,'text_file':text_path.name,'sha256':hashlib.sha256(response.content).hexdigest()})
    manifest={'ticker':ticker.upper(),'company':company,'cik':int(cik),'accession':accession,'accepted':accepted,'retrieved_at':datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds'),'documents':docs}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def main():
    p=argparse.ArgumentParser();
    for name in ('ticker','company','cik','accession','accepted','index-url','exhibit-url','output'): p.add_argument('--'+name,required=True)
    a=p.parse_args(); save_bundle(ticker=a.ticker,company=a.company,cik=a.cik,accession=a.accession,accepted=a.accepted,index_url=a.index_url,exhibit_url=a.exhibit_url,output=a.output); print(f"Saved filing bundle for {a.ticker.upper()} in {a.output}")
if __name__=='__main__': main()
