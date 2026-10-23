/* A rolagem permanece nativa. A cena interpola os passos da roda do mouse
   com um relógio independente da taxa de quadros e para quando se acomoda. */
(() => {
  const raiz=document.documentElement;
  const historia=document.getElementById('inicio-historia');
  if(!historia)return;
  const palco=historia.querySelector('.inicio-palco');
  const identidade=document.getElementById('inicio-identidade');
  const apresentacao=document.getElementById('apresentacao');
  const conteudo=historia.querySelector('.inicio-apresentacao-conteudo');
  const convite=historia.querySelector('.inicio-convite');
  const rolar=document.getElementById('inicio-rolar');
  const etapa=document.getElementById('inicio-etapa');
  const letras=[...historia.querySelectorAll('#manchete .letra')];
  const logo=historia.querySelector('.inicio-logo');
  const ambiente=historia.querySelector('.inicio-ambiente');
  const portal=historia.querySelector('.inicio-portal');
  const sobretitulo=historia.querySelector('.inicio-sobretitulo');
  let estilos=new WeakMap(),estado='',identidadeOculta=null;
  let exibido=null,ultimoQuadro=0;
  let ativo=false,inicio=0,distancia=1,pedido=0,focoPendente=false;
  const limitar=n=>Math.max(0,Math.min(1,n));
  const suave=(a,b,n)=>{const t=limitar((n-a)/(b-a));return t*t*(3-2*t);};
  const movimento=()=>window.spectraMovimentoLigado?window.spectraMovimentoLigado():raiz.dataset.movimento!=='off';
  const numero=n=>Number(n.toFixed(4));
  function estilo(elemento,nome,valor){
    let anterior=estilos.get(elemento);
    if(!anterior){anterior={};estilos.set(elemento,anterior);}
    if(anterior[nome]===valor)return;
    anterior[nome]=valor;elemento.style[nome]=valor;
  }

  function pintar(agora){
    pedido=0;
    if(!ativo||document.hidden){ultimoQuadro=0;return;}
    const bruto=(window.scrollY-inicio)/distancia,alvo=limitar(bruto);
    const dt=ultimoQuadro?Math.min(64,agora-ultimoQuadro):1000/60;
    ultimoQuadro=agora;
    if(exibido===null||bruto<-.05||bruto>1.05)exibido=alvo;
    else exibido+=(alvo-exibido)*(1-Math.exp(-dt/95));
    const acomodado=Math.abs(alvo-exibido)<.00015;
    if(acomodado)exibido=alvo;
    const p=exibido;
    historia.dataset.progresso=p.toFixed(3);
    // Atualizar diretamente as superfícies evita recalcular variáveis CSS
    // herdadas por toda a árvore da apresentação a cada quadro.
    estilo(logo,'transform',`scale(${numero(1+suave(0,.6,p)*3.2)})`);
    estilo(logo,'opacity',numero(1-suave(.14,.4,p)));
    estilo(logo,'willChange',p<.4?'transform, opacity':'auto');
    estilo(apresentacao,'opacity',numero(suave(.25,.35,p)));
    const entrada=suave(.43,.65,p),subida=`translate3d(0,${numero((1-entrada)*22)}px,0)`;
    for(const elemento of [sobretitulo,convite]){
      estilo(elemento,'opacity',numero(entrada));estilo(elemento,'transform',subida);
    }
    estilo(ambiente,'opacity',numero(.35+suave(.18,.65,p)*.32));
    estilo(ambiente,'transform',`scale(${numero(1+suave(0,.6,p)*.06)})`);
    estilo(portal,'opacity',numero(.2+Math.sin(suave(.08,.65,p)*Math.PI)*.45));
    estilo(portal,'transform',`scale(${numero(1+suave(0,.65,p)*.9)})`);
    letras.forEach((letra,i)=>{
      const t=suave(.25+i*.0032,.44+i*.0032,p);
      estilo(letra,'opacity',numero(t));
      estilo(letra,'transform',`translate3d(0,${numero((1-t)*32)}px,0)`);
    });
    const pronto=p>=.65,proximo=p<.18?'01':pronto?'03':'02';
    if(estado!==proximo){
      estado=proximo;apresentacao.inert=!pronto;
      apresentacao.setAttribute('aria-hidden',String(!pronto));
      convite.style.pointerEvents=pronto?'':'none';
      etapa.textContent=proximo;
      rolar.href=pronto?'#inicio-recursos':'#apresentacao';
      rolar.firstElementChild.textContent=pronto?'Continue para explorar':'Role para explorar';
    }
    if(identidadeOculta!==(p>.4)){
      identidadeOculta=p>.4;identidade.setAttribute('aria-hidden',String(identidadeOculta));
    }
    if(pronto&&focoPendente){focoPendente=false;apresentacao.focus({preventScroll:true});}
    if(!acomodado)agendar();else ultimoQuadro=0;
  }

  function agendar(){if(ativo&&!pedido&&!document.hidden)pedido=requestAnimationFrame(pintar);}

  function medir(){
    // Conteúdo ampliado, paisagem baixa e movimento reduzido usam o fluxo
    // normal. Nenhum formulário fica preso dentro de uma cena menor que ele.
    ativo=movimento()&&window.innerHeight>=540&&conteudo.scrollHeight<=window.innerHeight-16;
    raiz.dataset.inicioRolagem=ativo?'on':'off';
    const caixa=historia.getBoundingClientRect();
    inicio=caixa.top+window.scrollY;
    distancia=Math.max(1,historia.offsetHeight-palco.offsetHeight);
    if(!ativo){
      cancelAnimationFrame(pedido);pedido=0;ultimoQuadro=0;exibido=null;estado='';identidadeOculta=null;
      historia.dataset.progresso='0';apresentacao.inert=false;
      apresentacao.removeAttribute('aria-hidden');identidade.removeAttribute('aria-hidden');
      convite.style.pointerEvents='';
      for(const elemento of [logo,ambiente,portal,apresentacao,sobretitulo,convite,...letras]){
        for(const propriedade of ['opacity','transform','will-change'])elemento.style.removeProperty(propriedade);
      }
      estilos=new WeakMap();
      rolar.href='#apresentacao';rolar.firstElementChild.textContent='Role para explorar';etapa.textContent='01';
    }
    agendar();
  }

  document.querySelectorAll('a[href="#apresentacao"],a[href="#conteudo"]').forEach(link=>{
    link.addEventListener('click',evento=>{
      if(evento.ctrlKey||evento.metaKey||evento.shiftKey||evento.altKey)return;
      if(link===rolar&&rolar.hash==='#inicio-recursos'){
        evento.preventDefault();const recursos=document.getElementById('inicio-recursos');
        recursos.scrollIntoView({behavior:movimento()?'smooth':'auto'});recursos.focus({preventScroll:true});return;
      }
      evento.preventDefault();
      if(ativo){focoPendente=true;window.scrollTo({top:inicio+distancia*.82,behavior:'smooth'});}
      else{apresentacao.scrollIntoView({behavior:'auto'});apresentacao.focus({preventScroll:true});}
    });
  });
  window.addEventListener('scroll',agendar,{passive:true});
  window.addEventListener('resize',medir,{passive:true});
  window.addEventListener('pageshow',medir);
  window.addEventListener('spectra:movimento',medir);
  document.addEventListener('visibilitychange',()=>{
    ultimoQuadro=0;if(document.hidden){cancelAnimationFrame(pedido);pedido=0;}else agendar();
  });
  if('ResizeObserver' in window){
    const observador=new ResizeObserver(medir);
    observador.observe(conteudo);observador.observe(historia);
  }
  document.fonts?.ready.then(medir);
  medir();
})();
