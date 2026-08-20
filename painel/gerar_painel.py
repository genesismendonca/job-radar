"""Gera o painel estático (docs/index.html) a partir de data/jobs.db.

Requisito atualizado pela usuária (20/08): a saída deixou de ser Telegram
(push) e passou a ser um painel que ela acessa quando quiser (pull),
publicado no GitHub Pages — mesma filosofia de custo zero do resto do
projeto (GitHub Actions já roda 1x/dia, de madrugada; este script roda
logo depois, no mesmo job, e o resultado é só mais um arquivo commitado,
igual data/jobs.db já era).

Página self-contained: HTML/CSS/JS embutidos num arquivo só, sem CDN
nenhum (mesmo raciocínio dos scrapers — nada externo pra quebrar ou
bloquear), com os dados embutidos como JSON e filtro/busca em
JavaScript puro no navegador. Não existe backend nenhum servindo isso —
GitHub Pages só serve arquivo estático — então toda a "consulta" (busca,
filtro, ordenação, agregação por fonte) acontece no navegador de quem
está olhando, a partir do JSON embutido.

Roda standalone (`python -m painel.gerar_painel`), sem depender de
main.py ter acabado de rodar na mesma execução — por isso chama
iniciar_db() aqui também (idempotente, mesma migração leve que main.py e
relatorio_precisao.py já rodavam antes de qualquer consulta).
"""

import html
import json
import os
import re
import sqlite3
from datetime import datetime, timezone

from core.config import DB_PATH, LIMIAR_RELEVANCIA_DESTAQUE
from core.perfis import PERFIS
from database.database import iniciar_db

_RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA_HTML = os.path.join(_RAIZ_PROJETO, "docs", "index.html")

_COLUNAS_VAGA = (
    "id", "titulo", "empresa", "local", "link", "site", "perfil",
    "modalidade", "relevancia", "motivo", "exploratoria", "situacao",
    "encontrada_em", "publicado_em",
)

# Mesmo critério de Job.publicacao_antiga (job.py) — não importa a função
# privada de lá de propósito (é lógica de FILTRO, interna ao pipeline de
# busca; o painel só PRECISA saber se mostra o aviso "pode já estar
# preenchida", uma decisão de exibição, não de regra de negócio). Reimplementa
# o mesmo critério simples (meses/anos no texto) em vez de acoplar o painel
# à camada de filtro.
_PADRAO_PUBLICACAO_ANTIGA = re.compile(r"\b(mes|meses|mês|mêses|ano|anos)\b", re.IGNORECASE)


def _carregar_vagas(conn: sqlite3.Connection) -> list[dict]:
    linhas = conn.execute(
        f"SELECT {', '.join(_COLUNAS_VAGA)} FROM vagas_vistas ORDER BY encontrada_em DESC"
    ).fetchall()
    vagas = []
    for linha in linhas:
        vaga = dict(zip(_COLUNAS_VAGA, linha))
        vaga["exploratoria"] = bool(vaga["exploratoria"])
        vaga["relevancia"] = vaga["relevancia"] if vaga["relevancia"] is not None else 0
        vaga["antiga"] = bool(
            vaga["publicado_em"] and _PADRAO_PUBLICACAO_ANTIGA.search(vaga["publicado_em"])
        )
        vagas.append(vaga)
    return vagas


def _carregar_status(conn: sqlite3.Connection) -> dict[str, dict | None]:
    """Status da última execução por perfil (ver main.py/
    _registrar_status_execucao) — o que substitui o heartbeat que o
    Telegram mandava. None quando o perfil nunca rodou ainda (banco novo,
    ou perfil adicionado recentemente) — o painel mostra isso como "sem
    dado ainda", não como execução travada."""
    status_por_perfil: dict[str, dict | None] = {}
    for chave in PERFIS:
        linha = conn.execute(
            "SELECT valor FROM metadados WHERE chave = ?",
            (f"status_ultima_execucao_{chave}",),
        ).fetchone()
        status_por_perfil[chave] = json.loads(linha[0]) if linha else None
    return status_por_perfil


