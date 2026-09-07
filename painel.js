const NAVY='#1B2A55', PINK='#C13B7E';
const fmt = n => (n==null?'—':n.toLocaleString('pt-BR'));
const f1  = n => (n==null?'—':(Math.round(n*10)/10).toLocaleString('pt-BR',{minimumFractionDigits:1}));

/* Mesmas faixas do painel de referência. */
function colorFor(v){
  if(v==null||isNaN(v)) return '#cfd3df';
  if(v>=65) return '#8f1f57';
  if(v>=57) return PINK;
  if(v>=50) return '#d97fae';
  if(v>=43) return '#aeb6d0';
  return '#5b6a99';
}
const FAIXAS=[['≥ 65','#8f1f57'],['57–65',PINK],['50–57','#d97fae'],['43–50','#aeb6d0'],['< 43','#5b6a99'],['sem dado','#cfd3df']];

let metric = DATA.eixos[0].k;
const L = k => DATA.labels[k] || k;
const B = DATA.bairros.filter(b=>b.Bairro!=='Não classificado');
const byB = Object.fromEntries(DATA.bairros.map(b=>[b.Bairro,b]));

/* ---------------------------------------------------- projeção do SVG */
function bounds(fc){
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  const walk=c=>{ if(typeof c[0]==='number'){x0=Math.min(x0,c[0]);x1=Math.max(x1,c[0]);
      y0=Math.min(y0,c[1]);y1=Math.max(y1,c[1]);} else c.forEach(walk); };
  fc.features.forEach(f=>walk(f.geometry.coordinates));
  return [x0,y0,x1,y1];
}
/* Equirretangular com correção de cosseno: fiel o bastante na escala de um
   município e sem a defasagem entre camadas que o Leaflet introduzia. */
function projector(bb,W,H,pad){
  const [x0,y0,x1,y1]=bb, lat0=(y0+y1)/2, kx=Math.cos(lat0*Math.PI/180);
  const w=(x1-x0)*kx, h=(y1-y0), s=Math.min((W-2*pad)/w,(H-2*pad)/h);
  const ox=(W-w*s)/2, oy=(H-h*s)/2;
  return (lon,lat)=>[ox+(lon-x0)*kx*s, H-oy-(lat-y0)*s];
}
function pathD(geom,P){
  const ring=r=>r.map((c,i)=>{const p=P(c[0],c[1]);return (i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1);}).join('')+'Z';
  const polys = geom.type==='Polygon' ? [geom.coordinates] : geom.coordinates;
  return polys.map(poly=>poly.map(ring).join('')).join('');
}

const tip=document.getElementById('tip');
function showTip(e,html){tip.innerHTML=html;tip.style.display='block';
  tip.style.left=Math.min(e.clientX+14,innerWidth-250)+'px';tip.style.top=(e.clientY+14)+'px';}
function hideTip(){tip.style.display='none';}

/* ------------------------------------------------------------ mapas */
const W=640,H=520;
let PROJ=null, BB=null;
/* Sem malha do IBGE o mapa vira de pontos: um círculo por bairro, no centroide dos
   seus setores. É a opção 4 do recorte geográfico — mantém a leitura espacial sem
   fingir uma fronteira que o IBGE não publicou. */
