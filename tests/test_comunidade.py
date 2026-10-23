"""Isolamento de conversas, perfil privado e autorização do blog."""
from fastapi.testclient import TestClient
from spectra_link_guard.web.app import app


def conta(email, nome="Pessoa Teste"):
    c = TestClient(app)
    r = c.post('/api/auth/cadastrar', json={'nome': nome, 'email': email, 'senha': 'Senha-forte123!'})
    assert r.status_code == 201, r.text
    return c, r.json()['usuario']['id']


def test_perfil_e_foto_privacidade():
    a, _ = conta('a@example.com')
    b, _ = conta('b@example.com')
    assert TestClient(app).get('/api/perfil').status_code == 401
    assert a.put('/api/perfil', json={'nome': 'Nome atualizado', 'bio': 'Pesquisa de segurança', 'foto': ''}).status_code == 200
    p = a.get('/api/perfil').json()
    assert p['nome'] == 'Nome atualizado' and 'ip' in p
    assert 'senha_hash' not in p
    assert b.get('/api/comunidade/usuarios').json() == []
    assert b.post('/api/usuarios/'+p['id']+'/seguir').status_code == 200
    dados = b.get('/api/comunidade/usuarios').json()[0]
    assert set(dados) == {'id', 'nome', 'foto'}
    assert a.put('/api/perfil', json={'nome': 'Nome Teste', 'foto': 'data:image/svg+xml,<svg/>'}).status_code == 422
    assert a.put('/api/perfil', json={'nome': 'Nome Teste'}, headers={'Origin':'https://outro.example'}).status_code == 403


def test_mensagens_so_para_participantes():
    a, aid = conta('a@example.com')
    b, bid = conta('b@example.com')
    c, _ = conta('c@example.com')
    assert a.post('/api/chat/'+bid, json={'texto':'Sem vínculo'}).status_code == 403
    assert a.post('/api/usuarios/'+bid+'/seguir').status_code == 200
    assert a.post('/api/chat/'+bid, json={'texto':'Mensagem privada'}).status_code == 201
    assert b.get('/api/chat/'+aid).json()[0]['texto'] == 'Mensagem privada'
    assert c.get('/api/chat/'+aid).status_code == 403
    assert c.get('/api/chat/'+bid).status_code == 403
    assert a.post('/api/chat/'+bid, json={'texto':'   '}).status_code == 422
    assert a.post('/api/chat/inexistente', json={'texto':'Olá'}).status_code == 404
    assert a.delete('/api/usuarios/'+bid+'/seguir').status_code == 200
    assert b.post('/api/chat/'+aid, json={'texto':'Sem vínculo'}).status_code == 403
    assert a.get('/api/comunidade/usuarios').json() == []


def test_forum_e_convite_de_especialista(monkeypatch):
    monkeypatch.setenv('SPECTRA_EDITOR_EMAILS','editor@example.com')
    editor, _ = conta('editor@example.com')
    autor, _ = conta('autor@example.com')
    outro, _ = conta('outro@example.com')
    post={'titulo':'Dicas de segurança', 'texto':'Como se proteger contra phishing.'}
    assert autor.post('/api/comunidade/blog', json=post).status_code == 403
    assert autor.post('/api/blog/convites', json={'email':'outro@example.com'}).status_code == 403
    convite=editor.post('/api/blog/convites', json={'email':'autor@example.com'})
    assert convite.status_code == 201
    token=convite.json()['link'].split('convite=')[1]
    assert outro.post('/api/blog/aceitar',json={'token':token}).status_code == 403
    assert autor.post('/api/blog/aceitar',json={'token':token}).status_code == 200
    assert autor.post('/api/blog/aceitar',json={'token':token}).status_code == 403
    assert autor.post('/api/comunidade/blog',json=post).status_code == 201
    r=autor.post('/api/comunidade/forum',json=post)
    assert r.status_code == 201
    ident=r.json()['id']
    assert outro.post(f'/api/publicacoes/{ident}/respostas',json={'texto':'Boa discussão!'}).status_code == 201
    assert len(autor.get(f'/api/publicacoes/{ident}/respostas').json()) == 1
    assert outro.delete('/api/publicacoes/'+ident).status_code == 404
    assert autor.delete('/api/publicacoes/'+ident).status_code == 200
    assert outro.get(f'/api/publicacoes/{ident}/respostas').json() == []


