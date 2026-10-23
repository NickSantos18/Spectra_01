"""Cinco trilhas educativas; correção e progresso ficam no servidor."""
import random
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from ..auth import bd
from .comunidade import exigir, data

router=APIRouter()
bd.registrar_esquema("""
CREATE TABLE IF NOT EXISTS desafio_fases (
 usuario_id TEXT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
 jogo TEXT NOT NULL, fase INTEGER NOT NULL, tentativas INTEGER NOT NULL DEFAULT 0,
 melhor_pontos INTEGER NOT NULL DEFAULT 0, concluida INTEGER NOT NULL DEFAULT 0,
 atualizado_em TEXT NOT NULL, PRIMARY KEY(usuario_id,jogo,fase));
""")


def ordem(titulo, contexto, itens, explicacao):
    return {'titulo':titulo,'contexto':contexto,'modo':'ordem','itens':[{'id':str(i),'texto':t} for i,t in enumerate(itens)],'correta':[str(i) for i in range(len(itens))],'explicacao':explicacao}


def escolha(titulo, contexto, opcoes, correta, explicacao):
    return {'titulo':titulo,'contexto':contexto,'modo':'escolha','itens':[{'id':str(i),'texto':t} for i,t in enumerate(opcoes)],'correta':[str(correta)],'explicacao':explicacao}