function pontosBounds(){
  const pts=DATA.bairros.filter(b=>b.lon!=null&&b.lat!=null);
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  pts.forEach(b=>{x0=Math.min(x0,b.lon);x1=Math.max(x1,b.lon);y0=Math.min(y0,b.lat);y1=Math.max(y1,b.lat);});
  const mx=(x1-x0)*.08||.01, my=(y1-y0)*.08||.01;
  return [x0-mx,y0-my,x1+mx,y1+my];
}
function desenhaPontos(el,{fill,raio,titulo}){
  titulo=titulo||L(metric);
  const pts=DATA.bairros.filter(b=>b.lon!=null&&b.lat!=null);
  if(!pts.length){el.innerHTML='<div class="note">Sem coordenadas para desenhar o mapa.</div>';return;}
  if(!BB){BB=pontosBounds();PROJ=projector(BB,W,H,26);}
  const rmax=Math.max(...pts.map(b=>raio(b)||0))||1;
  let s=`<svg class="svgmap" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">`;
  pts.slice().sort((a,b)=>(raio(b)||0)-(raio(a)||0)).forEach(b=>{
    const q=PROJ(b.lon,b.lat), r=5+20*Math.sqrt(Math.max(0,raio(b)||0)/rmax);
    s+=`<circle cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="${r.toFixed(1)}"
        style="fill:${fill(b)};fill-opacity:.8;stroke:#fff;stroke-width:1" data-b="${b.Bairro.replace(/"/g,'&quot;')}"></circle>`;
  });
  s+='</svg>';
  el.innerHTML=s;
  el.querySelectorAll('circle').forEach(c=>{
    c.onmousemove=e=>{const b=byB[c.dataset.b];
      showTip(e,`<b>${c.dataset.b}</b><br><span class="m">${titulo}</span><br>índice ${f1(b[metric])} · ${b.setores} setores`+
        (DATA.votes22.suprimido?'':`<br><span class="yr y22">2022</span> ${fmt(b.votos22)} votos`));};
    c.onmouseleave=hideTip;
  });
}
function desenhaMapa(el,{fill,tipo,circles,sel,pfill,praio,ptitulo}={}){
  if(!DATA.geojson){ desenhaPontos(el,{fill:pfill||(b=>colorFor(b[metric])),
      raio:praio||(b=>b.setores), titulo:ptitulo||L(metric)}); return; }
  if(!BB){BB=bounds(DATA.geojson);PROJ=projector(BB,W,H,10);}
  let s=`<svg class="svgmap" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">`;
  DATA.geojson.features.forEach(f=>{
    const p=f.properties;
    s+=`<path d="${pathD(f.geometry,PROJ)}" fill="${fill(p)}" data-b="${p.bairro.replace(/"/g,'&quot;')}"`+
       `${sel&&sel(p)?' class="sel"':''}></path>`;
  });
  if(circles){
    const mx=Math.max(...circles.map(c=>c[2]))||1;
    circles.forEach(c=>{ const q=PROJ(c[1],c[0]);
      s+=`<circle cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="${(3+16*Math.sqrt(c[2]/mx)).toFixed(1)}" data-c="${c[3].replace(/"/g,'&quot;')}"></circle>`;});
  }
  s+='</svg>';
  el.innerHTML=s;
  el.querySelectorAll('path').forEach(p=>{
    p.onmousemove=e=>{const b=byB[p.dataset.b];
      showTip(e, b ? `<b>${p.dataset.b}</b><br><span class="m">${L(metric)}</span><br>índice ${f1(b[metric])} · ${b.setores} setores<br>Lohanna 2022: ${fmt(b.votos22)}`
                   : `<b>${p.dataset.b}</b><br><span class="m">sem dado nesta base</span>`);};
    p.onmouseleave=hideTip;
  });
  el.querySelectorAll('circle').forEach(c=>{
    c.onmousemove=e=>{const b=byB[c.dataset.c];
      showTip(e,`<b>${c.dataset.c}</b><br><span class="m">Lohanna · 2022</span><br>${fmt(b?b.votos22:null)} votos`);};
    c.onmouseleave=hideTip;
  });
}

/* --------------------------------------------------------- seletor */
(function(){
  const sel=document.getElementById('selMetric');
  DATA.eixos.forEach(e=>{
    const og=document.createElement('optgroup'); og.label=e.nome;
    const o=new Option(L(e.k)+' — agregado', e.k); og.appendChild(o);
    e.membros.forEach(m=>og.appendChild(new Option('· '+L(m), m)));
    sel.appendChild(og);
  });
  if(DATA.labels.sup){
    const og=document.createElement('optgroup'); og.label='Combinações herdadas do painel de BH';
    og.appendChild(new Option(L('sup'),'sup')); sel.appendChild(og);
  }
  sel.value=metric;
  sel.onchange=()=>{metric=sel.value;render();};
})();