def _nomes_perfis() -> dict[str, str]:
    return {chave: perfil.nome for chave, perfil in PERFIS.items()}


def gerar_html(vagas: list[dict], status_por_perfil: dict[str, dict | None]) -> str:
    dados = {
        "geradoEm": datetime.now(timezone.utc).isoformat(),
        "limiarDestaque": LIMIAR_RELEVANCIA_DESTAQUE,
        "nomesPerfis": _nomes_perfis(),
        "status": status_por_perfil,
        "vagas": vagas,
    }
    # json.dumps dentro de <script type="application/json"> é seguro contra
    # o texto quebrar a tag (diferente de interpolar direto num template
    # literal JS) — só precisa escapar "</" pra não fechar a tag <script>
    # mais cedo se algum campo (ex: titulo raspado de um site) contiver
    # literalmente "</script>".
    payload = json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")
    return _TEMPLATE.replace("__DADOS_JSON__", payload)


_TEMPLATE = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JobRadar — Painel</title>
<style>
:root {
  --bg: #f7f7f8; --bg-elevado: #ffffff; --texto: #1a1a1e; --texto-fraco: #63636c;
  --borda: #e2e2e6; --acento: #2e5cff; --acento-fraco: #eef1ff;
  --sucesso: #1a7f37; --alerta: #b45309; --erro: #c0341f;
  --sombra: 0 1px 2px rgba(0,0,0,.05), 0 1px 8px rgba(0,0,0,.04);
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #111114; --bg-elevado: #1a1a1f; --texto: #ececf0; --texto-fraco: #9a9aa2;
    --borda: #2c2c33; --acento: #7c9bff; --acento-fraco: #1c2440;
    --sucesso: #3fb950; --alerta: #d29922; --erro: #f85149;
    --sombra: 0 1px 2px rgba(0,0,0,.3), 0 1px 8px rgba(0,0,0,.3);
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--texto);
  font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
