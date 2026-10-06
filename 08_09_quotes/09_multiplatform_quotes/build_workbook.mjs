import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root='/workspace/scratch/762a81acb5ac/msg_multiplatform_20260929';
const data=JSON.parse(await fs.readFile(path.join(root,'work/workbook_data.json'),'utf8'));
const out=path.join(root,'outputs');
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(root,'input/workbook_template_v0.xlsx')));
const sum=wb.worksheets.getItem('汇总与费率');
const quotes=wb.worksheets.getItem('地图报价');
const imgs=wb.worksheets.getItem('图片核对');
const cross=wb.worksheets.getItem('跨平台同排');
const crossBefore=JSON.stringify({values:cross.getRange('A1:H22').values,formulas:cross.getRange('A1:H22').formulas});
const obs=data.observations;const end=obs.length+1;
const imEnd=data.images.length+1;
const ddate=s=>s?new Date(s+'T00:00:00Z'):null;
// Extend the existing native tables; preserve tabs, styles and unaffected references.
quotes.tables.items.find(x=>x.name==='QuoteObservations').rows.add(null,obs.slice(978).map(()=>Array(27).fill(null)));
imgs.tables.items.find(x=>x.name==='ImageManifest').rows.add(null,data.images.slice(49).map(()=>Array(12).fill(null)));
for(const [sh,bounds] of [[quotes,`A980:AA${end}`],[imgs,`A51:L${imEnd}`]])sh.getRange(bounds).format.font={name:'Noto Sans CJK SC',size:11,color:'#202C3B'};
function header(sh,range){sh.getRange(range).format={fill:'#243A55',font:{name:'Noto Sans CJK SC',size:11,bold:true,color:'#FFFFFF'},rowHeight:32,horizontalAlignment:'center',verticalAlignment:'center',wrapText:true};}
function width(sh,col,n){sh.getRange(col).format.columnWidthPx=n;}
function title(sh,text,last){sh.getRange('A2').values=[[text]];sh.getRange('A2').format.font={name:'Noto Sans CJK SC',size:16,bold:true,color:'#243A55'};sh.getRange(`A3:${last}3`).format.borders={bottom:{style:'thin',color:'#BBC7D3'}};sh.getRange('A2').format.rowHeight=30;}

const qheaders=['观察ID','平台','文件夹场次','Section','Row','截图价格 USD','估算买方费率','估算手续费 USD','含费成本参考 USD','价格筛选','场次核对','Row识别方式','同座位价格观察数','重复组合','普通100区','参考用途','模型裸价：数量1','模型裸价：数量2','7日可比记录数','7日裸价中位数≥5','模型口径说明','选购张数','原图相对路径','图片ID','ZIP修改时间（时区未知）','识别备注','模型参考时刻 UTC'];
quotes.getRange(`A1:AA${end}`).values=[qheaders,...obs.map(x=>[x.observation_id,x.platform,ddate(x.event_date_folder),x.section_label,x.row,x.displayed_price_usd,null,null,null,null,x.event_identity_status,x.row_reading_method,x.same_seat_price_observation_count,x.repeated_seat_price_combination?'是':'否',x.ordinary100_section?'是':'否',null,x.model_sh_base_price_qty1_scenario??null,x.model_sh_base_price_qty2_scenario??null,x.historical_same_event_section_rowband_7d_n??null,x.historical_7d_median_base_min5??null,x.model_comparison_note,'未知',x.source_file,x.image_id,x.zip_member_modified_local,`[${x.snapshot_batch}] ${x.notes}`,x.reference_asof_utc])];
quotes.getRange(`G2:G${end}`).formulas=obs.map((x,i)=>[`=IF(B${i+2}="SeatGeek",'汇总与费率'!$B$22,"")`]);
quotes.getRange(`H2:H${end}`).formulas=obs.map((x,i)=>[`=IF(F${i+2}="","",IF(B${i+2}="SeatGeek",ROUND(F${i+2}*G${i+2},2),""))`]);
quotes.getRange(`I2:I${end}`).formulas=obs.map((x,i)=>[`=IF(F${i+2}="","",IF(B${i+2}="SeatGeek",ROUND(F${i+2}+H${i+2},2),F${i+2}))`]);
quotes.getRange(`J2:J${end}`).formulas=obs.map((x,i)=>[`=IF(F${i+2}="","待核对",IF(OR(F${i+2}>'汇总与费率'!$B$23,I${i+2}>'汇总与费率'!$B$23),"排除","保留"))`]);
quotes.getRange(`P2:P${end}`).formulas=obs.map((x,i)=>{const r=i+2;return [`=IF(J${r}="排除","排除",IF(F${r}="","价格待核对",IF(K${r}<>"按用户文件夹标注","场次待核对",IF(O${r}<>"是","普通100区外",IF(E${r}="","仅Section参考",IF(OR(E${r}<3,E${r}>22),"Row范围外","座位参考"))))))`];});
header(quotes,'A1:AA1');quotes.freezePanes.freezeRows(1);quotes.freezePanes.freezeColumns(4);
quotes.getRange(`A980:AA${end}`).format.rowHeight=23;
for(const [c,w] of Object.entries({A:100,B:100,C:115,D:90,E:60,F:120,G:115,H:130,I:140,J:100,K:255,L:205,M:145,N:100,O:110,P:160,Q:155,R:155,S:140,T:165,U:780,V:100,W:290,X:80,Y:230,Z:430,AA:270}))width(quotes,`${c}1:${c}${end}`,w);
quotes.getRange(`C2:C${end}`).setNumberFormat('yyyy-mm-dd');quotes.getRange(`F2:F${end}`).setNumberFormat('$#,##0.00');quotes.getRange(`G2:G${end}`).setNumberFormat('0.0000%');quotes.getRange(`H2:I${end}`).setNumberFormat('$#,##0.00');quotes.getRange(`Q2:R${end}`).setNumberFormat('$#,##0.00');quotes.getRange(`T2:T${end}`).setNumberFormat('$#,##0.00');
quotes.getRange(`J980:J${end}`).conditionalFormats.add('containsText',{text:'排除',format:{fill:'#FBE9E7',font:{color:'#9D211A'}}});
quotes.getRange(`K980:K${end}`).conditionalFormats.add('notContainsText',{text:'按用户文件夹标注',format:{fill:'#FFF1CF',font:{color:'#80510A'}}});

