"""Nome legível de cada código de achado, para os gráficos da Visão geral.

O título do próprio achado não serve: varia com a análise ("Domínio quase
igual ao de 'itau'"). Aqui é um nome fixo por código. Um teste confere que
todo código de achado do analisador tem nome.
"""

from __future__ import annotations

ROTULOS_SINAIS: dict[str, str] = {
    # sintaxe
    "url_invalida": "URL inválida",
    "esquema_perigoso": "Esquema perigoso",
    "esquema_ausente": "Sem protocolo",
    "userinfo_no_host": "'@' escondendo o destino",
    "host_ip_literal": "IP no lugar do domínio",
    "porta_incomum": "Porta incomum",
    "encurtador": "Link encurtado",
    "url_embutida": "URL escondida nos parâmetros",
    "subdominios_excessivos": "Subdomínios em excesso",
    "tld_de_risco": "Extensão de domínio de risco",
    "hifens_em_excesso": "Hífens em excesso",
    "url_muito_longa": "URL muito longa",
    "alfabetos_misturados": "Alfabetos misturados",
    "dominio_punycode": "Domínio em punycode",
    "dominio_sosia": "Domínio sósia de marca",
    "typosquatting": "Typosquatting",
    "marca_em_subdominio": "Marca em domínio de terceiro",
    "palavras_isca": "Palavras típicas de golpe",
    "download_executavel": "Download de executável",
    # TLS
    "sem_https": "Sem HTTPS",
    "tls_indisponivel": "Sem conexão segura",
    "certificado_invalido": "Certificado não confiável",
    "certificado_autoassinado": "Certificado autoassinado",
    "certificado_host_divergente": "Certificado de outro endereço",
    "certificado_expirado": "Certificado vencido",
    "certificado_perto_do_vencimento": "Certificado perto de vencer",
    "certificado_recem_emitido": "Certificado recém-emitido",
    "tls_obsoleto": "TLS obsoleto",
    # reputação
    "listado_como_malicioso": "Listado como malicioso",
    "reputacao_indisponivel": "Listas de ameaça indisponíveis",
    # registro e DNS
    "dominio_recem_registrado": "Domínio registrado há poucos dias",
    "dominio_novo": "Domínio novo",
    "dominio_estabelecido": "Domínio estabelecido",
    "dominio_suspenso": "Domínio suspenso",
    "dominio_expirado": "Domínio expirado",
    "sem_spf": "Sem SPF",
    "sem_dmarc": "Sem DMARC",
    "dmarc_permissivo": "DMARC permissivo",
    "sem_caa": "Sem CAA",
}


def rotulo_do_sinal(codigo: str) -> str:
    """Nome legível; um código sem nome aparece como o próprio código."""
    return ROTULOS_SINAIS.get(codigo, codigo)