JOGOS={
 'phishing':{'nome':'Investigue o phishing','icone':'scan-search','descricao':'Analise mensagens e escolha uma verificação segura.','fases':[
    escolha('A conta vai ser bloqueada?','Chegou uma mensagem urgente pedindo sua senha para evitar o bloqueio. Qual é o próximo passo mais seguro?',
      ['Responder com a senha para ganhar tempo','Abrir o serviço pelo aplicativo conhecido e conferir o aviso','Encaminhar o código de autenticação ao remetente'],1,
      'Verifique por um canal independente que você já conhece. Urgência e pedido de senha são sinais de alerta.'),
    ordem('Rotina de verificação','Neste exercício, organize a rotina: observe a mensagem, confira o endereço sem abri-lo, confirme por outro canal e reporte o golpe.',
      ['Observar remetente, urgência e pedido da mensagem','Conferir o domínio exibido sem acessar o link','Confirmar a solicitação pelo aplicativo ou canal oficial conhecido','Reportar a mensagem suspeita e encerrar o contato'],
      'A confirmação independente evita depender da própria mensagem suspeita.'),
    escolha('O cadeado é suficiente?','O link suspeito usa HTTPS e tem um cadeado. O que isso permite concluir?',
      ['Que a empresa é confiável','Que não pode existir phishing nessa página','Que a conexão é criptografada, mas a página ainda pode ser falsa'],2,
      'HTTPS protege a conexão; não atesta a honestidade do responsável pelo site.') ]},
 'conta':{'nome':'Proteja uma conta','icone':'shield-check','descricao':'Complete missões de senha, autenticação e recuperação.','fases':[
    escolha('Escolha uma senha','Você está criando uma conta fictícia. Qual estratégia é mais adequada?',
      ['Reutilizar a senha principal com um número no final','Usar uma senha longa e exclusiva, guardada em um gerenciador','Usar nome, aniversário e símbolo'],1,
      'Uma senha exclusiva reduz o efeito de vazamentos em outros serviços. Não digite senhas reais nos jogos.'),
    ordem('Ative a segunda camada','Siga o roteiro desta simulação: abrir as configurações, configurar o autenticador, confirmar o código e guardar a recuperação.',
      ['Abrir as configurações de segurança da conta fictícia','Vincular um autenticador seguindo as instruções do serviço','Confirmar o código para concluir a ativação','Guardar os códigos de recuperação em local protegido'],
      'Os códigos de recuperação ajudam a recuperar acesso se você perder o autenticador. Nunca os compartilhe.'),
    escolha('Pedido de código','Uma pessoa se diz do suporte e pede o código temporário da sua conta. Como agir?',
      ['Não compartilhar e procurar o suporte pelo canal conhecido','Enviar se a pessoa souber seu nome','Compartilhar só o primeiro código'],0,
      'Códigos de autenticação também permitem acesso. Saber seu nome não prova que o contato seja legítimo.') ]},
 'incidente':{'nome':'Reconstrua o incidente','icone':'route','descricao':'Organize pistas e encontre a linha do tempo de um caso fictício.','fases':[
    ordem('Quatro pistas','Ordene as evidências do registro fictício da mais antiga para a mais recente.',
      ['08:10 — Uma mensagem com anexo chega à caixa de entrada','08:14 — O anexo é aberto no computador','08:16 — O sistema registra a execução de um programa desconhecido','08:20 — O monitoramento gera um alerta'],
      'Ordenar evidências ajuda a reconstruir os fatos. A sequência temporal, sozinha, não prova a causa.'),
    escolha('Evidência ou hipótese?','O alerta veio após abrir o anexo. Qual afirmação mantém a investigação precisa?',
      ['O remetente foi identificado como criminoso com certeza','Não é necessário olhar os registros','É uma hipótese de relação que precisa ser confirmada pelas evidências'],2,
      'Diferencie o que os registros mostram das hipóteses que ainda precisam de confirmação.'),
    ordem('Preparar o relato','Neste exercício, monte um relato para a equipe responsável sem apagar ou alterar os registros originais.',
      ['Registrar horários e a origem das evidências disponíveis','Organizar os eventos em uma linha do tempo','Separar fatos confirmados das hipóteses','Encaminhar o relato à equipe responsável pelo incidente'],
      'Preserve os registros originais e siga o procedimento da sua organização. Este jogo não substitui um plano de resposta.') ]},
 'defesa':{'nome':'Monte a defesa','icone':'castle','descricao':'Escolha proteções para uma pequena empresa simulada.','fases':[
    escolha('Acesso aos documentos','Todos usam a mesma conta para acessar documentos da empresa fictícia. Qual melhoria ajuda a controlar os acessos?',
      ['Criar contas individuais e dar somente as permissões necessárias','Compartilhar a senha em mais grupos','Desativar os registros de acesso'],0,
      'Contas individuais e permissões adequadas ajudam a limitar o acesso e a rastrear ações.'),
    ordem('Missão de backup','Organize este roteiro de implantação de backup, terminando com a verificação de que a cópia funciona.',
      ['Identificar quais dados precisam ser recuperados','Definir a frequência e um destino protegido para as cópias','Configurar e executar a rotina de backup','Testar a restauração e registrar o resultado'],
      'Uma cópia precisa ser recuperável. Testar a restauração é parte da proteção dos dados.'),
    escolha('Atualização disponível','Uma correção de segurança está disponível no canal oficial do sistema. Qual caminho é adequado?',
      ['Baixar uma correção enviada por um desconhecido','Planejar a aplicação pelo processo oficial, considerando backup e compatibilidade','Ignorar todas as atualizações para sempre'],1,
      'Use fontes oficiais e um processo de atualização apropriado ao ambiente. Evite instaladores enviados por contatos desconhecidos.') ]},
 'links':{'nome':'Detetive de links','icone':'link','descricao':'Reconheça o domínio real e endereços que tentam confundir.','fases':[
    escolha('De quem é este endereço?','No exemplo https://login.banco.exemplo.invalid/conta, qual é o nome completo do host? Os endereços do jogo são fictícios e não devem ser abertos.',
      ['conta','login.banco.exemplo.invalid','https'],1,
      'O host fica entre o esquema e a próxima barra. Caminho e nome do host têm papéis diferentes.'),
    escolha('Marca escondida','O endereço https://banco.exemplo.invalid.site-teste.invalid/login pertence ao mesmo host de https://banco.exemplo.invalid/?',
      ['Não: o primeiro host termina em site-teste.invalid','Sim: basta conter banco.exemplo','Sim: ambos usam HTTPS'],0,
      'Uma marca no início pode ser apenas um subdomínio. Leia o host inteiro, inclusive sua parte final.'),
    ordem('Leia a estrutura','Ordene os componentes de https://conta.exemplo.invalid:8443/ajuda?tema=senha#topo, da esquerda para a direita.',
      ['https:// — esquema','conta.exemplo.invalid:8443 — host e porta','/ajuda — caminho','?tema=senha — consulta','#topo — fragmento'],
      'Separar os componentes ajuda a entender o destino. Não use palavras do caminho como prova da identidade do domínio.') ]},
}


