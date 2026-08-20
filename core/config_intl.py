
# Config do programa internacional (busca vaga remota fora do Brasil).
# Separado do config.py de propósito — ver decisão registrada na
# conversa: misturar ia forçar o filtro de cidade do Nordeste e as
# keywords em português do JobRadar original a servir dois propósitos
# diferentes ao mesmo tempo, deixando os dois mais frágeis.
#
# Caminho do banco é o MESMO do projeto principal (o dedup por link no
# mesmo jobs.db não tem risco de colisão — o id é hash do link, e vaga
# internacional nunca vai ter o mesmo link de uma vaga brasileira).
from core.config import DB_PATH, CIDADES_EUROPA_IBERICA  # noqa: F401

# Requisito atualizado pela usuaria (20/08): cargo passou a ser só em
# inglês/português — espanhol saiu (removida a nomenclatura em espanhol
# que existia aqui, ex: "Analista de Datos", "Analítica de Datos"). A
# elegibilidade de quem pode se candidatar (Brasil/LATAM) deixou de
# depender de idioma no anúncio — passou a ser resolvida pelo mercado
# declarado no texto (ver MERCADOS_REMOTO_ACEITOS_INTL mais abaixo).
KEYWORDS_INTL = [
    "Data Analyst",
    "Business Intelligence",
    "BI Analyst",
    "Data Analytics",
    "Data Specialist",
    "Analista de Dados",
    "Business Analyst",
    # Eixo separado: Data Annotation / AI Evaluator — não é análise de
    # dados, é rotular/avaliar dado pra treinar IA, mas é um nicho remoto
    # que contrata muito por idioma (PT-BR/ES) e paga em dólar, então entra
    # como categoria própria de cargo, não mistura com as de análise.
    "Data Annotator",
    "Data Annotation",
    "AI Evaluator",
    "AI Trainer",
    "Data Labeler",
    "Search Quality Rater",
]

# Requisito atualizado pela usuaria (20/08): busca de cargo PURO passou a
# ser a busca principal, sem exigir idioma/mercado emparelhado na mesma
# frase — antes o termo combinava cargo+idioma ("data analyst spanish
# speaker") de propósito, pra não trazer vaga do mundo inteiro sem filtro
# nenhum; isso deixou de ser necessário porque a elegibilidade de quem pode
# se candidatar (mora no Brasil/LATAM?) passou a ser resolvida DEPOIS, pelo
# mercado declarado no texto da vaga (ver MERCADOS_REMOTO_ACEITOS_INTL e
# Job.escopo_remoto) — vaga que declara exigir um país/região que não é
# Brasil/LATAM é rejeitada ali, mesmo tendo sido encontrada por um termo
# solto sem sinal de idioma nenhum.
#
# Derivado direto de KEYWORDS_INTL (mesma lógica de TERMOS_CARGO em
# config.py) em vez de mantido à mão em lista separada — toda keyword nova
# em KEYWORDS_INTL já vira busca também, sem risco de divergir com o tempo.
TERMOS_BUSCA_INTL = sorted(set(k.lower() for k in KEYWORDS_INTL))

# Requisito atualizado pela usuaria (20/08): o gate de idioma no título
# (IDIOMAS_EXIGIDOS_INTL) saiu. Antes, vaga remota sem mercado declarado no
# texto só passava se o título afirmasse espanhol/português/LATAM
# explicitamente — critério frágil (dependia do anúncio mencionar idioma no
# TÍTULO, que é só um pedaço do texto indexado). Agora a elegibilidade é só
# o mercado declarado (ver MERCADOS_REMOTO_ACEITOS_INTL): vaga remota SEM
# nenhuma restrição geográfica no texto passa direto (não tem base pra
# rejeitar); vaga que declara mercado passa se ele for Brasil/LATAM/Ibéria
# (a lista abaixo) e é rejeitada se declarar outro país/região — American,
# Reino Unido, Alemanha etc., mesmo sem nenhuma palavra em inglês "pura" no
# meio do caminho.

