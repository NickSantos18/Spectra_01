"""Regressões: não ignorar confusão de marca nem confundir falta de dados com confiança."""
from spectra_link_guard import analisar_url, ConfiguracaoLinkGuard
from spectra_link_guard.models import AnaliseLink, ResultadoReputacao, StatusReputacao

OFFLINE=ConfiguracaoLinkGuard(verificar_tls=False,verificar_reputacao=False,verificar_registro=False)


def test_marca_curta_com_repeticao_nao_depende_do_dominio_oficial_longo():
    r=analisar_url('https://steeam.com/',OFFLINE)
    achado=next(a for a in r.achados if a.codigo=='marca_com_letra_repetida')
    assert achado.evidencia['marca']=='steam'
    assert 'steampowered.com' in achado.evidencia['oficiais']
    assert r.risco>=30
    assert r.nivel.value in ('atencao','alto','critico')
    assert not next(c for c in r.checklist if c.codigo=='imitacao_de_marca').passou


def test_regra_de_repeticao_preserva_oficiais_e_palavras_diferentes():
    for url in ['https://store.steampowered.com/','https://steamcommunity.com/','https://www.netflix.com/','https://stream.com/']:
        assert not any(a.codigo=='marca_com_letra_repetida' for a in analisar_url(url,OFFLINE).achados)


def test_download_executavel_codificado_e_identificado():
    r=analisar_url('https://exemplo.com/instalador%2eexe',OFFLINE)
    assert any(a.codigo=='download_executavel' for a in r.achados)


def test_exemplos_de_video_sem_reputacao_sao_verificacao_limitada():
    for url in ['https://www.tokyvideo.com/br/filmes','https://www.pobreflixtv.sale/']:
        dados=analisar_url(url,OFFLINE).to_dict()
        assert dados['verificacao']['limitada']
        assert dados['verificacao']['provedores_consultados']==[]
        assert 'não confirma' in dados['verificacao']['motivo']


def test_erro_desconhecido_e_falta_de_chaves_nao_contam_como_reputacao_limpa():
    r=AnaliseLink(url_original='https://exemplo.com')
    for status in [StatusReputacao.ERRO,StatusReputacao.DESCONHECIDO,StatusReputacao.NAO_CONFIGURADO]:
        r.reputacao=[ResultadoReputacao('teste',status)]
        assert r.verificacao['limitada']
    for status in [StatusReputacao.LIMPO,StatusReputacao.MALICIOSO]:
        r.reputacao=[ResultadoReputacao('teste',status)]
        assert not r.verificacao['limitada']
        assert r.verificacao['provedores_consultados']==['teste']