/* ------------------------------------------------------------ cards */
function cards(){
  const v22=DATA.votes22, v24=DATA.votes24, c=v24&&v24.candidato;
  // O líder por pauta respeita o mesmo filtro de robustez dos rankings: um bairro
  // com 3 setores pode encabeçar por ruído amostral.
  const robCards=B.filter(b=>b.setores>=DATA.meta.min_setores && b[metric]!=null);
  const topM=[...robCards].sort((a,b)=>b[metric]-a[metric])[0];
  const el=[];
  if(c) el.push(`<div class="card"><h3>${DATA.apelido} — vereador · 2024</h3><div class="v">${fmt(c.votos)}</div>
    <div class="s">${c.pos}º de ${v24.n_cands} candidatos · ${f1(c.pct)}% dos votos nominais</div></div>`);
  if(!v22.suprimido){
    el.push(`<div class="card"><h3>Lohanna França — 2022</h3><div class="v">${fmt(v22.total)}</div>
      <div class="s">no município, somando ${DATA.setores.length.toLocaleString('pt-BR')} setores censitários, cada um uma única vez</div></div>`);
    el.push(`<div class="card"><h3>Bairro líder — Lohanna 2022</h3><div class="v">${v22.top_bairro.nome}</div>
      <div class="s">${fmt(v22.top_bairro.votos)} votos · região ${v22.top_bairro.regional}</div></div>`);
  }else{
    el.push(`<div class="card" style="border-top-color:#e0a800"><h3>Lohanna França — 2022</h3>
      <div class="v" style="color:#a07800">suprimida</div>
      <div class="s">a contagem de votos deste município está fora de escala e não é exibida; ver ressalva no rodapé</div></div>`);
  }
  el.push(`<div class="card"><h3>Bairro líder — ${L(metric)}</h3><div class="v">${topM?topM.Bairro:'—'}</div>
    <div class="s">índice ${topM?f1(topM[metric]):'—'} · ${topM?topM.setores:0} setores · mínimo ${DATA.meta.min_setores} setores</div></div>`);
  el.push(`<div class="card"><h3>Base territorial</h3><div class="v">${B.length} bairros</div>
    <div class="s">${DATA.regionais.length} regiões · ${DATA.meta.setores_observados} setores mapeados${DATA.meta.cobertura?` (${f1(DATA.meta.cobertura)}% dos declarados)`:''}</div></div>`);
  document.getElementById('cards').innerHTML=el.join('');
}

/* --------------------------------------------------------- insights */
function spearman(xs,ys){
  const rk=a=>{const s=a.map((v,i)=>[v,i]).sort((p,q)=>p[0]-q[0]);const r=Array(a.length);
    let i=0;while(i<s.length){let j=i;while(j+1<s.length&&s[j+1][0]===s[i][0])j++;
      const m=(i+j)/2+1;for(let k=i;k<=j;k++)r[s[k][1]]=m;i=j+1;}return r;};
  const rx=rk(xs),ry=rk(ys),n=xs.length;
  const mx=rx.reduce((a,b)=>a+b,0)/n, my=ry.reduce((a,b)=>a+b,0)/n;
  let num=0,dx=0,dy=0;
  for(let i=0;i<n;i++){const a=rx[i]-mx,b=ry[i]-my;num+=a*b;dx+=a*a;dy+=b*b;}
  return dx&&dy?num/Math.sqrt(dx*dy):0;
}
function insights(){
  const rob=B.filter(b=>b.setores>=DATA.meta.min_setores);
  const out=[];
  const semV=DATA.votes22.suprimido;
  if(!semV){
  const rho=spearman(rob.map(b=>b[metric]),rob.map(b=>b.votos22));
  const forca=Math.abs(rho)<.15?'praticamente nula':Math.abs(rho)<.35?'fraca':Math.abs(rho)<.6?'moderada':'forte';
  out.push(`<div class="insight"><b>Aderência × voto de 2022:</b> a correlação de Spearman entre o índice de
    <b>${L(metric)}</b> e os votos da Lohanna em 2022 é de <b>${rho.toFixed(2).replace('.',',')}</b> — ${forca}.
    ${rho>.3?'Onde a pauta adere, o voto acompanhou: é território de consolidação.'
            :rho<-.3?'A pauta adere justamente onde o voto não chegou — é o desenho clássico de expansão.'
            :'A pauta e o voto seguem geografias distintas, o que separa as duas frentes com nitidez.'}</div>`);

  const vazio=rob.filter(b=>b[metric]>=57).sort((a,b)=>a.votos22-b.votos22).slice(0,3);
  if(vazio.length) out.push(`<div class="insight"><b>Alta aderência, voto baixo:</b>
    ${vazio.map(b=>`<b>${b.Bairro}</b> (índice ${f1(b[metric])}, ${fmt(b.votos22)} votos em 2022)`).join(', ')}.
    São os bairros onde a pauta já encontra público e a campanha ainda não converteu — prioridade de expansão.</div>`);

  const forte=[...rob].sort((a,b)=>b.votos22-a.votos22).slice(0,3);
  out.push(`<div class="insight"><b>Onde a base de 2022 está:</b>
    ${forte.map(b=>`<b>${b.Bairro}</b> (${fmt(b.votos22)})`).join(', ')} concentram
    ${f1(100*forte.reduce((s,b)=>s+b.votos22,0)/DATA.votes22.total)}% dos votos da Lohanna no município.
    A região <b>${DATA.votes22.top_regional}</b> lidera o conjunto.</div>`);
  } else {
    out.push(`<div class="warn"><b>Sem leitura de voto neste município.</b> ${DATA.votes22.motivo}
      As leituras abaixo usam apenas o índice de aderência.</div>`);
    const alto=[...rob].sort((a,b)=>b[metric]-a[metric]).slice(0,3);
    const baixo=[...rob].sort((a,b)=>a[metric]-b[metric]).slice(0,3);
    out.push(`<div class="insight"><b>Onde ${L(metric)} adere mais:</b>
      ${alto.map(b=>`<b>${b.Bairro}</b> (${f1(b[metric])})`).join(', ')} — território natural desta pauta.</div>`);
    out.push(`<div class="insight"><b>Onde adere menos:</b>
      ${baixo.map(b=>`<b>${b.Bairro}</b> (${f1(b[metric])})`).join(', ')} — exigem outra porta de entrada.</div>`);
  }

  if(DATA.votes24&&DATA.votes24.candidato&&!semV){
    const c=DATA.votes24.candidato;
    out.push(`<div class="insight"><b>As duas candidaturas em escala:</b> ${DATA.apelido} fez
      <b>${fmt(c.votos)}</b> votos para vereador em <span class="yr y24">2024</span> (${c.pos}º de ${DATA.votes24.n_cands}),
      contra <b>${fmt(DATA.votes22.total)}</b> da Lohanna para deputada em <span class="yr y22">2022</span> no mesmo
      município — ${f1(c.votos/DATA.votes22.total)}× a votação dela aqui. São pleitos e cargos diferentes: a comparação
      é de <b>tamanho de base</b>, não de desempenho, e os números nunca se somam.</div>`);
  }
  if(DATA.votes24&&DATA.votes24.candidato&&semV){
    const c=DATA.votes24.candidato;
    out.push(`<div class="insight"><b>${DATA.apelido} em <span class="yr y24">2024</span>:</b>
      <b>${fmt(c.votos)}</b> votos para vereador, ${c.pos}º de ${DATA.votes24.n_cands}.
      A comparação com a base de 2022 fica pendente da correção daquela camada.</div>`);
  }
  document.getElementById('insights').innerHTML=out.join('');
}

