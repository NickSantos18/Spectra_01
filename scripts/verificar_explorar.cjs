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

async function verificarAcesso(){
  await js("fetch('/api/auth/sair',{method:'POST'}).then(r=>{if(!r.ok)throw Error('Logout falhou')})");
  await command('Page.navigate',{url:'http://127.0.0.1:8012/inicio'});
  await ready("document.readyState==='complete'&&typeof abrirModal==='function'");
  assert.equal(await js("getComputedStyle(document.getElementById('modal')).display"),'none');
  for(const aba of ['entrar','cadastrar']){
    await js(`document.querySelector('.inicio-acoes [data-abrir="${aba}"]').click()`);
    assert.equal(await js("getComputedStyle(document.getElementById('modal')).display"),'flex');
    assert.equal(await js(`document.getElementById('painel-${aba}').hidden`),false);
    assert.ok(await js("document.getElementById('modal-caixa').getBoundingClientRect().width>300"));
    await js("document.getElementById('fechar-modal').click()");
  }
  assert.equal(await js("document.getElementById('botao-google').getAttribute('aria-disabled')"),'true');
  await js("abrirModal('entrar');document.getElementById('entrar-email').value='visual@example.com';document.getElementById('esqueci').click()");
  await ready("document.getElementById('painel-entrar').textContent.includes('Recuperação por e-mail ainda não configurada')");
  for(const largura of [390,1440]){
    await command('Emulation.setDeviceMetricsOverride',{width:largura,height:900,deviceScaleFactor:1,mobile:largura<600});
    assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
    const shot=await command('Page.captureScreenshot',{format:'png'});
    fs.writeFileSync(path.join(temp,'acesso-'+largura+'.png'),Buffer.from(shot.data,'base64'));
  }
  for(const pagina of ['confirmar-email','redefinir-senha']){
    await command('Page.navigate',{url:'http://127.0.0.1:8012/'+pagina});
    await ready("document.getElementById('acesso-mensagem')?.textContent.includes('Link incompleto')");
    assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true);
  }
  assert.deepEqual(erros,[]);
  console.log('Acesso com CSP: CSS local, modais, aviso Google, recuperação indisponível, links incompletos e celular: OK. Capturas: '+temp);
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
  assert.ok(new Set(amostras.filter(a=>a.p>.005&&a.p<.295).map(a=>a.p)).size>=4,'A roda deve produzir posições intermediárias: '+JSON.stringify(amostras));
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
  const png='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4////fwAJ+wP9KobjigAAAABJRU5ErkJggg==';
  await js(`fetch('/api/perfil',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:'Pessoa Visual',bio:'Teste do perfil',foto:${JSON.stringify(png)}})}).then(r=>{if(!r.ok)throw Error('Perfil falhou')})`);
  async function origem(comFoto=true){
    await command('Page.navigate',{url:'http://127.0.0.1:8012/painel/explorar'});
    await ready("location.pathname==='/painel/explorar'&&document.body.classList.contains('com-conta')&&"+(comFoto?"!!document.querySelector('.conta-avatar img')":"document.querySelector('.conta-avatar').textContent==='P'"));
  }
  async function abrir(){
    await js("document.querySelector('[data-perfil-acesso]').click()");
    await ready("document.documentElement.dataset.perfilTransicao==='aguardando'");
    assert.equal(await js("document.querySelector('[data-perfil-cofre]').open"),true);
    assert.equal(await js("location.pathname"),'/painel/explorar');
  }
  const captura=async nome=>{const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(temp,nome+'.png'),Buffer.from(shot.data,'base64'));};
  for(const pagina of ['/painel','/painel/visao-geral','/painel/historico','/painel/explorar','/painel/blog','/painel/forum','/painel/aprender','/privacidade','/termos']){
    await command('Page.navigate',{url:'http://127.0.0.1:8012'+pagina});
    await ready(`location.pathname===${JSON.stringify(pagina)}&&document.body.classList.contains('com-conta')`);
    assert.equal(await js("document.querySelectorAll('[data-perfil-cofre]').length"),1,pagina);
    assert.equal(await js('document.documentElement.scrollWidth<=innerWidth'),true,pagina);
  }
  await origem();
  const avatarOrigem=await js("(()=>{const r=document.querySelector('.conta-avatar').getBoundingClientRect();return {x:r.left,y:r.top,width:r.width}})()");
  await js("document.querySelector('[data-perfil-acesso]').click()");
  await ready("document.documentElement.dataset.perfilTransicao==='abertura'");
  await js("document.getAnimations().filter(a=>a.effect.target?.closest?.('[data-perfil-cofre],.perfil-cofre-voo')).forEach(a=>{a.pause();a.currentTime=0})");
  const avatarVoo=await js("(()=>{const r=document.querySelector('.perfil-cofre-voo').getBoundingClientRect();return {x:r.left,y:r.top,width:r.width}})()");
  assert.ok(Math.abs(avatarOrigem.x-avatarVoo.x)<1&&Math.abs(avatarOrigem.y-avatarVoo.y)<1&&Math.abs(avatarOrigem.width-avatarVoo.width)<1,'A foto deve iniciar no botao real.');
  await js("document.getAnimations().filter(a=>a.effect.target?.closest?.('[data-perfil-cofre],.perfil-cofre-voo')).forEach(a=>a.currentTime=470)");
  assert.equal(await js("document.querySelector('[data-cofre-foto] img').src"),png);
  await captura('cofre-01-foto');
  await js("document.getAnimations().filter(a=>a.effect.target?.closest?.('[data-perfil-cofre],.perfil-cofre-voo')).forEach(a=>a.play())");
  await ready("document.documentElement.dataset.perfilTransicao==='aguardando'");
  await captura('cofre-02-cadeado');
  assert.equal(await js("document.querySelector('[data-cofre-pular],.perfil-cofre-cabecalho')===null"),true);
  assert.equal(await js("(()=>{const d=document.querySelector('[data-perfil-cofre]').getBoundingClientRect(),s=document.querySelector('.trilho').getBoundingClientRect();return d.left>=s.right&&!!document.elementFromPoint(s.left+20,s.top+180)?.closest('.trilho')})()"),true,'A barra lateral deve permanecer visivel e acessivel.');
  assert.equal(await js("(()=>{const a=document.querySelector('.perfil-cofre-palco').getBoundingClientRect(),b=document.querySelector('.perfil-cofre-instrucoes').getBoundingClientRect();return b.top-a.bottom>=8&&b.top-a.bottom<=24})()"),true);
  assert.equal(await js("getComputedStyle(document.querySelector('[data-perfil-cofre]')).backgroundColor===getComputedStyle(document.body).backgroundColor"),true);
  await command('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
  await command('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
  await ready("!document.querySelector('[data-perfil-cofre]').open&&!document.documentElement.dataset.perfilTransicao");
  assert.equal(await js("document.activeElement===document.querySelector('[data-perfil-acesso]')"),true);
  await abrir();
  const pontos=await js("(()=>{const a=document.querySelector('[data-cofre-chave]').getBoundingClientRect(),b=document.querySelector('[data-cofre-fechadura]').getBoundingClientRect();return {x:a.left+a.width*.75,y:a.top+a.height/2,alvoX:b.left+b.width/2,alvoY:b.top+b.height/2}})()");
  await command('Input.dispatchMouseEvent',{type:'mousePressed',x:pontos.x,y:pontos.y,button:'left',clickCount:1});
  await command('Input.dispatchMouseEvent',{type:'mouseMoved',x:40,y:350,button:'left',buttons:1});
  await command('Input.dispatchMouseEvent',{type:'mouseReleased',x:40,y:350,button:'left',clickCount:1});
  assert.equal(await js("document.documentElement.dataset.perfilTransicao"),'aguardando');
  await command('Input.dispatchMouseEvent',{type:'mousePressed',x:pontos.x,y:pontos.y,button:'left',clickCount:1});
  for(let i=1;i<=8;i++)await command('Input.dispatchMouseEvent',{type:'mouseMoved',x:pontos.x+(pontos.alvoX-pontos.x)*i/8,y:pontos.y+(pontos.alvoY-pontos.y)*i/8,button:'left',buttons:1});
  await command('Input.dispatchMouseEvent',{type:'mouseReleased',x:pontos.alvoX,y:pontos.alvoY,button:'left',clickCount:1});
  await ready("document.documentElement.dataset.perfilTransicao==='fragmentando'");
  await js("document.querySelector('[data-perfil-cofre]').getAnimations({subtree:true}).forEach(a=>{a.pause();a.currentTime=200})");
  await captura('cofre-03-fragmentos');
  await js("document.querySelector('[data-perfil-cofre]').getAnimations({subtree:true}).forEach(a=>a.play())");
  await ready("location.pathname==='/painel/perfil'&&!document.documentElement.classList.contains('perfil-cofre-chegando')&&!document.getElementById('perfil').hidden");
  assert.equal(await js("document.getElementById('nome').value"),'Pessoa Visual');
  assert.equal(await js("sessionStorage.getItem('spectra:perfil-cofre')"),null);
  await captura('cofre-04-perfil');
  // Teclado: a chave e o cadeado são botões reais e não exigem arrasto.
  await origem();await abrir();
  assert.equal(await js("document.activeElement===document.querySelector('[data-cofre-chave]')"),true);
  await command('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r',unmodifiedText:'\r'});
  await command('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
  assert.equal(await js("document.querySelector('[data-cofre-chave]').getAttribute('aria-pressed')"),'true');
  await command('Input.dispatchKeyEvent',{type:'keyDown',key:'Tab',code:'Tab',windowsVirtualKeyCode:9,modifiers:8});
  await command('Input.dispatchKeyEvent',{type:'keyUp',key:'Tab',code:'Tab',windowsVirtualKeyCode:9,modifiers:8});
  assert.equal(await js("document.activeElement===document.querySelector('[data-cofre-cadeado]')"),true);
  await command('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r',unmodifiedText:'\r'});
  await command('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
  await ready("location.pathname==='/painel/perfil'&&!document.documentElement.dataset.perfilTransicao");
  await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await command('Emulation.setTouchEmulationEnabled',{enabled:true});
  await js("localStorage.setItem('spectra:tema','claro')");
  await origem();await abrir();await captura('cofre-05-celular-claro');
  assert.equal(await js("(()=>{const b=document.querySelector('.barra-abas').getBoundingClientRect(),d=document.querySelector('[data-perfil-cofre]').getBoundingClientRect();return d.bottom<=b.top&&!!document.elementFromPoint(b.left+20,b.top+20)?.closest('.barra-abas')})()"),true);
  const toque=await js("(()=>{const a=document.querySelector('[data-cofre-chave]').getBoundingClientRect(),b=document.querySelector('[data-cofre-fechadura]').getBoundingClientRect();return {x:a.left+a.width*.75,y:a.top+a.height/2,alvoX:b.left+b.width/2,alvoY:b.top+b.height/2}})()");
  await command('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:toque.x,y:toque.y}]});
  await command('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:toque.alvoX,y:toque.alvoY}]});
  await command('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
  await ready("location.pathname==='/painel/perfil'&&!document.documentElement.dataset.perfilTransicao");
  await js("fetch('/api/perfil',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({nome:'Pessoa Visual',bio:'Teste sem foto',foto:''})}).then(r=>{if(!r.ok)throw Error('Perfil sem foto falhou')})");
  await origem(false);await abrir();
  assert.equal(await js("document.querySelector('[data-cofre-foto]').textContent"),'P');
  await js("document.querySelector('[data-cofre-cancelar]').click()");
  await ready("location.pathname==='/painel/explorar'&&!document.documentElement.dataset.perfilTransicao");
  await abrir();
  await js("document.querySelector('.barra-abas a[href=\"/painel/historico\"]').click()");
  await ready("location.pathname==='/painel/historico'&&!document.documentElement.dataset.perfilTransicao");
  // Preferência reduzida: acesso direto e sem cena bloqueando a página.
  await origem(false);
  await js("localStorage.setItem('spectra:movimento','off');document.documentElement.dataset.movimento='off';document.querySelector('[data-perfil-acesso]').click()");
  await ready("location.pathname==='/painel/perfil'&&!document.getElementById('perfil').hidden");
  assert.equal(await js("document.querySelector('[data-perfil-cofre]').open"),false);
  assert.equal(await js("document.documentElement.dataset.perfilTransicao||null"),null);
  await js("localStorage.setItem('spectra:movimento','on');localStorage.setItem('spectra:tema','escuro')");
  await command('Emulation.setTouchEmulationEnabled',{enabled:false});
  await command('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
  assert.deepEqual(erros,[]);
  console.log('Perfil: voo desde o botao, barra lateral acessivel, espacamento, arrasto, teclado, toque, cancelar, navegacao e movimento reduzido: OK. Capturas: '+temp);
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
  if(process.argv.includes('--acesso')){await verificarAcesso();return;}
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
  const png=path.join(temp,'teste.png');fs.writeFileSync(png,Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4////fwAJ+wP9KobjigAAAABJRU5ErkJggg==','base64'));
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
