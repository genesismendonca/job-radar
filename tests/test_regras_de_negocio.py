"""Regras de negocio do usuario, escritas como teste executavel.

Estas regras foram definidas por escrito e sao a especificacao do que o
JobRadar deve ou nao notificar.

Regra, resumida (atualizada em 20/08 -- ver historico da regra de cidade
anterior, as oito cidades do Nordeste/Norte, em tests/test_senior.py e
config.py via git log; e o pivo de cargo de Dados/BI pra Produto no mesmo
dia, tambem via git log):
  BRASIL   -> remoto de qualquer lugar do pais;
              hibrido/presencial SO em Sao Paulo.
  EXTERIOR -> SO remoto, nunca hibrido, nunca presencial.
              Aceita quando o mercado declarado no texto e Brasil/LATAM/
              Iberia (ver MERCADOS_REMOTO_ACEITOS_INTL) OU quando a vaga
              nao declara mercado nenhum (sem base pra rejeitar) -- nao
              depende mais de idioma no titulo.
  CARGO    -> Product Manager / Product Owner / variacoes (ver
              KEYWORDS_CARGO_FORTE em config.py) -- pivo de Dados/BI pra
              Produto, perfil real do usuario (Senior Product Manager).
"""

import pytest

from core.job import Job
from core.perfis import PERFIL_BR, PERFIL_INTL


def _vaga(titulo, local, modalidade):
    return Job(
        titulo=titulo, empresa="Empresa Teste", local=local,
        link=f"https://exemplo.com/{abs(hash((titulo, local, modalidade)))}",
        site="Teste", modalidade=modalidade,
    )


# ---------------------------------------------------------------- BRASIL

@pytest.mark.parametrize("modalidade", ["Híbrido", "Presencial"])
def test_br_hibrido_e_presencial_em_sao_paulo(modalidade):
    assert _vaga("Product Manager", "São Paulo - SP", modalidade).combina_com(PERFIL_BR.regras)


# Variacoes de escrita que as fontes realmente usam -- separador, acento e
# caixa nao podem mudar o resultado.
@pytest.mark.parametrize("local", [
    "São Paulo", "São Paulo - SP", "São Paulo, SP", "São Paulo/SP",
    "SÃO PAULO - SP", "sao paulo, sp", "Sao Paulo - SP",
])
def test_br_variacoes_de_escrita_da_cidade(local):
    assert _vaga("Product Manager", local, "Híbrido").combina_com(PERFIL_BR.regras)


@pytest.mark.parametrize("modalidade", ["Híbrido", "Presencial"])
@pytest.mark.parametrize("local", [
    "Belo Horizonte, MG", "Salvador - BA", "Rio de Janeiro, RJ",
    "Curitiba - PR", "Brasília, DF", "Fortaleza - CE", "Porto Alegre - RS",
    # Requisito anterior (revogado em 20/08) aceitava hibrida/presencial
    # nestas oito -- agora so Sao Paulo vale.
    "Campina Grande - PB", "João Pessoa - PB", "Recife - PE", "Natal - RN",
    "Caruaru - PE", "Manaus - AM", "Maceió - AL", "Aracaju - SE",
])
def test_br_hibrido_e_presencial_fora_de_sao_paulo_e_rejeitado(local, modalidade):
    assert not _vaga("Product Manager", local, modalidade).combina_com(PERFIL_BR.regras)


@pytest.mark.parametrize("local", [
    "Remoto", "Remoto (São Paulo, SP)", "Remoto (Manaus, AM)",
    "Remoto - Brasil", "Remote, Brazil", "Remoto (Belo Horizonte, MG)",
])
def test_br_remoto_no_brasil_e_aceito_de_qualquer_cidade(local):
    """Remoto nao tem restricao de cidade -- a regra de CIDADES vale so
    pra hibrido/presencial."""
    assert _vaga("Product Manager", local, "Remoto").combina_com(PERFIL_BR.regras)


@pytest.mark.parametrize("local", [
    "Remote - US only", "Remote, United States", "Remote (Austin, TX)",
    "Remote - India",
])
def test_br_remoto_de_mercado_nao_aceito_e_rejeitado(local):
    assert not _vaga("Product Manager", local, "Remoto").combina_com(PERFIL_BR.regras)


