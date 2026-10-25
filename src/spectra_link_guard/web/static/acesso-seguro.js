(() => {
  const token=new URLSearchParams(location.hash.slice(1)).get('token');
  history.replaceState({},'',location.pathname);
  const aviso=document.getElementById('acesso-mensagem'),form=document.getElementById('nova-senha');
  const redefinir=location.pathname==='/redefinir-senha';
  document.getElementById('acesso-titulo').textContent=redefinir?'Redefinir senha':'Confirmar e-mail';
  async function enviar(url,dados){
    const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(dados)});
    const d=await r.json();if(!r.ok)throw Error(d.erro||'Não foi possível concluir.');return d;
  }
  if(!token){aviso.textContent='Link incompleto. Solicite um novo link.';return;}
  if(!redefinir){
    aviso.textContent='Confirmando seu e-mail…';
    enviar('/api/auth/confirmar-email',{token}).then(d=>{aviso.textContent=d.mensagem;}).catch(e=>{aviso.textContent=e.message;});
    return;
  }
  form.hidden=false;
  form.addEventListener('submit',async e=>{
    e.preventDefault();const senha=document.getElementById('senha').value;
    if(senha!==document.getElementById('senha-confirmar').value){aviso.textContent='As senhas não conferem.';return;}
    const botao=form.querySelector('button');botao.disabled=true;
    try{const d=await enviar('/api/auth/redefinir-senha',{token,senha});form.reset();form.hidden=true;aviso.textContent=d.mensagem;}
    catch(erro){aviso.textContent=erro.message;}finally{botao.disabled=false;}
  });
})();
