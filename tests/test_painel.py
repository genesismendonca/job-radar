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
