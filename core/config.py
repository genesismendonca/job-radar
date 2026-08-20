
import os
from dotenv import load_dotenv

load_dotenv()

# Requisito atualizado pelo usuário (20/08): o projeto pivotou de Dados/BI
# pra Produto (PM/PO) — perfil real do usuário (Senior Product Manager,
# veio de Product Owner) via LinkedIn. Substituição completa, não adição:
# o histórico de Dados/BI (cidades do Nordeste, keywords em espanhol pra
# Argentina/Chile etc.) era de outra pessoa (ver "Autora" no README),
# sem relação com quem usa o projeto agora.
#
# Cargo forte: título que só existe mesmo em vaga de Produto, sem
# possibilidade real de ser outra área.
KEYWORDS_CARGO_FORTE = [
    "Product Manager",
    "Product Owner",
    "Gerente de Produto",
    "Gerente de Producto",  # espanhol — LinkedInScraper já busca em Argentina/Chile (ver LOCATIONS_LINKEDIN)
    "Head of Product",
    "Diretor de Produto",
    "Group Product Manager",
    "Principal Product Manager",
    "Product Lead",
    "Líder de Produto",
    "VP of Product",
    "VP de Produto",
]

# Sem eixo de cargo ambíguo neste perfil: as siglas óbvias ("PM", "PO")
# são justamente o tipo de palavra-chave solta que este projeto evita de
# propósito ("nada aprova por palavra-chave solta") — "PM" aparece à
# beça em vaga de Project Manager, "PO" em vaga de logística (Purchase
# Order). Sem sinal forte o bastante nem pra valer como AMBÍGUO
# (qualificador "produto"/"product" não resolveria a ambiguidade com
# segurança pra uma sigla de 2 letras), então ficam de fora — só os
# títulos por extenso de KEYWORDS_CARGO_FORTE valem.
KEYWORDS_CARGO_AMBIGUO = []
QUALIFICADORES_DADOS = []

# Sem ferramenta-núcleo equivalente a "Power BI" no domínio de Produto —
# fica vazio de propósito (mesmo padrão que o perfil internacional já usa
# pra esse eixo). Se um padrão real de título aparecer, entra aqui.
FERRAMENTAS_TITULO = []
QUALIFICADORES_CARGO = []

KEYWORDS = KEYWORDS_CARGO_FORTE + KEYWORDS_CARGO_AMBIGUO

# Termos de busca enviados a cada site. Ficam separados das KEYWORDS de
# propósito: TERMOS_BUSCA é a rede ampla (o que é pesquisado em cada site,
# incluindo termos de ferramenta/stack pra achar vaga com título atípico),
# enquanto KEYWORDS é o filtro final e só olha o título da vaga já
# encontrada. Um termo de ferramenta (ex: "dax") só resulta em notificação
# se o TÍTULO da vaga também bater com uma keyword de cargo — isso evita
# falso positivo de vaga que só cita a ferramenta como diferencial.
#
# TERMOS_CARGO é derivado direto de KEYWORDS (em vez de mantido à mão em
# lista separada) — antes as duas listas divergiam: metade das KEYWORDS
# nunca era buscada de verdade, só existia como filtro, então só pegava
# essas vagas por sorte via outro termo. Com a derivação automática isso
# não pode mais acontecer — toda keyword nova em KEYWORDS já vira busca
# também.
#
# Requisito atualizado (20/08, pivô Dados/BI → Produto): sem termo EXTRA
# por enquanto — ao contrário do Power BI/"inteligência de mercado" de
# antes (termo mais amplo que a keyword exata, pra dar rede maior sem
# frouxar o filtro de título), não há um equivalente medido ainda pro
# domínio de Produto. Fácil adicionar aqui se algum termo mostrar valor
# real (ex: nicho como "growth product manager" render vaga que os
# títulos completos não acham).
TERMOS_CARGO_EXTRA = []

TERMOS_CARGO = sorted(set(k.lower() for k in KEYWORDS) | set(TERMOS_CARGO_EXTRA))

