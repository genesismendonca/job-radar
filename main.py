
import argparse
import json
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone

from core.config import INTERVALO_MINUTOS
from database.database import (
    BancoVazioSuspeito,
    definir_metadado,
    iniciar_db,
    ja_vista,
    obter_metadado,
    salvar_vaga,
)
from core.perfis import FREQUENCIA_ALTA, PERFIS, Perfil
from utils.filtro import filtrar_vagas
from core.logger import get_logger

logger = get_logger()


def _fontes_baixa_frequencia_ja_rodaram_hoje(perfil: Perfil) -> bool:
    chave = f"baixa_frequencia_ultimo_dia_{perfil.chave}"
    return obter_metadado(chave) == date.today().isoformat()


# Não é mais uma lista fixa construída uma vez: os scrapers recebem só o
# BLOCO de termos do ciclo atual (ver _proximo_bloco_termos), e a lista de
# QUAIS fontes entram também varia por ciclo (fonte de baixa frequência só
# entra na primeira execução do dia) — então precisam ser (re)criados a
# cada ciclo, não guardados numa constante de módulo. Cada perfil tem sua
# própria chave de metadados (sufixo perfil.chave), pra rodar dois perfis
# na mesma execução sem um pisar na cadência do outro.
def _construir_scrapers(perfil: Perfil, termos_busca: list[str]):
    rodar_baixa_frequencia = not _fontes_baixa_frequencia_ja_rodaram_hoje(perfil)

    scrapers = [
        definicao.classe(termos_busca=termos_busca, **definicao.kwargs_extras)
        for definicao in perfil.definicao_scrapers
        if definicao.frequencia == FREQUENCIA_ALTA or rodar_baixa_frequencia
    ]

    if rodar_baixa_frequencia:
        # Marca ANTES de rodar (não depois): mesmo que uma fonte de baixa
        # frequência falhe nesse ciclo, ela "rodou" no sentido de já ter
        # sido tentada hoje — não deve ser tentada de novo no ciclo
        # seguinte só porque deu erro. Falha individual já é tratada e
        # logada normalmente em ciclo_de_busca(), como qualquer scraper.
        definir_metadado(f"baixa_frequencia_ultimo_dia_{perfil.chave}", date.today().isoformat())

    return scrapers


def _proximo_bloco_termos(perfil: Perfil) -> list[str]:
    """Termos deste ciclo: os PRIORITÁRIOS (todo ciclo, fora do rodízio) mais
    um BLOCO fixo (perfil.termos_por_ciclo) do resto, começando de onde o
    ciclo anterior parou e avançando
    — volta pro início quando chega no fim da lista. A posição fica salva
    no jobs.db (tabela metadados, chave com sufixo do perfil — dois perfis
    rotacionam de forma independente), então sobrevive entre execuções do
    GitHub Actions (cada run é uma máquina nova).

    Isso é o que desacopla custo por ciclo do tamanho da lista de termos:
    lista grande leva mais ciclos pra cobrir tudo, mas cada ciclo individual
    continua custando o mesmo. Sem isso, dobrar a lista de termos dobrava o
    tempo de TODO ciclo.
    """
    # MEDIDO: uma vaga real ("Analista de Dados", JCPM Shoppings, Recife)
    # nunca foi notificada — e nao por causa do filtro: o titulo bate a
    # keyword mais forte da lista e Recife e uma das 8 cidades. Ela nunca
    # chegou a ser BUSCADA. Com 44 termos e 10 por ciclo, uma volta completa
    # leva 13 horas, e o rodizio e alfabetico: "analista de dados" disputa vez
    # de igual pra igual com "bigquery" e "looker".
    #
    # perfil.termos_prioritarios sai do rodizio e entra em TODO ciclo. Os
    # demais continuam rodando como antes, so que num conjunto menor.
    prioritarios = [t for t in perfil.termos_prioritarios if t in perfil.termos_busca]
    rodizio = [t for t in perfil.termos_busca if t not in prioritarios]

    total = len(rodizio)
    if total == 0:
        return list(prioritarios)

    tamanho_bloco = min(perfil.termos_por_ciclo, total)

    chave_offset = f"termos_offset_{perfil.chave}"
    offset_salvo = obter_metadado(chave_offset)
    # % total protege contra a lista ter encolhido desde o último ciclo
    # (termo removido do config.py) — sem isso, um offset salvo maior que o
    # tamanho atual da lista quebraria o acesso por índice abaixo.
    offset = int(offset_salvo) % total if offset_salvo else 0

    bloco = [rodizio[(offset + i) % total] for i in range(tamanho_bloco)]

    definir_metadado(chave_offset, str((offset + tamanho_bloco) % total))

    return list(prioritarios) + bloco


