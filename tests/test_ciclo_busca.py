"""Regressão do rodízio de termos de busca e do alerta de saúde (ver
main.py) — extraído de um arquivo que antes também testava o disparo do
digest diário do Telegram (removido em 20/08, ver requisito atualizado: a
saída passou a ser um painel estático, sem push nenhum). O rodízio de
termos e a decisão "as fontes falharam de verdade?" continuam 100% válidos
independente do canal de saída.
"""

import json

import pytest

import main


# ------------------------------------------------- ALERTA DE SAUDE

@pytest.mark.parametrize("com_problema, total, esperado", [
    # 2 fontes: o caso que motivou a mudanca. Perfil Internacional ficou
    # assim quando o Indeed foi desligado, e o WeWorkRemotely e pequeno o
    # bastante pra voltar vazio num dia fraco.
    (0, 2, False),
    (1, 2, False),   # antes disparava aqui -- alerta falso
    (2, 2, True),    # as duas cairam: e problema de verdade
    # 3 fontes (perfil Brasil num ciclo normal): comportamento inalterado.
    (1, 3, False),
    (2, 3, True),
    (3, 3, True),
    # 7 fontes (Brasil no ciclo que roda as de baixa frequencia).
    (3, 7, False),
    (4, 7, True),
    # numero par maior: fica um pouco mais exigente, de proposito.
    (4, 8, False),
    (5, 8, True),
    # nenhuma fonte no ciclo: nao ha o que alertar.
    (0, 0, False),
])
def test_alerta_de_saude_exige_maioria_estrita(com_problema, total, esperado):
    """Alerta que dispara sem motivo deixa de ser lido -- e ai nao serve nem
    quando o problema e real."""
    assert main._deve_alertar_saude(com_problema, total) is esperado


# --------------------------------------------- RODIZIO DE TERMOS DE BUSCA

class _PerfilFalso:
    def __init__(self, termos, por_ciclo, prioritarios=()):
        self.chave = "teste"
        self.termos_busca = list(termos)
        self.termos_por_ciclo = por_ciclo
        self.termos_prioritarios = list(prioritarios)


@pytest.fixture
def metadados(monkeypatch):
    estado = {}
    monkeypatch.setattr(main, "obter_metadado", lambda c: estado.get(c))
    monkeypatch.setattr(main, "definir_metadado", lambda c, v: estado.__setitem__(c, v))
    return estado


def test_prioritarios_entram_em_todo_ciclo(metadados):
    """MEDIDO: uma vaga real ("Analista de Dados", Recife) nunca foi buscada
    porque o termo so passava a cada 13 horas no rodizio alfabetico."""
    perfil = _PerfilFalso(list("abcdefghij") + ["ALVO"], por_ciclo=3, prioritarios=["ALVO"])
    for _ in range(6):
        assert "ALVO" in main._proximo_bloco_termos(perfil)


def test_prioritario_nao_ocupa_vaga_do_rodizio(metadados):
    perfil = _PerfilFalso(list("abcdef") + ["ALVO"], por_ciclo=3, prioritarios=["ALVO"])
    bloco = main._proximo_bloco_termos(perfil)
    assert len(bloco) == 4                 # 1 prioritario + 3 do rodizio
    assert bloco[0] == "ALVO"
    assert set(bloco[1:]).issubset(set("abcdef"))


def test_rodizio_cobre_todos_os_termos_nao_prioritarios(metadados):
    perfil = _PerfilFalso(list("abcdefghi") + ["ALVO"], por_ciclo=3, prioritarios=["ALVO"])
    vistos = set()
    for _ in range(3):
        vistos.update(main._proximo_bloco_termos(perfil))
    assert vistos == set("abcdefghi") | {"ALVO"}


def test_prioritario_nao_e_repetido_no_rodizio(metadados):
    """Termo prioritario sai do conjunto que rotaciona -- senao ele apareceria
    duas vezes no mesmo ciclo, gastando busca a toa."""
    perfil = _PerfilFalso(["a", "ALVO", "b", "c"], por_ciclo=3, prioritarios=["ALVO"])
    bloco = main._proximo_bloco_termos(perfil)
    assert bloco.count("ALVO") == 1


def test_sem_prioritarios_o_comportamento_e_o_de_antes(metadados):
    """Perfil internacional nao usa prioritarios: rodizio puro."""
    perfil = _PerfilFalso(list("abcdef"), por_ciclo=2)
    assert main._proximo_bloco_termos(perfil) == ["a", "b"]
    assert main._proximo_bloco_termos(perfil) == ["c", "d"]
    assert main._proximo_bloco_termos(perfil) == ["e", "f"]
    assert main._proximo_bloco_termos(perfil) == ["a", "b"]


def test_prioritario_fora_da_lista_de_busca_e_ignorado(metadados):
    perfil = _PerfilFalso(["a", "b"], por_ciclo=1, prioritarios=["NAO_EXISTE"])
    assert main._proximo_bloco_termos(perfil) == ["a"]


def test_todos_prioritarios_e_nenhum_rodizio(metadados):
    perfil = _PerfilFalso(["a", "b"], por_ciclo=3, prioritarios=["a", "b"])
    assert main._proximo_bloco_termos(perfil) == ["a", "b"]


# ------------------------------------------- STATUS DE EXECUCAO (PAINEL)

def test_registrar_status_execucao_grava_json_em_metadados(metadados):
    """Ver painel/gerar_painel.py -- é isso que o painel lê pra mostrar
    "última execução" por perfil, no lugar do heartbeat que o Telegram
    mandava por push."""
    perfil = _PerfilFalso(["a"], por_ciclo=1)
    perfil.chave = "brasil"
    perfil.nome = "Brasil"

    main._registrar_status_execucao(
        perfil, total_brutas=50, total_filtradas=10, total_novas=3,
        scrapers_com_problema=["CathoScraper"], total_fontes=5,
    )

    salvo = json.loads(metadados["status_ultima_execucao_brasil"])
    assert salvo["total_brutas"] == 50
    assert salvo["total_filtradas"] == 10
    assert salvo["total_novas"] == 3
    assert salvo["total_fontes"] == 5
    assert salvo["fontes_com_problema"] == ["CathoScraper"]
    assert "quando" in salvo
