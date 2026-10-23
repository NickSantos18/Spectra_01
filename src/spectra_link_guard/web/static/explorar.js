/* Abas, conexões e jogos; pontuação e desbloqueios são conferidos pela API. */
window.SpectraExplorar = (() => {
  let api,no,executar,publicacoes,contatos,eu,aba='feed',versao=0;
  let catalogo=[],jogoAtual=null,faseAtual=1;
  const el=id=>document.getElementById(id);
  const areas=['feed','publicar','conexoes','conversas','desafios'];
  function icones(){if(window.lucide)window.lucide.createIcons();}
  function linkPerfil(u){const a=no('a',u.nome);a.href='/painel/perfil?usuario='+encodeURIComponent(u.id);return a;}
  async function mudar(){
    const solicitada=location.hash.slice(1);aba=areas.includes(solicitada)?solicitada:'feed';
    const atual=++versao;
    document.querySelectorAll('[data-explorar]').forEach(a=>{if(a.dataset.explorar===aba)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
    const nav=el('explorar-nav'),ativa=nav.querySelector('[aria-current=page]');
    if(ativa)nav.scrollLeft=ativa.offsetLeft-nav.clientWidth/2+ativa.offsetWidth/2;
    el('publicacoes').hidden=!['feed','publicar'].includes(aba);
    el('form-publicacao').hidden=aba!=='publicar';el('lista-publicacoes').hidden=aba!=='feed';
    el('chat').hidden=aba!=='conversas';el('explorar-conexoes').hidden=aba!=='conexoes';el('explorar-desafios').hidden=aba!=='desafios';
    el('aviso').textContent='';
    if(aba==='feed')await publicacoes();
    if(aba==='conversas')await contatos();
    if(aba==='conexoes')await conexoes(atual);
    if(aba==='desafios')await carregarCatalogo(atual);
  }
  async function conexoes(atual){
    const resultados=await Promise.all(['seguindo','seguidores'].map(t=>api('/api/conexoes/'+t)));
    if(atual!==versao)return;
    ['seguindo','seguidores'].forEach((tipo,i)=>{
      const lista=resultados[i],destino=el('lista-'+tipo);destino.replaceChildren();el('total-'+tipo).textContent='('+lista.length+')';
      if(!lista.length)destino.append(no('p',tipo==='seguindo'?'Você ainda não segue ninguém. Conheça os autores no Feed.':'Seus seguidores aparecerão aqui.'));
      for(const u of lista){const linha=no('div',undefined,'conexao-item');const a=linkPerfil(u);a.className='autor-perfil';
        if(u.foto){const img=no('img',undefined,'avatar-mini');img.src=u.foto;img.alt='';a.prepend(img);}linha.append(a);
        const seguir=no('button',u.seguindo?'Deixar de seguir':'Seguir de volta');seguir.type='button';
        seguir.onclick=executar(async()=>{seguir.disabled=true;try{await api(`/api/usuarios/${u.id}/seguir`,u.seguindo?'DELETE':'POST');await conexoes(versao);}finally{seguir.disabled=false;}});
        const conversar=no('a','Conversar');conversar.href='#conversas';linha.append(seguir,conversar);destino.append(linha);
      }
    });
  }
  async function carregarCatalogo(atual=versao){
    const dados=await api('/api/desafios');if(atual!==versao)return;catalogo=dados;
    const destino=el('desafios-catalogo');destino.replaceChildren();
    const pontos=dados.reduce((s,j)=>s+j.pontos,0),fases=dados.reduce((s,j)=>s+j.concluidas,0);
    el('desafios-resumo').textContent=`${fases} de 15 fases concluídas · ${pontos} pontos · Progresso salvo na sua conta`;
    for(const j of dados){const card=no('article',undefined,'social-card desafio-card');const icone=no('i');icone.dataset.lucide=j.icone;icone.setAttribute('aria-hidden','true');
      const titulo=no('h3',j.nome);card.append(icone,titulo,no('p',j.descricao),no('p',`${j.concluidas}/${j.total_fases} fases · ${j.pontos} pontos`,'post-meta'));
      const progresso=no('progress');progresso.max=j.total_fases;progresso.value=j.concluidas;progresso.setAttribute('aria-label','Fases concluídas em '+j.nome);card.append(progresso);
      const botao=no('button',j.concluidas===j.total_fases?'Jogar novamente':j.concluidas?'Continuar':'Começar');botao.type='button';
      botao.onclick=executar(()=>abrirFase(j.id,j.proxima>j.total_fases?1:j.proxima));card.append(botao);destino.append(card);
    }icones();
  }
  async function abrirFase(id,fase){
    const dados=await api(`/api/desafios/${id}/fases/${fase}`);
    if(aba!=='desafios')return;
    jogoAtual=id;faseAtual=fase;
    const destino=el('desafio-partida');destino.hidden=false;destino.replaceChildren();el('desafios-catalogo').hidden=true;
    const voltar=no('button','Voltar às trilhas');voltar.type='button';voltar.onclick=executar(async()=>{destino.hidden=true;el('desafios-catalogo').hidden=false;await carregarCatalogo();});
    const titulo=no('h3',dados.titulo);titulo.id='desafio-titulo';titulo.tabIndex=-1;
    destino.append(voltar,no('p',`Fase ${fase} de ${dados.total_fases}`,'post-meta'),titulo,no('p',dados.contexto));
    const form=no('form',undefined,'social-form'),feedback=no('p');feedback.setAttribute('role','status');feedback.className='desafio-feedback';
    let itens=dados.itens.slice(),escolhida=null;
    const opcoes=no(dados.modo==='ordem'?'ol':'fieldset',undefined,'desafio-opcoes');
    function montar(){opcoes.replaceChildren();
      if(dados.modo==='ordem'){
        itens.forEach((item,i)=>{const linha=no('li',undefined,'desafio-etapa');linha.append(no('span',item.texto));
          for(const [texto,passo] of [['Subir',-1],['Descer',1]]){const b=no('button',texto);b.type='button';b.disabled=i+passo<0||i+passo>=itens.length;b.setAttribute('aria-label',texto+': '+item.texto);
            b.onclick=()=>{const destino=i+passo;[itens[i],itens[destino]]=[itens[destino],itens[i]];montar();const foco=opcoes.children[destino].querySelectorAll('button')[passo===-1?0:1];if(!foco.disabled)foco.focus();};linha.append(b);}
          opcoes.append(linha);
        });
      }else{opcoes.append(no('legend','Escolha uma alternativa'));itens.forEach(item=>{const label=no('label',undefined,'desafio-alternativa'),radio=no('input');radio.type='radio';radio.name='alternativa';radio.value=item.id;radio.required=true;radio.onchange=()=>{escolhida=item.id;};label.append(radio,no('span',item.texto));opcoes.append(label);});}
    }montar();
    const confirmar=no('button','Conferir resposta');confirmar.type='submit';form.append(opcoes,confirmar,feedback);
    form.onsubmit=executar(async()=>{
      if(dados.modo==='escolha'&&escolhida===null)return;
      confirmar.disabled=true;
      try{const r=await api(`/api/desafios/${id}/fases/${fase}/responder`,'POST',{itens:dados.modo==='ordem'?itens.map(i=>i.id):[escolhida]});
        feedback.textContent=(r.acertou?'Acertou! ':'Tente novamente. ')+r.feedback+(r.acertou?` +${r.pontos_fase} pontos nesta tentativa.`:'');feedback.dataset.acertou=String(r.acertou);
        if(r.acertou){form.querySelectorAll('input,button').forEach(b=>b.disabled=true);
          const proximo=no('button',fase<dados.total_fases?'Próxima fase':'Trilha concluída! Ver progresso');proximo.type='button';proximo.onclick=executar(async()=>{if(fase<dados.total_fases)await abrirFase(id,fase+1);else{destino.hidden=true;el('desafios-catalogo').hidden=false;await carregarCatalogo();}});form.append(proximo);
          await carregarCatalogo();
        }else confirmar.disabled=false;
      }catch(e){confirmar.disabled=false;throw e;}
    });
    destino.append(form);titulo.focus();destino.scrollIntoView({block:'start',behavior:'auto'});
  }
  async function iniciar(contexto){
    ({api,no,executar,publicacoes,contatos,eu}=contexto);el('explorar-nav').hidden=false;
    window.addEventListener('hashchange',executar(mudar));await mudar();
  }
  return {iniciar,abaAtual:()=>aba};
})();
