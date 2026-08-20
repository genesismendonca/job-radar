"""Testes do gerador do painel estático (painel/gerar_painel.py) — o
canal de saída que substituiu o Telegram (ver requisito atualizado 20/08).

_carregar_vagas/_carregar_status recebem uma conexão sqlite já aberta (não
DB_PATH direto), então testam com um banco em memória montado com o mesmo
schema mínimo que iniciar_db() cria — sem precisar de arquivo em disco nem
rodar a migração inteira.
"""

import json
import sqlite3

import pytest

from painel.gerar_painel import (
    _carregar_status,
    _carregar_vagas,
    _categoria,
    _PADRAO_PUBLICACAO_ANTIGA,
    gerar_html,
)


@pytest.fixture
def conn():
    conexao = sqlite3.connect(":memory:")
    conexao.execute("""
        CREATE TABLE vagas_vistas (
            id TEXT PRIMARY KEY, titulo TEXT, empresa TEXT, local TEXT, link TEXT,
            site TEXT, perfil TEXT, modalidade TEXT, relevancia INTEGER, motivo TEXT,
            exploratoria INTEGER, situacao TEXT, encontrada_em TEXT, publicado_em TEXT,
            mercado_confirmado INTEGER
        )
    """)
    conexao.execute("CREATE TABLE metadados (chave TEXT PRIMARY KEY, valor TEXT)")
    yield conexao
    conexao.close()


def _inserir_vaga(conn, **campos):
    padrao = dict(
        id="id1", titulo="Product Manager", empresa="Empresa", local="São Paulo",
        link="https://exemplo.com/vaga", site="LinkedIn", perfil="brasil",
        modalidade="Remoto", relevancia=7, motivo="Cargo forte", exploratoria=0,
        situacao="nova", encontrada_em="2026-08-20 10:00:00", publicado_em="",
        mercado_confirmado=0,
    )
    padrao.update(campos)
    conn.execute(
        """INSERT INTO vagas_vistas
           (id, titulo, empresa, local, link, site, perfil, modalidade, relevancia,
            motivo, exploratoria, situacao, encontrada_em, publicado_em, mercado_confirmado)
           VALUES (:id, :titulo, :empresa, :local, :link, :site, :perfil, :modalidade,
                   :relevancia, :motivo, :exploratoria, :situacao, :encontrada_em, :publicado_em,
                   :mercado_confirmado)""",
        padrao,
    )
    conn.commit()


# ---------------------------------------------------------- _carregar_vagas

def test_carrega_vaga_com_campos_basicos(conn):
    _inserir_vaga(conn, id="abc")
    vagas = _carregar_vagas(conn)
    assert len(vagas) == 1
    assert vagas[0]["id"] == "abc"
    assert vagas[0]["titulo"] == "Product Manager"
    assert vagas[0]["exploratoria"] is False


def test_exploratoria_vira_booleano(conn):
    _inserir_vaga(conn, id="x", exploratoria=1)
    vagas = _carregar_vagas(conn)
    assert vagas[0]["exploratoria"] is True


def test_mercado_confirmado_vira_booleano(conn):
    _inserir_vaga(conn, id="x", mercado_confirmado=1)
    vagas = _carregar_vagas(conn)
    assert vagas[0]["mercado_confirmado"] is True

    _inserir_vaga(conn, id="y", mercado_confirmado=0)
    vagas = _carregar_vagas(conn)
    assert [v for v in vagas if v["id"] == "y"][0]["mercado_confirmado"] is False


def test_relevancia_nula_vira_zero(conn):
    _inserir_vaga(conn, id="x", relevancia=None)
    vagas = _carregar_vagas(conn)
    assert vagas[0]["relevancia"] == 0


@pytest.mark.parametrize("publicado_em, esperado", [
    ("há 7 meses", True),
    ("há 2 anos", True),
    ("há 3 dias", False),
    ("", False),
    ("Publicada em 11/08", False),
])
def test_flag_antiga(conn, publicado_em, esperado):
    _inserir_vaga(conn, id="x", publicado_em=publicado_em)
    vagas = _carregar_vagas(conn)
    assert vagas[0]["antiga"] is esperado


def test_ordena_mais_recente_primeiro(conn):
    _inserir_vaga(conn, id="antiga", encontrada_em="2026-08-01 10:00:00")
    _inserir_vaga(conn, id="nova", encontrada_em="2026-08-20 10:00:00")
    vagas = _carregar_vagas(conn)
    assert [v["id"] for v in vagas] == ["nova", "antiga"]


# --------------------------------------------------------------- _categoria
#
# Requisito atualizado (20/08): "algumas vagas estão aparecendo na aba
# internacional, mas são do BR" -- LinkedInIntlScraper busca por PAÍS
# estrangeiro (LOCATIONS_INTL), mas o filtro nativo de remoto do LinkedIn
# às vezes devolve vaga clara e exclusivamente brasileira mesmo assim. O
# campo `perfil` salvo no banco só diz qual PIPELINE achou a vaga, não
# onde ela é de verdade -- por isso _categoria reextrai o escopo (mesma
# função usada em produção pro filtro) como double-check, pra qualquer
# fonte, não só LinkedIn.