# --------------------------------------------------------- INTERNACIONAL

@pytest.mark.parametrize("local", [
    "Remote - Spain", "Madrid, Spain", "España (En remoto)",
    "Remote - Mexico", "Ciudad de México, México", "Remote - Portugal",
    "Remote - Latin America", "Remote - Colombia", "Buenos Aires, Argentina",
    # Requisito atualizado (20/08): Brasil entrou na allowlist tambem --
    # vaga internacional que declara aceitar morador do Brasil passa.
    "Remote - Brazil",
])
def test_intl_remoto_em_mercado_aceito_e_aceito(local):
    assert _vaga("Product Manager", local, "Remoto").combina_com(PERFIL_INTL.regras)


@pytest.mark.parametrize("modalidade", ["Híbrido", "Presencial"])
@pytest.mark.parametrize("local", [
    "Madrid, Spain", "Barcelona, España", "Lisboa, Portugal",
    "Ciudad de México, México", "Buenos Aires, Argentina",
])
def test_intl_hibrido_e_presencial_sempre_rejeitado(local, modalidade):
    """Do exterior so interessa vaga remota -- nem mesmo em Portugal ou
    Espanha vale presencial/hibrida."""
    assert not _vaga("Product Manager", local, modalidade).combina_com(PERFIL_INTL.regras)


@pytest.mark.parametrize("local", [
    "Remote - US only", "Remote, United States", "Remote (Seattle, WA)",
    "Remote, but candidates must be located in the United States",
    "Remote - India", "Remote - United Kingdom", "Remote - Germany",
    "Remote - Poland",
])
def test_intl_remoto_de_mercado_nao_aceito_e_rejeitado(local):
    """Requisito atualizado (20/08): a busca internacional passou a cobrir
    EUA e a Europa inteira (ver LOCATIONS_INTL) -- e exatamente por isso
    que este gate de mercado importa mais agora. Vaga que DECLARA exigir
    um pais/regiao fora da allowlist (Brasil/LATAM/Iberia) e rejeitada,
    mesmo sem nada em espanhol/portugues no texto."""
    assert not _vaga("Product Manager", local, "Remoto").combina_com(PERFIL_INTL.regras)


@pytest.mark.parametrize("titulo", [
    "Senior Product Manager - Remote (US)",
    "US Remote Product Owner",
    "Product Manager, Remote - United States",
])
def test_intl_remoto_de_mercado_nao_aceito_no_titulo_e_rejeitado(titulo):
    """Requisito do usuario (21/08): "vagas que tenham no ... titulo
    remote us ... sejam desconsideras" -- fonte as vezes so declara a
    restricao geografica no TITULO, com `local` vazio ou com a sede da
    empresa (sem relacao com o mercado de contratacao). Mesma rejeicao que
    ja valia pra restricao escrita em `local`."""
    assert not _vaga(titulo, "", "Remoto").combina_com(PERFIL_INTL.regras)


def test_intl_remoto_de_mercado_aceito_no_titulo_e_aceito():
    """Espelho do teste acima -- titulo que declara mercado ACEITO (nao
    US/India/etc.) continua passando, mesmo sem nada em `local`."""
    assert _vaga("Product Manager - Remote (Brazil)", "", "Remoto").combina_com(PERFIL_INTL.regras)


def test_intl_titulo_hibrido_vence_a_classificacao_da_fonte():
    """O filtro nativo do LinkedIn as vezes marca como remota uma vaga que
    o proprio anuncio chama de hibrida -- o titulo vence."""
    vaga = _vaga("Product Manager (Hybrid)", "Madrid, Spain", "Remoto")
    assert vaga.modalidade == "Híbrido"
    assert not vaga.combina_com(PERFIL_INTL.regras)