# Requisito atualizado (20/08): sem termo de ferramenta pro domínio de
# Produto — ao contrário de Dados/BI (SQL, Python, Tableau...), não existe
# um conjunto de ferramenta-núcleo que sinalize vaga de Produto de forma
# confiável (Jira/Figma são usados por times inteiros, não só por PM/PO) —
# incluir um termo desses aqui só multiplicaria busca sem sinal real.
# Fácil adicionar se surgir um padrão medido.
TERMOS_FERRAMENTA = []

TERMOS_BUSCA = TERMOS_CARGO + TERMOS_FERRAMENTA

# Termos que rodam em TODO ciclo, fora do rodízio — os títulos que
# definem o perfil (ver histórico de por que isso existe: vaga real que
# batia a keyword mais forte da lista nunca era BUSCADA porque o rodízio
# alfabético só passava pelo termo a cada várias horas).
TERMOS_PRIORITARIOS = [
    "product manager",
    "product owner",
    "gerente de produto",
]

# Medido: os TERMOS_BUSCA inteiros (hoje 42) rodando em TODO ciclo é o que
# gera as centenas de sessões de navegador por execução — o custo cresce
# linear com o tamanho da lista, e a lista só cresce (mais ainda com a
# expansão internacional puxando mais termos no radar). TERMOS_POR_CICLO é
# o tamanho do BLOCO usado por ciclo, não o total de termos — main.py roda
# um bloco por vez em rodízio (ver _proximo_bloco_termos) e avança pro
# próximo bloco no ciclo seguinte, salvando a posição no jobs.db. Isso
# desacopla custo por ciclo de tamanho da lista: dobrar TERMOS_BUSCA dobra
# quantos ciclos até cobrir tudo de novo, não o custo de cada ciclo.
TERMOS_POR_CICLO = 10

# Onde vaga HIBRIDA ou PRESENCIAL e aceita (mais "Remoto", que nao e
# cidade e sim a porta de entrada da regra de modalidade remota — ver
# _FLAGS_REMOTO em job.py). Vaga hibrida/presencial fora desta lista e
# rejeitada; e uma whitelist, nao uma preferencia de ordenacao.
#
# Requisito atualizado pela usuaria (20/08): vaga nacional passou a ser
# EXCLUSIVAMENTE remota — hibrida/presencial so entra quando for em Sao
# Paulo. Substitui o requisito anterior (as seis cidades do Nordeste mais
# Manaus, Maceio e Aracaju — historico em tests/test_regras_de_negocio.py
# via git log), que deixou de valer com a mudanca de prioridade.
#
# job.py nao distingue Hibrido de Presencial na checagem de cidade (so
# `modalidade` decide o caminho de remoto — ver _avaliar) — as duas
# modalidades passam pela MESMA whitelist, entao "so Sao Paulo pra
# hibrida" cobre presencial tambem, sem precisar de campo novo.
CIDADES = [
    "Remoto",
    "São Paulo",
]

# MEDIDO: "Data Analyst @ Lisboa" e "Analista de Datos @ Madrid" reprovavam
# na localização, não no cargo — CIDADES acima é whitelist só de cidade
# brasileira, e a expansão de LOCATIONS_LINKEDIN pra Argentina/Chile (ver
# abaixo) passou a trazer vaga presencial/híbrida em Portugal/Espanha de
# vez em quando junto. Lista SEPARADA (não misturada em CIDADES, que
# continua só-Brasil de propósito — ver decisão registrada na criação do
# config_intl.py) com toggle próprio, pra dar pra ligar/desligar esse eixo
# sem mexer no resto do filtro. Canônica aqui porque config_intl.py já
# importa de config.py (não o contrário) — o pipeline internacional reusa
# essa mesma lista em vez de manter uma cópia (risco de divergir, mesmo
# motivo da unificação de _contem_termo/_tem_termo).
CIDADES_EUROPA_IBERICA = [
    "Portugal",
    "Lisboa",
    "Porto",
    "Braga",
    "Espanha",
    "España",
    "Spain",
    "Madrid",
    "Barcelona",
    "Valencia",
]

