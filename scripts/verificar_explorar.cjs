/* Smoke test real em Edge headless. Usa banco e perfil de navegador isolados. */
const {spawn}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const temp=path.join(root,'.pytest_tmp_browser',String(Date.now()));fs.mkdirSync(temp,{recursive:true});
const server=spawn(path.join(root,'.venv/Scripts/python.exe'),['-m','uvicorn','spectra_link_guard.web.app:app','--host','127.0.0.1','--port','8012'],{cwd:root,env:{...process.env,SPECTRA_BD:path.join(temp,'teste.db')},windowsHide:true,stdio:'ignore'});
const browser=spawn('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',['--headless=new','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=9337','--user-data-dir='+path.join(temp,'edge'),'about:blank'],{windowsHide:true,stdio:'ignore'});
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn,timeout=20000){const inicio=Date.now();let erro;while(Date.now()-inicio<timeout){try{const r=await fn();if(r)return r;}catch(e){erro=e;}await sleep(100);}throw erro||Error('Tempo de espera excedido');}
let socket;const pending=new Map();let seq=0;const erros=[];
function command(method,params={}){return new Promise((resolve,reject)=>{const id=++seq;const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP timeout '+method));},15000);pending.set(id,{resolve:r=>{clearTimeout(timer);resolve(r)},reject:e=>{clearTimeout(timer);reject(e)}});socket.send(JSON.stringify({id,method,params}));});}
async function js(expression){const r=await command('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;}
const ready=expression=>until(()=>js(expression));

async function verificarLaudo(){
  await command('Page.navigate',{url:'http://127.0.0.1:8012/painel'});
  await ready("typeof periciar==='function'&&document.getElementById('copiloto-ctx')!==null");
  // Exercita a API real em modo offline; não consulta o endereço de terceiros.
  await js(`window.fetchReal=window.fetch.bind(window);window.fetch=(input,options)=>{
    if(input==='/api/analisar')return window.fetchReal(input,{...options,body:JSON.stringify({...JSON.parse(options.body),offline:true})});
    return window.fetchReal(input,options);
  };window.fetchOffline=window.fetch;`);
  for(const url of ['https://www.tokyvideo.com/br/filmes','https://itau.seguranca-cliente.top/atualizar/senha']){
    await js(`document.getElementById('url').value=${JSON.stringify(url)};document.getElementById('formulario').requestSubmit()`);
    await ready("document.getElementById('grade').getAttribute('aria-busy')==='false'&&document.getElementById('q-amostras').hidden");
    assert.equal(await js("document.getElementById('aviso').hidden"),true);
    for(const id of ['q-cadeia','q-evidencias','q-sinais','q-checklist','subnav-analise'])assert.equal(await js(`document.getElementById('${id}').hidden`),false);
    assert.ok(await js("document.getElementById('parecer').textContent.trim().length>30"));
    assert.ok(await js("document.querySelectorAll('#checklist-corpo tr').length>0"));
    assert.equal(await js("document.getElementById('enviar').disabled"),false);
  }
  await js("periciar('https://www.tokyvideo.com/br/filmes')");
  assert.equal(await js("document.getElementById('verificacao-cobertura').hidden"),false);
  assert.ok(await js("document.getElementById('sentenca').getAttribute('aria-label').includes('Verificação limitada')"));
  assert.equal(await js("document.getElementById('pastilha').textContent"),'não confirmado');
  assert.ok(await js("respostaSobreLaudo('Posso abrir esse link?').includes('Não posso confirmar')"));
  if(await js("!!window.Chart"))assert.equal(await js("Chart.getChart(document.getElementById('grafico-pontuacao')).data.datasets[0].backgroundColor[0]===getComputedStyle(document.documentElement).getPropertyValue('--nivel-seguro').trim()"),true);
  console.log('Laudos offline real: link da captura e exemplo suspeito exibidos com explicacoes e checklist.');
  await js("window.renderEvidenciasOriginal=renderEvidencias;window.renderEvidencias=()=>{throw Error('Falha simulada de interface')}");
  await js("periciar('https://exemplo.invalid')");
  assert.ok(await js("document.getElementById('aviso').textContent.includes('falha ao exibir')"));
  assert.equal(await js("document.getElementById('enviar').disabled"),false);
  await js("window.renderEvidencias=window.renderEvidenciasOriginal;window.fetch=()=>Promise.reject(Error('Falha simulada de rede'))");
  await js("periciar('https://exemplo.invalid')");
  assert.ok(await js("document.getElementById('aviso').textContent.includes('comunicar com o servidor')"));
  await js("window.fetch=()=>Promise.resolve({ok:true,json:async()=>{throw Error('JSON invalido')}})");
  await js("periciar('https://exemplo.invalid')");
  assert.ok(await js("document.getElementById('aviso').textContent.includes('não pôde ser lida')"));
  await js("window.fetch=window.fetchOffline");await js("periciar('https://example.com')");
  assert.equal(await js("document.getElementById('aviso').hidden"),true);
  assert.deepEqual(erros,[]);
  console.log('Erros de interface, rede e resposta diferenciados; nova tentativa recupera o laudo.');
}

async function verificarGraficos(){
  const urls=['https://example.com/a','https://example.com/b','https://example.com/c','https://example.com/d','https://bit.ly/abc','https://bit.ly/def','https://steeam.com/','https://itau.seguro.top/login/senha/verificar','https://bradesc0.com.br/'];
  for(const url of urls)await js(`fetch('/api/analisar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:${JSON.stringify(url)},offline:true})}).then(r=>{if(!r.ok)throw Error('Falha ao preparar dados')})`);
  await command('Page.navigate',{url:'http://127.0.0.1:8012/painel/visao-geral'});
  await ready("document.querySelectorAll('.radial-linha').length===5");
  for(const [width,height] of [[1440,1000],[1050,900],[390,844]]){
    await command('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:width<600});await sleep(300);
    assert.equal(await js(`Array.from(document.querySelectorAll('.radial-linha')).every(l=>{const nome=l.querySelector('.radial-nome').getBoundingClientRect(),valor=l.querySelector('.radial-valor').getBoundingClientRect(),pct=l.querySelector('.radial-pct').getBoundingClientRect();return nome.right<=valor.left&&valor.right<=pct.left;})`),true);
    assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
    const grafico=await command('Runtime.evaluate',{expression:"document.getElementById('g-niveis').scrollIntoView({block:'center'});document.getElementById('g-niveis').getBoundingClientRect().toJSON()",returnByValue:true});
    const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,'graficos-'+width+'.png'),Buffer.from(shot.data,'base64'));
  }
  assert.equal(await js("Array.from(document.querySelectorAll('.radial-arco')).every(a=>a.getAttribute('stroke')===getComputedStyle(document.documentElement).getPropertyValue('--nivel-'+a.dataset.chave).trim())"),true);
  assert.ok(await js("document.getElementById('g-niveis').getAttribute('aria-label').includes('Sem sinais')"));
  assert.deepEqual(erros,[]);
  console.log('Graficos em 1440, 1050 e 390px: legenda sem sobreposicao, cinco cores canonicas e sem overflow. Capturas: '+temp);
  await command('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await js("document.documentElement.dataset.tema='escuro';window.dispatchEvent(new Event('spectra:tema'))");await sleep(600);
  assert.equal(await js("Array.from(document.querySelectorAll('.radial-linha')).every(l=>l.querySelector('.radial-nome').getBoundingClientRect().right<=l.querySelector('.radial-valor').getBoundingClientRect().left)"),true);
  const escuro=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,'graficos-escuro.png'),Buffer.from(escuro.data,'base64'));
}

async function verificarInicio(){
  await js("fetch('/api/auth/sair',{method:'POST'});localStorage.setItem('spectra:movimento','on');localStorage.setItem('spectra:tema','escuro')");
  await command('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'no-preference'}]});
  const abrir=async()=>{
    await command('Page.navigate',{url:'http://127.0.0.1:8012/inicio'});
    await ready("location.pathname==='/inicio'&&document.readyState==='complete'&&!!document.getElementById('inicio-historia')");
    await js('document.fonts.ready');
    await ready("document.documentElement.dataset.inicioRolagem==='on'");
  };
  const progresso=async p=>{
    await js(`(()=>{const h=document.getElementById('inicio-historia'),palco=h.querySelector('.inicio-palco');window.scrollTo({top:h.getBoundingClientRect().top+scrollY+(h.offsetHeight-palco.offsetHeight)*${p},behavior:'instant'})})()`);
    await ready(`Math.abs(Number(document.getElementById('inicio-historia').dataset.progresso)-${p})<.001`);
  };
  const captura=async nome=>{const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,nome+'.png'),Buffer.from(shot.data,'base64'));};
  await abrir();
  assert.equal(await js("document.querySelector('body>header,body>nav')===null"),true);
  await progresso(0);
  assert.equal(await js("getComputedStyle(document.querySelector('.inicio-logo')).opacity"),'1');
  assert.equal(await js("document.getElementById('apresentacao').inert"),true);
  await captura('inicio-identidade');
  // Um salto nativo da roda deve atravessar posições intermediárias, sem
  // alterar a posição real da página ou deixar um loop rodando em repouso.
  const amostras=await js(`new Promise(resolve=>{
    const h=document.getElementById('inicio-historia'),palco=h.querySelector('.inicio-palco'),valores=[],comeco=performance.now();
    window.scrollTo({top:h.getBoundingClientRect().top+scrollY+(h.offsetHeight-palco.offsetHeight)*.3,behavior:'instant'});
    function quadro(agora){valores.push({p:Number(h.dataset.progresso),y:scrollY});if(agora-comeco>650)resolve(valores);else requestAnimationFrame(quadro)}requestAnimationFrame(quadro);
  })`);
  assert.ok(new Set(amostras.filter(a=>a.p>.005&&a.p<.295).map(a=>a.p)).size>=4,'A roda deve produzir posições intermediárias');
  assert.ok(amostras.at(-1).p>.299,'A suavização deve alcançar o destino sem atraso prolongado');
  assert.ok(amostras.every((a,i)=>i===0||a.p>=amostras[i-1].p),'O movimento deve ser monotônico');
  assert.ok(amostras.every(a=>a.y===amostras[0].y),'A suavização não pode interceptar a rolagem nativa');
  await sleep(150);
  assert.equal(await js("new Promise(resolve=>{let mudancas=0;const o=new MutationObserver(l=>mudancas+=l.length);o.observe(document.getElementById('inicio-historia'),{subtree:true,attributes:true,attributeFilter:['style']});setTimeout(()=>{o.disconnect();resolve(mudancas)},250)})"),0);
  await progresso(.28);await captura('inicio-zoom');
  const escala=await js("new DOMMatrixReadOnly(getComputedStyle(document.querySelector('.inicio-logo')).transform).a");
  assert.ok(escala>1.5&&escala<3,'O zoom deve ampliar sem a intensidade anterior');
  await progresso(.82);await captura('inicio-apresentacao');
  assert.equal(await js("document.getElementById('apresentacao').inert"),false);
  assert.equal(await js("getComputedStyle(document.querySelector('.inicio-logo')).opacity"),'0');
  assert.equal(await js("Array.from(document.querySelectorAll('#manchete .letra')).every(l=>getComputedStyle(l).opacity==='1')"),true);
  await js("window.mudancasLetras=0;window.observarLetras=new MutationObserver(l=>window.mudancasLetras+=l.length);document.querySelectorAll('#manchete .letra').forEach(l=>window.observarLetras.observe(l,{attributes:true,attributeFilter:['style']}))");
  await progresso(.92);
  assert.equal(await js("window.observarLetras.disconnect();window.mudancasLetras"),0);
  await progresso(.82);
  for(const aba of ['entrar','cadastrar']){
    await js(`document.querySelector('.inicio-acoes [data-abrir="${aba}"]').click()`);
    assert.equal(await js("document.getElementById('modal').classList.contains('flex')"),true);
    assert.equal(await js(`document.getElementById('painel-${aba}').hidden`),false);
    await js("document.getElementById('fechar-modal').click()");
  }
  await progresso(0);
  assert.equal(await js("getComputedStyle(document.querySelector('.inicio-logo')).opacity"),'1');
  // A sequência responde à rolagem sem layouts contínuos.
  await command('Performance.enable');await command('Emulation.setCPUThrottlingRate',{rate:4});
  const antes=await command('Performance.getMetrics');
  for(const p of [.15,.35,.55,.82])await progresso(p);
  const depois=await command('Performance.getMetrics');
  const layouts=depois.metrics.find(m=>m.name==='LayoutCount').value-antes.metrics.find(m=>m.name==='LayoutCount').value;
  assert.ok(layouts<12,'Layouts na rolagem: '+layouts);
  await command('Emulation.setCPUThrottlingRate',{rate:1});
  await js("document.getElementById('inicio-recursos').scrollIntoView({behavior:'instant'})");
  await ready("document.getElementById('inicio-recursos').getBoundingClientRect().top<20");
  await captura('inicio-restante');
  await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await abrir();await progresso(0);await captura('inicio-celular-logo');
  await progresso(.82);await captura('inicio-celular-apresentacao');
  assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
  assert.equal(await js("(()=>{const r=document.querySelector('.inicio-apresentacao-conteudo').getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight})()"),true);
  assert.equal(await js("(()=>{const dica=document.getElementById('inicio-rolar').getBoundingClientRect(),chat=document.getElementById('abrir-chat').getBoundingClientRect(),a11y=document.getElementById('a11y-abrir').getBoundingClientRect();return dica.left>a11y.right&&dica.right<chat.left})()"),true);
  await js("document.querySelector('[data-a11y-tema]').click()");
  await ready("document.documentElement.dataset.tema==='claro'");await progresso(0);
  assert.equal(await js("getComputedStyle(document.querySelector('.inicio-logo .marca-clara')).display"),'block');
  await captura('inicio-celular-claro');
  await progresso(.82);await captura('inicio-celular-claro-apresentacao');
  // O atalho por teclado pula a abertura e deixa o conteúdo focado.
  await progresso(0);await js("document.getElementById('inicio-rolar').click()");
  await ready("document.activeElement.id==='apresentacao'&&Number(document.getElementById('inicio-historia').dataset.progresso)>.72");
  // Preferência de movimento e telas baixas mantêm todo o texto no fluxo normal.
  await js("document.querySelector('[data-interruptor-movimento]').click()");
  await ready("document.documentElement.dataset.inicioRolagem==='off'");
  assert.equal(await js("document.getElementById('apresentacao').inert"),false);
  assert.equal(await js("getComputedStyle(document.getElementById('apresentacao')).position"),'relative');
  await command('Emulation.setDeviceMetricsOverride',{width:844,height:390,deviceScaleFactor:1,mobile:true});
  await js("document.querySelector('[data-interruptor-movimento]').click()");
  await ready("document.documentElement.dataset.inicioRolagem==='off'");
  assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
  // Sem execução de scripts, a marca e a apresentação continuam visíveis.
  await command('Emulation.setScriptExecutionDisabled',{value:true});
  await command('Page.navigate',{url:'http://127.0.0.1:8012/inicio'});
  await ready("location.pathname==='/inicio'&&document.readyState==='complete'&&!!document.getElementById('apresentacao')");
  assert.equal(await js("getComputedStyle(document.getElementById('apresentacao')).position"),'relative');
  assert.equal(await js("getComputedStyle(document.getElementById('apresentacao')).opacity"),'1');
  await command('Emulation.setScriptExecutionDisabled',{value:false});
  assert.deepEqual(erros,[]);
  console.log('Abertura sem navbar: logo, zoom, manchete e restante; reversível, login/cadastro, teclado, celular, movimento reduzido e paisagem. CPU 4x: '+layouts+' layouts. Capturas: '+temp);
}

async function verificarLogos(){
  await js("fetch('/api/auth/sair',{method:'POST'})");
  for(const pagina of ['/inicio','/painel','/painel/explorar','/privacidade','/termos']){
    await command('Page.navigate',{url:'http://127.0.0.1:8012'+pagina});
    await ready(`location.pathname===${JSON.stringify(pagina)}&&document.readyState==='complete'&&!!document.querySelector('[data-a11y-tema]')`);
    await js("Promise.all(Array.from(document.querySelectorAll('.marca-clara,.marca-escura')).map(img=>img.decode()))");
    for(const tema of ['claro','escuro']){
      await js(`if(document.documentElement.dataset.tema!==${JSON.stringify(tema)})document.querySelector('[data-a11y-tema]').click()`);
      const marca=tema==='claro'?'marca-clara':'marca-escura';
      assert.equal(await js(`Array.from(document.querySelectorAll('.marca-clara,.marca-escura')).every(img=> (getComputedStyle(img).display!=='none')===img.classList.contains('${marca}'))`),true);
      assert.equal(await js(`document.querySelector('link[rel="icon"]').href.endsWith('logo-spectra-${tema}.svg')`),true);
      assert.equal(await js("Array.from(document.querySelectorAll('.marca-clara,.marca-escura')).every(img=>img.naturalWidth>0)"),true);
      assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
      if(pagina==='/inicio'){
        const rect=await js("document.querySelector('.spectra-logo-hero').getBoundingClientRect().toJSON()");
        const shot=await command('Page.captureScreenshot',{format:'png',clip:{x:Math.max(0,rect.x-16),y:Math.max(0,rect.y-16),width:rect.width+32,height:rect.height+32,scale:2}});
        fs.writeFileSync(path.join(temp,'logo-'+tema+'.png'),Buffer.from(shot.data,'base64'));
      }
    }
    if(pagina==='/inicio')await js("fetch('/api/auth/entrar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:'visual@example.com',senha:'SenhaTeste123!'})}).then(r=>{if(!r.ok)throw Error('Login falhou')})");
  }
  await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await command('Page.navigate',{url:'http://127.0.0.1:8012/painel/explorar'});
  await ready("location.pathname==='/painel/explorar'&&document.body.classList.contains('com-conta')");
  assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
  assert.deepEqual(erros,[]);
  console.log('Logos originais: texto preto no claro, branco no escuro; troca ao vivo em cinco páginas, ícone da aba e celular sem overflow. Capturas: '+temp);
}

async function verificarPerfil(){
  await command('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'no-preference'}]});
  await js("localStorage.setItem('spectra:movimento','on')");
  const png='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aR1cAAAAASUVORK5CYII=';
  await js(`fetch('/api/perfil',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:'Pessoa Visual',bio:'Teste do perfil',foto:${JSON.stringify(png)}})}).then(r=>{if(!r.ok)throw Error('Perfil falhou')})`);
  for(const pagina of ['/painel','/painel/visao-geral','/painel/historico','/painel/explorar','/painel/blog','/painel/forum','/painel/aprender','/privacidade','/termos']){
    await command('Page.navigate',{url:'http://127.0.0.1:8012'+pagina});
    await ready(`location.pathname===${JSON.stringify(pagina)}&&document.body.classList.contains('com-conta')&&!!document.querySelector('.conta-avatar img')`);
    assert.equal(await js("document.querySelectorAll('.trilho [href=\"/painel/perfil\"]').length"),0);
    assert.equal(await js("document.querySelectorAll('.gaveta-menu [data-menu=perfil]').length"),0);
    assert.equal(await js("(()=>{const r=document.querySelector('.conta-superior').getBoundingClientRect();return r.top>=0&&r.top<20&&document.documentElement.clientWidth-r.right<25})()"),true,pagina);
    assert.equal(await js("getComputedStyle(document.querySelector('.conta-avatar')).borderRadius"),'0px');
    assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
  }
  await command('Page.navigate',{url:'http://127.0.0.1:8012/painel/explorar'});await ready("location.pathname==='/painel/explorar'&&document.body.classList.contains('com-conta')");
  const origem=await js("(()=>{const r=document.querySelector('.conta-avatar').getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2}})()");
  assert.ok(origem.x>1000);
  await command('Performance.enable');
  await command('Emulation.setCPUThrottlingRate',{rate:4});
  await js("document.querySelector('[data-perfil-acesso]').click()");
  assert.equal(await js("document.documentElement.dataset.perfilTransicao"),'arredondando');
  await ready("location.pathname==='/painel/perfil'&&document.documentElement.dataset.perfilTransicao==='deslocando'");
  await ready("(()=>{const animacoes=document.getAnimations().filter(a=>a.effect.pseudoElement?.startsWith('::view-transition-'));if(!animacoes.length)return false;animacoes.forEach(a=>{a.pause();a.currentTime=350});return true})()");
  const metricsAntes=await command('Performance.getMetrics');
  assert.equal(await js("document.documentElement.classList.contains('perfil-transicao-nativa')"),true);
  assert.equal(await js("getComputedStyle(document.documentElement,'::view-transition-old(root)').animationName"),'perfil-tela-sair');
  assert.equal(await js("getComputedStyle(document.documentElement,'::view-transition-new(root)').animationName"),'perfil-tela-entrar');
  assert.equal(await js("getComputedStyle(document.documentElement,'::view-transition-group(perfil-foto)').animationDuration"),'1.25s');
  assert.equal(await js("document.getAnimations().filter(a=>a.effect.pseudoElement==='::view-transition-group(perfil-foto)').every(a=>a.effect.getKeyframes().every(f=>f.transform&&!('width' in f)&&!('height' in f)))"),true);
  assert.equal(await js("getComputedStyle(document.documentElement,'::view-transition-old(root)').opacity"),'1');
  assert.equal(await js("getComputedStyle(document.documentElement,'::view-transition-new(root)').opacity"),'0');
  assert.ok(Math.abs(await js("parseFloat(document.documentElement.style.getPropertyValue('--perfil-origem-x'))")-origem.x)<2);
  const transicao=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,'perfil-transicao.png'),Buffer.from(transicao.data,'base64'));
  await js("document.getAnimations().filter(a=>a.effect.pseudoElement?.startsWith('::view-transition-')).forEach(a=>a.currentTime=1050)");
  const chegada=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,'perfil-chegada.png'),Buffer.from(chegada.data,'base64'));
  await js("document.getAnimations().filter(a=>a.effect.pseudoElement?.startsWith('::view-transition-')).forEach(a=>a.play())");
  await ready("!document.documentElement.dataset.perfilTransicao&&!document.getElementById('perfil').hidden&&document.body.classList.contains('com-conta')");
  assert.equal(await js("getComputedStyle(document.body).visibility"),'visible');
  assert.equal(await js("document.querySelectorAll('.perfil-morph').length"),0);
  const metricsDepois=await command('Performance.getMetrics');
  const layouts=metricsDepois.metrics.find(m=>m.name==='LayoutCount').value-metricsAntes.metrics.find(m=>m.name==='LayoutCount').value;
  assert.ok(layouts<12,'Layouts durante o movimento: '+layouts);
  await command('Emulation.setCPUThrottlingRate',{rate:1});
  console.log('Tela anterior preservada; perfil e fundo revelados juntos na chegada. CPU 4x; layouts: '+layouts);
  assert.equal(await js("getComputedStyle(document.querySelector('[data-perfil-acesso]')).display"),'none');
  assert.equal(await js("getComputedStyle(document.getElementById('foto-preview')).visibility"),'visible');
  assert.equal(await js("document.getAnimations().some(a=>a.effect?.getKeyframes().some(f=>f.clipPath))"),false);
  const desktop=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,'perfil-desktop.png'),Buffer.from(desktop.data,'base64'));
  console.log('Conta no alto a direita em nove paginas; quadrado vira circulo e se desloca ate o avatar grande: OK');
  // O caso da gravação: inicial no lugar da foto, com tema escuro.
  await js("fetch('/api/perfil',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:'Pessoa Visual',bio:'Teste do perfil',foto:''})}).then(r=>{if(!r.ok)throw Error('Perfil falhou')});localStorage.setItem('spectra:tema','escuro')");
  await command('Page.navigate',{url:'http://127.0.0.1:8012/painel/explorar'});
  await ready("location.pathname==='/painel/explorar'&&document.body.classList.contains('com-conta')&&document.querySelector('.conta-avatar').textContent==='P'");
  await js("document.querySelector('[data-perfil-acesso]').click()");
  await ready("(()=>{if(location.pathname!=='/painel/perfil')return false;const a=document.getAnimations().filter(a=>a.effect.pseudoElement?.startsWith('::view-transition-'));if(!a.length)return false;a.forEach(a=>{a.pause();a.currentTime=350});return true})()");
  const inicialVoo=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,'perfil-inicial-transicao.png'),Buffer.from(inicialVoo.data,'base64'));
  assert.equal(await js("document.getAnimations().some(a=>a.effect.pseudoElement==='::view-transition-group(perfil-letra)'&&a.effect.getKeyframes().every(f=>f.transform&&!('width' in f)&&!('height' in f)))"),true);
  assert.equal(await js("getComputedStyle(document.querySelector('.perfil-morph')).backgroundColor===getComputedStyle(document.getElementById('foto-inicial')).backgroundColor"),true);
  await js("document.getAnimations().filter(a=>a.effect.pseudoElement?.startsWith('::view-transition-')).forEach(a=>a.currentTime=1050)");
  const inicialChegada=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,'perfil-inicial-chegada.png'),Buffer.from(inicialChegada.data,'base64'));
  await js("document.getAnimations().filter(a=>a.effect.pseudoElement?.startsWith('::view-transition-')).forEach(a=>a.play())");
  await ready("!document.documentElement.dataset.perfilTransicao&&document.body.classList.contains('com-conta')");
  assert.equal(await js("document.getElementById('foto-inicial').textContent"),'P');
  assert.equal(await js("getComputedStyle(document.getElementById('foto-inicial')).visibility"),'visible');
  console.log('Inicial sem foto no tema escuro: trajeto e chegada capturados; sem troca brusca de cor no encaixe.');
  // O botão também deve animar quando a própria página de perfil já está aberta.
  await js("document.querySelector('[data-perfil-acesso]').click()");
  assert.equal(await js("document.documentElement.dataset.perfilTransicao"),'arredondando');
  await ready("document.documentElement.dataset.perfilTransicao==='deslocando'");
  await ready("!document.documentElement.dataset.perfilTransicao&&document.body.classList.contains('com-conta')");
  // Uma escolha explícita de movimento ligado prevalece sobre o sistema.
  await command('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  await command('Page.navigate',{url:'http://127.0.0.1:8012/painel/explorar'});
  await ready("location.pathname==='/painel/explorar'&&document.body.classList.contains('com-conta')");
  assert.equal(await js("document.documentElement.dataset.movimento"),'on');
  await js("document.querySelector('[data-perfil-acesso]').click()");
  assert.equal(await js("document.documentElement.dataset.perfilTransicao"),'arredondando');
  await ready("location.pathname==='/painel/perfil'&&document.documentElement.dataset.perfilTransicao==='deslocando'");
  await ready("!document.documentElement.dataset.perfilTransicao&&document.body.classList.contains('com-conta')");
  await command('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'no-preference'}]});
  console.log('Repeticao no perfil e escolha explicita de movimento ligado com sistema em reduce: OK');
  await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await command('Page.navigate',{url:'http://127.0.0.1:8012/painel/explorar'});await ready("document.body.classList.contains('com-conta')&&document.querySelector('[data-explorar=feed][aria-current=page]')");
  assert.equal(await js("document.getElementById('explorar-nav').getBoundingClientRect().top>=document.querySelector('.conta-superior').getBoundingClientRect().bottom"),true);
  assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
  const mobile=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,'perfil-mobile.png'),Buffer.from(mobile.data,'base64'));
  // Sem transição entre documentos na origem, o recorte local continua funcionando.
  await js("const estilo=document.createElement('style');estilo.textContent='@view-transition { navigation: none; }';document.head.append(estilo);document.querySelector('[data-perfil-acesso]').click()");
  await ready("location.pathname==='/painel/perfil'&&document.documentElement.dataset.perfilTransicao==='deslocando'");
  await ready("!document.documentElement.dataset.perfilTransicao&&document.body.classList.contains('com-conta')");
  assert.equal(await js("getComputedStyle(document.body).visibility"),'visible');
  await command('Page.navigate',{url:'http://127.0.0.1:8012/painel/explorar'});await ready("location.pathname==='/painel/explorar'&&document.body.classList.contains('com-conta')");
  await command('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
  await js("localStorage.setItem('spectra:movimento','off');document.documentElement.dataset.movimento='off';document.querySelector('[data-perfil-acesso]').click()");
  await ready("location.pathname==='/painel/perfil'&&document.body.classList.contains('com-conta')");
  assert.equal(await js("!!document.querySelector('.perfil-morph')||!!document.documentElement.dataset.perfilTransicao"),false);
  await ready("document.querySelector('[data-ativar-transicao]')!==null");
  await js("document.querySelector('[data-ativar-transicao]').click()");
  assert.equal(await js("document.documentElement.dataset.perfilTransicao"),'arredondando');
  await ready("document.documentElement.dataset.perfilTransicao==='deslocando'");
  await ready("!document.documentElement.dataset.perfilTransicao&&document.body.classList.contains('com-conta')");
  assert.equal(await js("document.documentElement.dataset.movimento"),'on');
  assert.deepEqual(erros,[]);
  console.log('Celular sem sobreposicao, fallback, movimento reduzido e foto da conta: OK. Capturas: '+temp);
}