def resumo(con,usuario,jogo):
    rows=con.execute('SELECT * FROM desafio_fases WHERE usuario_id=? AND jogo=?',(usuario,jogo)).fetchall()
    feitas={r['fase'] for r in rows if r['concluida']}
    atual=next((i for i in range(1,len(JOGOS[jogo]['fases'])+1) if i not in feitas),len(JOGOS[jogo]['fases'])+1)
    return {'concluidas':len(feitas),'proxima':atual,'pontos':sum(r['melhor_pontos'] for r in rows)}


@router.get('/api/desafios')
def catalogo(request:Request):
    u=exigir(request)
    with bd.conexao() as con:
        return [{'id':id,'nome':j['nome'],'icone':j['icone'],'descricao':j['descricao'],'total_fases':len(j['fases']),**resumo(con,u['id'],id)} for id,j in JOGOS.items()]


def fase_disponivel(con,usuario,jogo,fase):
    if jogo not in JOGOS:raise HTTPException(404,'Desafio não encontrado.')
    if fase<1 or fase>len(JOGOS[jogo]['fases']):raise HTTPException(404,'Fase não encontrada.')
    if fase>resumo(con,usuario,jogo)['proxima']:raise HTTPException(403,'Conclua a fase anterior para avançar.')
    return JOGOS[jogo]['fases'][fase-1]


@router.get('/api/desafios/{jogo}/fases/{fase}')
def carregar(jogo:str,fase:int,request:Request):
    u=exigir(request)
    with bd.conexao() as con:f=fase_disponivel(con,u['id'],jogo,fase)
    itens=list(f['itens']);random.SystemRandom().shuffle(itens)
    return {k:f[k] for k in ('titulo','contexto','modo')}|{'itens':itens,'fase':fase,'total_fases':len(JOGOS[jogo]['fases'])}


class Resposta(BaseModel):
    itens:list[str]=Field(min_length=1,max_length=10)


@router.post('/api/desafios/{jogo}/fases/{fase}/responder')
def responder(jogo:str,fase:int,p:Resposta,request:Request):
    u=exigir(request)
    with bd.conexao() as con:
        # Serializa tentativas simultâneas antes de conferir o desbloqueio.
        con.execute('BEGIN IMMEDIATE')
        f=fase_disponivel(con,u['id'],jogo,fase)
        ids={i['id'] for i in f['itens']}
        if len(p.itens)!=len(set(p.itens)) or not set(p.itens)<=ids or (f['modo']=='ordem' and set(p.itens)!=ids) or (f['modo']=='escolha' and len(p.itens)!=1):
            raise HTTPException(422,'Selecione uma alternativa ou organize todos os itens sem repetir.')
        antes=con.execute('SELECT tentativas FROM desafio_fases WHERE usuario_id=? AND jogo=? AND fase=?',(u['id'],jogo,fase)).fetchone()
        tentativas=antes['tentativas'] if antes else 0
        acertou=p.itens==f['correta'];pontos=max(25,100-tentativas*15) if acertou else 0
        con.execute('''INSERT INTO desafio_fases VALUES (?,?,?,?,?,?,?)
          ON CONFLICT(usuario_id,jogo,fase) DO UPDATE SET tentativas=desafio_fases.tentativas+1,
          melhor_pontos=MAX(desafio_fases.melhor_pontos,excluded.melhor_pontos),
          concluida=MAX(desafio_fases.concluida,excluded.concluida),atualizado_em=excluded.atualizado_em''',
          (u['id'],jogo,fase,tentativas+1,pontos,int(acertou),data()))
        progresso=resumo(con,u['id'],jogo)
    return {'acertou':acertou,'pontos_fase':pontos,'feedback':f['explicacao'] if acertou else 'Ainda não. Releia as pistas do cenário e tente novamente.','progresso':progresso}
