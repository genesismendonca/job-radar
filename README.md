<div align="center">

<!-- ![JobRadar](assets/cover.png) -->

# 📡 JobRadar
### Monitor Automatizado de Vagas de Dados & BI

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-Scraping-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-Banco%20versionado-07405E?style=for-the-badge&logo=sqlite&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-Cron-2088FF?style=for-the-badge&logo=githubactions&logoColor=white)
![Tests](https://img.shields.io/badge/testes-295%20passing-success?style=for-the-badge)
![Status](https://img.shields.io/badge/status-em%20produção-success?style=for-the-badge)

**Autora:** Liliam Kezia Oliveira Souza

</div>

---

## 💎 Proposta de valor

> Em cidade pequena, vaga boa de Dados/BI aparece pouco e some rápido — quem checa o board duas vezes por dia perde pra quem checou na primeira hora. **JobRadar** é um sistema de monitoramento contínuo que substitui essa checagem manual: varre **8 fontes** a cada **3 horas**, filtra por cargo/cidade/mercado/idioma com três níveis de confiança, pontua cada vaga por relevância e publica tudo num painel — rodando de graça, sem servidor próprio, 24 horas por dia.

## 📄 Resumo executivo

Entre 07 e 15 de agosto, o sistema já processou **1.052 vagas únicas**, sem intervenção manual nenhuma — mas os números também expõem os riscos reais da arquitetura atual:

| Achado | Número |
|---|---|
| 📊 Vagas processadas (deduplicadas) | **1.052** |
| 🔗 Concentração numa única fonte (LinkedIn) | **89,5%** |
| 🧪 Testes automatizados (CI a cada push) | **295** |
| 🌎 Fontes monitoradas em paralelo | **8** |
| ⏱️ Frequência de checagem | **a cada 3h** |
| 💰 Custo de infraestrutura | **R$ 0** |

A concentração em LinkedIn é um risco medido, não ignorado: o endpoint usado não é oficial e o próprio código documenta a chance de bloqueio — por isso parte do trabalho recente foi medir o rendimento de cada fonte secundária e paginar mais fundo nelas, em vez de só empilhar fonte nova.

---

## 📸 Como chega pra você

<!-- ![Painel do JobRadar](assets/screenshots/painel.png) -->

Um painel estático, publicado no GitHub Pages e regenerado a cada ciclo (3h): destaques recentes ranqueados por relevância no topo, histórico completo pesquisável e filtrável logo abaixo, métricas por fonte no fim da página — e o status da última execução de cada perfil, pra saber se o robô ainda está de pé sem precisar abrir o log do GitHub Actions. Sem push, sem app — só um link que reflete o estado mais recente do banco toda vez que é aberto.

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
| **Filtra** | Cargo (forte / ambíguo + qualificador / ferramenta + cargo), cidade ou mercado remoto, idioma |
| **Pontua** | Score 0–10 por vaga: cargo, ferramenta, senioridade, mercado, idioma — soma de sinais, sem IA |
| **Deduplica** | Por link e por empresa+título, pra pegar a mesma vaga republicada em fonte diferente |
| **Publica** | Painel estático regenerado do zero a cada ciclo, com o que existe no banco até ali — sem push, sem spam |

## 🏗️ Arquitetura técnica

- **Filtro em 3 níveis de confiança:** cargo inequívoco passa sozinho; cargo ambíguo (ex: "Business Analyst") só conta com qualificador de dados junto no título; ferramenta (ex: "Power BI") só conta com palavra de cargo junto — nada aprova por palavra-chave solta.
- **Score de relevância sem ML:** 5 sinais conhecidos (cargo, ferramenta, senioridade, mercado, idioma), pesos calibrados contra o histórico real do banco, não chutados.
- **Zero infraestrutura:** GitHub Actions como motor de cron, SQLite como banco — versionado no próprio Git, o histórico de vagas já vistas *é* o commit. O painel (ver [Painel](#%EF%B8%8F-painel)) segue a mesma lógica: HTML estático gerado a cada ciclo e publicado no GitHub Pages, sem servidor, sem banco externo.
- **Resiliente:** nunca marca vaga como "vista" sem confirmar que ela foi salva; status de cada ciclo (fontes com problema, total de vagas novas) gravado no banco e exibido no painel — sem depender de log do GitHub Actions pra saber se o robô ainda está de pé.
- **295 testes automatizados em CI:** cada caso documenta um bug real já corrigido nesta base — não é cenário hipotético, é regressão registrada.

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
├── tests/ ← 295 casos, roda em CI a cada push
├── data/
│ └── jobs.db ← banco versionado (histórico de dedup)
├── docs/
│ └── index.html ← painel publicado no GitHub Pages (gerado, não editado à mão)
└── .github/workflows/
├── jobradar.yml ← cron de produção (a cada 3h) — busca + gera painel + commita
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

295 casos parametrizados, cobrindo a camada de filtro e o gerador do painel — todos rodando automaticamente a cada push via GitHub Actions.

---

<div align="center">

*Case de portfólio em automação de dados — Python, Playwright, SQLite, GitHub Actions e engenharia de filtro sem ML.*

</div>