# Rodízio de termos, mesmo mecanismo do TERMOS_POR_CICLO em config.py (ver
# _proximo_bloco_termos em main.py) — só que com chave de metadados própria
# (sufixo "_internacional"), pra não colidir com o rodízio do perfil BR.
# Esse perfil nunca tinha rodízio antes de virar perfil de verdade (rodava a
# lista de termos INTEIRA todo ciclo, sem custo controlado, e nem chegava a
# rodar de fato — não estava no workflow do GitHub Actions). 27 termos x até
# 6 países/domínios por fonte já é bastante busca; bloco de 10 mantém o
# custo por ciclo parecido com o do perfil BR.
TERMOS_POR_CICLO_INTL = 10

# Mercados pesquisados por rodada de busca no LinkedIn (parâmetro location
# do endpoint). Cada país aqui multiplica o número de buscas (termos ×
# países × 2 passadas — ver LinkedInIntlScraper.buscar_vagas), então é o
# parâmetro que mais pesa no custo/tempo do ciclo.
#
# Requisito atualizado pela usuaria (20/08): "United States"/"United
# Kingdom" (removidos antes por trazerem vaga que exige inglês nativo, sem
# chance real pra quem mora no Brasil/LATAM) voltaram, e a Europa passou a
# entrar INTEIRA, incluindo Leste Europeu — não só Ibéria. Isso só é seguro
# porque o gate de elegibilidade (MERCADOS_REMOTO_ACEITOS_INTL, mais abaixo)
# deixou de depender de idioma no anúncio: vaga achada aqui que declarar
# exigência de um país fora da lista aceita (ex: "Remote — US only",
# "Remote — Germany") é rejeitada ali, mesmo sem nada em espanhol/português
# no texto. Sem esse gate, reabrir estes países alagaria o pipeline de vaga
# que exige inglês nativo — não é a busca aqui que filtra isso, é o mercado
# depois.
#
# CUSTO (estimado em 20/08, não medido ao vivo — tentativa de medir direto
# neste ambiente de dev falhou: sem saída de rede até o linkedin.com daqui,
# só em produção/GitHub Actions): a base real é a própria medição em
# perfis.py (histórico) — 6 países, 10 termos × 6 × 2 passadas = 120
# requisições em 6m24s reais (~3,2s/requisição, navegação completa
# incluída). Escalando linear pra 44 países (10 × 44 × 2 = 880
# requisições): ~47min só pro LinkedIn Intl, cenário otimista. Somado ao
# perfil Brasil (~11-12min medidos) dá ciclo completo perto de ~60min —
# dentro do timeout do job (150min, ver .github/workflows/jobradar.yml).
#
# A pressão de tempo que motivou essa conta caiu bastante desde que o cron
# passou de 8 ciclos/dia (a cada 3h) pra 1x/dia (ver jobradar.yml,
# requisito atualizado 20/08): mesmo o cenário pessimista (ciclo bem acima
# do estimado, por bloqueio do LinkedIn — mesmo padrão que já tirou o
# Indeed Intl do projeto) tem folga enorme numa janela de 24h, ao contrário
# de antes, quando o ciclo precisava terminar bem dentro de 3h pra não
# empilhar em cima do próximo. Ainda assim é extrapolação, não medição —
# MEDIR de verdade no primeiro ciclo real após o merge (ver jobradar.log)
# antes de considerar reativar Indeed Intl ou paginar (MAX_PAGINAS) de
# novo. Se algum dia o cron voltar a ser mais frequente, a mitigação pra
# custo alto é introduzir rodízio por país (mesmo mecanismo do
# TERMOS_POR_CICLO_INTL, que este projeto ainda não tem pra location).
#
# "Latin America"/"LATAM"/"EMEA"/"Iberia" continuam FORA: testei ao vivo no
# endpoint do LinkedIn e nenhum nome de região resolve como location de
# verdade (retorna resultado genérico, sem filtrar nada, ou vazio) — só
# país/cidade específico. Por isso todo país entra nominalmente, e
# "latam"/"latin america" seguem como texto de ESCOPO aceito (ver
# MERCADOS_REMOTO_ACEITOS_INTL), não como valor de location.
#
# Micro-estados europeus (Vaticano, San Marino, Mônaco, Liechtenstein,
# Andorra) ficaram de fora de propósito — mercado de trabalho remoto
# irrelevante pra esses, custaria busca sem gerar vaga real. Fácil
# adicionar depois se algum mostrar volume.
LOCATIONS_INTL = [
    # Ibéria + LATAM (já cobertos antes)
    "Spain",
    "Portugal",
    "Mexico",
    "Colombia",
    "Argentina",
    "Chile",
    # América do Norte / Reino Unido
    "United States",
    "United Kingdom",
    "Ireland",
    # Europa Ocidental
    "France",
    "Germany",
    "Netherlands",
    "Belgium",
    "Switzerland",
    "Austria",
    "Luxembourg",
    # Europa do Norte
    "Sweden",
    "Norway",
    "Denmark",
    "Finland",
    "Iceland",
    # Europa do Sul
    "Italy",
    "Greece",
    "Malta",
    "Cyprus",
    # Europa Central e do Leste
    "Poland",
    "Czech Republic",
    "Slovakia",
    "Hungary",
    "Romania",
    "Bulgaria",
    "Croatia",
    "Slovenia",
    "Serbia",
    "Bosnia and Herzegovina",
    "Montenegro",
    "North Macedonia",
    "Albania",
    "Lithuania",
    "Latvia",
    "Estonia",
    "Ukraine",
    "Moldova",
    "Belarus",
]