/* ------------------------------------------------- mapa + ranking */
let chReg=null;
function mapaRanking(){
  document.getElementById('mapTitle').textContent='Mapa por bairro — '+L(metric);
  document.getElementById('rkTitle').textContent='Ranking das regiões — '+L(metric);
  desenhaMapa(document.getElementById('map'),{fill:p=>colorFor(p[metric])});
  if(DATA.geojson && document.getElementById('showPts').checked) pontos();
  document.getElementById('legend').innerHTML =
    `<span style="font-weight:700;color:var(--navy)">Índice 0–100:</span>`+
    FAIXAS.map(([t,c])=>`<span><i style="background:${c}"></i>${t}</span>`).join('');

  const regs=[...DATA.regionais].sort((a,b)=>b[metric]-a[metric]);
  const ctx=document.getElementById('chReg');
  if(chReg) chReg.destroy();
  chReg=new Chart(ctx,{type:'bar',data:{labels:regs.map(r=>r.regional),
    datasets:[{label:L(metric),data:regs.map(r=>r[metric]),
      backgroundColor:regs.map(r=>colorFor(r[metric]))}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},
      tooltip:{callbacks:{label:c=>`índice ${f1(c.raw)} · ${DATA.regionais.find(r=>r.regional===c.label).setores} setores`}}},
      scales:{x:{beginAtZero:true,max:100,title:{display:true,text:'índice percentílico 0–100'}},
              y:{ticks:{autoSkip:false,font:{size:11}}}}}});
}
function pontos(){
  const svg=document.querySelector('#map svg'); if(!svg||!PROJ) return;
  const i=DATA.mk.indexOf(metric); const ns='http://www.w3.org/2000/svg';
  DATA.setores.forEach(s=>{
    const v=s[4+i]; const q=PROJ(s[1],s[0]);
    const c=document.createElementNS(ns,'circle');
    c.setAttribute('cx',q[0].toFixed(1));c.setAttribute('cy',q[1].toFixed(1));c.setAttribute('r',1.7);
    c.setAttribute('style',`fill:${colorFor(v)};fill-opacity:.85;stroke:#fff;stroke-width:.3`);
    svg.appendChild(c);
  });
}
document.getElementById('showPts').onchange=mapaRanking;