def _registrar_status_execucao(
    perfil: Perfil, total_brutas: int, total_filtradas: int, total_novas: int,
    scrapers_com_problema: list[str], total_fontes: int,
):
    """Grava o status desta execução em metadados, pro painel (ver
    painel/gerar_painel.py) mostrar "última execução" por perfil — a versão
    pull deste projeto do que o heartbeat diário do Telegram fazia por
    push. Diferença de propósito: o heartbeat só mandava 1x/dia (pra não
    virar spam de push); aqui não tem custo de "spam" nenhum — sobrescreve
    a cada ciclo, então o painel sempre mostra o estado mais recente, sem
    esperar um dia inteiro pra saber se o robô ainda está de pé.

    JSON simples (não uma coluna por campo) porque isso nunca é
    consultado por SQL — só lido inteiro pelo painel na hora de gerar a
    página.
    """
    status = {
        "quando": datetime.now(timezone.utc).isoformat(),
        "total_brutas": total_brutas,
        "total_filtradas": total_filtradas,
        "total_novas": total_novas,
        "total_fontes": total_fontes,
        "fontes_com_problema": scrapers_com_problema,
    }
    definir_metadado(f"status_ultima_execucao_{perfil.chave}", json.dumps(status))


def _deve_alertar_saude(com_problema: int, total: int) -> bool:
    """A maioria ESTRITA das fontes falhou neste ciclo?

    MEDIDO: a regra era ">= metade", o que com 2 fontes significa que UMA
    sozinha ja dispara o alerta. Isso passou a importar quando o Indeed foi
    desligado e o perfil Internacional ficou com 2 fontes: o WeWorkRemotely e
    pequeno (5 vagas no ciclo medido, vazio em 9 dos 10 termos), entao um dia
    mais fraco viraria "JobRadar com problema" sem haver problema nenhum.

    Alerta que dispara sem motivo e pior que alerta que nao existe: depois de
    duas ou tres vezes, ele deixa de ser lido -- e ai nao serve mais nem
    quando o problema e real.

    Maioria ESTRITA (">" em vez de ">=") resolve sem enfraquecer o resto:

        2 fontes -> exige 2 (antes 1)  <- o caso que motivou a mudanca
        3 fontes -> exige 2 (igual)
        7 fontes -> exige 4 (igual)
        8 fontes -> exige 5 (antes 4)

    Ou seja: com 2 fontes o alerta passa a significar "as duas cairam", que e
    o que "com problema" deveria querer dizer.
    """
    if total <= 0:
        return False
    return com_problema > total / 2

