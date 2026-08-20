<div align="center">

<!-- ![JobRadar](assets/cover.png) -->

# 📡 JobRadar
### Monitor Automatizado de Vagas de Produto (PM/PO)

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Scraping-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Banco%20versionado-07405E?style=for-the-badge&logo=sqlite&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Cron-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Tests](https://img.shields.io/badge/testes-305%20passing-success?style=for-the-badge)
![Status](https://img.shields.io/badge/status-em%20produção-success?style=for-the-badge)

**Autor:** Gênesis Mendonça
**Base original:** fork do projeto de Liliam Kezia Oliveira Souza — arquitetura de scraping/filtro/painel reaproveitada, cargo-alvo migrado de Dados/BI para Produto (PM/PO) em 20/08.

</div>

---

## 💎 Proposta de valor

> Vaga boa de Product Manager/Product Owner aparece pouco e some rápido — quem checa o board uma vez por dia perde pra quem checou na primeira hora. **JobRadar** é um sistema de monitoramento contínuo que substitui essa checagem manual: varre **8 fontes** uma vez por dia, de madrugada, filtra por cargo (Product Manager, Product Owner e variações)/cidade/mercado com três níveis de confiança, pontua cada vaga por relevância e publica tudo num painel pronto quando o usuário acorda — rodando de graça, sem servidor próprio.

## 📄 Resumo executivo

| Achado | Número |
|---|---|
| 🧪 Testes automatizados (CI a cada push) | **305** |
| 🌎 Fontes monitoradas em paralelo | **8** (perfil Brasil) + LinkedIn/WeWorkRemotely (perfil Internacional) |
| ⏱️ Frequência de checagem | **1x por dia, 06h (Brasília)** |
| 💰 Custo de infraestrutura | **R$ 0** |

Os números de volume/concentração por fonte da era anterior (Dados/BI) não valem mais — a busca de Produto começa do zero em 20/08, sem histórico próprio ainda. Vale remedir depois de rodar um tempo em produção (ver aviso em `core/perfis.py`).

---

## 📸 Como chega pra você

<!-- ![Painel do JobRadar](assets/screenshots/painel.png) -->

Um painel estático, publicado no GitHub Pages e regenerado a cada ciclo (1x/dia): destaques recentes ranqueados por relevância no topo, histórico completo pesquisável e filtrável logo abaixo, métricas por fonte no fim da página — e o status da última execução de cada perfil, pra saber se o robô ainda está de pé sem precisar abrir o log do GitHub Actions. Sem push, sem app — só um link que reflete o estado mais recente do banco toda vez que é aberto.

---

## 🗂️ Sumário

- [Como funciona (pipeline)](#-como-funciona-pipeline)
- [Arquitetura técnica](#%EF%B8%8F-arquitetura-técnica)
- [Estrutura do repositório](#-estrutura-do-repositório)
- [Como rodar](#-como-rodar)
- [Painel](#%EF%B8%8F-painel)
- [Testes](#-testes)

---

## 🧭 Como funciona (pipeline)

| Etapa | O que faz |
|---|---|
| **Busca** | Varre as fontes em paralelo, com rodízio de termos pra controlar custo por ciclo |
| **Filtra** | Cargo (Product Manager, Product Owner e variações — título exato, sem palavra-chave solta), cidade ou mercado remoto |
| **Pontua** | Score 0–10 por vaga: cargo, senioridade, mercado, idioma — soma de sinais, sem IA |
| **Deduplica** | Por link e por empresa+título, pra pegar a mesma vaga republicada em fonte diferente |
| **Publica** | Painel estático regenerado do zero a cada ciclo, com o que existe no banco até ali — sem push, sem spam |

## 🏗️ Arquitetura técnica

- **Filtro por título exato, sem palavra-chave solta:** só título inequívoco de Produto (Product Manager, Product Owner, Gerente de Produto e variações — ver `KEYWORDS_CARGO_FORTE` em `core/config.py`) aprova. O mecanismo de filtro também suporta um eixo de "cargo ambíguo + qualificador" e outro de "ferramenta + palavra de cargo" (usados antes do pivô, quando o alvo era Dados/BI — ex: "Business Analyst" só contava com qualificador de dados junto), mas o perfil de Produto não precisa deles por enquanto: siglas como "PM"/"PO" são ambíguas demais pra valer até com qualificador, então ficam fora.
- **Score de relevância sem ML:** sinais conhecidos (cargo, senioridade, mercado, idioma), pesos calibrados contra o histórico real do banco, não chutados.
- **Zero infraestrutura:** GitHub Actions como motor de cron, SQLite como banco — versionado no próprio Git, o histórico de vagas já vistas *é* o commit. O painel (ver [Painel](#%EF%B8%8F-painel)) segue a mesma lógica: HTML estático gerado a cada ciclo e publicado no GitHub Pages, sem servidor, sem banco externo.
- **Resiliente:** nunca marca vaga como "vista" sem confirmar que ela foi salva; status de cada ciclo (fontes com problema, total de vagas novas) gravado no banco e exibido no painel — sem depender de log do GitHub Actions pra saber se o robô ainda está de pé.
- **305 testes automatizados em CI:** cada caso documenta um bug real já corrigido nesta base — não é cenário hipotético, é regressão registrada.

## 📁 Estrutura do repositório

jobradar/
├── README.md
├── requirements.txt
├── main.py ← motor único: um ciclo de busca por perfil
├── core/
│ ├── perfis.py ← Brasil vs Internacional (dado, não lógica duplicada)
│ ├── config.py / config_intl.py ← cargos, cidades, termos de busca, pesos
│ └── job.py ← Job, filtro, score de relevância
├── database/
│ └── database.py ← SQLite: dedup, metadados (status de execução, rodízio de termos)
├── painel/
│ └── gerar_painel.py ← lê o banco e gera docs/index.html (painel estático)
├── scrapers/ ← um módulo por fonte (LinkedIn, Gupy, Indeed...)
├── utils/
│ └── filtro.py
├── tests/ ← 305 casos, roda em CI a cada push
├── data/
│ └── jobs.db ← banco versionado (histórico de dedup)
├── docs/
│ └── index.html ← painel publicado no GitHub Pages (gerado, não editado à mão)
└── .github/workflows/
├── jobradar.yml ← cron de produção (1x/dia, 06h Brasília) — busca + gera painel + commita
└── testes.yml ← CI

## 💻 Como rodar

```bash
git clone <repo>
cd jobradar
python -m venv venv && venv\Scripts\activate   # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

```bash
python main.py --perfil brasil internacional --once
python -m painel.gerar_painel   # gera docs/index.html a partir do banco
```

Pra ver o painel localmente, abra `docs/index.html` direto no navegador (não precisa de servidor — é um arquivo estático self-contained).

## 🖥️ Painel

Publicado via GitHub Pages, servindo a pasta `docs/` da branch `main` — configuração única, feita uma vez em *Settings → Pages → Source: Deploy from a branch → main / docs*. Depois disso, todo push em `docs/index.html` (o workflow de produção faz isso a cada ciclo) atualiza o painel publicado automaticamente, sem passo manual nenhum.

## 🧪 Testes

```bash
pytest tests/ -v
```

305 casos parametrizados, cobrindo a camada de filtro e o gerador do painel — todos rodando automaticamente a cada push via GitHub Actions.

---

<div align="center">

*Case de portfólio em automação de busca de vagas — Python, Playwright, SQLite, GitHub Actions e engenharia de filtro sem ML.*

</div>