/* ------------------------------------------------- desempenho 2024 */
function v24(){
  const v=DATA.votes24, box=document.getElementById('v24');
  if(!v){document.getElementById('pV24').style.display='none';return;}
  const c=v.candidato;
  let h=`<div class="note"><b>Granularidade municipal.</b> O arquivo do TSE recebido traz o total de cada
    candidato no município inteiro — não há votos por seção, local de votação, zona ou bairro. Por isso esta
    seção é um bloco de contexto, e não o acordeão por região que o painel de 2022 tem logo abaixo.
    Com o arquivo por local de votação, ela vira camada de mapa.</div>`;
  h+=`<div class="big">
    <div class="p"><div class="k">Votos de ${DATA.apelido} · 2024</div><div class="n">${fmt(c.votos)}</div>
      <div class="d">${f1(c.pct)}% dos ${fmt(v.total_nominal)} votos nominais a vereador</div></div>
    <div><div class="k">Colocação</div><div class="n">${c.pos}º</div><div class="d">entre ${v.n_cands} candidatos</div></div>
    <div><div class="k">Locais com voto</div><div class="n">${fmt(c.locais)}</div><div class="d">de ${fmt(v.n_locais)} no município</div></div>
    <div><div class="k">Seções com voto</div><div class="n">${fmt(c.secoes)}</div><div class="d">de ${fmt(v.n_secoes)} no município</div></div>
    <div><div class="k">Capilaridade</div><div class="n">${f1(100*c.locais/v.n_locais)}%</div>
      <div class="d">dos locais de votação tiveram ao menos um voto seu</div></div></div>`;
  const mx=v.mais_votados[0].votos;
  h+=`<h3 style="font-size:.85rem;color:var(--navy);margin:14px 0 8px;">Os 15 vereadores mais votados em ${DATA.municipio} <span class="yr y24">2024</span></h3>`;
  h+=v.mais_votados.map(r=>{
    const eu=r.nr===String(DATA.numero);
    return `<div class="crow"${eu?' style="background:#fdf3f8"':''}>
      <span class="n">${r.pos}</span>
      <span class="nm"${eu?' style="font-weight:800;color:var(--pink)"':''}>${r.nome}</span>
      <span class="pt">${r.nr}</span>
      <span class="bar" style="width:${(120*r.votos/mx).toFixed(0)}px"></span>
      <span class="v">${fmt(r.votos)}</span><span class="pc">${f1(r.pct)}%</span></div>`;}).join('');
  if(v.prefeito&&v.prefeito.length)
    h+=`<p style="font-size:.76rem;color:var(--muted);margin-top:12px;">Contexto — prefeito eleito em 2024:
      <b>${v.prefeito[0].nome}</b> (${fmt(v.prefeito[0].votos)} votos).</p>`;
  box.innerHTML=h;
}

/* ------------------------------------------- desempenho 2022 (acordeão) */
function v22(){
  if(DATA.votes22.suprimido){
    document.getElementById('mapV').innerHTML='';
    document.getElementById('vAccord').innerHTML=
      `<div class="warn"><b>Camada de 2022 suprimida neste município.</b> ${DATA.votes22.motivo}
       <br><br>As pautas e o índice de aderência continuam válidos e são exibidos normalmente —
       o que está suprimido é apenas a contagem de votos, que seria enganosa.</div>`;
    return;
  }
  const comCirc=document.getElementById('tgCirc').checked;
  desenhaMapa(document.getElementById('mapV'),{
    fill:p=>p.votos22==null?'#e6e9f2':colorFor(null),
    circles:comCirc?DATA.votes22.circ:null,
    // Sem malha, o próprio ponto carrega o voto: rosa, dimensionado pela votação.
    pfill:()=>PINK, praio:b=>comCirc?(b.votos22||0):0.0001,
    ptitulo:'Lohanna · 2022'});
  const V=DATA.votes22, mx=Math.max(...V.regionais.map(r=>r.votos))||1;
  document.getElementById('vAccord').innerHTML=V.regionais.map((r,i)=>{
    const mb=Math.max(...r.bairros.map(b=>b.v))||1;
    return `<div class="vreg${i===0?' lead open':''}">
      <div class="vhead" onclick="this.parentNode.classList.toggle('open')">
        <span class="nm">${r.regional}</span>
        <span class="vb"><i style="width:${(100*r.votos/mx).toFixed(1)}%"></i></span>
        <span class="vt">${fmt(r.votos)}</span>
        <span class="cx">${r.setores} set.</span>${i===0?'<span class="badge">líder</span>':''}</div>
      <div class="vlist">${r.bairros.map((b,j)=>`<div class="vrow${j===0?' lead2':''}">
        <span class="n">${j+1}</span><span class="b">${b.b}</span>
        <span class="bar2" style="width:${(90*b.v/mb).toFixed(0)}px"></span>
        <span class="v">${fmt(b.v)}</span></div>`).join('')}</div></div>`;}).join('');
}
document.getElementById('tgCirc').onchange=v22;