# Toggle independente do ATIVAR_EIXO_IBERICO de config_intl.py — são dois
# eixos diferentes (esse aqui é do pipeline BR/main.py, aquele é do
# pipeline internacional/main_intl.py), cada um com seu próprio liga/
# desliga, mesmo compartilhando a mesma lista de cidades acima.
#
# DESLIGADO: do mercado internacional, só interessa vaga remota — vaga
# presencial/híbrida em Lisboa/Madrid (o que esse eixo notifica, marcada
# "exploratória") não é o que o usuário quer. CIDADES_EUROPA_IBERICA
# continua definida (não precisa apagar) pra caso o eixo volte a ser
# ligado depois — só o toggle muda.
ATIVAR_EIXO_IBERICO_BR = False

# LinkedInScraper é a única fonte do pipeline BR que também alcança vaga
# fora do Brasil (as outras são portais brasileiros) — mas até aqui rodava
# só com location=Brasil fixo no código (scrapers/linkedin.py:88), então
# essa "porta pra fora" nunca era usada.
#
# Mercado "casa": busca modalidade completa (presencial/híbrida + remoto),
# porque o usuário mora aqui e vaga local de verdade interessa.
LOCATIONS_LINKEDIN = ["Brasil"]

# Mercados adicionais: só busca REMOTA (f_WT=2) — vaga presencial/híbrida
# num país onde o usuário não mora não serve, então nem faz sentido gastar
# a passada nacional ali (era puro desperdício: Argentina/Chile já rodavam
# as duas passadas antes, mas a nacional nunca batia em CIDADES mesmo,
# que é só cidade brasileira). Espanhol ou português — mesmo critério do
# pipeline internacional. Lista reaproveita exatamente os países já usados
# e testados ao vivo no endpoint do LinkedIn em config_intl.py
# (LOCATIONS_INTL) — evita arriscar nome de país nunca testado (grafia
# errada ou região que o LinkedIn não resolve como location de verdade,
# como já visto com "LATAM"/"Latin America").
LOCATIONS_LINKEDIN_REMOTO_APENAS = ["Argentina", "Chile", "México", "Colômbia", "Espanha", "Portugal"]

# MEDIDO (histórico, quando CIDADES tinha cidade do Nordeste): a passada
# nacional (location="Brasil") varre o país inteiro e só sobra o que bate
# em CIDADES depois do filtro — pra termo concorrido em SP/RJ/MG, as 3
# páginas (30 resultados) nunca chegavam numa vaga de cidade menor do
# Nordeste, porque o volume dos polos maiores ocupava tudo antes. Busca
# ESPECÍFICA por cidade não depende de volume nacional — o próprio
# location= do LinkedIn já restringe o resultado à cidade.
#
# Com CIDADES agora só "São Paulo" (ver requisito atualizado acima), essa
# passada específica sobrepõe bastante a nacional (SP já domina o resultado
# nacional por si só) — mantida mesmo assim por ser 1 cidade só, custo de 1
# busca a mais por termo, e ainda cobre o que as 3 primeiras páginas da
# passada nacional cortam. "Remoto" (item de CIDADES) não é local de busca
# de verdade — sai da lista, já coberto pela passada remoto=True de
# LOCATIONS_LINKEDIN acima.
LOCATIONS_LINKEDIN_CIDADES_PRESENCIAL = [c for c in CIDADES if c != "Remoto"]

