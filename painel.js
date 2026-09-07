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

/* Enquadramento do mapa. O padrão é o município inteiro — é o que garante que
   todo polígono da malha apareça. "Mancha urbana" recorta pelo percentil 2–98 dos
   centroides ponderados por setor urbano, que é o que separa a cidade dos núcleos
   isolados sem descartar nenhum polígono: o que sai do quadro fica desenhado,
   apenas fora da área visível. */
let enquadre='mun';
function centroFeat(f){
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
  const walk=c=>{ if(typeof c[0]==='number'){x0=Math.min(x0,c[0]);x1=Math.max(x1,c[0]);
      y0=Math.min(y0,c[1]);y1=Math.max(y1,c[1]);} else c.forEach(walk); };
  walk(f.geometry.coordinates);
  return [(x0+x1)/2,(y0+y1)/2];
}
function boundsUrbano(fc){
  const pts=fc.features.map(f=>[centroFeat(f), f.properties.urbano||0]).filter(p=>p[1]>0);
  const tw=pts.reduce((a,p)=>a+p[1],0);
  if(!tw) return bounds(fc);
  const faixa=i=>{const a=pts.map(p=>[p[0][i],p[1]]).sort((u,v)=>u[0]-v[0]);
    let acc=0,lo=null,hi=null;
    for(const [v,w] of a){acc+=w; if(lo===null&&acc>=.02*tw)lo=v; if(hi===null&&acc>=.98*tw)hi=v;}
    return [lo,hi===null?a[a.length-1][0]:hi];};
  const [x0,x1]=faixa(0), [y0,y1]=faixa(1);
  const mx=(x1-x0)*.10||.005, my=(y1-y0)*.10||.005;
  return [x0-mx,y0-my,x1+mx,y1+my];
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
  if(!BB){BB=(enquadre==='urb')?boundsUrbano(DATA.geojson):bounds(DATA.geojson);
          PROJ=projector(BB,W,H,10);}
  let s=`<svg class="svgmap" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">`;
  DATA.geojson.features.forEach(f=>{
    const p=f.properties;
    s+=`<path d="${pathD(f.geometry,PROJ)}" fill="${fill(p)}" data-b="${p.bairro.replace(/"/g,'&quot;')}"`+
       `${sel&&sel(p)?' class="sel"':''}></path>`;
  });
  /* `circles` é uma lista de CAMADAS: cada uma com seus pontos, sua cor e seu
     rótulo, e cada uma escalada pelo próprio máximo — o raio compara bairros
     dentro de um ano, nunca um ano com o outro, que têm cargos diferentes. */
  (circles||[]).forEach(cam=>{
    if(!cam || !cam.pts || !cam.pts.length) return;
    const mx=Math.max(...cam.pts.map(c=>c[2]))||1;
    [...cam.pts].sort((a,b)=>b[2]-a[2]).forEach(c=>{ const q=PROJ(c[1],c[0]);
      s+=`<circle cx="${q[0].toFixed(1)}" cy="${q[1].toFixed(1)}" r="${(3+16*Math.sqrt(c[2]/mx)).toFixed(1)}"`+
         ` style="fill:${cam.cor};fill-opacity:.42;stroke:${cam.cor};stroke-width:1.2;stroke-opacity:.9"`+
         ` data-c="${c[3].replace(/"/g,'&quot;')}" data-v="${c[2]}" data-l="${cam.rot}"></circle>`;});
  });
  s+='</svg>';
  el.innerHTML=s;
  el.querySelectorAll('path').forEach(p=>{
    p.onmousemove=e=>{const b=byB[p.dataset.b];
      showTip(e, b ? `<b>${p.dataset.b}</b><br><span class="m">${L(metric)}</span><br>índice ${f1(b[metric])} · ${b.setores} setores<br>Lohanna 2022: ${fmt(b.votos22)}`
                   : `<b>${p.dataset.b}</b><br><span class="m">sem dado nesta base</span>`);};
    p.onmouseleave=hideTip;
  });
  el.querySelectorAll('circle').forEach(c=>{
    c.onmousemove=e=>showTip(e,`<b>${c.dataset.c}</b><br><span class="m">${c.dataset.l}</span><br>`+
      `${fmt(+c.dataset.v)} votos`);
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
    <div class="s">${c.pos}º de ${v24.n_cands} candidatos · ${f1(c.pct)}% dos votos nominais${
      c.vence_em!=null?` · 1º lugar em ${c.vence_em} de ${c.locais} locais`:''}</div></div>`);
  if(!v22.suprimido){
    el.push(`<div class="card"><h3>Lohanna França — 2022</h3><div class="v">${fmt(v22.total)}</div>
      <div class="s">${v22.granularidade==='local de votação'
        ? `para <b>${v22.cargo}</b>, somando os ${fmt(v22.n_locais)} locais de votação do município, cada seção uma única vez`
        : `no município, somando ${DATA.setores.length.toLocaleString('pt-BR')} setores censitários, cada um uma única vez`}</div></div>`);
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

/* ------------------------------- as duas eleições, na mesma unidade: o bairro */
/* Antes eram duas seções: "Desempenho eleitoral — Vereador 2024", que listava
   local de votação por local de votação, e "Desempenho da Lohanna — Deputada
   2022", que listava região e bairro. Duas unidades diferentes para a mesma
   pergunta. Aqui as duas viram uma coisa só: cada local de votação é situado no
   seu bairro pela coordenada oficial do TSE, os votos são somados por bairro nos
   dois anos, e as camadas ficam lado a lado — sem nunca serem somadas entre si,
   porque são cargos e pleitos diferentes. */

const CAM = DATA.camadas || null;
const CORES = {c22:PINK, c24:NAVY};
/* Rampas sequenciais, uma por camada. A faixa é a razão para o maior bairro
   daquele ano: cada camada é lida na própria escala. */
const RAMPA22=['#fbeaf2','#f2c2d9','#e28cb8','#cf5896','#a32c6c'];
const RAMPA24=['#e9ecf5','#c3cbe1','#8f9dc5','#5769a1','#293e76'];
/* Precisa destoar do fundo do SVG (#eef1f7): senão o bairro sem voto some e o
   mapa parece esburacado, quando na verdade a malha cobre o município inteiro. */
const SEMDADO='#dbe0ec';
let camFill='24', camOn={'22':true,'24':true};

function corCamada(v,mx,rampa){
  if(v==null||!mx) return SEMDADO;
  if(v<=0) return SEMDADO;
  const r=v/mx;
  return rampa[r<.05?0:r<.15?1:r<.35?2:r<.65?3:4];
}

function camMapa(){
  const el=document.getElementById('mapCam'); if(!el||!CAM) return;
  const porB=Object.fromEntries(CAM.bairros.map(x=>[x.b,x]));
  const usa22 = camFill==='22' && CAM.tem22;
  const usa24 = camFill==='24' && CAM.tem24;
  const mx = usa22?CAM.max22:usa24?CAM.max24:0;
  const rampa = usa22?RAMPA22:RAMPA24;
  const camadas=[];
  if(CAM.tem22 && camOn['22'])
    camadas.push({pts:CAM.circ22, cor:CORES.c22, rot:'Lohanna · Deputada 2022'});
  if(CAM.tem24 && camOn['24'])
    camadas.push({pts:CAM.circ24, cor:CORES.c24, rot:`${DATA.apelido} · Vereador 2024`});

  desenhaMapa(el,{
    fill:p=>{
      if(!usa22&&!usa24) return SEMDADO;
      const x=porB[p.bairro];
      return corCamada(x?(usa22?x.v22:x.v24):null, mx, rampa);
    },
    circles:camadas,
    // Sem malha o mapa cai para pontos; o raio então carrega o voto da camada escolhida.
    pfill:()=>usa22?CORES.c22:CORES.c24,
    praio:b=>{const x=porB[b.Bairro]; return x?((usa22?x.v22:x.v24)||0):0;},
    ptitulo:usa22?'Lohanna · 2022':`${DATA.apelido} · 2024`});

  const leg=document.getElementById('camLeg');
  if(!leg) return;
  const nome = usa22?'votos da Lohanna · 2022':usa24?`votos de ${DATA.apelido} · 2024`:null;
  let h='';
  if(nome){
    h+=`<span style="font-weight:700;color:var(--navy)">Cor do bairro — ${nome}:</span>`;
    const rot=['até 5%','5–15%','15–35%','35–65%','65–100%'];
    h+=rampa.map((c,i)=>`<span><i style="background:${c}"></i>${rot[i]}</span>`).join('');
    h+=`<span><i style="background:${SEMDADO}"></i>sem voto</span>`;
    h+=`<span style="opacity:.8">(% do bairro mais votado, ${fmt(mx)} votos)</span>`;
  }else{
    h+=`<span style="font-weight:700;color:var(--navy)">Polígonos sem pintura</span>`
      +`<span style="opacity:.8">— só os círculos carregam o voto</span>`;
  }
  if(camadas.length) h+=camadas.map(c=>
    `<span><i style="background:${c.cor};opacity:.5;border-radius:50%"></i>círculo · ${c.rot}</span>`).join('');
  leg.innerHTML=h;
}

function camLinha(x,i,mx22,mx24){
  const cel=(v,cls,mx,bcls)=>{
    if(v==null) return `<div class="cel"><span class="q zero">—</span></div>`;
    return `<div class="cel"><span class="q ${v?cls:'zero'}">${fmt(v)}</span>
      <span class="cambar"><i class="${bcls}" style="width:${mx?Math.max(v?2:0,Math.round(70*v/mx)):0}px"></i></span></div>`;
  };
  return `<div class="crow2"><span class="n">${i+1}</span>
    <span class="b" title="${x.b.replace(/"/g,'&quot;')}">${x.b}</span>
    ${cel(x.v22,'q22',mx22,'b22')}${cel(x.v24,'q24',mx24,'b24')}</div>`;
}

function camAcordeao(){
  const box=document.getElementById('camAccord'); if(!box||!CAM) return;
  const mx22=CAM.max22, mx24=CAM.max24;
  const topReg=Math.max(...CAM.regionais.map(r=>CAM.tem24?r.v24:r.v22))||1;
  box.innerHTML=`<div class="camhead"><span class="n">#</span><span>Bairro</span>
      <span style="text-align:left">Lohanna 2022</span>
      <span style="text-align:left">${DATA.apelido} 2024</span></div>`
    + CAM.regionais.map((r,i)=>{
    const total=CAM.tem24?r.v24:r.v22;
    return `<div class="vreg${i===0?' lead open':''}">
      <div class="vhead" onclick="this.parentNode.classList.toggle('open')">
        <span class="nm">${r.regional}</span>
        <span class="vb"><i style="width:${(100*total/topReg).toFixed(1)}%"></i></span>
        <span class="vt">${fmt(total)}</span>
        <span class="cx">${r.n} bairro${r.n===1?'':'s'}</span>${i===0?'<span class="badge">líder</span>':''}</div>
      <div class="vlist">${r.bairros.map((b,j)=>camLinha(b,j,mx22,mx24)).join('')}</div></div>`;
  }).join('');
}

function cam(){
  const box=document.getElementById('cam'); if(!box) return;
  if(!CAM){ document.getElementById('pCam').style.display='none'; return; }
  const v22=DATA.votes22, v24=DATA.votes24, c=v24&&v24.candidato;

  let h='';
  if(v22.suprimido)
    h+=`<div class="warn"><b>Camada de 2022 suprimida neste município.</b> ${v22.motivo}
        A coluna de 2022 aparece vazia; a de 2024 continua íntegra.</div>`;
  h+=`<div class="note"><b>Uma seção, duas eleições, a mesma unidade.</b>
      Os votos dos dois anos estão organizados <b>por bairro</b>, não por seção eleitoral:
      cada seção do TSE é contada uma única vez, somada ao seu local de votação, e o local é
      situado no bairro pela coordenada oficial do TSE. É o que torna as duas camadas
      comparáveis — <span class="yr y22">2022</span> era ${CAM.cargo22} e
      <span class="yr y24">2024</span> foi vereador, cargos e pleitos diferentes, por isso os
      números ficam <b>lado a lado e nunca somados</b>.
      ${CAM.tem22&&CAM.total22?`Dos ${fmt(CAM.total22)} votos da Lohanna, ${fmt(CAM.soma22)} caem num bairro identificado`:''}${
        CAM.tem24&&CAM.total24?`${CAM.tem22&&CAM.total22?'; dos':'Dos'} ${fmt(CAM.total24)} de ${DATA.apelido}, ${fmt(CAM.soma24)}`:''}${
        (CAM.tem22||CAM.tem24)?' — o restante está em locais sem coordenada na fonte e não é rateado.':''}</div>`;

  h+=`<div class="big">`;
  if(!v22.suprimido)
    h+=`<div class="p"><div class="k">Lohanna · ${CAM.cargo22} 2022</div><div class="n">${fmt(v22.total)}</div>
        <div class="d">em ${CAM.n_com22} dos ${CAM.n_bairros} bairros · ${fmt(v22.n_locais_com_voto)} de ${fmt(v22.n_locais)} locais com voto</div></div>`;
  if(c)
    h+=`<div><div class="k">${DATA.apelido} · Vereador 2024</div><div class="n">${fmt(c.votos)}</div>
        <div class="d">${c.pos}º de ${v24.n_cands} · ${f1(c.pct)}% dos ${fmt(v24.total_nominal)} votos nominais</div></div>`;
  if(CAM.tem22){
    const top=[...CAM.bairros].sort((a,b)=>(b.v22||0)-(a.v22||0))[0];
    h+=`<div class="p"><div class="k">Bairro líder · 2022</div><div class="n">${top?top.b:'—'}</div>
        <div class="d">${top?fmt(top.v22):'—'} votos${top&&top.reg?` · região ${top.reg}`:''}</div></div>`;
  }
  if(CAM.tem24){
    const top=[...CAM.bairros].sort((a,b)=>(b.v24||0)-(a.v24||0))[0];
    h+=`<div><div class="k">Bairro líder · 2024</div><div class="n">${top?top.b:'—'}</div>
        <div class="d">${top?fmt(top.v24):'—'} votos${top&&top.reg?` · região ${top.reg}`:''}</div></div>`;
  }
  if(CAM.tem22&&CAM.tem24){
    const ambos=CAM.bairros.filter(x=>(x.v22||0)>0&&(x.v24||0)>0).length;
    h+=`<div><div class="k">Bairros em comum</div><div class="n">${ambos}</div>
        <div class="d">receberam voto nas duas eleições, de ${CAM.n_bairros} bairros do município</div></div>`;
  }
  h+=`</div>`;

  /* --- controles do mapa: um botão por camada de círculos --- */
  h+=`<div class="camctl"><span class="lbl">Círculos de votos por bairro</span>`;
  if(CAM.tem22)
    h+=`<button type="button" class="tgb on" id="tg22" style="--tgc:${PINK}" aria-pressed="true">
        <i></i>Lohanna · Deputada 2022</button>`;
  if(CAM.tem24)
    h+=`<button type="button" class="tgb on" id="tg24" style="--tgc:${NAVY}" aria-pressed="true">
        <i></i>${DATA.apelido} · Vereador 2024</button>`;
  h+=`<label for="camFill" style="margin-left:6px">Pintar bairros por:</label>
      <select id="camFill">
        ${CAM.tem24?`<option value="24">votos de ${DATA.apelido} · 2024</option>`:''}
        ${CAM.tem22?`<option value="22">votos da Lohanna · 2022</option>`:''}
        <option value="">nenhum (só o contorno)</option>
      </select></div>`;

  h+=`<div class="grid2" style="margin-bottom:0;">
        <div><div id="mapCam"></div><div class="maplegend" id="camLeg"></div></div>
        <div id="camAccord" style="max-height:560px;overflow:auto;border:1.5px solid #e3e6f0;border-radius:10px;"></div>
      </div>`;

  /* --- ranking municipal de 2024, que não é por bairro e continua útil --- */
  if(v24&&v24.mais_votados&&v24.mais_votados.length){
    const mx=v24.mais_votados[0].votos;
    h+=`<h3 class="hsec">Os ${v24.mais_votados.length} vereadores mais votados em ${DATA.municipio}
        <span class="yr y24">2024</span></h3>`;
    h+=v24.mais_votados.map(r=>{
      const eu=r.nr===String(DATA.numero);
      return `<div class="crow"${eu?' style="background:#fdf3f8"':''}>
        <span class="n">${r.pos}</span>
        <span class="nm"${eu?' style="font-weight:800;color:var(--pink)"':''}>${r.nome}</span>
        <span class="pt">${r.nr}</span>
        <span class="bar" style="width:${(120*r.votos/mx).toFixed(0)}px"></span>
        <span class="v">${fmt(r.votos)}</span><span class="pc">${f1(r.pct)}%</span></div>`;}).join('');
  }

  /* --- o detalhe por local de votação vira anexo: a organização principal é o bairro --- */
  const det=[];
  if(v24&&v24.locais&&v24.locais.length) det.push(['24',`${DATA.apelido} · 2024`,v24.locais]);
  if(v22.locais&&v22.locais.length&&!v22.suprimido) det.push(['22','Lohanna · 2022',v22.locais]);
  if(det.length){
    h+=`<details class="camdet"><summary>Detalhe por local de votação (a unidade bruta do TSE, antes da soma por bairro)</summary>
        <div class="in"><div class="note" style="margin-top:8px">O bairro é a unidade de leitura deste painel.
        Esta lista fica aqui como rastro da apuração: é dela que os números por bairro saem, somando cada
        local ao bairro em que sua coordenada cai.</div>`;
    det.forEach(([ano,rot,L])=>{
      const mx=Math.max(...L.map(x=>x.v))||1;
      h+=`<h3 class="hsec">${rot} — ${L.length} locais</h3>
          <div style="max-height:300px;overflow:auto;border:1.5px solid #e3e6f0;border-radius:8px;">`;
      L.forEach((x,i)=>{
        h+=`<div class="vrow" style="padding:6px 11px;align-items:center;">
          <span class="n">${i+1}</span>
          <div style="flex:1;min-width:0;">
            <b style="color:var(--navy)">${x.nome}</b>
            <div style="font-size:.7rem;color:var(--muted);margin-top:1px;">${x.end||''}${x.zona?` · zona ${x.zona}`:''}${x.b?` · bairro ${x.b}`:' · sem bairro atribuído'}</div>
          </div>
          <span class="bar2" style="width:${(60*x.v/mx).toFixed(0)}px"></span>
          <span class="v" style="min-width:56px">${fmt(x.v)}</span></div>`;
      });
      h+=`</div>`;
    });
    h+=`</div></details>`;
  }

  if(v24&&v24.prefeito&&v24.prefeito.length)
    h+=`<p style="font-size:.76rem;color:var(--muted);margin-top:12px;">Contexto — prefeito eleito em 2024:
      <b>${v24.prefeito[0].nome}</b> (${fmt(v24.prefeito[0].votos)} votos).</p>`;

  box.innerHTML=h;

  const btn=(id,k)=>{const b=document.getElementById(id); if(!b) return;
    b.onclick=()=>{camOn[k]=!camOn[k];
      b.classList.toggle('on',camOn[k]); b.classList.toggle('off',!camOn[k]);
      b.setAttribute('aria-pressed',String(camOn[k])); camMapa();};};
  btn('tg22','22'); btn('tg24','24');
  const sf=document.getElementById('camFill');
  if(sf){ camFill = CAM.tem24?'24':(CAM.tem22?'22':''); sf.value=camFill;
          sf.onchange=()=>{camFill=sf.value;camMapa();}; }
  camMapa(); camAcordeao();
}

/* ------------------------------------------------------ sobreposição */
const QUAD={
  comum:  {cor:'#5B3A8E', nome:'Base comum',            desc:'a Lohanna teve voto e o aliado também — o território onde as duas candidaturas já se sobrepõem'},
  cand:   {cor:NAVY,      nome:'Território do aliado',  desc:'forte para o aliado em 2024 e fraco para a Lohanna em 2022 — onde ele pode entregar voto'},
  lohanna:{cor:PINK,      nome:'Território da Lohanna', desc:'forte para a Lohanna em 2022 e fraco para o aliado — onde ela pode entregar voto'},
  vazio:  {cor:'#9aa2bb', nome:'Vazio compartilhado',   desc:'nenhuma das duas chegou — expansão de fato, e a mais cara'}
};
function over(){
  const box=document.getElementById('over'), o=DATA.over, v=DATA.votes24;
  if(!o){
    box.innerHTML = (v && v.granularidade==='local de votação')
     ? `<div class="warn"><b>Seção indisponível neste município.</b> A camada de
        <span class="yr y24">2024</span> está por local de votação, mas não foi possível
        situar os locais nos bairros — sem isso as duas camadas não caem na mesma unidade
        geográfica. Conforme a regra de não inventar dado, o bloco fica vazio em vez de
        preenchido por estimativa.</div>`
     : `<div class="warn"><b>Seção indisponível neste município.</b> A comparação território a
        território exige as duas camadas na mesma unidade geográfica: a de 2022 está por setor
        censitário agregado a bairro, e a de 2024 não chegou por local de votação.
        ${DATA.votes22.suprimido?'Além disso, a camada de 2022 está suprimida aqui.':''}</div>`;
    return;
  }
  const r=o.spearman;
  const forca = r==null?'—':Math.abs(r)>=.7?'forte':Math.abs(r)>=.4?'moderada':Math.abs(r)>=.2?'fraca':'praticamente nula';
  const g=v.geo||{};
  let h=`<div class="insight"><b>As duas bases medidas no mesmo bairro.</b>
    ${fmt(o.n)} bairros têm dado nos dois anos. A correlação de postos (Spearman) entre os votos da
    <span class="yr y22">Lohanna 2022</span> e os de <span class="yr y24">${DATA.apelido} 2024</span>
    é <b>ρ = ${r==null?'—':r.toFixed(3).replace('.',',')}</b> — associação <b>${forca}</b>${r!=null&&r>0?' e positiva':''}:
    ${r!=null&&r>=.4
      ? 'os territórios das duas candidaturas se parecem, e a maior parte do esforço é de <b>consolidação conjunta</b>.'
      : 'os territórios são bastante distintos, e é aí que a <b>reciprocidade</b> vale mais — cada um leva voto onde o outro não tem.'}</div>`;

  h+=`<div class="note"><b>Como o cruzamento é feito.</b> A camada de 2022 vem de setor censitário
    agregado a bairro; a de 2024, de ${fmt(g.locais)} locais de votação situados no bairro pela sua
    coordenada oficial do TSE (${fmt(g.por_poligono)} dentro do polígono do bairro,
    ${fmt(g.por_centroide)} pelo centroide mais próximo${g.com_bairro<g.locais?`, ${fmt(g.locais-g.com_bairro)} sem bairro atribuído e por isso fora do cruzamento`:''}).
    Nenhum número é estimado: são duas contagens reais somadas na mesma unidade.
    O corte de cada eixo é a <b>mediana</b> entre esses bairros — ${fmt(o.corte22)} votos em 2022 e
    ${fmt(o.corte24)} em 2024 —, um limiar relativo a este município.</div>`;

  /* --- scatter --- */
  const W=640,H=420,pad={l:56,r:16,t:16,b:44};
  const mx22=Math.max(...o.pontos.map(p=>p[1]))||1, mx24=Math.max(...o.pontos.map(p=>p[2]))||1;
  const X=x=>pad.l+(W-pad.l-pad.r)*Math.sqrt(x/mx22);
  const Y=y=>H-pad.b-(H-pad.t-pad.b)*Math.sqrt(y/mx24);
  let sv=`<svg viewBox="0 0 ${W} ${H}" class="scatter" preserveAspectRatio="xMidYMid meet">`;
  sv+=`<rect x="${pad.l}" y="${pad.t}" width="${W-pad.l-pad.r}" height="${H-pad.t-pad.b}" fill="#fafbfd" stroke="#e3e6f0"/>`;
  sv+=`<line x1="${X(o.corte22).toFixed(1)}" y1="${pad.t}" x2="${X(o.corte22).toFixed(1)}" y2="${H-pad.b}" stroke="#b9c0d4" stroke-dasharray="4 3"/>`;
  sv+=`<line x1="${pad.l}" y1="${Y(o.corte24).toFixed(1)}" x2="${W-pad.r}" y2="${Y(o.corte24).toFixed(1)}" stroke="#b9c0d4" stroke-dasharray="4 3"/>`;
  [[0,'0'],[.25,''],[.5,''],[1,'']].forEach(()=>{});
  [0,.25,.5,.75,1].forEach(t=>{
    const vx=Math.round(mx22*t*t), vy=Math.round(mx24*t*t);
    sv+=`<text x="${X(vx).toFixed(1)}" y="${H-pad.b+15}" class="ax" text-anchor="middle">${fmt(vx)}</text>`;
    sv+=`<text x="${pad.l-7}" y="${(Y(vy)+4).toFixed(1)}" class="ax" text-anchor="end">${fmt(vy)}</text>`;
  });
  o.pontos.forEach(p=>{
    sv+=`<circle cx="${X(p[1]).toFixed(1)}" cy="${Y(p[2]).toFixed(1)}" r="5" fill="${QUAD[p[3]].cor}"
      fill-opacity=".72" stroke="#fff" stroke-width="1" data-b="${String(p[0]).replace(/"/g,'&quot;')}"
      data-v="${p[1]}|${p[2]}|${p[3]}|${String(p[4]||'').replace(/"/g,'&quot;')}"></circle>`;
  });
  sv+=`<text x="${(pad.l+(W-pad.r))/2}" y="${H-8}" class="axt" text-anchor="middle">votos da Lohanna · 2022</text>`;
  sv+=`<text x="14" y="${(pad.t+(H-pad.b))/2}" class="axt" text-anchor="middle" transform="rotate(-90 14 ${((pad.t+(H-pad.b))/2).toFixed(1)})">votos de ${DATA.apelido} · 2024</text>`;
  sv+=`</svg>`;
  h+=`<div class="scwrap">${sv}</div>
    <div class="qleg">${Object.entries(QUAD).map(([k,q])=>
      `<span><i style="background:${q.cor}"></i>${q.nome} <b>${fmt(o.n_quad[k])}</b></span>`).join('')}</div>
    <p class="axn">Os eixos são de raiz quadrada: sem isso a nuvem se amontoaria perto da origem e os
      bairros grandes tomariam o gráfico inteiro. As linhas tracejadas são as medianas.</p>`;

  /* --- mapa por quadrante --- */
  const q4=Object.fromEntries(o.pontos.map(p=>[p[0],p[3]]));
  h+=`<h3 class="hsec">Os quatro quadrantes no mapa</h3><div id="mapQ" class="mapbox"></div>`;

  /* --- listas por quadrante --- */
  h+=`<div class="quads">`+Object.entries(QUAD).map(([k,q])=>{
    const arr=o.quadrantes[k]||[];
    return `<div class="qcol" style="--qc:${q.cor}"><h4>${q.nome}
      <span class="sub">${fmt(o.n_quad[k])} bairros</span></h4>
      <p class="qd">${q.desc}</p>
      ${arr.length?arr.map(x=>`<div class="qrow"><b>${x.b}</b>
        <span class="qv"><span class="yr y22">${fmt(x.v22)}</span> · <span class="yr y24">${fmt(x.v24)}</span></span></div>`).join('')
        :'<div class="qrow" style="opacity:.6">nenhum bairro</div>'}</div>`;
  }).join('')+`</div>`;

  box.innerHTML=h;
  desenhaMapa(document.getElementById('mapQ'),{
    fill:p=>q4[p.bairro]?QUAD[q4[p.bairro]].cor:'#e6e9f2',
    sel:p=>!!q4[p.bairro],
    pfill:b=>q4[b.Bairro]?QUAD[q4[b.Bairro]].cor:'#d5d9e6',
    praio:b=>q4[b.Bairro]?b.setores:0.2*b.setores});
  box.querySelectorAll('.scatter circle').forEach(c=>{
    c.onmousemove=e=>{const [a,b,k,rg]=c.dataset.v.split('|');
      showTip(e,`<b>${c.dataset.b}</b>${rg?`<br><span class="m">${rg}</span>`:''}
        <br><span class="yr y22">2022</span> ${fmt(+a)} votos
        <br><span class="yr y24">2024</span> ${fmt(+b)} votos
        <br><span class="m">${QUAD[k].nome}</span>`);};
    c.onmouseleave=hideTip;
  });
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
    ${DATA.over?`<div class="insight" style="border-left-color:#5B3A8E"><b>Frente 3 – Reciprocidade (roxo):</b>
      o que cada candidatura leva de novo para a outra. A medida é a diferença entre a
      <b>fatia do município</b> que o bairro representa em cada camada — cada ano normalizado pelo seu
      próprio total, senão a camada de maior volume dominaria por puro tamanho.
      <b>${DATA.apelido} entrega</b> onde é forte e a Lohanna é fraca; <b>a Lohanna entrega</b> no inverso.
      A lista vem logo abaixo do plano.</div>`
     :`<div class="note"><b>Frente 3 – Reciprocidade</b> (território forte de uma candidatura e fraco da outra)
      depende da camada de 2024 por local de votação e por isso não entra neste município.</div>`}`;

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

  /* --- Frente 3: reciprocidade, bairro a bairro --- */
  const R=document.getElementById('recip'), o=DATA.over;
  if(!o){ R.innerHTML=''; return; }
  const lista=(t,cls,arr)=>`<div class="front ${cls}"><h3>${t}
      <span class="sub">${arr.length} bairros</span></h3>
      ${arr.length?arr.map((x,i)=>`<div class="trow"><span class="n">${i+1}</span>
        <div class="info"><b>${x.b}</b><span class="rg">${x.reg||'—'}</span>
          <span class="rg"><span class="yr y22">2022</span> ${fmt(x.v22)} (${f1(x.s22)}%) ·
            <span class="yr y24">2024</span> ${fmt(x.v24)} (${f1(x.s24)}%)</span></div>
        <span class="sc">${f1(Math.abs(x.dif))} p.p.</span></div>`).join('')
       :'<div class="trow" style="opacity:.6">nenhum bairro nesta condição</div>'}</div>`;
  R.innerHTML = `<h3 class="hsec">Frente 3 – Reciprocidade: quem leva voto para quem</h3>`
    + `<div class="lists">`
    + lista(`Onde ${DATA.apelido} entrega à Lohanna`,'cons',o.recip_cand)
    + lista('Onde a Lohanna entrega ao aliado','exp',o.recip_loh)
    + `</div>`;
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
  const CB=DATA.comp_bairro;
  let h = CB
   ? `<div class="note"><b>Recorte municipal e por bairro.</b> Abaixo, quem divide o eleitorado com
      ${DATA.apelido} no município inteiro; mais adiante, bairro a bairro — os três mais votados em cada um,
      a partir dos locais de votação situados ali pela coordenada do TSE.</div>`
   : `<div class="note"><b>Recorte municipal.</b> Sem os votos por local de votação situados no bairro, não é
      possível dizer quem disputa o eleitorado de ${DATA.apelido} <b>bairro a bairro</b> — só quem disputa no
      município. O bloco por bairro entra junto com a seção de sobreposição.</div>`;
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
  /* --- quem disputa, bairro a bairro --- */
  if(CB){
    const linhas=(DATA.votes24.bairros||[]).filter(b=>CB[b.b]);
    const venc=linhas.filter(b=>CB[b.b].pos===1).length;
    box.insertAdjacentHTML('beforeend',
      `<h3 class="hsec">Quem disputa o eleitorado, bairro a bairro</h3>
       <div class="note">${DATA.apelido} é o mais votado em <b>${fmt(venc)}</b> dos ${fmt(linhas.length)} bairros
         com dado de 2024. Os votos de um bairro são a soma dos locais de votação situados nele; locais sem
         coordenada ficam de fora, e por isso a soma da tabela pode ficar abaixo do total municipal.</div>
       <div style="max-height:460px;overflow:auto;border:1.5px solid #e3e6f0;border-radius:10px;">
       <table class="cbtab"><thead><tr>
         <th>Bairro</th><th class="num">${DATA.apelido}</th><th class="num">pos.</th>
         <th>Os três mais votados no bairro</th></tr></thead><tbody>` +
      linhas.map(b=>{const c=CB[b.b];const win=c.pos===1;
        return `<tr class="${win?'win':''}"><td><b>${b.b}</b>
          <div style="font-size:.7rem;color:var(--muted)">${b.reg||'—'} · ${b.locais} local${b.locais>1?'is':''}</div></td>
          <td class="num"><b style="color:${win?'var(--pink)':'var(--navy)'}">${fmt(b.v)}</b>
            <div style="font-size:.7rem;color:var(--muted)">${f1(b.pct)}%</div></td>
          <td class="num">${c.pos?c.pos+'º':'—'}<div style="font-size:.7rem;color:var(--muted)">de ${c.n}</div></td>
          <td>${c.top.map(t=>`<span style="color:${t.nr===String(DATA.numero)?'var(--pink)':'var(--txt)'};
            font-weight:${t.nr===String(DATA.numero)?'700':'400'}">${curto(t.nome)} ${fmt(t.v)}</span>`).join(' · ')}</td>
        </tr>`;}).join('') +
      `</tbody></table></div>`);
  }

}

/* --------------------------------------------------------- rodapé */
function foot(){
  const m=DATA.meta, f=m.fontes;
  const partes=[
    `<b>Camada ${'2022'}:</b> ${f['2022']}`,
    f['2024']?`<b>Camada 2024:</b> ${f['2024']}`:null,
    f.geo?`<b>Geometria:</b> ${f.geo}`:null,
    `<b>Unidade geográfica:</b> ${m.unidade}. ${m.unidade_por_que}`,
    m.malha_poligonos?`<b>Malha:</b> ${m.malha_poligonos} polígonos, cobrindo o município inteiro — todo setor censitário entra em algum bairro, inclusive o rural, e todos são desenhados. ${
      m.malha_fontes?`Origem do nome de cada setor: ${
        [['IBGE','NM_BAIRRO do IBGE'],['CNEFE','campo Bairro do CNEFE'],
         ['vizinho','herdado do bairro vizinho de maior fronteira (setor urbano sem nome nas duas fontes)'],
         ['distrito','nomeado pelo distrito, na forma "Zona rural — X" ou "X — sem bairro declarado"']]
        .filter(([k])=>m.malha_fontes[k]).map(([k,t])=>`${m.malha_fontes[k]} ${t}`).join('; ')}.`:''}`:null,
    `<b>Índice:</b> percentil médio do valor ajustado, normalizado por pauta, escala 0–100.`,
    DATA.votes22.granularidade==='local de votação'
      ? `<b>Camada 2022 — origem:</b> votos de urna do TSE (${DATA.votes22.cargo}, 2022) por seção, somados ao local de votação, cada seção uma única vez. NÃO vem da coluna <i>Votos_Candidato</i> da tabela de aderência: aquela coluna repete, em cada setor, o total do local de votação mais próximo, e somá-la sobre os setores infla a votação em várias vezes.`
      : `<b>Sem dupla contagem:</b> cada setor censitário entra uma única vez na soma de votos.`,
    DATA.votes22.geo?`<b>Locais de votação de 2022:</b> ${DATA.votes22.geo.com_bairro} de ${DATA.votes22.geo.locais} situados num bairro (${DATA.votes22.geo.por_poligono} por polígono, ${DATA.votes22.geo.por_centroide} por centroide); os demais ficam fora do recorte por bairro e não são rateados.`:null,
    m.cobertura?`<b>Cobertura:</b> ${m.setores_observados} de ${m.setores_declarados} setores do município (${f1(m.cobertura)}%) — os que têm endereço CNEFE correspondido. O índice descreve esses setores, não o município inteiro.`:null,
    `<b>Filtro de robustez:</b> rankings de bairro exigem ao menos ${m.min_setores} setores — ${m.min_setores_por_que}.`,
    DATA.votes22.suprimido?`<b>ATENÇÃO — camada 2022 suprimida:</b> ${DATA.votes22.motivo}`:null,
    DATA.votes24&&DATA.votes24.geo?`<b>Situação dos locais de votação:</b> ${DATA.votes24.geo.com_bairro} de ${DATA.votes24.geo.locais} locais foram atribuídos a um bairro (${DATA.votes24.geo.por_poligono} por estarem dentro do polígono, ${DATA.votes24.geo.por_centroide} pelo centroide mais próximo, dentro de 3 km); ${DATA.votes24.geo.locais-DATA.votes24.geo.com_coord} não têm coordenada na fonte do TSE. Os não atribuídos ficam fora do cruzamento por bairro, e não são rateados.`:null,
    DATA.camadas?`<b>Seção unificada:</b> as duas eleições são apresentadas numa única seção, ambas somadas <b>por bairro</b> e não por seção eleitoral. ${DATA.camadas.tem22?`Da votação da Lohanna, ${fmt(DATA.camadas.soma22)} de ${fmt(DATA.camadas.total22)} votos caem num bairro identificado`:''}${DATA.camadas.tem24?`${DATA.camadas.tem22?'; da de ':'Da votação de '}${DATA.apelido}, ${fmt(DATA.camadas.soma24)} de ${fmt(DATA.camadas.total24)}`:''}. A diferença está em locais de votação sem coordenada na fonte do TSE e <b>não é rateada</b> entre bairros.`:null,
    `<b>Ressalva:</b> 2022 e 2024 são pleitos e cargos diferentes e nunca são somados. ${DATA.over?'A sobreposição compara os dois anos bairro a bairro, mas sempre como duas contagens lado a lado.':(DATA.votes24&&DATA.votes24.granularidade==='local de votação'?'A camada de 2024 está por local de votação.':'A camada de 2024 está no nível municipal nesta versão.')}`,
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
  const se=document.getElementById('selEnq');
  se.value=enquadre;
  se.onchange=()=>{enquadre=se.value; BB=null; PROJ=null;
    render(); cam(); over(); mob();};
  const fr=document.getElementById('fReg');
  DATA.regionais.map(r=>r.regional).sort().forEach(r=>fr.appendChild(new Option(r,r)));
  render(); cam(); over(); mob(); graficos(); tabela(); tops(); comp(); foot();
})();