/* ------------------------------------------------------ sobreposição */
function over(){
  const box=document.getElementById('over');
  if(DATA.votes24 && DATA.votes24.granularidade!=='municipal'){ box.innerHTML='<div class="note">—</div>'; return; }
  box.innerHTML=`<div class="warn"><b>Seção indisponível nesta versão.</b> A comparação território a território
    entre a base de <span class="yr y24">2024</span> e a de <span class="yr y22">2022</span> — com scatter,
    correlação de Spearman e os quatro quadrantes (base comum, território do candidato, território da Lohanna e
    vazio compartilhado) — exige as duas camadas na mesma unidade geográfica.
    A camada de 2022 está por setor censitário, agregada a bairro. A de 2024 chegou apenas com o total municipal.
    <br><br>Assim que o arquivo do TSE vier por <b>local de votação</b>, esta seção e a frente de
    <b>Reciprocidade</b> do plano de mobilização entram sem nenhuma outra mudança —
    o restante do painel já está montado sobre a unidade correta.
    <br><br>Conforme a regra de não inventar dado, o bloco fica visível e vazio em vez de preenchido por estimativa.</div>`;
}

/* ------------------------------------------------------- mobilização */
function mob(){
  const M=DATA.mob;
  document.getElementById('mobLogica').innerHTML=
   `<div class="insight"><b>Frente 1 – Consolidação (azul-marinho):</b> score = ${M.pesos.cons}.
      ${DATA.votes22.suprimido?'Onde a pauta adere com mais força':'Onde a base de <span class="yr y22">2022</span> já existe e a pauta adere'}: <b>volume e visibilidade</b> —
      panfletagem de alto fluxo, adesivaço, presença em pontos de concentração.</div>
    <div class="insight"><b>Frente 2 – Expansão (rosa):</b> score = ${M.pesos.exp}.
      Onde a pauta adere e o voto não chegou: <b>abrir território</b> — lideranças locais primeiro,
      rodas de conversa, recorrência semanal em vez de um evento único.</div>
    <div class="note"><b>Frente 3 – Reciprocidade</b> (território forte de uma candidatura e fraco da outra)
      depende da camada de 2024 por local de votação e por isso não entra nesta versão.</div>`;

  const alvo=new Set([...M.cons,...M.exp].map(x=>x.b));
  const cons=new Set(M.cons.map(x=>x.b));
  desenhaMapa(document.getElementById('mapM'),{
    fill:p=>alvo.has(p.bairro)?(cons.has(p.bairro)?NAVY:PINK):'#e6e9f2',
    sel:p=>alvo.has(p.bairro),
    pfill:b=>alvo.has(b.Bairro)?(cons.has(b.Bairro)?NAVY:PINK):'#c9cee0',
    praio:b=>alvo.has(b.Bairro)?b.setores:0.15*b.setores});
  const bloco=(t,cls,arr,campo)=>`<div class="front ${cls}"><h3>${t}
      <span class="sub">${arr.length} bairros</span></h3>
      ${arr.map((x,i)=>`<div class="trow"><span class="n">${i+1}</span>
        <div class="info"><b>${x.b}</b><span class="rg">${x.reg}</span>
          <div class="anc">ens. superior <em>${f1(x.sup)}</em> · LGBT <em>${f1(x.lgbt)}</em> ·
            gênero <em>${f1(x.gen)}</em> · antirracismo <em>${f1(x.rac)}</em><br>
${DATA.votes22.suprimido?'':`<span class="yr y22">2022</span> ${fmt(x.votos22)} votos · `}${x.setores} setores</div></div>
        <span class="sc">${f1(x[campo])}</span></div>`).join('')}</div>`;
  document.getElementById('lists').innerHTML=
    bloco('Consolidação','cons',M.cons,'cons')+bloco('Expansão','exp',M.exp,'exp');
}