def ciclo_de_busca(perfil: Perfil):
    total_novas = 0
    total_brutas = 0
    total_filtradas = 0
    scrapers_com_problema = []
    descartes_escopo_ciclo: Counter = Counter()

    termos_do_ciclo = _proximo_bloco_termos(perfil)
    logger.info(
        f"[{perfil.nome}] Bloco de termos deste ciclo: {len(termos_do_ciclo)}/"
        f"{len(perfil.termos_busca)} — {', '.join(termos_do_ciclo)}"
    )
    scrapers = _construir_scrapers(perfil, termos_do_ciclo)

    # A parte lenta (abrir navegador, navegar, esperar seletor) roda em
    # paralelo aqui. Tudo que segue (filtrar, checar dedup, salvar) continua
    # rodando só na thread principal, um scraper de cada vez, conforme a
    # future dele termina — nunca duas threads escrevendo no SQLite ao
    # mesmo tempo. Cada scraper já é
    # auto-contido (cria e fecha seu(s) próprio(s) browser(s) Playwright
    # dentro de buscar_vagas()), então dá pra rodar vários ao mesmo tempo em
    # threads sem risco — nenhum compartilha Browser/Page com outro.
    with ThreadPoolExecutor(max_workers=perfil.max_scrapers_concorrentes) as executor:
        futures = {executor.submit(scraper.buscar_vagas): scraper for scraper in scrapers}

        for future in as_completed(futures):
            scraper = futures[future]
            nome = scraper.__class__.__name__

            try:
                vagas = future.result()
            except Exception as e:
                logger.error(f"[{perfil.nome}] Erro no scraper {nome}: {e}")
                scrapers_com_problema.append(nome)
                continue

            # Cada scraper trata timeout por termo internamente (só loga e
            # segue pro próximo termo), então um site totalmente bloqueado
            # não lança exceção pra cá — só devolve lista vazia. Por isso
            # também contamos "0 vaga bruta nessa fonte" como problema, não
            # só exceção.
            if not vagas:
                logger.warning(f"[{perfil.nome}] {nome} não retornou nenhuma vaga bruta neste ciclo.")
                scrapers_com_problema.append(nome)
                continue

            total_brutas += len(vagas)
            vagas_filtradas, descartes = filtrar_vagas(vagas, perfil.regras)
            descartes_escopo_ciclo.update(descartes)

            # Eixo secundário (Ibéria, quando ligado): mesma regra de cargo,
            # cidade diferente — sem duplicar o que já bateu na regra
            # primária.
            vagas_secundarias = []
            if perfil.eixo_secundario_ativo and perfil.regras_eixo_secundario is not None:
                ids_filtradas = {v.id for v in vagas_filtradas}
                candidatas, descartes_secundario = filtrar_vagas(vagas, perfil.regras_eixo_secundario)
                descartes_escopo_ciclo.update(descartes_secundario)
                vagas_secundarias = [v for v in candidatas if v.id not in ids_filtradas]

            total_filtradas += len(vagas_filtradas) + len(vagas_secundarias)

            novas_da_fonte = 0
            for vaga in vagas_filtradas:
                if ja_vista(vaga):
                    continue

                # Sem canal de push (ver requisito atualizado 20/08 — saída
                # passou a ser o painel estático, não mais Telegram), toda
                # vaga nova aprovada só precisa ser salva: o painel é
                # regenerado do zero a cada ciclo a partir do que está no
                # banco, então não existe mais "notifica imediata vs. fila
                # de digest" — LIMIAR_RELEVANCIA_DESTAQUE (ver config.py)
                # ainda existe, mas só como sinal visual no painel.
                salvar_vaga(vaga, perfil_chave=perfil.chave)
                logger.info(f"[{perfil.nome}] Nova vaga: {vaga.titulo} - {vaga.empresa}")
                total_novas += 1
                novas_da_fonte += 1

            for vaga in vagas_secundarias:
                if ja_vista(vaga):
                    continue

                salvar_vaga(vaga, perfil_chave=perfil.chave, exploratoria=True)
                logger.info(
                    f"[{perfil.nome}] Nova vaga exploratória ({perfil.eixo_secundario_rotulo}): "
                    f"{vaga.titulo} - {vaga.empresa}"
                )
                total_novas += 1
                novas_da_fonte += 1

            # Funil por fonte: sem isso só dava pra ver bruta (por fonte) e
            # nova (só o total do ciclo) — o meio (quanto o filtro de
            # cargo/cidade descarta, fonte por fonte) ficava invisível.
            logger.info(
                f"[{perfil.nome}][{nome}] Funil: {len(vagas)} brutas → "
                f"{len(vagas_filtradas) + len(vagas_secundarias)} filtradas → {novas_da_fonte} novas"
            )

    logger.info(
        f"[{perfil.nome}] Ciclo concluído: {total_brutas} brutas → {total_filtradas} filtradas → "
        f"{total_novas} nova(s)."
    )

    # MEDIDO: descarte por escopo era invisível no log — o funil mostra
    # bruta → filtrada → nova, mas nunca QUAL escopo derrubou vaga nem
    # QUANTAS. Um escopo mal reconhecido (texto cru tipo "lagos nigeria",
    # não mapeado em _MERCADOS_REMOTO) barra do jeito certo, mas some sem
    # rastro — foi assim que um bug real (escopo virando allowlist) passou
    # despercebido até virar relato explícito. Loga só quando há descarte
    # (a maioria dos ciclos não tem nenhum), ordenado do que mais derrubou
    # vaga pro que menos derrubou.
    if descartes_escopo_ciclo:
        detalhe = "; ".join(
            f"{escopo} ({n})" for escopo, n in descartes_escopo_ciclo.most_common()
        )
        logger.info(f"[{perfil.nome}] Descarte por escopo: {detalhe}")

    # Alerta de saúde: se a maioria das fontes falhou/voltou vazia, o painel
    # (ver painel/gerar_painel.py) precisa poder mostrar isso — sem isso, um
    # bloqueio geral ou mudança de layout passaria despercebido, porque o
    # workflow do GitHub Actions continuaria "verde" mesmo com tudo
    # quebrado. _deve_alertar_saude só calcula o sinal; quem exibe é o
    # painel, lendo o status gravado logo abaixo.
    if _deve_alertar_saude(len(scrapers_com_problema), len(scrapers)):
        logger.warning(
            f"[{perfil.nome}] {len(scrapers_com_problema)}/{len(scrapers)} fontes com "
            f"problema neste ciclo: {', '.join(scrapers_com_problema)}."
        )

    _registrar_status_execucao(
        perfil, total_brutas, total_filtradas, total_novas, scrapers_com_problema, len(scrapers)
    )


