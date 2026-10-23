/* Dados de usuários são inseridos apenas como texto, nunca como HTML. */
(() => {
  const el = id => document.getElementById(id);
  const pagina = location.pathname.split('/').pop();
  const perfilVisitado=pagina==='perfil'?new URLSearchParams(location.search).get('usuario'):null;
  let eu, contato = null, ultima = 0, foto = '', carregando = false, buscaVersao = 0;
  let fotoOriginal=null;
  let arquivosMidia=[],previewsMidia=[],uploadsMidia=new Map();
  const titulos = {perfil:'Perfil',chat:'Conversas',explorar:'Explorar',blog:'Blog de especialistas',forum:'Fórum de cibersegurança'};
  function aviso(texto, erro=false){el('aviso').textContent=texto;el('aviso').dataset.erro=erro;}
  function no(tag,texto,classe){const n=document.createElement(tag);if(texto!==undefined)n.textContent=texto;if(classe)n.className=classe;return n;}
  async function api(url,method='GET',dados){
    const r=await fetch(url,{method,headers:dados?{'Content-Type':'application/json'}:{},body:dados?JSON.stringify(dados):undefined});
    let d;try{d=await r.json();}catch{throw Error('O servidor não respondeu. Tente novamente.');}
    if(!r.ok)throw Error(typeof d.erro==='string'?d.erro:typeof d.detail==='string'?d.detail:'Confira os campos e tente novamente.');
    return d;
  }
  const executar = fn => async evento => {if(evento)evento.preventDefault();try{await fn(evento);}catch(e){aviso(e.message,true);}};
  function horario(data){return new Date(data).toLocaleString('pt-BR');}
  function linkPerfil(id,nome){const a=no('a',nome);a.href='/painel/perfil?usuario='+encodeURIComponent(id);return a;}
  function estadoSeguir(id,seguindo){document.querySelectorAll('[data-seguir]').forEach(b=>{if(b.dataset.seguir===id){b.textContent=seguindo?'Seguindo':'Seguir';b.setAttribute('aria-pressed',String(seguindo));}});}
  function preview(){el('foto-preview').hidden=!foto;el('foto-inicial').hidden=!!foto;el('foto-preview').src=foto;el('ajustar-foto').hidden=!foto;el('foto-inicial').textContent=el('nome').value.trim().slice(0,1).toUpperCase();window.dispatchEvent(new Event('spectra:perfil-pronto'));}
  async function iniciar(){
    eu=await (window.spectraCarregarPerfil?window.spectraCarregarPerfil():api('/api/perfil'));
    document.title=`${titulos[pagina]} · Spectra`;el('titulo').textContent=titulos[pagina];
    if(pagina==='explorar'){
      el('compor-titulo').textContent='Compartilhar com a comunidade';
      await window.SpectraExplorar.iniciar({api,no,executar,publicacoes,contatos,eu});return;
    }
    if(pagina==='perfil'){
      if(perfilVisitado){await mostrarMembro();return;}
      el('perfil').hidden=false;foto=eu.foto;fotoOriginal=foto||null;el('nome').value=eu.nome;el('bio').value=eu.bio;el('email').textContent=eu.email;el('identificador').textContent=eu.id;el('ip').textContent=eu.ip;el('criado').textContent=horario(eu.criado_em);preview();
      el('publicacoes').hidden=false;el('perfil-postagens').hidden=false;el('perfil-postagens').textContent='Minhas publicações';await publicacoes();
    }else if(pagina==='chat'){el('chat').hidden=false;await contatos();}
    else{
      el('publicacoes').hidden=false;
      const token=new URLSearchParams(location.search).get('convite');
      if(token&&pagina==='blog'){
        await api('/api/blog/aceitar','POST',{token});history.replaceState({},'',location.pathname);eu=await api('/api/perfil');aviso('Convite aceito! Você já pode publicar no blog.');
      }
      el('form-publicacao').hidden=pagina==='blog'&&!eu.pode_publicar;el('blog-info').hidden=pagina!=='blog'||eu.pode_publicar;el('convites').hidden=pagina!=='blog'||!eu.editor;el('compor-titulo').textContent=pagina==='blog'?'Escrever artigo':'Compartilhar com a comunidade';await publicacoes();
    }
  }
  async function mostrarMembro(){
    const membro=await api('/api/usuarios/'+encodeURIComponent(perfilVisitado)+'/perfil');
    el('titulo').textContent='Perfil de '+membro.nome;document.title=membro.nome+' · Spectra';
    el('perfil-membro').hidden=false;el('membro-nome').textContent=membro.nome;
    el('membro-bio').textContent=membro.bio||'Este membro ainda não adicionou uma biografia.';
    el('membro-total').textContent=membro.total_publicacoes+' publicação(ões)';
    el('membro-foto').hidden=!membro.foto;el('membro-inicial').hidden=!!membro.foto;
    el('membro-foto').src=membro.foto;el('membro-inicial').textContent=membro.nome.charAt(0).toUpperCase();
    const seguir=el('membro-seguir');seguir.hidden=membro.id===eu.id;
    el('membro-editar').hidden=membro.id!==eu.id;seguir.dataset.seguir=membro.id;estadoSeguir(membro.id,!!membro.seguindo);
    seguir.onclick=executar(async()=>{seguir.disabled=true;try{const d=await api('/api/usuarios/'+membro.id+'/seguir',seguir.getAttribute('aria-pressed')==='true'?'DELETE':'POST');estadoSeguir(membro.id,d.seguindo);}finally{seguir.disabled=false;}});
    el('publicacoes').hidden=false;el('perfil-postagens').hidden=false;await publicacoes();
  }
  el('nome').addEventListener('input',preview);
  el('alterar-foto').onclick=()=>el('foto').click();
  el('foto').addEventListener('change',executar(async()=>{
    const arquivo=el('foto').files[0];if(!arquivo)return;
    try {
      const ajustada=await window.SpectraFoto.abrir(arquivo);
      if(ajustada){foto=ajustada;fotoOriginal=arquivo;preview();aviso('Foto ajustada. Clique em Salvar perfil para guardar a alteração.');}
    }finally{el('foto').value='';}
  }));
  el('ajustar-foto').onclick=executar(async()=>{
    if(!fotoOriginal)return;
    const ajustada=await window.SpectraFoto.abrir(fotoOriginal);
    if(ajustada){foto=ajustada;preview();aviso('Foto ajustada. Clique em Salvar perfil para guardar a alteração.');}
  });
  el('remover-foto').onclick=()=>{foto='';fotoOriginal=null;el('foto').value='';preview();};
  el('form-perfil').addEventListener('submit',executar(async()=>{
    await api('/api/perfil','PUT',{nome:el('nome').value,bio:el('bio').value,foto});
    document.querySelectorAll('[data-conta-nome]').forEach(n=>n.textContent=el('nome').value.trim());
    document.querySelector('[data-perfil-acesso]')?.setAttribute('aria-label','Abrir perfil de '+el('nome').value.trim());
    document.querySelectorAll('[data-conta-inicial]').forEach(n=>{
      if(foto){const img=no('img');img.src=foto;img.alt='';img.className='conta-foto';n.replaceChildren(img);}
      else n.textContent=el('nome').value.trim().charAt(0).toUpperCase();
    });
    aviso('Perfil atualizado.');
  }));
  async function contatos(){
    const versao=++buscaVersao;const lista=await api('/api/comunidade/usuarios?busca='+encodeURIComponent(el('busca').value));if(versao!==buscaVersao)return;
    el('contatos').replaceChildren();if(!lista.length)el('contatos').append(no('p','Nenhuma conexão encontrada. Vá ao Explorar e siga o autor de uma publicação para conversar.'));
    for(const u of lista){const b=no('button');b.type='button';b.dataset.id=u.id;b.setAttribute('aria-pressed',String(contato===u.id));if(u.foto){const img=no('img',undefined,'avatar-mini');img.src=u.foto;img.alt='';b.append(img);}b.append(no('span',u.nome));b.onclick=executar(async()=>{contato=u.id;ultima=0;el('mensagens').replaceChildren();el('contato-nome').replaceChildren(linkPerfil(u.id,u.nome));el('mensagem').disabled=false;el('enviar').disabled=false;document.querySelectorAll('[data-id]').forEach(n=>n.setAttribute('aria-pressed',String(n.dataset.id===contato)));await mensagens();el('mensagem').focus();});el('contatos').append(b);}
  }
  let atraso;el('busca').addEventListener('input',()=>{clearTimeout(atraso);atraso=setTimeout(executar(contatos),250);});
  async function mensagens(){
    if(!contato||carregando)return;carregando=true;const alvo=contato;
    try{const lista=await api(`/api/chat/${alvo}?depois=${ultima}`);if(contato!==alvo)return;
      for(const m of lista){const b=no('div',m.texto,'balao'+(m.remetente===eu.id?' minha':''));const t=no('time',horario(m.criado_em));t.dateTime=m.criado_em;b.append(t);el('mensagens').append(b);ultima=Math.max(ultima,m.id);}
      if(lista.length)el('mensagens').scrollTop=el('mensagens').scrollHeight;
    }finally{carregando=false;}
  }
  el('form-mensagem').addEventListener('submit',executar(async()=>{if(!contato)return;el('enviar').disabled=true;try{await api('/api/chat/'+contato,'POST',{texto:el('mensagem').value});el('mensagem').value='';await mensagens();}finally{el('enviar').disabled=false;}}));
  setInterval(()=>{if((pagina==='chat'||(pagina==='explorar'&&window.SpectraExplorar.abaAtual()==='conversas'))&&!document.hidden)executar(mensagens)();},3000);
  async function publicacoes(){
    const endereco=pagina==='perfil'?'/api/comunidade/explorar?autor='+encodeURIComponent(perfilVisitado||eu.id):'/api/comunidade/'+pagina;
    const lista=await api(endereco);el('lista-publicacoes').replaceChildren();
    if(!lista.length)el('lista-publicacoes').append(no('p',pagina==='perfil'?'Nenhuma publicação por aqui ainda.':pagina==='blog'?'Os primeiros artigos dos especialistas aparecerão aqui.':'Ainda não há discussões. Comece a primeira!'));
    for(const p of lista){
      const card=no('article',undefined,'social-card');
      const cabecalho=no('div',undefined,'post-autor');
      const autor=linkPerfil(p.autor,p.autor_nome);autor.className='autor-perfil';
      if(p.autor_foto){const img=no('img',undefined,'avatar-mini');img.src=p.autor_foto;img.alt='';autor.prepend(img);}
      cabecalho.append(autor,no('span',p.tipo==='blog'?'Blog':'Comunidade','post-meta'));
      if(p.autor!==eu.id){
        const seguir=no('button',p.seguindo?'Seguindo':'Seguir');seguir.type='button';seguir.dataset.seguir=p.autor;seguir.setAttribute('aria-pressed',String(!!p.seguindo));
        seguir.onclick=executar(async()=>{seguir.disabled=true;try{const d=await api(`/api/usuarios/${p.autor}/seguir`,seguir.getAttribute('aria-pressed')==='true'?'DELETE':'POST');estadoSeguir(p.autor,d.seguindo);aviso(d.seguindo?'Você está seguindo '+p.autor_nome+'. Essa pessoa já aparece nas suas conversas.':'Você deixou de seguir '+p.autor_nome+'.');}finally{seguir.disabled=false;}});cabecalho.append(seguir);
      }
      card.append(cabecalho,no('h2',p.titulo),no('p',horario(p.criado_em),'post-meta'),no('div',p.texto,'post-corpo'));
      if(p.midias?.length){const galeria=no('div',undefined,'post-midias');
        for(const m of p.midias){const item=no(m.tipo==='video'?'video':'img');item.src=m.url;
          if(m.tipo==='video'){item.controls=true;item.preload='metadata';item.playsInline=true;}
          else{item.alt=p.titulo;item.loading='lazy';}
          galeria.append(item);
        }card.append(galeria);
      }
      const acoes=no('div',undefined,'post-acoes');const abrir=no('button',`Comentários (${p.respostas})`);abrir.type='button';acoes.append(abrir);const area=no('div',undefined,'respostas');area.hidden=true;
      async function comentarios(){area.replaceChildren();const rs=await api(`/api/publicacoes/${p.id}/respostas`);if(!rs.length)area.append(no('p','Seja a primeira pessoa a comentar.'));for(const r of rs){const box=no('div',undefined,'resposta');box.append(linkPerfil(r.autor,r.autor_nome),no('p',r.texto),no('small',horario(r.criado_em)));area.append(box);}const form=no('form',undefined,'social-form');const label=no('label','Seu comentário');const campo=no('textarea');campo.id='resposta-'+p.id;label.htmlFor=campo.id;campo.required=true;campo.maxLength=4000;campo.rows=3;const enviar=no('button','Comentar');form.append(label,campo,enviar);form.addEventListener('submit',executar(async()=>{enviar.disabled=true;try{await api(`/api/publicacoes/${p.id}/respostas`,'POST',{texto:campo.value});p.respostas++;abrir.textContent=`Comentários (${p.respostas})`;await comentarios();}finally{enviar.disabled=false;}}));area.append(form);}
      abrir.onclick=executar(async()=>{area.hidden=!area.hidden;abrir.setAttribute('aria-expanded',String(!area.hidden));if(!area.hidden)await comentarios();});abrir.setAttribute('aria-expanded','false');
      if(p.autor===eu.id||eu.editor){const excluir=no('button','Excluir publicação');excluir.type='button';excluir.onclick=executar(async()=>{if(!confirm('Excluir esta publicação e seus comentários?'))return;await api('/api/publicacoes/'+p.id,'DELETE');await publicacoes();});acoes.append(excluir);}
      card.append(acoes,area);el('lista-publicacoes').append(card);
    }
  }
  function mostrarMidias(){
    previewsMidia.forEach(url=>URL.revokeObjectURL(url));previewsMidia=[];el('midias-preview').replaceChildren();
    for(const arquivo of arquivosMidia){const url=URL.createObjectURL(arquivo);previewsMidia.push(url);const bloco=no('div',undefined,'midia-previa');const item=no(arquivo.type.startsWith('video/')?'video':'img');item.src=url;
      if(item.tagName==='VIDEO'){item.controls=true;item.preload='metadata';}else item.alt='Prévia de '+arquivo.name;
      const remover=no('button','Remover');remover.type='button';remover.setAttribute('aria-label','Remover '+arquivo.name);remover.onclick=()=>{arquivosMidia=arquivosMidia.filter(a=>a!==arquivo);mostrarMidias();};bloco.append(item,no('small',arquivo.name),remover);el('midias-preview').append(bloco);
    }
  }
  el('post-midias').addEventListener('change',executar(async()=>{
    const arquivos=[...el('post-midias').files];el('post-midias').value='';
    if(arquivosMidia.length+arquivos.length>4)throw Error('Selecione no máximo 4 arquivos por publicação.');
    for(const a of arquivos){if(!['image/png','image/jpeg','image/webp','video/mp4','video/webm'].includes(a.type))throw Error('Use foto PNG, JPEG ou WebP, ou vídeo MP4 ou WebM.');if(a.size>(a.type.startsWith('video/')?40:10)*1024*1024)throw Error('Limite por arquivo: fotos de 10 MB e vídeos de 40 MB.');}
    arquivosMidia.push(...arquivos);mostrarMidias();
  }));
  window.addEventListener('pagehide',()=>previewsMidia.forEach(url=>URL.revokeObjectURL(url)));
  el('form-publicacao').addEventListener('submit',executar(async()=>{
    const b=el('form-publicacao').querySelector('button[type="submit"]');b.disabled=true;
    const selecionados=arquivosMidia.slice();
    try{
      const midias=[];
      for(const [i,arquivo] of selecionados.entries()){
        b.textContent=`Enviando arquivo ${i+1}/${selecionados.length}…`;
        if(!uploadsMidia.has(arquivo)){
          const r=await fetch('/api/midias',{method:'POST',headers:{'Content-Type':arquivo.type},body:arquivo});const d=await r.json();if(!r.ok)throw Error(d.erro||d.detail||'Falha ao enviar arquivo.');uploadsMidia.set(arquivo,d.id);
        }midias.push(uploadsMidia.get(arquivo));
      }
      b.textContent='Publicando…';await api('/api/comunidade/'+(pagina==='explorar'?'forum':pagina),'POST',{titulo:el('post-titulo').value,texto:el('post-texto').value,midias});
      el('form-publicacao').reset();arquivosMidia=[];uploadsMidia.clear();mostrarMidias();aviso('Publicação criada.');
      if(pagina==='explorar'){location.hash='feed';}else await publicacoes();
    }finally{b.disabled=false;b.textContent='Publicar';}
  }));
  el('form-convite').addEventListener('submit',executar(async()=>{const d=await api('/api/blog/convites','POST',{email:el('email-convite').value});el('link-convite').replaceChildren(no('span','Compartilhe este link com o especialista: '));const link=no('a',d.link);link.href=d.link;el('link-convite').append(link);}));
  executar(iniciar)();
})();