# Sem cidade nenhuma — só remoto, de qualquer país. "Remote" cobre o termo
# em inglês (a maioria dos cards vai estar em inglês), "Remoto" cobre os
# poucos que vierem em português/espanhol.
#
# PROBLEMA que isso sozinho causava: CIDADES_INTL é uma whitelist — só
# aceita "Remote"/"Remoto" no local. Isso rejeita vaga presencial/híbrida
# em Lisboa ou Madrid mesmo quando ela é achada de propósito (via
# LOCATIONS_INTL = Portugal/Spain), porque o local não escreve "Remote"
# literalmente. Não é uma regra "excluir Portugal" — é a lógica de
# whitelist só admitir o que está na lista, o que dá no mesmo na prática.
#
CIDADES_INTL = ["Remote", "Remoto"]

# Ver MERCADOS_REMOTO_ACEITOS em config.py e Job.escopo_remoto/
# extrair_escopo_remoto em job.py. Duas listas com propósito DIFERENTE,
# mesma lógica de TERMOS_BUSCA/TERMOS_POR_CICLO vs KEYWORDS: LOCATIONS_INTL
# é ONDE BUSCAR (custo real — cada país multiplica busca × termo, então fica
# enxuto nos mercados que mais contratam); esta lista aqui é O QUE ACEITAR
# (custo zero — só comparação de string), então cobre TODO país
# hispanofalante/lusófono, não só os 6 de LOCATIONS_INTL. Precisa ser
# abrangente porque desde que _mercado_correspondente() virou allowlist
# estrita (ver job.py) — escopo declarado que não bate aqui é REJEITADO,
# mesmo vindo de um país que o projeto quer aceitar, então faltar um país
# aqui vira falso negativo (barra vaga boa), não falso positivo.
#
# Requisito atualizado pela usuaria (20/08): "Brasil" ENTROU. O critério
# de elegibilidade passou a ser explícito — "a vaga pode ser aplicada por
# morador do Brasil e LATAM" — então "Remote — Brazil"/"Remote — Brazil
# only" declarado num anúncio internacional (achado via LOCATIONS_INTL,
# fora do pipeline BR) agora é aceito aqui também, em vez de cair no
# mesmo balde de "país fora do escopo" que Alemanha/Polônia/EUA. Continua
# sem duplicar PERFIL_BR: aquele pipeline busca por CARGO em fonte
# brasileira; este busca por PAÍS em fonte internacional — o mesmo link
# nunca aparece nos dois ao mesmo tempo, e o dedup por link cobre o caso
# raro de aparecer.
#
# Vaga "Remote — US only"/"Remote — India"/"Remote — Vietnam"/"Remote —
# Germany" segue sendo rejeitada, inclusive quando o país não está no
# dicionário de job.py (ver MEDIDO em _mercado_correspondente) — é
# justamente essa allowlist estrita que torna seguro buscar em EUA/Europa
# inteira (ver LOCATIONS_INTL) sem mais depender de idioma no anúncio.
MERCADOS_REMOTO_ACEITOS_INTL = [
    "Brasil",
    "Portugal",
    "Espanha",
    "México",
    "Colômbia",
    "Argentina",
    "Chile",
    "Peru",
    "Uruguai",
    "Paraguai",
    "Bolívia",
    "Equador",
    "Venezuela",
    "Costa Rica",
    "Panamá",
    "Guatemala",
    "Honduras",
    "El Salvador",
    "Nicarágua",
    "República Dominicana",
    "Porto Rico",
    "Cuba",
    "Angola",
    "Moçambique",
    "Cabo Verde",
    "LATAM",
]