/* ------------------------------------------------- gráficos por eixo */
const chs=[];
function graficos(){
  const box=document.getElementById('charts'); box.innerHTML='';
  chs.forEach(c=>c.destroy()); chs.length=0;
  const paleta=[NAVY,PINK,'#d97fae','#5b6a99','#8f1f57','#aeb6d0'];
  Object.entries(DATA.quebras).forEach(([k,q],n)=>{
    const id='ch_'+k;
    box.insertAdjacentHTML('beforeend',
      `<div class="panel"><h2>${q.titulo}: as ${q.vars.length} pautas por região</h2>
       <div class="body"><canvas id="${id}"></canvas></div></div>`);
    chs.push(new Chart(document.getElementById(id),{type:'bar',
      data:{labels:q.regionais,datasets:q.vars.map((v,i)=>({label:v,
        data:q.values.map(r=>r[i]),backgroundColor:paleta[i%paleta.length]}))},
      options:{responsive:true,plugins:{legend:{position:'bottom',
        labels:{boxWidth:11,font:{size:10}}},
        tooltip:{callbacks:{label:c=>`${c.dataset.label}: ${f1(c.raw)}`}}},
        scales:{y:{beginAtZero:true,max:100,title:{display:true,text:'índice 0–100'}},
                x:{ticks:{autoSkip:false,maxRotation:0,minRotation:0,font:{size:10}}}}}}));
  });
}

/* ------------------------------------------------------- tabela */
let sortK=DATA.votes22.suprimido?'setores':'votos22', sortD=-1;
const COLS=()=>[['Bairro','Bairro'],['regional','Região'],
  ...DATA.eixos.map(e=>[e.k,e.nome.split(' ')[0]]),
  ...(DATA.votes22.suprimido?[]:[['votos22','Lohanna 2022']]),['setores','Set.']];
function tabela(){
  const head=document.getElementById('tbHead');
  head.innerHTML=COLS().map(([k,t])=>`<th data-k="${k}">${t} <span class="arr">${k===sortK?(sortD<0?'▼':'▲'):''}</span></th>`).join('');
  head.querySelectorAll('th').forEach(th=>th.onclick=()=>{
    const k=th.dataset.k; if(k===sortK) sortD*=-1; else {sortK=k;sortD=-1;} tabela();});
  const fr=document.getElementById('fReg').value, mn=+document.getElementById('fMin').value;
  let rows=B.filter(b=>(!fr||b.regional===fr)&&b.setores>=mn);
  rows.sort((a,b)=>{const x=a[sortK],y=b[sortK];
    return (typeof x==='string')?sortD*x.localeCompare(y,'pt-BR'):sortD*((y??-1)-(x??-1));});
  const pill=v=>v==null?'<span class="pill pB">—</span>':
    v>=57?`<span class="pill pA">${f1(v)}</span>`:v>=43?`<span class="pill pM">${f1(v)}</span>`:`<span class="pill pB">${f1(v)}</span>`;
  document.querySelector('#tb tbody').innerHTML=rows.map(b=>`<tr>
    <td><b>${b.Bairro}</b></td><td>${b.regional}</td>
    ${DATA.eixos.map(e=>`<td>${pill(b[e.k])}</td>`).join('')}
    ${DATA.votes22.suprimido?'':`<td><b>${fmt(b.votos22)}</b></td>`}<td>${b.setores}</td></tr>`).join('');
  document.getElementById('countInfo').textContent=
    `${rows.length} bairros · classificação: alta ≥ 57 · média 43–57 · baixa < 43`;
}
document.getElementById('fReg').onchange=tabela;
document.getElementById('fMin').onchange=tabela;

/* --------------------------------------------------------- top 10 */
function tops(){
  document.getElementById('tops').innerHTML=DATA.eixos.map(e=>{
    const t=DATA.tops[e.k]||[];
    return `<div class="topcol"><h4>${e.nome}</h4><ol>${t.map(x=>
      `<li><b>${x.b}</b><span class="rg">${x.reg} · ${x.s} set.</span>
       <span style="font-weight:800;color:var(--pink)">${f1(x.i)}</span></li>`).join('')}</ol></div>`;
  }).join('');
}