def _rodar_um_ciclo_de_cada(perfis: list[Perfil]):
    for perfil in perfis:
        print(f"\n{'=' * 50}")
        print(f"PERFIL: {perfil.nome.upper()}")
        print("=" * 50)

        print("\nPalavras monitoradas:")
        for palavra in perfil.palavras_monitoradas:
            print(f"• {palavra}")

        if perfil.paises_pesquisados:
            print("\nPaíses pesquisados:")
            for pais in perfil.paises_pesquisados:
                print(f"• {pais}")

        ciclo_de_busca(perfil)


def main():
    parser = argparse.ArgumentParser(description="JobRadar - monitor de vagas")
    parser.add_argument(
        "--perfil",
        required=True,
        nargs="+",
        choices=sorted(PERFIS.keys()),
        help=(
            "Qual(is) mercado(s) rodar nesta execução — 'brasil', 'internacional', "
            "ou os dois (--perfil brasil internacional)."
        ),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Roda um único ciclo de busca (de cada perfil selecionado) e encerra "
             "(usado no GitHub Actions, que já dispara o script periodicamente via cron).",
    )
    args = parser.parse_args()

    perfis_selecionados = [PERFIS[chave] for chave in args.perfil]

    if not args.once:
        print(f"\nIntervalo de checagem: {INTERVALO_MINUTOS} min\n")

    # Chamado UMA VEZ só, antes de qualquer perfil rodar — não por perfil.
    # A checagem de "banco suspeito" (ver database.py) compara se o arquivo
    # já existia ANTES desta execução; se cada perfil chamasse iniciar_db()
    # separadamente na mesma execução, o segundo perfil veria o arquivo que
    # o primeiro acabou de criar/popular momentos atrás e podia disparar
    # falso positivo (arquivo "já existia" só porque o perfil anterior já
    # rodou nesta mesma execução, não porque é run antigo de verdade).
    try:
        iniciar_db()
    except BancoVazioSuspeito as e:
        logger.error(str(e))
        sys.exit(1)

    if args.once:
        _rodar_um_ciclo_de_cada(perfis_selecionados)
        return

    while True:
        _rodar_um_ciclo_de_cada(perfis_selecionados)
        logger.info(f"Aguardando {INTERVALO_MINUTOS} minutos até a próxima checagem...")
        time.sleep(INTERVALO_MINUTOS * 60)


if __name__ == "__main__":
    main()