# Mercado que a vaga remota precisa aceitar pra contar, quando o texto de
# local DECLARA um escopo geográfico ("Remote — US only", "Remote — India").
# Ver Job.escopo_remoto/RegrasFiltro.mercados_remoto_aceitos em job.py — sem
# isso, uma vaga remota só pra outro país passava igual a uma remota de
# verdade pro Brasil. Vaga remota SEM escopo declarado no texto (a grande
# maioria) continua batendo normalmente, isso só filtra quando a fonte
# EXPLICITA um mercado incompatível.
#
# MEDIDO: Argentina/Chile/México/Colômbia ENTRAM nominalmente agora — a
# suposição de que "LATAM" cobria os quatro como guarda-chuva só valia
# enquanto extrair_escopo_remoto resolvia o texto pra "LATAM" literal.
# Depois que passou a reconhecer cidade (Buenos Aires/Santiago/Cidade do
# México/Bogotá — ver _CIDADES_MERCADO em job.py), o escopo passou a
# resolver pro PAÍS específico, não mais pro guarda-chuva — e o país
# específico nunca esteve nessa lista. Resultado: LOCATIONS_LINKEDIN_
# REMOTO_APENAS pagava o custo de buscar nesses 4 países e o filtro
# descartava tudo que a busca trazia de lá. "LATAM" continua na lista pra
# quando o texto disser isso literalmente (guarda-chuva de verdade, não
# substituto de nome de país). Portugal e Espanha entraram nominalmente
# pelo mesmo motivo, desde antes.
MERCADOS_REMOTO_ACEITOS = ["Brasil", "LATAM", "Argentina", "Chile", "México", "Colômbia", "Portugal", "Espanha"]

INTERVALO_MINUTOS = int(os.getenv("INTERVALO_MINUTOS", 180))

# Requisito atualizado pela usuária (20/08): a saída deixou de ser Telegram
# (notificação push) e passou a ser um painel estático (GitHub Pages, ver
# painel/gerar_painel.py) — não tem mais "notifica na hora" vs "fila de
# digest diário", o painel é regenerado a cada ciclo com tudo que existe no
# banco até ali. Este limiar sobrevive com propósito diferente: continua
# marcando o que é vaga de destaque de verdade, só que agora como sinal
# visual no painel (badge/prioridade), não mais como gatilho de mensagem.
#
# MEDIDO (na época em que era gatilho de notificação): rodei o score contra
# as ~305 vagas do jobs.db real que ainda batem as regras atuais.
# Distribuição: score 4 (2%), 5 (24%), 6 (67%), 7 (5%), 8 (2%) — nada em
# 9-10 na amostra (exige acertar praticamente todo sinal ao mesmo tempo:
# cargo forte + ferramenta + senioridade alvo + mercado confirmado). Limiar
# 7 deixa ~7% em destaque — mesma leitura de "isso aqui é excelente, o
# resto é só ok" continua válida pro painel.
LIMIAR_RELEVANCIA_DESTAQUE = 7

# Caminho ancorado na RAIZ do projeto, não na pasta deste arquivo.
#
# MEDIDO: o commit b8227b0 ("Reorganiza raiz: ... -> core/") moveu este
# config.py da raiz pra core/. Como DB_PATH era relativo a __file__, o
# banco se mudou junto, em silêncio: data/jobs.db virou core/data/jobs.db.
# Efeito real, confirmado em disco e no jobradar.log:
#   - data/jobs.db (1.080 vagas, versionado) ficou órfão;
#   - core/data/jobs.db nasceu vazio, então iniciar_db() passou a abortar
#     por BancoVazioSuspeito em toda execução local;
#   - no GitHub Actions a pasta core/data/ não existe no repositório, então
#     o banco era recriado do zero a cada run — toda vaga virava "nova"
#     (renotificação a cada 3h), o rodízio de termos travava no offset 0
#     (só os 10 primeiros de 44 termos eram buscados), a fila do digest era
#     descartada e o heartbeat saía a cada ciclo em vez de 1x/dia;
#   - o passo "git add data/jobs.db" do workflow não via mudança nenhuma
#     ("Nada novo pra commitar"), então o estado nunca mais persistiu.
#
# _RAIZ_PROJETO sobe um nível a partir de core/, então o caminho deixa de
# depender de onde este arquivo mora — mover config.py de novo não move
# mais o banco junto. Coberto por tests/test_db_path.py, pra uma
# reorganização futura quebrar o teste em vez da produção.
#
# JOBRADAR_DB_PATH existe pra apontar um banco descartável em teste/
# experimento sem risco de escrever no banco real.
_RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.getenv("JOBRADAR_DB_PATH") or os.path.join(_RAIZ_PROJETO, "data", "jobs.db")