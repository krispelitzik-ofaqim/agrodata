/* AgroData auto-translate — translates any page's Hebrew text into the chosen
   language via /api/translate (Gemini, cached). Choice persists in localStorage.
   Mark elements you do NOT want translated with class="notrans" or data-notrans. */
(function(){
  var LANGS=[['he','🇮🇱 עברית'],['en','🇬🇧 English'],['de','🇩🇪 Deutsch'],['fr','🇫🇷 Français'],['zh','🇨🇳 中文'],['ar','🇸🇦 العربية'],['ru','🇷🇺 Русский'],['hi','🇮🇳 हिन्दी']];
  var LNAME={he:'עברית',en:'English',de:'Deutsch',fr:'Français',zh:'中文',ar:'العربية',ru:'Русский',hi:'हिन्दी'};
  function get(){try{return localStorage.getItem('agrolang')||'he';}catch(e){return 'he';}}
  var lang=get(), de=document.documentElement;
  de.lang=lang; de.dir=(lang==='he'||lang==='ar')?'rtl':'ltr';
  var HEB=/[֐-׿]/;

  function setLang(l){ try{localStorage.setItem('agrolang',l);}catch(e){} location.reload(); }

  function menu(){
    if(document.getElementById('ag-langbox')) return;
    var side=(de.dir==='rtl')?'left':'right';
    var box=document.createElement('div'); box.id='ag-langbox';
    box.style.cssText='position:fixed;top:10px;'+side+':10px;z-index:99999;font-family:system-ui,-apple-system,Arial,sans-serif;';
    var btn=document.createElement('button');
    btn.textContent='🌐 '+(LNAME[lang]||'עברית')+' ▾';
    btn.style.cssText='border:1px solid rgba(0,0,0,.15);background:#fff;color:#1c2b35;border-radius:20px;padding:7px 13px;font-size:13px;font-weight:700;cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.14);';
    var list=document.createElement('div');
    list.style.cssText='display:none;position:absolute;top:40px;'+side+':0;background:#fff;border:1px solid rgba(0,0,0,.12);border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,.16);overflow:hidden;min-width:150px;';
    LANGS.forEach(function(L){
      var a=document.createElement('div'); a.textContent=L[1];
      a.style.cssText='padding:9px 14px;font-size:13.5px;color:#1c2b35;cursor:pointer;'+(L[0]===lang?'background:#eef7f0;font-weight:800;':'');
      a.onmouseover=function(){a.style.background='#f3f6f4';};
      a.onmouseout=function(){a.style.background=(L[0]===lang?'#eef7f0':'#fff');};
      a.onclick=function(){ if(L[0]!==lang) setLang(L[0]); };
      list.appendChild(a);
    });
    btn.onclick=function(e){e.stopPropagation();list.style.display=(list.style.display==='none')?'block':'none';};
    document.addEventListener('click',function(){list.style.display='none';});
    box.appendChild(btn); box.appendChild(list); document.body.appendChild(box);
  }

  function skip(node){
    var p=node.parentNode;
    while(p && p.nodeType===1){
      var tag=p.tagName;
      if(tag==='SCRIPT'||tag==='STYLE'||tag==='NOSCRIPT'||tag==='TEXTAREA') return true;
      if(p.id==='ag-langbox') return true;
      if(p.classList && (p.classList.contains('notrans'))) return true;
      if(p.hasAttribute && p.hasAttribute('data-notrans')) return true;
      p=p.parentNode;
    }
    return false;
  }

  function translate(){
    var walker=document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null), nodes=[], set={}, uniq=[], n;
    while(n=walker.nextNode()){
      var v=n.nodeValue; if(!v) continue;
      var t=v.trim(); if(!t || !HEB.test(t)) continue;
      if(skip(n)) continue;
      nodes.push(n); if(!(t in set)){ set[t]=1; uniq.push(t); }
    }
    var phEls=[].slice.call(document.querySelectorAll('[placeholder]'));
    phEls.forEach(function(el){ var t=(el.getAttribute('placeholder')||'').trim(); if(t&&HEB.test(t)&&!(t in set)){set[t]=1;uniq.push(t);} });
    if(!uniq.length) return;
    fetch('/api/translate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lang:lang,texts:uniq})})
     .then(function(r){return r.json();}).then(function(j){
        var m=(j&&j.map)||{};
        nodes.forEach(function(nn){ var v=nn.nodeValue, t=v.trim(); if(m[t]&&m[t]!==t){ nn.nodeValue=v.replace(t, m[t]); } });
        phEls.forEach(function(el){ var t=(el.getAttribute('placeholder')||'').trim(); if(m[t]) el.setAttribute('placeholder', m[t]); });
     }).catch(function(){});
  }

  function init(){ menu(); if(lang!=='he') translate(); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init); else init();
})();
