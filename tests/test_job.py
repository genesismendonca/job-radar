"""Testes de Job.senioridade (core/job.py) — sem arquivo próprio até agora.

MEDIDO (20/08, pivô Dados/BI -> Produto): rodando a classificação contra
as 543 vagas do primeiro ciclo real do perfil Produto, 261 (48%) caíam em
"Liderança" só porque "manager"/"gerente" são PARTE DO NOME DO CARGO BASE
("Product Manager", "Gerente de Produto" — os próprios KEYWORDS_CARGO_FORTE),
não um sinal de senioridade acima do padrão. Isso derrubava o score de
quase metade das vagas aprovadas (_PESO_SENIORIDADE_ACIMA_DO_ALVO = -2)
sem relação nenhuma com senioridade real. Corrigido com lookaround que
exclui só o cargo base, sem tirar o sinal de vaga que É de gestão de
verdade (ver _NIVEIS_SENIORIDADE).
"""

import pytest

from core.job import Job


def _vaga(titulo):
    return Job(titulo=titulo, empresa="Empresa", local="São Paulo", link="https://x/1", site="Teste")


@pytest.mark.parametrize("titulo, esperado", [
    # Cargo base (Product Manager / Gerente de Produto), sem qualificador:
    # NÃO é sinal de liderança -- é o próprio nome do cargo que o projeto
    # busca (ver KEYWORDS_CARGO_FORTE em config.py).
    ("Product Manager", "Não especificado"),
    ("Gerente de Produto", "Não especificado"),
    ("Product Manager - Energias Renovables", "Não especificado"),
    # Com qualificador de nível, o nível continua batendo normalmente.
    ("Product Manager Pleno", "Pleno"),
    ("Product Owner Jr", "Júnior"),
    ("Senior Product Manager", "Sênior"),
    ("PRODUCT MANAGER ESPECIALISTA I", "Especialista"),
    # Vaga que É de gestão de verdade (não é o cargo base do projeto)
    # continua classificando Liderança normalmente -- a exclusão é só
    # pro caso "product manager"/"gerente de produto" literal.
    ("Engineering Manager", "Liderança"),
    ("Coordenador de Growth", "Liderança"),
    ("Gerente de TI", "Liderança"),
    ("Head of Product", "Liderança"),
])
def test_senioridade(titulo, esperado):
    assert _vaga(titulo).senioridade == esperado


# --------------------------------------------------- escopo_remoto (título)
#
# Requisito do usuário (21/08): "vagas que tenham no ... titulo remote us
# por exemplo, sejam desconsideras" -- restrição geográfica às vezes está
# só no TÍTULO ("Senior Product Manager - Remote (US)"), não no campo
# `local` (que pode vir vazio ou com a sede da empresa, sem relação com o
# mercado de contratação -- ver escopo_indefinido). extrair_escopo_remoto
# nunca olhava o título; Job.escopo_remoto agora une os dois.

@pytest.mark.parametrize("titulo, esperado", [
    ("Senior Product Manager - Remote (US)", {"Estados Unidos"}),
    ("US Remote Product Owner", {"Estados Unidos"}),
    ("Product Manager, Remote - United States", {"Estados Unidos"}),
    ("Product Owner - Remote (Brazil)", {"Brasil"}),
    # Título sem nenhum país conhecido perto de "remote" -- conjunto vazio,
    # não "escopo desconhecido" (título nunca rejeita por palavra não
    # mapeada, ver docstring de _escopo_do_titulo).
    ("Remote Product Manager for Fintech", set()),
    ("Product Manager - Fully Remote", set()),
])
def test_escopo_remoto_le_restricao_do_titulo(titulo, esperado):
    vaga = Job(titulo=titulo, empresa="Empresa", local="", link="https://x/1", site="Teste", modalidade="Remoto")
    assert vaga.escopo_remoto == esperado


def test_escopo_remoto_titulo_nao_falso_positivo_por_substring():
    """"Focus"/"Trust" contêm "us" como substring e caem dentro da janela
    de 3 palavras ao redor de "remote", mas não como palavra ISOLADA --
    \\b nas duas pontas evita casar."""
    vaga = Job(
        titulo="Focus Trust Remote Product",
        empresa="Empresa", local="", link="https://x/1", site="Teste", modalidade="Remoto",
    )
    assert vaga.escopo_remoto == set()


def test_escopo_remoto_titulo_soma_com_escopo_do_local():
    """Restrição no local ("Remote - India") e restrição de mercado
    ACEITO no título ("Remote Brazil") coexistem -- união dos dois, igual
    o caso já coberto de multi-mercado no texto de local."""
    vaga = Job(
        titulo="Product Manager - Remote Brazil",
        empresa="Empresa", local="Remote - India", link="https://x/1", site="Teste", modalidade="Remoto",
    )
    assert vaga.escopo_remoto == {"Índia", "Brasil"}