def _vaga_base(**over):
    padrao = dict(
        perfil="internacional", local="", modalidade="Remoto", mercado_confirmado=False,
    )
    padrao.update(over)
    return padrao


def test_categoria_brasil_remoto():
    assert _categoria(_vaga_base(perfil="brasil", modalidade="Remoto")) == "br-remoto"


@pytest.mark.parametrize("modalidade", ["Híbrido", "Presencial"])
def test_categoria_brasil_hibrido(modalidade):
    assert _categoria(_vaga_base(perfil="brasil", modalidade=modalidade)) == "br-hibrido"


def test_categoria_internacional_mercado_confirmado():
    assert _categoria(_vaga_base(local="Remote - Spain", mercado_confirmado=True)) == "intl-explicito"


def test_categoria_internacional_sem_mercado():
    assert _categoria(_vaga_base(local="Remote", mercado_confirmado=False)) == "intl-sem-mercado"


def test_categoria_reclassifica_vaga_brasileira_achada_pelo_pipeline_internacional():
    """MEDIDO (primeiro ciclo real, 20/08): "Porto Alegre, Rio Grande do
    Sul, Brazil" com modalidade=Remoto, perfil=internacional -- claramente
    uma vaga brasileira, achada só porque o LinkedIn devolveu ela pra uma
    busca de país estrangeiro. Precisa virar br-remoto, não intl."""
    vaga = _vaga_base(
        perfil="internacional", local="Porto Alegre, Rio Grande do Sul, Brazil",
        modalidade="Remoto", mercado_confirmado=False,
    )
    assert _categoria(vaga) == "br-remoto"


def test_categoria_nao_reclassifica_vaga_de_mercado_multiplo():
    """"Remote - Brazil/LATAM" aceita mais gente que só quem mora no
    Brasil -- não é o mesmo caso de vaga EXCLUSIVAMENTE brasileira, então
    continua internacional (o double-check só reclassifica quando o
    escopo resolve só e exatamente pra Brasil)."""
    vaga = _vaga_base(
        perfil="internacional", local="Remote - Brazil/LATAM",
        modalidade="Remoto", mercado_confirmado=True,
    )
    assert _categoria(vaga) == "intl-explicito"


def test_categoria_double_check_vale_pra_qualquer_fonte():
    """O double-check não é específico do LinkedIn -- roda pra qualquer
    vaga perfil=internacional, seja qual for o `site`."""
    vaga = _vaga_base(
        perfil="internacional", local="Recife, PE, Brazil", modalidade="Remoto",
    )
    assert _categoria(vaga) == "br-remoto"


def test_carregar_vagas_preenche_categoria(conn):
    _inserir_vaga(conn, id="x", perfil="brasil", modalidade="Remoto")
    vagas = _carregar_vagas(conn)
    assert vagas[0]["categoria"] == "br-remoto"


# --------------------------------------------------------- _carregar_status

def test_status_ausente_vira_none(conn):
    status = _carregar_status(conn)
    assert status["brasil"] is None
    assert status["internacional"] is None


def test_status_presente_e_desserializado(conn):
    payload = {"total_novas": 5, "fontes_com_problema": []}
    conn.execute(
        "INSERT INTO metadados (chave, valor) VALUES (?, ?)",
        ("status_ultima_execucao_brasil", json.dumps(payload)),
    )
    conn.commit()
    status = _carregar_status(conn)
    assert status["brasil"] == payload
    assert status["internacional"] is None


# -------------------------------------------------------------- gerar_html

def test_gerar_html_embute_json_valido_e_escapa_fechamento_de_script():
    vagas = [{
        "id": "1", "titulo": "Analista</script><script>alert(1)</script>",
        "empresa": "X", "local": "Y", "link": "https://x.com", "site": "Z",
        "perfil": "brasil", "modalidade": "Remoto", "relevancia": 5, "motivo": "",
        "exploratoria": False, "situacao": "nova", "encontrada_em": "2026-08-20 10:00:00",
        "publicado_em": "", "antiga": False,
    }]
    pagina = gerar_html(vagas, {"brasil": None, "internacional": None})

    # A página não pode ter a sequência crua "</script>" no MEIO do JSON —
    # isso fecharia a tag <script> mais cedo e quebraria o parse.
    inicio = pagina.index('id="dados-painel"')
    fim = pagina.index("</script>", inicio)
    bloco = pagina[inicio:fim]
    assert "</script>" not in bloco.replace("<\\/script>", "")

    dados_json = pagina[pagina.index(">", inicio) + 1:fim]
    dados = json.loads(dados_json.replace("<\\/", "</"))
    assert dados["vagas"][0]["titulo"] == "Analista</script><script>alert(1)</script>"


def test_gerar_html_inclui_titulo_da_pagina():
    pagina = gerar_html([], {"brasil": None, "internacional": None})
    assert "<title>JobRadar" in pagina
