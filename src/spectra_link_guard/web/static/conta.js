/* Conta global. A cena interativa de entrada fica em perfil-cofre.js. */
(() => {
  let perfilPromise = null;
  window.spectraCarregarPerfil = (atualizar = false) => {
    if (atualizar) perfilPromise = null;
    if (!perfilPromise) perfilPromise = fetch('/api/perfil').then(async resposta => {
      const dados = await resposta.json();
      if (!resposta.ok) throw Error(dados.erro || 'Não foi possível carregar o perfil.');
      return dados;
    }).catch(erro => { perfilPromise = null; throw erro; });
    return perfilPromise;
  };
  async function iniciar() {
    const acesso = document.querySelector('[data-perfil-acesso]');
    if (!acesso) return;
    document.querySelectorAll('[data-sair]').forEach(botao => botao.addEventListener('click', async () => {
      botao.disabled = true;
      try {
        const resposta = await fetch('/api/auth/sair', { method: 'POST' });
        if (!resposta.ok) throw Error('Falha ao sair');
        location.assign('/inicio');
      } catch {
        botao.disabled = false;
        window.avisarToast?.('Não foi possível sair. Tente novamente.', 'erro');
      }
    }));
    try {
      const resposta = await fetch('/api/auth/eu');
      if (!resposta.ok) return;
      const { usuario } = await resposta.json();
      if (!usuario) return;
      document.querySelectorAll('[data-conta-nome]').forEach(no => { no.textContent = usuario.nome; });
      document.querySelectorAll('[data-conta-inicial]').forEach(no => { no.textContent = usuario.nome.trim().charAt(0).toUpperCase(); });
      acesso.setAttribute('aria-label', 'Abrir perfil de ' + usuario.nome);
      document.querySelector('[data-conta]').hidden = false;
      document.body.classList.add('com-conta');
      const perfil = await window.spectraCarregarPerfil();
      if (perfil.foto) document.querySelectorAll('[data-conta-inicial]').forEach(no => {
        const img = document.createElement('img');
        img.src = perfil.foto; img.alt = ''; img.className = 'conta-foto'; no.replaceChildren(img);
      });
    } catch { /* A navegação permanece disponível mesmo se a consulta falhar. */ }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar, { once: true });
  else iniciar();
})();
