"""Listas curadas usadas na análise sintática.

São dados abertos e verificáveis: domínios oficiais de marcas muito imitadas em
golpes no Brasil, sufixos públicos, encurtadores e TLDs historicamente abusados.
Nenhum dado pessoal é armazenado aqui.
"""

from __future__ import annotations

#: Marca -> domínios registráveis legítimos.
#: Serve para dois testes: (a) typosquatting — domínio *parecido* com o oficial;
#: (b) impersonação — a marca aparece no subdomínio/caminho, mas o domínio que
#: realmente controla a página é outro (ex.: itau.seguranca-cliente.top).
MARCAS_OFICIAIS: dict[str, tuple[str, ...]] = {
    "itau": ("itau.com.br", "itau.com", "iti.com.br"),
    "bradesco": ("bradesco.com.br", "bradesco.b.br"),
    "santander": ("santander.com.br", "santander.com"),
    "bancodobrasil": ("bb.com.br", "bancodobrasil.com.br"),
    "caixa": ("caixa.gov.br", "loterias.caixa.gov.br"),
    "nubank": ("nubank.com.br", "nubank.com"),
    "bancointer": ("bancointer.com.br", "inter.co"),
    "c6bank": ("c6bank.com.br",),
    "picpay": ("picpay.com",),
    "mercadopago": ("mercadopago.com.br", "mercadopago.com"),
    "mercadolivre": ("mercadolivre.com.br", "mercadolibre.com"),
    "magazineluiza": ("magazineluiza.com.br", "magalu.com"),
    "americanas": ("americanas.com.br",),
    "casasbahia": ("casasbahia.com.br",),
    "shopee": ("shopee.com.br", "shopee.com"),
    "amazon": ("amazon.com.br", "amazon.com"),
    "correios": ("correios.com.br",),
    "receitafederal": ("receita.fazenda.gov.br", "gov.br"),
    "govbr": ("gov.br",),
    "serasa": ("serasa.com.br", "serasaexperian.com.br"),
    "detran": ("detran.sp.gov.br", "gov.br"),
    "inss": ("inss.gov.br", "gov.br"),
    "ifood": ("ifood.com.br",),
    "olx": ("olx.com.br",),
    "vivo": ("vivo.com.br",),
    "claro": ("claro.com.br",),
    "netflix": ("netflix.com",),
    "whatsapp": ("whatsapp.com", "wa.me"),
    "instagram": ("instagram.com",),
    "facebook": ("facebook.com", "fb.com"),
    "google": ("google.com", "google.com.br"),
    "microsoft": ("microsoft.com", "live.com", "office.com"),
    "apple": ("apple.com", "icloud.com"),
    "steam": ("steampowered.com", "steamcommunity.com"),
    "binance": ("binance.com",),
}

#: Sufixos públicos de dois níveis mais comuns, usados quando `tldextract`
#: (que carrega a Public Suffix List completa) não está instalado.
SUFIXOS_COMPOSTOS: frozenset[str] = frozenset(
    {
        "com.br", "net.br", "org.br", "gov.br", "edu.br", "mil.br", "art.br",
        "blog.br", "eco.br", "emp.br", "ind.br", "inf.br", "jus.br", "leg.br",
        "med.br", "adv.br", "esp.br", "srv.br", "tur.br", "tv.br", "app.br",
        "com.pt", "com.ar", "com.mx", "com.co", "com.pe", "com.uy", "com.py",
        "co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "net.au", "org.au",
        "co.jp", "co.in", "co.za", "com.tr", "com.cn", "com.hk", "com.sg",
    }
)

#: TLDs com histórico desproporcional de abuso (registro gratuito/barato ou
#: extensão que se confunde com nome de arquivo). Sinal fraco, nunca conclusivo.
TLDS_DE_RISCO: frozenset[str] = frozenset(
    {"zip", "mov", "tk", "ml", "ga", "cf", "gq", "top", "xyz", "click",
     "country", "kim", "work", "rest", "surf", "cam", "quest", "cfd", "sbs"}
)

#: Encurtadores: não são maliciosos, mas escondem o destino real do usuário.
ENCURTADORES: frozenset[str] = frozenset(
    {"bit.ly", "tinyurl.com", "goo.gl", "t.co", "ow.ly", "is.gd", "buff.ly",
     "rebrand.ly", "cutt.ly", "encurtador.com.br", "shorturl.at", "bl.ink",
     "rb.gy", "shre.ink", "l1nk.dev", "linktr.ee", "acesse.one", "n9.cl"}
)

#: Palavras-isca típicas de phishing em português e inglês.
ISCAS: frozenset[str] = frozenset(
    {"login", "signin", "senha", "password", "verificar", "verificacao",
     "validar", "atualizar", "atualizacao", "recadastro", "recadastramento",
     "desbloqueio", "desbloquear", "seguranca", "confirmar", "confirmacao",
     "cpf", "boleto", "segundavia", "2via", "nota-fiscal", "notafiscal",
     "premio", "sorteio", "resgate", "promocao", "black-friday", "pix",
     "token", "chave", "recuperar", "suporte", "central-cliente", "acesso",
     "banco", "gratis"}
)

#: Extensões que, entregues por link recebido, tipicamente iniciam a instalação
#: de um programa no dispositivo da vítima.
EXTENSOES_EXECUTAVEIS: frozenset[str] = frozenset(
    {".exe", ".scr", ".msi", ".bat", ".cmd", ".com", ".pif", ".vbs", ".js",
     ".jar", ".apk", ".ps1", ".hta", ".lnk", ".iso", ".img"}
)

#: Esquemas de URI que não devem chegar a um usuário por link "de site".
ESQUEMAS_PERIGOSOS: frozenset[str] = frozenset(
    {"javascript", "data", "vbscript", "file", "blob"}
)

#: Homóglifos: caracteres de outros alfabetos ou dígitos que, na tela, se
#: parecem com letras latinas. Base do teste de domínio "visualmente idêntico".
CONFUSAVEIS: dict[str, str] = {
    # cirílico
    "а": "a", "в": "b", "е": "e", "к": "k", "м": "m", "н": "h", "о": "o",
    "р": "p", "с": "c", "т": "t", "у": "y", "х": "x", "і": "i", "ѕ": "s",
    "ԁ": "d", "ј": "j", "ӏ": "l", "ԛ": "q", "ԝ": "w",
    # grego
    "α": "a", "β": "b", "ε": "e", "ι": "i", "κ": "k", "ν": "v", "ο": "o",
    "ρ": "p", "τ": "t", "υ": "u", "χ": "x", "ϲ": "c",
    # dígitos e símbolos usados como letras
    "0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "6": "b", "7": "t",
    "8": "b", "9": "g", "$": "s", "@": "a", "!": "i", "|": "l",
}

#: Pares de letras que juntas imitam outra letra ("rn" ≈ "m").
DIGRAFOS_CONFUSAVEIS: tuple[tuple[str, str], ...] = (
    ("rn", "m"), ("vv", "w"), ("cl", "d"), ("nn", "m"),
)
