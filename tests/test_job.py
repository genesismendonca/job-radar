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