def test_paginas_exigem_login():
    anonimo = TestClient(app)
    for pagina in ('perfil','chat','blog','forum','explorar'):
        assert anonimo.get('/painel/'+pagina, follow_redirects=False).status_code == 303
    usuario, _ = conta('a@example.com')
    for pagina in ('perfil','chat','blog','forum','explorar'):
        r = usuario.get('/painel/'+pagina)
        assert r.status_code == 200
        menu = 'explorar' if pagina == 'chat' else pagina
        assert f'data-menu="{menu}" aria-current="page"' in r.text
        esperado = {'perfil':'energia-perfil', 'chat':'explorar', 'blog':'ondas', 'forum':'forum', 'explorar':'explorar'}.get(pagina)
        if esperado:
            assert f'data-efeito="{esperado}"' in r.text
        assert '__FUNDO_COMUNIDADE__' not in r.text
        assert r.text.count('class="conta-superior"') == 1
        assert '/static/conta.js?v=' in r.text
    redirecionado=usuario.get('/painel/chat',follow_redirects=False)
    assert redirecionado.headers['location']=='/painel/explorar#conversas'


def test_explorar_agrega_posts_e_estado_seguindo(monkeypatch):
    monkeypatch.setenv('SPECTRA_EDITOR_EMAILS','editor@example.com')
    autor, aid = conta('editor@example.com')
    leitor, lid = conta('leitor@example.com')
    for tipo in ('blog','forum'):
        assert autor.post('/api/comunidade/'+tipo, json={'titulo':'Publicação de teste','texto':'Conteúdo para explorar e seguir autores.'}).status_code == 201
    feed = leitor.get('/api/comunidade/explorar').json()
    assert {p['tipo'] for p in feed} == {'blog','forum'}
    assert all(not p['seguindo'] for p in feed)
    assert leitor.post('/api/usuarios/'+aid+'/seguir').status_code == 200
    assert leitor.post('/api/usuarios/'+aid+'/seguir').status_code == 200
    assert len(leitor.get('/api/comunidade/usuarios').json()) == 1
    assert all(p['seguindo'] for p in leitor.get('/api/comunidade/explorar').json())
    assert leitor.post('/api/usuarios/'+lid+'/seguir').status_code == 404
    assert autor.post('/api/chat/'+lid,json={'texto':'Resposta ao meu seguidor'}).status_code == 201
    assert leitor.get('/api/chat/'+aid).json()[0]['texto'] == 'Resposta ao meu seguidor'


def test_perfil_de_membro_autenticado_e_publicacoes():
    autor, aid = conta('autor@example.com', 'Autora Teste')
    leitor, lid = conta('leitor@example.com')
    anonimo = TestClient(app)
    assert anonimo.get('/api/usuarios/'+aid+'/perfil').status_code == 401
    assert anonimo.get('/api/comunidade/explorar?autor='+aid).status_code == 401
    assert anonimo.get('/painel/perfil?usuario='+aid, follow_redirects=False).status_code == 303
    autor.put('/api/perfil', json={'nome':'Autora Teste', 'bio':'Pesquisadora de segurança', 'foto':''})
    for cliente, titulo in [(autor,'Postagem da autora'), (leitor,'Postagem do leitor')]:
        assert cliente.post('/api/comunidade/forum',json={'titulo':titulo,'texto':'Conteúdo de cibersegurança para testes.'}).status_code == 201
    membro = leitor.get('/api/usuarios/'+aid+'/perfil')
    assert membro.status_code == 200
    assert set(membro.json()) == {'id','nome','criado_em','bio','foto','seguindo','total_publicacoes'}
    assert membro.json()['bio'] == 'Pesquisadora de segurança'
    assert membro.json()['total_publicacoes'] == 1
    posts = leitor.get('/api/comunidade/explorar?autor='+aid).json()
    assert len(posts) == 1 and posts[0]['autor'] == aid
    assert posts[0]['titulo'] == 'Postagem da autora'
    assert leitor.get('/api/usuarios/inexistente/perfil').status_code == 404
    assert leitor.get('/api/usuarios/'+lid+'/perfil').json()['total_publicacoes'] == 1
    assert leitor.get('/painel/perfil?usuario='+aid).status_code == 200