title(sum,'Harry Styles MSG：三平台区域报价整理','L');
sum.getRange('A4').values=[['59张截图，含原始与重拍批次；地图观察数不是库存张数，也不是成交笔数。']];
sum.getRange('A6:F6').values=[['平台','场次','图片数','报价观察数','价格排除数','座位参考组合数']];header(sum,'A6:F6');
for(let i=0;i<data.summary.length;i++){
 const x=data.summary[i],r=i+7;
 sum.getRange(`A${r}:D${r}`).values=[[x.platform,ddate(x.event_date_folder),x.image_count,x.marker_observations]];
 const cond=x.event_date_folder?`'地图报价'!$C$2:$C$${end},B${r}`:`'地图报价'!$K$2:$K$${end},"缺少场次日期"`;
 sum.getRange(`E${r}`).formulas=[[`=COUNTIFS('地图报价'!$B$2:$B$${end},A${r},${cond},'地图报价'!$J$2:$J$${end},"排除")`]];
 sum.getRange(`F${r}`).formulas=[[`=COUNTIFS('地图报价'!$B$2:$B$${end},A${r},${cond},'地图报价'!$P$2:$P$${end},"座位参考",'地图报价'!$N$2:$N$${end},"否")`]];
}
sum.getRange('B7:B18').setNumberFormat('yyyy-mm-dd');
sum.getRange('A19').values=[['合计']];sum.getRange('C19:F19').formulas=[['=SUM(C7:C18)','=SUM(D7:D18)','=SUM(E7:E18)','=SUM(F7:F18)']];sum.getRange('A19:F19').format.font={bold:true};
sum.getRange('H6').values=[['本次日期核对与筛选']];sum.getRange('H6').format.font={bold:true,color:'#80510A'};
const notes=[
['H7','“新建文件夹”4张已按用户明确说明确认为10/7。'],
['H8','旧0930共74组：与新1002重合63组，与新0930重合3组。'],
['H9','旧0930与旧1002继续隔离；9/30与10/2参考使用重拍图。'],
['H11','SeatGeek所有排号暂留空：图中只有未标号座位点。'],
['H12','Gametime部分指针难以追踪，Row留空并保留价格。'],
['H13','新增10张、140条观察；共22个价格被遮挡或裁切。'],
['H15','当前筛选：展示价或含费成本参考 > $1,000排除。'],
['H16','154条展示价超限，另9条加估算费后超限，共排除163条。'],
['H17','高价标记保留在明细；不证明错误或无人会买。'],
['H20','新0930有12条普通100区参考，新1002有71条；含图间重叠。'],
['H21','Gametime / TickPick含费口径按用户说明，未重复加费。'],
['H22','SeatGeek裸价口径按用户说明，平均费率只是估算。'],
['H23','16组费率简单平均；折扣单列，不从费用中冲减。'],
['H25','截图未显示购买张数、Listing ID、卖方费和交付条件。'],
['H26','新图ZIP时钟21:10–21:13，时区未知；缺失报价不认定为售出。'],
['H27','原批次/重拍参考UTC 01:45/02:15；均不是精确采集时刻。'],
['H28','模型训练截止：纽约9/29 18:36:39；系数未重拟合。'],
['H29','模型是sh裸价；不得直接用含费地图价相减计算收益。'],
['H30','数量1/2仅为模型情景，实际选购张数未知。'],
['H31','原始图片、CSV、代码和输入模型保存在同名数据包。']
];for(const [cell,txt]of notes)sum.getRange(cell).values=[[txt]];
sum.getRange('A21:B23').values=[['费用与筛选参数',null],['SeatGeek平均买方费率',null],['价格上限 USD',1000]];
sum.getRange('B22').formulas=[['=AVERAGE(E28:E43)']];sum.getRange('B22').setNumberFormat('0.0000%');sum.getRange('B23').setNumberFormat('$#,##0');sum.getRange('B23').format.fill='#FFF1CF';
sum.getRange('A25').values=[['费率校准：16组不同座位／报价明细（重复观察已合并）']];
sum.getRange('A27:F27').values=[['Section / Row','基础价 USD','买方费 USD','折扣 USD','费率','此前来源文件']];header(sum,'A27:F27');
sum.getRange('A28:F43').values=data.fees.map(x=>[`${x.section} / ${x.row}`,x.base,x.fee,x.discount,null,x.file]);
sum.getRange('E28:E43').formulas=data.fees.map((_,i)=>[`=C${28+i}/B${28+i}`]);sum.getRange('B28:D43').setNumberFormat('$#,##0.00');sum.getRange('E28:E43').setNumberFormat('0.0000%');
sum.getRange('A6:L43').format.rowHeight=27;sum.getRange('A6:F6').format.rowHeight=40;sum.getRange('A27:F27').format.rowHeight=34;
for(const [c,w] of Object.entries({A:200,B:130,C:125,D:125,E:125,F:260,G:24,H:180,I:140,J:140,K:140,L:180}))width(sum,`${c}1:${c}43`,w);
sum.tabColor='#243A55';