# Eixo separado pra isso, controlado por ATIVAR_EIXO_IBERICO — dá pra
# desligar sem mexer no resto do pipeline internacional (nem em
# CIDADES_INTL). Quando ativo, vaga presencial/híbrida em Portugal/Espanha
# passa também, mas marcada como "exploratória" na notificação (ver
# main_intl.py), pra distinguir de vaga remota de verdade.
# CIDADES_EUROPA_IBERICA (a lista de cidades) mudou pra config.py — o
# pipeline BR (main.py) passou a ter o mesmo eixo (ver ATIVAR_EIXO_IBERICO_BR
# lá), e as duas listas eram idênticas, então centralizei numa só pra não
# correr risco de uma mudar e a outra ficar pra trás. Esse toggle aqui
# continua LOCAL e independente do ATIVAR_EIXO_IBERICO_BR — são eixos de
# pipelines diferentes, cada um liga/desliga por conta própria.
#
# DESLIGADO: do mercado internacional, só interessa vaga remota — vaga
# presencial/híbrida em Lisboa/Madrid não é o que o usuário quer, mesmo
# achada de propósito via LOCATIONS_INTL. Continua fácil de religar depois
# (só o toggle), sem apagar nada da lista/lógica.
ATIVAR_EIXO_IBERICO = False

# Indeed usa subdomínio por país, não parâmetro de location como o
# LinkedIn. Confirmei ao vivo que es.indeed.com, pt.indeed.com e
# mx.indeed.com funcionam e trazem vaga local de verdade (ex: "Analista de
# Dados" em Lisboa, "Data Analyst" em Barcelona). co/ar/cl seguem o mesmo
# padrão de domínio mas não testei individualmente — se algum não resolver
# como esperado, o scraper só loga 0 vagas pra aquele país, não quebra o
# resto.
#
# "Estados Unidos" (www.indeed.com) e "Reino Unido" (uk.indeed.com) foram
# REMOVIDOS pelo mesmo motivo do LOCATIONS_INTL: domínio de país não filtra
# idioma, e a maioria das vagas desses dois mercados pede inglês fluente —
# era a fonte real das notificações de vaga em inglês.
#
# Mesmo aviso do Indeed BR original: tem proteção anti-bot que pode
# bloquear acesso automatizado (principalmente de IP de nuvem/datacenter),
# mesmo funcionando em teste manual.
DOMINIOS_INDEED_INTL = {
    "Espanha": "es.indeed.com",
    "Portugal": "pt.indeed.com",
    "México": "mx.indeed.com",
    "Colômbia": "co.indeed.com",
    "Argentina": "ar.indeed.com",
    "Chile": "cl.indeed.com",
}