main { max-width: 1080px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 22px; margin: 0 0 4px; }
h2 { font-size: 17px; margin: 0 0 12px; }
.subtitulo { color: var(--texto-fraco); font-size: 13px; margin: 0 0 24px; }
.cartao {
  background: var(--bg-elevado); border: 1px solid var(--borda); border-radius: 10px;
  padding: 16px; margin-bottom: 20px; box-shadow: var(--sombra);
}
.grade-status { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-bottom: 24px; }
.status-perfil { display: flex; flex-direction: column; gap: 4px; }
.status-perfil .nome { font-weight: 600; }
.pill { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; padding: 2px 8px; border-radius: 999px; width: fit-content; }
.pill.ok { background: color-mix(in srgb, var(--sucesso) 15%, transparent); color: var(--sucesso); }
.pill.alerta { background: color-mix(in srgb, var(--erro) 15%, transparent); color: var(--erro); }
.pill.neutro { background: var(--acento-fraco); color: var(--acento); }
.abas { display: flex; gap: 6px; margin-bottom: 16px; flex-wrap: wrap; }
.aba {
  border: 1px solid var(--borda); background: var(--bg-elevado); color: var(--texto);
  padding: 6px 14px; border-radius: 999px; font-size: 13px; cursor: pointer;
}
.aba.ativa { background: var(--acento); border-color: var(--acento); color: #fff; }
.vagas-grade { display: grid; gap: 10px; }
.vaga { border: 1px solid var(--borda); border-radius: 8px; padding: 12px 14px; background: var(--bg-elevado); }
.vaga .topo { display: flex; justify-content: space-between; gap: 8px; align-items: baseline; flex-wrap: wrap; }
.vaga .titulo { font-weight: 600; }
.vaga .empresa { color: var(--texto-fraco); }
.vaga .meta { font-size: 13px; color: var(--texto-fraco); margin-top: 4px; }
.estrelas { color: #e0a000; letter-spacing: -1px; }
.tag { display: inline-block; font-size: 11px; padding: 1px 7px; border-radius: 999px; background: var(--acento-fraco); color: var(--acento); margin-left: 6px; }
.tag.aviso { background: color-mix(in srgb, var(--alerta) 18%, transparent); color: var(--alerta); }
a.link-vaga { color: var(--acento); text-decoration: none; font-size: 13px; }
a.link-vaga:hover { text-decoration: underline; }
.controles { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.controles input, .controles select {
  padding: 7px 10px; border-radius: 8px; border: 1px solid var(--borda);
  background: var(--bg-elevado); color: var(--texto); font-size: 13px;
}
.controles input[type="search"] { flex: 1; min-width: 180px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { text-align: left; padding: 7px 8px; border-bottom: 1px solid var(--borda); }
th { color: var(--texto-fraco); font-weight: 600; white-space: nowrap; cursor: pointer; user-select: none; }
tbody tr:hover { background: var(--acento-fraco); }
.tabela-wrap { overflow-x: auto; }
.rodape-tabela { display: flex; justify-content: space-between; align-items: center; margin-top: 10px; font-size: 13px; color: var(--texto-fraco); }
button.pagina {
  border: 1px solid var(--borda); background: var(--bg-elevado); color: var(--texto);
  border-radius: 6px; padding: 5px 12px; cursor: pointer; font-size: 13px;
}
button.pagina:disabled { opacity: .4; cursor: default; }
.barra-fundo { background: var(--acento-fraco); border-radius: 4px; height: 8px; overflow: hidden; }
.barra-preenchida { background: var(--acento); height: 100%; }
.metricas-tabela td:nth-child(2), .metricas-tabela th:nth-child(2) { min-width: 140px; }
footer { text-align: center; color: var(--texto-fraco); font-size: 12px; margin-top: 32px; }
</style>
</head>
<body>
<main>
  <h1>📡 JobRadar — Painel</h1>
  <p class="subtitulo" id="rodape-geracao"></p>

  <div class="grade-status" id="status-execucao"></div>

  <section class="cartao">
    <h2 id="titulo-recentes">Destaques recentes</h2>
    <div class="abas" id="abas-perfil-recentes"></div>
    <div class="vagas-grade" id="lista-recentes"></div>
  </section>

  <section class="cartao">
    <h2>Todas as vagas</h2>
    <div class="controles">
      <input type="search" id="busca" placeholder="Buscar por título, empresa, local ou fonte…">
      <select id="filtro-perfil"><option value="">Todos os perfis</option></select>
      <select id="filtro-site"><option value="">Todas as fontes</option></select>
      <select id="filtro-modalidade">
        <option value="">Qualquer modalidade</option>
        <option value="Remoto">Remoto</option>
        <option value="Híbrido">Híbrido</option>
        <option value="Presencial">Presencial</option>
      </select>
    </div>
    <div class="tabela-wrap">
      <table>
        <thead>
          <tr>
            <th data-col="titulo">Vaga</th>
            <th data-col="empresa">Empresa</th>
            <th data-col="local">Local</th>
            <th data-col="modalidade">Modalidade</th>
            <th data-col="site">Fonte</th>
            <th data-col="relevancia">Score</th>
            <th data-col="encontrada_em">Encontrada em</th>
          </tr>
        </thead>
        <tbody id="corpo-tabela"></tbody>
      </table>
    </div>
    <div class="rodape-tabela">
      <span id="contagem-tabela"></span>
      <span>
        <button class="pagina" id="pagina-anterior">← anterior</button>
        <button class="pagina" id="pagina-proxima">próxima →</button>
      </span>
    </div>
  </section>

  <section class="cartao">
    <h2>Métricas por fonte</h2>
    <div class="tabela-wrap">
      <table class="metricas-tabela">
        <thead>
          <tr><th>Fonte</th><th>Volume</th><th>Total</th><th>Score médio</th></tr>
        </thead>
        <tbody id="corpo-metricas"></tbody>
      </table>
    </div>
  </section>

  <footer>Gerado automaticamente a cada ciclo do JobRadar — <a class="link-vaga" href="https://github.com/genesismendonca/job-radar">código-fonte</a>.</footer>
</main>

<script id="dados-painel" type="application/json">__DADOS_JSON__</script>
<script>
(function () {
  "use strict";
  var DADOS = JSON.parse(document.getElementById("dados-painel").textContent);
  var VAGAS = DADOS.vagas;
  var LINHAS_POR_PAGINA = 25;
  var TAMANHO_JANELA_RECENTE_DIAS = 7;
  var MIN_RECENTES = 8; // se a janela de 7 dias vier curta demais, completa até este mínimo

  function el(tag, props, filhos) {
    var e = document.createElement(tag);
    if (props) for (var k in props) {
      if (k === "class") e.className = props[k];
      else if (k === "text") e.textContent = props[k];
      else e.setAttribute(k, props[k]);
    }
    (filhos || []).forEach(function (f) { if (f) e.appendChild(f); });
    return e;
  }

  function formatarData(iso) {
    if (!iso) return "—";
    var s = iso.replace(" ", "T");
    var d = new Date(s.endsWith("Z") || s.includes("+") ? s : s + "Z");
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }

  function estrelas(pontos) {
    pontos = pontos || 0;
    var cheias = Math.floor((pontos + 1) / 2);
    return "★".repeat(cheias) + "☆".repeat(Math.max(0, 5 - cheias)) + " (" + pontos + "/10)";
  }

  function linkSeguro(url) {
    return typeof url === "string" && /^https?:\/\//i.test(url) ? url : null;
  }

  // ---------------------------------------------------------- STATUS

  function renderStatus() {
    var alvo = document.getElementById("status-execucao");
    Object.keys(DADOS.nomesPerfis).forEach(function (chave) {
      var nome = DADOS.nomesPerfis[chave];
      var st = DADOS.status[chave];
      var corpo = [el("div", { class: "nome", text: nome })];
      if (!st) {
        corpo.push(el("span", { class: "pill neutro", text: "ainda sem execução registrada" }));
      } else {
        var temProblema = st.fontes_com_problema && st.fontes_com_problema.length > 0;
        var pill = el("span", {
          class: "pill " + (temProblema ? "alerta" : "ok"),
          text: temProblema
            ? st.fontes_com_problema.length + "/" + st.total_fontes + " fonte(s) com problema"
            : "todas as fontes ok",
        });
        corpo.push(pill);
        corpo.push(el("span", { class: "meta", text: formatarData(st.quando) + " — " + st.total_novas + " vaga(s) nova(s) neste ciclo" }));
        if (temProblema) {
          corpo.push(el("span", { class: "meta", text: st.fontes_com_problema.join(", ") }));
        }
      }
      alvo.appendChild(el("div", { class: "cartao status-perfil" }, corpo));
    });
    document.getElementById("rodape-geracao").textContent = "Painel gerado em " + formatarData(DADOS.geradoEm);
  }

  // -------------------------------------------------------- RECENTES

  var perfilAtivoRecentes = "";

  function vagasRecentes(perfilChave) {
    var agora = Date.now();
    var limite = agora - TAMANHO_JANELA_RECENTE_DIAS * 24 * 60 * 60 * 1000;
    var base = perfilChave ? VAGAS.filter(function (v) { return v.perfil === perfilChave; }) : VAGAS.slice();
    var recentes = base.filter(function (v) {
      var t = new Date((v.encontrada_em || "").replace(" ", "T") + "Z").getTime();
      return !isNaN(t) && t >= limite;
    });
    if (recentes.length < MIN_RECENTES) recentes = base.slice(0, MIN_RECENTES);
    recentes.sort(function (a, b) {
      return (b.relevancia - a.relevancia) || (b.encontrada_em || "").localeCompare(a.encontrada_em || "");
    });
    return recentes.slice(0, 30);
  }

  function cartaoVaga(v) {
    var linha1 = el("div", { class: "topo" }, [
      el("span", { class: "titulo", text: v.titulo || "(sem título)" }),
      el("span", { class: "estrelas", text: estrelas(v.relevancia) }),
    ]);
    var metaTexto = (v.empresa || "Não informada") + " · " + (v.local || "—") +
      (v.modalidade ? " · " + v.modalidade : "") + " · " + (v.site || "");
    var linha2 = el("div", { class: "meta" }, [document.createTextNode(metaTexto)]);
    if (v.exploratoria) linha2.appendChild(el("span", { class: "tag", text: "exploratória" }));
    if (v.antiga) linha2.appendChild(el("span", { class: "tag aviso", text: "publicação antiga" }));
    var linha3 = el("div", { class: "meta", text: v.motivo || "" });
    var filhos = [linha1, linha2];
    if (v.motivo) filhos.push(linha3);
    var url = linkSeguro(v.link);
    if (url) {
      filhos.push(el("a", { class: "link-vaga", href: url, target: "_blank", rel: "noopener", text: "Ver vaga →" }));
    }
    return el("div", { class: "vaga" }, filhos);
  }

  function renderRecentes() {
    var abas = document.getElementById("abas-perfil-recentes");
    abas.innerHTML = "";
    var opcoes = [["", "Todos"]].concat(Object.keys(DADOS.nomesPerfis).map(function (c) { return [c, DADOS.nomesPerfis[c]]; }));
    opcoes.forEach(function (par) {
      var chave = par[0], rotulo = par[1];
      var botao = el("button", { class: "aba" + (chave === perfilAtivoRecentes ? " ativa" : ""), text: rotulo });
      botao.addEventListener("click", function () { perfilAtivoRecentes = chave; renderRecentes(); });
      abas.appendChild(botao);
    });

    var lista = document.getElementById("lista-recentes");
    lista.innerHTML = "";
    var recentes = vagasRecentes(perfilAtivoRecentes);
    if (recentes.length === 0) {
      lista.appendChild(el("p", { class: "meta", text: "Nenhuma vaga ainda." }));
      return;
    }
    recentes.forEach(function (v) { lista.appendChild(cartaoVaga(v)); });
  }

  // ------------------------------------------------------- TABELA

  var paginaAtual = 0;
  var ordemColuna = "encontrada_em";
  var ordemAsc = false;

  function popularSelects() {
    var selPerfil = document.getElementById("filtro-perfil");
    Object.keys(DADOS.nomesPerfis).forEach(function (c) {
      selPerfil.appendChild(el("option", { value: c, text: DADOS.nomesPerfis[c] }));
    });
    var sites = Array.from(new Set(VAGAS.map(function (v) { return v.site; }).filter(Boolean))).sort();
    var selSite = document.getElementById("filtro-site");
    sites.forEach(function (s) { selSite.appendChild(el("option", { value: s, text: s })); });
  }

  function vagasFiltradas() {
    var termo = document.getElementById("busca").value.trim().toLowerCase();
    var perfil = document.getElementById("filtro-perfil").value;
    var site = document.getElementById("filtro-site").value;
    var modalidade = document.getElementById("filtro-modalidade").value;

    return VAGAS.filter(function (v) {
      if (perfil && v.perfil !== perfil) return false;
      if (site && v.site !== site) return false;
      if (modalidade && v.modalidade !== modalidade) return false;
      if (termo) {
        var alvo = [v.titulo, v.empresa, v.local, v.site].join(" ").toLowerCase();
        if (alvo.indexOf(termo) === -1) return false;
      }
      return true;
    }).sort(function (a, b) {
      var av = a[ordemColuna], bv = b[ordemColuna];
      var cmp;
      if (typeof av === "number" || typeof bv === "number") cmp = (av || 0) - (bv || 0);
      else cmp = String(av || "").localeCompare(String(bv || ""));
      return ordemAsc ? cmp : -cmp;
    });
  }

  function renderTabela() {
    var filtradas = vagasFiltradas();
    var totalPaginas = Math.max(1, Math.ceil(filtradas.length / LINHAS_POR_PAGINA));
    paginaAtual = Math.min(paginaAtual, totalPaginas - 1);
    var inicio = paginaAtual * LINHAS_POR_PAGINA;
    var pagina = filtradas.slice(inicio, inicio + LINHAS_POR_PAGINA);

    var corpo = document.getElementById("corpo-tabela");
    corpo.innerHTML = "";
    pagina.forEach(function (v) {
      var celTitulo = el("td", {}, [
        (function () {
          var url = linkSeguro(v.link);
          return url ? el("a", { class: "link-vaga", href: url, target: "_blank", rel: "noopener", text: v.titulo || "(sem título)" })
                      : el("span", { text: v.titulo || "(sem título)" });
        })(),
      ]);
      var linha = el("tr", {}, [
        celTitulo,
        el("td", { text: v.empresa || "—" }),
        el("td", { text: v.local || "—" }),
        el("td", { text: v.modalidade || "—" }),
        el("td", { text: v.site || "—" }),
        el("td", { text: String(v.relevancia) }),
        el("td", { text: formatarData(v.encontrada_em) }),
      ]);
      corpo.appendChild(linha);
    });

    document.getElementById("contagem-tabela").textContent =
      filtradas.length + " vaga(s) — página " + (paginaAtual + 1) + "/" + totalPaginas;
    document.getElementById("pagina-anterior").disabled = paginaAtual === 0;
    document.getElementById("pagina-proxima").disabled = paginaAtual >= totalPaginas - 1;
  }

  function religarControles() {
    ["busca", "filtro-perfil", "filtro-site", "filtro-modalidade"].forEach(function (id) {
      document.getElementById(id).addEventListener("input", function () { paginaAtual = 0; renderTabela(); });
    });
    document.getElementById("pagina-anterior").addEventListener("click", function () { paginaAtual--; renderTabela(); });
    document.getElementById("pagina-proxima").addEventListener("click", function () { paginaAtual++; renderTabela(); });
    document.querySelectorAll("th[data-col]").forEach(function (th) {
      th.addEventListener("click", function () {
        var col = th.getAttribute("data-col");
        if (ordemColuna === col) ordemAsc = !ordemAsc;
        else { ordemColuna = col; ordemAsc = false; }
        renderTabela();
      });
    });
  }

  // ----------------------------------------------------- MÉTRICAS

  function renderMetricas() {
    var porSite = {};
    VAGAS.forEach(function (v) {
      var s = v.site || "—";
      if (!porSite[s]) porSite[s] = { total: 0, somaRelevancia: 0 };
      porSite[s].total += 1;
      porSite[s].somaRelevancia += (v.relevancia || 0);
    });
    var linhas = Object.keys(porSite).map(function (s) { return [s, porSite[s]]; });
    linhas.sort(function (a, b) { return b[1].total - a[1].total; });
    var maxTotal = linhas.reduce(function (m, l) { return Math.max(m, l[1].total); }, 1);

    var corpo = document.getElementById("corpo-metricas");
    corpo.innerHTML = "";
    linhas.forEach(function (par) {
      var site = par[0], info = par[1];
      var media = info.total ? (info.somaRelevancia / info.total).toFixed(1) : "—";
      var pct = Math.round((info.total / maxTotal) * 100);
      var barra = el("div", { class: "barra-fundo" }, [el("div", { class: "barra-preenchida", style: "width:" + pct + "%" })]);
      corpo.appendChild(el("tr", {}, [
        el("td", { text: site }),
        el("td", {}, [barra]),
        el("td", { text: String(info.total) }),
        el("td", { text: String(media) }),
      ]));
    });
  }

  renderStatus();
  renderRecentes();
  popularSelects();
  religarControles();
  renderTabela();
  renderMetricas();
})();
</script>
</body>
</html>
"""


def main():
    iniciar_db()
    conn = sqlite3.connect(DB_PATH)
    try:
        vagas = _carregar_vagas(conn)
        status_por_perfil = _carregar_status(conn)
    finally:
        conn.close()

    os.makedirs(os.path.dirname(SAIDA_HTML), exist_ok=True)
    with open(SAIDA_HTML, "w", encoding="utf-8") as f:
        f.write(gerar_html(vagas, status_por_perfil))

    print(f"Painel gerado: {SAIDA_HTML} ({len(vagas)} vaga(s), {html.escape(DB_PATH)})")


if __name__ == "__main__":
    main()