const imheads=['图片ID','平台','文件夹场次','场次核对','原图相对路径','图宽','图高','观察数','遮挡价格数','普通100区未知Row数','ZIP修改时间（时区未知）','原图SHA256'];
imgs.getRange(`A1:L${imEnd}`).values=[imheads,...data.images.map(x=>[x.image_id,x.platform,ddate(x.event_date_folder),x.event_identity_status,x.path,x.width,x.height,x.markers,x.prices_occluded,x.rows_unknown_ordinary100,x.zip_member_modified_local,x.sha256])];
header(imgs,'A1:L1');imgs.freezePanes.freezeRows(1);imgs.getRange(`C2:C${imEnd}`).setNumberFormat('yyyy-mm-dd');
imgs.getRange(`A51:L${imEnd}`).format.rowHeight=25;

const cn=data.cross_platform.length+6;

wb.recalculate();
// Meaningful recalculation check: rate update must propagate to a SeatGeek quote,
// while Gametime stays unchanged. Restore the authoritative average formula.
const sgIndex=obs.findIndex(x=>x.platform==='SeatGeek'&&x.displayed_price_usd!==null);const rr=sgIndex+2;
const gtIndex=obs.findIndex(x=>x.platform==='Gametime'&&x.displayed_price_usd!==null)+2;
const original=quotes.getRange(`I${rr}`).values[0][0];const gtOriginal=quotes.getRange(`I${gtIndex}`).values[0][0];
sum.getRange('B22').values=[[0.20]];wb.recalculate();
const changed=quotes.getRange(`I${rr}`).values[0][0];
if(Math.abs(changed-Math.round(obs[sgIndex].displayed_price_usd*1.20*100)/100)>1e-6)throw new Error('Fee change did not recalculate');
if(quotes.getRange(`I${gtIndex}`).values[0][0]!==gtOriginal)throw new Error('Gametime charged twice');
sum.getRange('B22').formulas=[['=AVERAGE(E28:E43)']];wb.recalculate();
if(Math.abs(quotes.getRange(`I${rr}`).values[0][0]-original)>1e-6)throw new Error('Fee restoration failed');
const check={rate:sum.getRange('B22').values[0][0],totals:sum.getRange('C19:F19').values[0],fee_recalculation_passed:true};
if(Math.abs(check.rate-data.audit.fee_rate_mean)>1e-10)throw new Error('Fee mismatch');
if(check.totals[0]!==data.audit.images||check.totals[1]!==data.audit.marker_observations||check.totals[2]!==data.audit.excluded_total_including_estimated_fee_crossings||check.totals[3]!==data.audit.seat_references_after_combination_dedup)throw new Error('Summary reconciliation mismatch '+JSON.stringify(check));
if(crossBefore!==JSON.stringify({values:cross.getRange('A1:H22').values,formulas:cross.getRange('A1:H22').formulas}))throw new Error('Unaffected cross-platform sheet changed');
const allcost=quotes.getRange(`I2:I${end}`).values;
for(let i=0;i<obs.length;i++)if(obs[i].buyer_cost_per_ticket_reference!==null&&Math.abs(allcost[i][0]-obs[i].buyer_cost_per_ticket_reference)>1e-6)throw new Error('Cost mismatch at '+i);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},summary:'Final formula errors',maxChars:2000});
await fs.writeFile(path.join(root,'work/workbook_checks.json'),JSON.stringify({check,errors:errors.ndjson},null,2));
console.log(JSON.stringify(check));console.log(errors.ndjson);
const previews=[['汇总与费率','A1:L31','summary_update'],['地图报价','A980:K992','new_quotes'],['图片核对','A49:E60','new_images']];
for(const[sheetName,range,name]of previews){const p=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(root,'work',name+'.png'),new Uint8Array(await p.arrayBuffer()));}
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(path.join(out,'Harry_MSG_multiplatform_quotes.xlsx'));
console.log('EXPORTED');