(async()=>{
 try{
  await until(async()=>{const r=await fetch('http://127.0.0.1:8012/api/saude');return r.ok;});
  const pages=await until(async()=>{const r=await fetch('http://127.0.0.1:9337/json/list');const p=await r.json();return p.find(p=>p.type==='page');});
  socket=new WebSocket(pages.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  socket.onmessage=({data})=>{const m=JSON.parse(data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(m.error.message)):p.resolve(m.result);}if(m.method==='Runtime.exceptionThrown')erros.push(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text);};
  await command('Runtime.enable');await command('Page.enable');
  await command('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  await command('Page.navigate',{url:'http://127.0.0.1:8012/inicio'});await ready("location.pathname==='/inicio'&&document.readyState!=='loading'");
  await js(`fetch('/api/auth/cadastrar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:'Pessoa Visual',email:'visual@example.com',senha:'SenhaTeste123!'})}).then(r=>{if(!r.ok)throw Error('Cadastro falhou')})`);
  if(process.argv.includes('--laudo')){await verificarLaudo();return;}
  if(process.argv.includes('--graficos')){await verificarGraficos();return;}
  if(process.argv.includes('--perfil')){await verificarPerfil();return;}
  if(process.argv.includes('--logos')){await verificarLogos();return;}
  if(process.argv.includes('--inicio')){await verificarInicio();return;}
  await command('Page.navigate',{url:'http://127.0.0.1:8012/painel/explorar'});
  await ready("document.querySelector('[data-explorar=feed][aria-current=page]')!==null");
  assert.equal(await js("document.getElementById('form-publicacao').hidden"),true);
  assert.equal(await js("document.querySelector('[data-menu=chat]')===null"),true);
  assert.equal(await js("Math.abs(document.getElementById('explorar-nav').getBoundingClientRect().top)<2"),true);
  assert.equal(await js("Math.abs(document.getElementById('explorar-nav').getBoundingClientRect().width-document.querySelector('.corpo').getBoundingClientRect().width)<2"),true);
  await js("document.querySelector('[data-explorar=publicar]').click()");await ready("!document.getElementById('form-publicacao').hidden");
  await js("document.getElementById('post-titulo').value='Imagem de teste';document.getElementById('post-texto').value='Discussao sobre seguranca digital com uma foto de teste.'");
  const png=path.join(temp,'teste.png');fs.writeFileSync(png,Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aR1cAAAAASUVORK5CYII=','base64'));
  const dom=await command('DOM.getDocument');const field=await command('DOM.querySelector',{nodeId:dom.root.nodeId,selector:'#post-midias'});
  await command('DOM.setFileInputFiles',{nodeId:field.nodeId,files:[png]});await ready("document.querySelectorAll('.midia-previa').length===1");
  await js("document.querySelector('#form-publicacao button[type=submit]').click()");
  await ready("location.hash==='#feed'&&document.querySelectorAll('#lista-publicacoes .post-midias img').length===1");
  const imagem=await js("document.querySelector('#lista-publicacoes .post-midias img').src");assert.ok(imagem.includes('/api/midias/'));
  console.log('Feed padrao, publicacao com foto e navbar: OK');
  await js("document.querySelector('[data-explorar=conexoes]').click()");await ready("!document.getElementById('explorar-conexoes').hidden&&document.getElementById('total-seguindo').textContent==='(0)'");
  await js("document.querySelector('[data-explorar=conversas]').click()");await ready("!document.getElementById('chat').hidden");
  await js("document.querySelector('[data-explorar=desafios]').click()");await ready("document.querySelectorAll('.desafio-card').length===5");
  await js("document.querySelector('.desafio-card button').click()");await ready("!document.getElementById('desafio-partida').hidden&&document.querySelector('input[name=alternativa]')!==null");
  await js("document.querySelector('input[name=alternativa][value=\"1\"]').click();document.querySelector('#desafio-partida button[type=submit]').click()");
  await ready("document.querySelector('.desafio-feedback[data-acertou=true]')!==null");
  await js("document.querySelector('#desafio-partida form>button:last-child').click()");await ready("document.querySelectorAll('.desafio-etapa').length===4");
  const antes=await js("document.querySelector('.desafio-etapa span').textContent");
  await js("document.querySelectorAll('.desafio-etapa')[1].querySelector('button').click()");
  assert.notEqual(await js("document.querySelector('.desafio-etapa span').textContent"),antes);
  console.log('Conexoes, conversas, cinco jogos, correcao e sequencia: OK');
  const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,'desktop.png'),Buffer.from(shot.data,'base64'));
  await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await sleep(300);
  assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
  assert.equal(await js("document.getElementById('explorar-nav').getBoundingClientRect().top>=document.querySelector('.conta-superior').getBoundingClientRect().bottom"),true);
  const mobile=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,'mobile.png'),Buffer.from(mobile.data,'base64'));
  assert.deepEqual(erros,[]);
  console.log('Celular sem overflow; nenhum erro JavaScript. Capturas: '+temp);
 }finally{
  if(socket){try{await command('Browser.close');}catch{}socket.close();}
  server.kill();browser.kill();
 }
})().catch(e=>{console.error(e);process.exitCode=1;});
