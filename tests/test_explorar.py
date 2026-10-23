import base64
from fastapi.testclient import TestClient
from spectra_link_guard.web.app import app, PARCIAIS
from spectra_link_guard.web.desafios import JOGOS

PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aR1cAAAAASUVORK5CYII=')


def conta(email):
    c=TestClient(app)
    r=c.post('/api/auth/cadastrar',json={'nome':'Pessoa Teste','email':email,'senha':'Senha-forte123!'})
    assert r.status_code==201
    return c,r.json()['usuario']['id']


def test_conexoes_direcionais_e_privadas():
    a,aid=conta('a@example.com');b,bid=conta('b@example.com');c,_=conta('c@example.com')
    a.post('/api/usuarios/'+bid+'/seguir')
    assert a.get('/api/conexoes/seguindo').json()[0]['id']==bid
    assert a.get('/api/conexoes/seguidores').json()==[]
    assert b.get('/api/conexoes/seguidores').json()[0]['id']==aid
    assert c.get('/api/conexoes/seguidores').json()==[]
    assert set(b.get('/api/conexoes/seguidores').json()[0])=={'id','nome','foto','seguindo'}
    assert TestClient(app).get('/api/conexoes/seguidores').status_code==401


def test_midias_ownership_publicacao_range_e_exclusao():
    a,aid=conta('a@example.com');b,_=conta('b@example.com');anon=TestClient(app)
    url='/api/midias'
    assert anon.post(url,content=PNG,headers={'content-type':'image/png'}).status_code==401
    assert a.post(url,content=b'<script/>',headers={'content-type':'image/png'}).status_code==415
    up=a.post(url,content=PNG,headers={'content-type':'image/png'})
    assert up.status_code==201
    midia=up.json()['id'];url=up.json()['url']
    assert b.get(url).status_code==404
    assert anon.get(url).status_code==401
    post={'titulo':'Foto de segurança','texto':'Um exemplo para discutir segurança.','midias':[midia]}
    assert b.post('/api/comunidade/forum',json=post).status_code==403
    assert b.get('/api/comunidade/forum').json()==[]
    r=a.post('/api/comunidade/forum',json=post);assert r.status_code==201
    ident=r.json()['id']
    feed=b.get('/api/comunidade/explorar').json()
    assert feed[0]['midias'][0]['url']==url
    arquivo=b.get(url);assert arquivo.content==PNG
    assert arquivo.headers['x-content-type-options']=='nosniff'
    faixa=b.get(url,headers={'Range':'bytes=2-5'})
    assert faixa.status_code==206 and faixa.content==PNG[2:6]
    assert b.get(url,headers={'Range':'bytes=-4'}).content==PNG[-4:]
    assert b.get(url,headers={'Range':'bytes=99999-'}).status_code==416
    assert b.get(url,headers={'Range':'bytes='+'9'*100+'-'}).status_code==416
    assert b.head(url).headers['content-length']==str(len(PNG))
    assert a.post('/api/comunidade/forum',json=post).status_code==403
    assert a.delete('/api/publicacoes/'+ident).status_code==200
    assert b.get(url).status_code==404 and a.get(url).status_code==404


def test_video_tipo_e_limites():
    a,_=conta('a@example.com')
    mp4=b'\x00\x00\x00\x18ftypisom\x00\x00\x00\x00isommp42'
    up=a.post('/api/midias',content=mp4,headers={'content-type':'video/mp4'})
    assert up.status_code==201 and up.json()['tipo']=='video'
    assert a.get(up.json()['url'],headers={'Range':'bytes=0-7'}).content==mp4[:8]
    assert a.post('/api/midias',content=PNG,headers={'content-type':'text/html'}).status_code==415
    assert a.post('/api/midias',content=b'a'*(10*1024*1024+1),headers={'content-type':'image/png'}).status_code==413
    assert a.post('/api/midias',content=PNG,headers={'content-type':'image/png','Origin':'https://outro.invalid'}).status_code==403


def test_cinco_trilhas_sequenciais_correcao_e_progresso_isolado():
    a,_=conta('a@example.com');b,_=conta('b@example.com')
    anon=TestClient(app)
    assert anon.get('/api/desafios').status_code==401
    assert len(a.get('/api/desafios').json())==5
    for id,jogo in JOGOS.items():
        assert a.get(f'/api/desafios/{id}/fases/2').status_code==403
        assert a.post(f'/api/desafios/{id}/fases/2/responder',json={'itens':jogo['fases'][1]['correta']}).status_code==403
        for fase,f in enumerate(jogo['fases'],1):
            dados=a.get(f'/api/desafios/{id}/fases/{fase}').json()
            assert 'correta' not in dados and 'explicacao' not in dados
            assert len(dados['itens'])>=3
            resp=a.post(f'/api/desafios/{id}/fases/{fase}/responder',json={'itens':f['correta'],'pontos':999999})
            assert resp.status_code==200 and resp.json()['acertou']
            assert resp.json()['progresso']['concluidas']==fase
        repetir=a.post(f'/api/desafios/{id}/fases/1/responder',json={'itens':jogo['fases'][0]['correta']})
        assert repetir.json()['progresso']['pontos']==300
    assert sum(j['pontos'] for j in a.get('/api/desafios').json())==1500
    assert sum(j['pontos'] for j in b.get('/api/desafios').json())==0
    assert a.get('/api/desafios/nao-existe/fases/1').status_code==404


def test_tentativa_errada_nao_desbloqueia_e_nao_fabrica_pontos():
    a,_=conta('a@example.com')
    endpoint='/api/desafios/phishing/fases/1/responder'
    assert a.post(endpoint,json={'itens':['invalido']}).status_code==422
    errada=a.post(endpoint,json={'itens':['0']}).json()
    assert not errada['acertou'] and errada['progresso']['proxima']==1
    certa=a.post(endpoint,json={'itens':JOGOS['phishing']['fases'][0]['correta']}).json()
    assert certa['pontos_fase']==85 and certa['progresso']['proxima']==2
    assert a.post('/api/desafios/phishing/fases/2/responder',json={'itens':['0','0','1','2']}).status_code==422


def test_conversas_moraram_no_explorar():
    menu=(PARCIAIS/'menu.html').read_text(encoding='utf-8')
    assert 'data-menu="chat"' not in menu
    a,_=conta('a@example.com')
    html=a.get('/painel/explorar').text
    for aba in ('feed','publicar','conexoes','conversas','desafios'):
        assert f'data-explorar="{aba}"' in html