def test_intl_remoto_sem_mercado_declarado_passa_sem_precisar_de_idioma():
    """Requisito atualizado (20/08): o gate de idioma no titulo saiu --
    antes, remoto sem mercado declarado so passava se o titulo afirmasse
    espanhol/portugues/LATAM explicitamente. Agora passa direto, sem base
    nenhuma pra rejeitar (nem precisa mencionar idioma)."""
    assert _vaga("Product Manager (Spanish speaker)", "Remote - Worldwide", "Remoto").combina_com(PERFIL_INTL.regras)
    assert _vaga("Product Manager", "Remote - Worldwide", "Remoto").combina_com(PERFIL_INTL.regras)


# ------------------------------------------------------------------ CARGO

@pytest.mark.parametrize("titulo, esperado", [
    ("Product Manager Pleno", True),
    ("Senior Product Owner", True),
    ("Gerente de Produto", True),
    ("Head of Product - LATAM", True),
    ("Group Product Manager", True),
    ("Principal Product Manager", True),
    ("Product Lead", True),
    ("Líder de Produto", True),
    ("VP of Product", True),
    ("VP de Produto", True),
    ("Gerente de Producto", True),          # espanhol -- LinkedInScraper busca Argentina/Chile
    # Requisito atualizado (20/08): pivo de Dados/BI pra Produto -- o que
    # antes era o alvo do projeto agora e rejeitado, de proposito.
    ("Analista de Dados", False),
    ("Analista de BI", False),
    ("Business Intelligence Analyst", False),
    ("Business Analyst", False),
    # Sem eixo ambiguo/ferramenta neste perfil (ver KEYWORDS_CARGO_AMBIGUO
    # e FERRAMENTAS_TITULO em config.py, ambos vazios) -- sigla solta
    # nunca aprova, mesmo com qualificador junto.
    ("PM Pleno de Produto", False),
    ("PO Sênior - Produto", False),
    ("Vendedor Externo", False),
    ("Engenheiro de Software", False),
])
def test_cargo_no_titulo(titulo, esperado):
    assert _vaga(titulo, "São Paulo - SP", "Presencial").combina_com(PERFIL_BR.regras) is esperado


# ------------------------- CIDADE DE NOME PARECIDO, ESTADO DIFERENTE

@pytest.mark.parametrize("local", [
    # Municipios brasileiros reais com "Sao Paulo" como PREFIXO do nome --
    # mesmo risco de substring que motivou o fix original (ver
    # "Campina Grande do Sul" no historico deste arquivo via git log):
    # "sao paulo" bate com borda de palavra dentro do nome maior, mas a UF
    # declarada contradiz Sao Paulo/SP.
    "São Paulo do Potengi - RN",
    "SÃO PAULO DO POTENGI - RN",
    "São Paulo do Potengi, RN",
    "São Paulo do Potengi/RN",
    "São Paulo de Olivença - AM",
    # E o inverso: cidade certa, UF errada, ainda e outro lugar (nao existe
    # "Sao Paulo" fora de SP -- exemplo sintetico so pra exercitar a guarda
    # de UF, mesmo padrao do teste antigo com "Recife - SP").
    "São Paulo - RJ",
    "São Paulo - MG",
])
def test_cidade_de_nome_parecido_em_outro_estado_e_rejeitada(local):
    assert not _vaga("Product Manager", local, "Presencial").combina_com(PERFIL_BR.regras)


@pytest.mark.parametrize("local", [
    "São Paulo - SP", "SÃO PAULO - SP", "São Paulo, SP", "São Paulo/SP",
    "Sao Paulo - SP", "sao paulo, sp",
])
def test_cidade_certa_com_a_uf_certa_continua_passando(local):
    assert _vaga("Product Manager", local, "Presencial").combina_com(PERFIL_BR.regras)


@pytest.mark.parametrize("local", [
    # Sem UF nenhuma nao ha o que comparar: continua passando, de proposito.
    # Barrar aqui exigiria adivinhar por contagem de palavras, e isso
    # derrubaria "vaga em Sao Paulo" sozinho, que e valido.
    "São Paulo", "Vaga em São Paulo", "São Paulo, São Paulo, Brasil",
])
def test_sem_uf_declarada_a_cidade_continua_valendo(local):
    assert _vaga("Product Manager", local, "Presencial").combina_com(PERFIL_BR.regras)
