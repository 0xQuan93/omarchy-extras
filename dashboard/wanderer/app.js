'use strict';
const $ = id => document.getElementById(id);
let readings = [], topic = 'All', offset = 0, dayKey = '';
function localDate() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
function readStore(key, fallback) { try { return JSON.parse(localStorage.getItem(key)) ?? fallback; } catch { return fallback; } }
function writeStore(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch { return false; } }
let saved = readStore('wanderer-saved', []);
if (!Array.isArray(saved)) saved = [];
function node(tag, text, cls) { const e=document.createElement(tag); if(text)e.textContent=text; if(cls)e.className=cls; return e; }
function link(text, url) { const a=node('a',text); a.href=url; a.target='_blank'; a.rel='noopener'; return a; }
function daily() {
  dayKey=localDate(); $('date').textContent=new Date().toLocaleDateString(undefined,{month:'long',day:'numeric',weekday:'short'});
  const day=Math.floor(Date.parse(dayKey+'T00:00:00Z')/86400000), r=readings[(day+offset)%readings.length];
  $('kind').textContent=r.kind; $('daily-title').textContent=r.title; $('daily-description').textContent=r.description; $('daily-link').href=r.url; $('prompt').textContent=r.prompt;
  $('note').value=readStore('wanderer-notes',{})[dayKey] || '';
}
function render() {
  const query=$('search').value.toLowerCase(); $('library').replaceChildren();
  const matches=readings.filter(r=>(topic==='All'||r.topic===topic||(topic==='Saved'&&saved.includes(r.url)))&&JSON.stringify(r).toLowerCase().includes(query));
  for(const r of matches){
    const card=node('article',null,'tile'); card.append(node('small',r.kind+' / '+r.topic),node('h3',r.title),node('p',r.description),node('small',r.source));
    const actions=node('div',null,'actions'), b=node('button',saved.includes(r.url)?'Saved ✓':'Save');
    b.setAttribute('aria-pressed',String(saved.includes(r.url)));
    b.onclick=()=>{ const next=saved.includes(r.url)?saved.filter(x=>x!==r.url):[...saved,r.url]; if(writeStore('wanderer-saved',next)){saved=next;render();}else b.textContent='Storage unavailable'; };
    actions.append(link('Explore ↗',r.url),b);card.append(actions);$('library').append(card);
  }
  if(!matches.length)$('library').append(node('p','No readings match this view.'));
}
let loading=false;
async function news() {
  if(loading)return;loading=true;$('refresh').disabled=true;$('feed-status').textContent='Checking public feeds…';
  try {
    const res=await fetch('/api/wanderer/news');if(!res.ok)throw Error();const data=await res.json();$('news').replaceChildren();
    for(const r of data.items){ const card=node('article',null,'tile');card.append(node('small',r.source+' · '+(r.date||'Date not supplied')),link(r.title,r.url),node('p',r.kind));$('news').append(card); }
    $('feed-status').textContent=`Last checked ${new Date(data.checkedAt*1000).toLocaleString()}. Checks every 30 minutes while open.`+(data.errors.length?' Unavailable feeds: '+data.errors.join(', ')+'.':'')+(!data.items.length?' No headlines available right now. Your reading room is still available.':'');
  }catch{$('feed-status').textContent='The news service is unavailable. Previously displayed headlines may be out of date.';}
  finally{loading=false;$('refresh').disabled=false;}
}
$('another').onclick=()=>{offset++;daily();};$('search').oninput=render;$('refresh').onclick=news;
$('note').oninput=()=>{ const notes=readStore('wanderer-notes',{});notes[dayKey]=$('note').value;$('saved').textContent=writeStore('wanderer-notes',notes)?'Saved in this browser.':'Could not save. Copy your note before closing.'; };
$('export').onclick=()=>{const notes=readStore('wanderer-notes',{});const text=Object.entries(notes).sort().map(([day,note])=>`## ${day}\n\n${note}`).join('\n\n');download(new Blob([text],{type:'text/markdown'}),'wanderer-reflections.md');};
function download(blob,name){const url=URL.createObjectURL(blob),a=link('',url);a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);}
let db;
function transaction(mode, fn){return new Promise((resolve,reject)=>{const tx=db.transaction('pdfs',mode);fn(tx.objectStore('pdfs'));tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error);});}
async function shelf(){
  const rows=await new Promise((resolve,reject)=>{const req=db.transaction('pdfs').objectStore('pdfs').getAll();req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});
  $('shelf').replaceChildren();if(!rows.length)$('shelf').append(node('p','Your shelf is ready for its first PDF.'));
  for(const r of rows){const row=node('div',null,'pdf-row'),open=node('button','Read ↗'),remove=node('button','Remove');row.append(node('span',r.name),open,remove);open.onclick=()=>{const url=URL.createObjectURL(r.file);window.open(url,'_blank','noopener');setTimeout(()=>URL.revokeObjectURL(url),60000);};remove.onclick=async()=>{try{await transaction('readwrite',s=>s.delete(r.id));await shelf();}catch{$('pdf-status').textContent='Could not remove this PDF.';}};$('shelf').append(row);}
}
$('pdfs').onchange=async()=>{try{for(const file of $('pdfs').files){if(!file.name.toLowerCase().endsWith('.pdf'))continue;if(file.size>100*1024*1024)throw Error('Please use PDFs smaller than 100 MB.');await transaction('readwrite',s=>s.put({id:file.name+':'+file.size,name:file.name,file}));}await shelf();$('pdf-status').textContent='Saved locally in this browser. Keep your original files as backups.';}catch(e){$('pdf-status').textContent=e.message||'Could not save. Browser storage may be full.';}finally{$('pdfs').value='';}};
const request=indexedDB.open('wanderer-library',1);request.onupgradeneeded=()=>request.result.createObjectStore('pdfs',{keyPath:'id'});request.onsuccess=()=>{db=request.result;shelf().catch(()=>{$('pdf-status').textContent='Could not read the PDF shelf.';});};request.onerror=()=>{$('pdf-status').textContent='PDF storage is unavailable in this browser.';$('pdfs').disabled=true;};
fetch('/wanderer/readings.json').then(r=>{if(!r.ok)throw Error();return r.json();}).then(data=>{readings=data;for(const name of ['All',...new Set(readings.map(r=>r.topic)),'Saved']){const b=node('button',name);b.classList.toggle('active',name===topic);b.onclick=()=>{topic=name;for(const child of $('filters').children)child.classList.toggle('active',child===b);render();};$('filters').append(b);}daily();render();setInterval(()=>{if(localDate()!==dayKey){offset=0;daily();}},60000);}).catch(()=>{$('daily-title').textContent='The reading room could not load. Please reload the page.';});
news();setInterval(news,1800000);

// Reload just the palette: preserve scroll, notes, and the PDF shelf.
let themeLoading = false;
function refreshTheme() {
  if (document.hidden || themeLoading) return;
  themeLoading = true;
  const previous = $('machine-theme'), next = document.createElement('link');
  next.rel = 'stylesheet'; next.href = '/wanderer/theme.css?t=' + Date.now();
  next.onload = () => { previous.remove(); next.id = 'machine-theme'; themeLoading = false; };
  next.onerror = () => { next.remove(); themeLoading = false; };
  previous.after(next);
}
setInterval(refreshTheme, 2000);
document.addEventListener('visibilitychange', refreshTheme);
window.addEventListener('focus', refreshTheme);
