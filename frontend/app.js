const val=id=>document.getElementById(id).value;
document.getElementById('analyze-message').addEventListener('click',()=>submitForm('/api/message',{text:val('msg'),sender:val('sender')},'out-message'));
document.getElementById('analyze-url').addEventListener('click',()=>submitForm('/api/url',{url:val('urlvalue')},'out-url'));
document.getElementById('ask-assistant').addEventListener('click',()=>submitForm('/api/assistant',{question:val('question')},'out-assistant'));
document.getElementById('search-incidents').addEventListener('click',()=>submitForm('/api/incidents',{description:val('incident')},'out-incidents'));
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{document.querySelectorAll('nav button').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('body>section').forEach(s=>s.classList.toggle('hidden',s.id!==b.dataset.tab))});
async function submitForm(path,payload,target){const box=document.getElementById(target);box.textContent='Analyzing…';try{const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});box.textContent=JSON.stringify(await r.json(),null,2)}catch(e){box.textContent='Local service unavailable.'}}