/* -------------------------------------------- inteligência competitiva */
const PROG=new Set(['PT','PSOL','PDT','PV','REDE','PSB','PCDOB','UP','PSTU','PCB','PCO']);
function comp(){
  const v=DATA.votes24, box=document.getElementById('cand');
  if(!v){document.getElementById('pCand').style.display='none';return;}
  const c=v.candidato;
  const acima=v.mais_votados.filter(r=>r.pos<c.pos);
  let h=`<div class="note"><b>Recorte municipal.</b> Sem os votos por local de votação, não é possível
    dizer quem disputa o eleitorado de ${DATA.apelido} <b>bairro a bairro</b> — só quem disputa no município.
    O bloco por bairro entra junto com a seção de sobreposição.</div>`;
  h+=`<div class="insight"><b>A disputa em ${DATA.municipio} em <span class="yr y24">2024</span>:</b>
    ${fmt(v.n_cands)} candidatos a vereador dividiram ${fmt(v.total_nominal)} votos nominais.
    ${DATA.apelido} ficou em <b>${c.pos}º</b> com ${fmt(c.votos)} votos —
    ${c.pos===1?'<b>o mais votado do município</b>.':`atrás de ${acima.length} candidato${acima.length>1?'s':''}.`}
    Sua votação equivale a ${f1(c.pct)}% do total nominal, e alcançou
    ${f1(100*c.locais/v.n_locais)}% dos locais de votação.</div>`;
  const ctx=document.createElement('canvas'); ctx.id='chComp';
  box.innerHTML=h+`<h3 style="font-size:.85rem;color:var(--navy);margin:14px 0 8px;">
    Os 12 mais votados a vereador em ${DATA.municipio} <span class="yr y24">2024</span></h3>
    <div style="max-width:100%"><canvas id="chComp" height="340"></canvas></div>`;
  const top=v.mais_votados.slice(0,12);
  // Nome de urna completo estoura o eixo; o primeiro e o último nome bastam para
  // identificar, e o nome inteiro continua no tooltip.
  const curto=n=>{const p=n.split(/\s+/);return p.length<3?n:p[0]+' '+p[p.length-1];};
  new Chart(document.getElementById('chComp'),{type:'bar',
    data:{labels:top.map(r=>curto(r.nome)),
      datasets:[{label:'Votos · 2024',data:top.map(r=>r.votos),
        backgroundColor:top.map(r=>r.nr===String(DATA.numero)?PINK:NAVY)}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,
      layout:{padding:{right:10}},
      plugins:{legend:{display:false},
        tooltip:{callbacks:{title:c2=>top[c2[0].dataIndex].nome,
                            label:c2=>`${fmt(c2.raw)} votos · ${f1(top[c2.dataIndex].pct)}%`}}},
      scales:{x:{beginAtZero:true,ticks:{callback:v2=>fmt(v2)}},
              y:{ticks:{autoSkip:false,font:{size:11}}}}}});
}

/* --------------------------------------------------------- rodapé */
function foot(){
  const m=DATA.meta, f=m.fontes;
  const partes=[
    `<b>Camada ${'2022'}:</b> ${f['2022']}`,
    f['2024']?`<b>Camada 2024:</b> ${f['2024']}`:null,
    f.geo?`<b>Geometria:</b> ${f.geo}`:null,
    `<b>Unidade geográfica:</b> ${m.unidade}. ${m.unidade_por_que}`,
    `<b>Índice:</b> percentil médio do valor ajustado, normalizado por pauta, escala 0–100.`,
    `<b>Sem dupla contagem:</b> cada setor censitário entra uma única vez na soma de votos.`,
    m.cobertura?`<b>Cobertura:</b> ${m.setores_observados} de ${m.setores_declarados} setores do município (${f1(m.cobertura)}%) — os que têm endereço CNEFE correspondido. O índice descreve esses setores, não o município inteiro.`:null,
    `<b>Filtro de robustez:</b> rankings de bairro exigem ao menos ${m.min_setores} setores — ${m.min_setores_por_que}.`,
    DATA.votes22.suprimido?`<b>ATENÇÃO — camada 2022 suprimida:</b> ${DATA.votes22.motivo}`:null,
    `<b>Ressalva:</b> 2022 e 2024 são pleitos e cargos diferentes e nunca são somados. A camada de 2024 está no nível municipal nesta versão.`,
    `Painel 100% offline: nenhuma requisição a servidor externo. Coordenadas em SIRGAS 2000 (EPSG:4674), equivalentes a WGS 84 nesta escala.`,
    `Gerado em ${m.gerado_em}.`,
  ].filter(Boolean);
  document.getElementById('foot').innerHTML=partes.join(' · ');
}

/* ------------------------------------------------------------ render */
function render(){ cards(); insights(); mapaRanking(); }
(function init(){
  const fm=document.getElementById('fMin'), m=DATA.meta.min_setores;
  [[1,'todos os bairros'],[2,'≥ 2 setores'],[3,'≥ 3 setores'],[5,'≥ 5 setores'],[10,'≥ 10 setores']]
    .forEach(([v,t])=>fm.appendChild(new Option(t+(v===m?' (padrão deste município)':''),v)));
  fm.value=String(m);
  const fr=document.getElementById('fReg');
  DATA.regionais.map(r=>r.regional).sort().forEach(r=>fr.appendChild(new Option(r,r)));
  render(); v24(); v22(); over(); mob(); graficos(); tabela(); tops(); comp(); foot();
})();
