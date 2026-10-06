from pathlib import Path
import hashlib,json,zipfile,xml.etree.ElementTree as ET
import pandas as pd

ROOT=Path(__file__).resolve().parent
out=ROOT/'outputs'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

# Scope checks: original prices/seat readings unchanged, new batch separate,
# uncertain dates never used as current quotes, and original model unchanged.
d=pd.read_csv(out/'all_quote_observations.csv')
assert len(d)==1118 and d.observation_id.is_unique
assert d[d.snapshot_batch.eq('重拍批次')].shape[0]==140
old_sg=d[d.platform.eq('SeatGeek')&d.snapshot_batch.eq('原始批次')&d.event_date_folder.isin(['2026-09-30','2026-10-02'])]
assert len(old_sg)==202 and not old_sg.quote_reference_eligible.any()
sg7=d[d.image_id.isin(['I28','I29','I30','I31'])]
assert len(sg7)==78 and sg7.event_date_folder.eq('2026-10-07').all()
assert int(d.excluded_displayed_over_1000.sum())==154
assert int(d.excluded_by_price_policy.sum())==163
assert len(pd.read_csv(out/'seat_quote_references.csv'))==306
assert not d[d.displayed_price_usd.gt(1000)].quote_reference_eligible.any()
assert not d[d.quote_reference_eligible].buyer_cost_per_ticket_reference.gt(1000).any()
assert sha(ROOT/'input/Harry_current_sales_20260929.csv')=='21fa02d9447e0e4f18df309af6c2286025bf8a49c5927991ed9fcd288284cfcc'
assert sha(ROOT/'input/frozen_forecast_model.json')=='f0468789de1509ec645d776258f1b6f54ff9da1ea13b90864a273ae4318a7f1b'

ns={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(out/'Harry_MSG_multiplatform_quotes.xlsx') as z:
    assert z.testzip() is None
    tables={}
    for f in z.namelist():
        if f.startswith('xl/tables/') and f.endswith('.xml'):
            x=ET.fromstring(z.read(f));tables[x.attrib['name']]=x.attrib['ref']
    assert tables['QuoteObservations']=='A1:AA1119',tables
    assert tables['ImageManifest']=='A1:L60',tables
    # Cross-platform tab was not part of this edit: retain its values/formulas.
    with zipfile.ZipFile(ROOT/'input/workbook_template_v0.xlsx') as old:
        def cells(archive,sheet):
            root=ET.fromstring(archive.read(sheet));shared=[]
            if 'xl/sharedStrings.xml' in archive.namelist():
                sr=ET.fromstring(archive.read('xl/sharedStrings.xml'))
                shared=[''.join(si.itertext()) for si in sr]
            result={}
            for c in root.findall('.//x:sheetData/x:row/x:c',ns):
                v=c.find('x:v',ns);f=c.find('x:f',ns)
                val=None if v is None else v.text
                if c.attrib.get('t')=='s':val=shared[int(val)]
                elif c.attrib.get('t')=='inlineStr':val=''.join(c.find('x:is',ns).itertext())
                result[c.attrib['r']]=(val,None if f is None else f.text)
            return result
        assert cells(z,'xl/worksheets/sheet4.xml')==cells(old,'xl/worksheets/sheet4.xml')
        original=cells(old,'xl/worksheets/sheet2.xml');updated=cells(z,'xl/worksheets/sheet2.xml')
        for r in range(2,980):
            for col in ['A','B','D','E','F','L','M','N','O','Q','R','S','T','U','V','W','X','Y','AA']:
                assert original.get(f'{col}{r}')==updated.get(f'{col}{r}'),(col,r)

files=[]
for folder in ['raw','raw_update_seatgeek','fee_source_images','input']:
    files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file())
files.extend(p for p in out.iterdir() if p.suffix in {'.csv','.json','.xlsx'})
files.extend(ROOT/name for name in ['README.txt','analyze.py','build_workbook.mjs','package.py',
    'work/manual_extract.py','work/manual_extract_update.py','work/images.json',
    'work/update_images.json','work/workbook_data.json','work/workbook_checks.json'])
target=out/'Harry_MSG_multiplatform_package.zip'
with zipfile.ZipFile(target.with_suffix('.pending'), 'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(set(files)):z.write(p,p.relative_to(ROOT))
target.with_suffix('.pending').replace(target)
manifest=pd.read_csv(out/'image_manifest.csv')
with zipfile.ZipFile(target) as z:
    assert z.testzip() is None
    for _,m in manifest.iterrows():
        assert hashlib.sha256(z.read(m.raw_file_relativepath)).hexdigest()==m.sha256
    assert z.read('outputs/Harry_MSG_multiplatform_quotes.xlsx')==(out/'Harry_MSG_multiplatform_quotes.xlsx').read_bytes()
checks={'zip_crc':'PASS','images_verified':len(manifest),'original_price_and_seat_cells_unchanged':True,
        'cross_platform_tab_unchanged':True,'native_table_ranges':tables,
        'package_files':len(files),'package_bytes':target.stat().st_size,'package_sha256':sha(target)}
(ROOT/'work/package_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2))
print(json.dumps(checks,ensure_ascii=False,indent=2))
