"""Mensagem diária do Plutus (HTML do Teams) para o grupo "Diagnóstico - Prev".

  python robot/digest.py      grava private/digest.html e imprime o HTML

Seções (só aparecem se tiverem itens): entregas atrasadas, ações de hoje e entregas dos próximos 3 dias úteis,
esperando documentos ou aprovação do cliente, parados com a gente, sem data, novos e marcos desde o último dia útil.
A primeira linha começa com 🤖 para o robô não reprocessar a própria mensagem.
"""
import json
from datetime import date, timedelta
from html import escape

from lib import ROOT

SRC = ROOT / "private" / "diagnosticos.json"
DASH = "https://veigalaw.github.io/consultivo-prev/"
PRE = {"contratacao", "documentos", "conferencia", "levantamento", "revisao", "entrega"}
FIM = {"concluido", "cancelado"}
SLA = {"contratacao": 3, "conferencia": 2, "levantamento": 10, "revisao": 3, "entrega": 2, "execucao": 15}
DOW = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def mais_uteis(d, n):
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def anterior_util(d):
    d -= timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def brl(v):
    if not v:
        return ""
    return f"R$ {v/1e6:.1f} mi".replace(".", ",") if v >= 1e6 else f"R$ {round(v/1e3)} mil"


def valor(x):
    return x.get("credito_aprovado") or x.get("credito_identificado") or x.get("credito_estimado")


def item(x, extra=""):
    v = brl(valor(x))
    return f"<li><b>{escape(x['cliente'])}</b>{' · ' + v if v else ''}: {escape(x.get('proximo_passo') or 'definir próximo passo')}{extra}</li>"


def secao(titulo, itens, fmt=item):
    if not itens:
        return ""
    pessoas = sorted({x.get("responsavel") or "Sem responsável" for x in itens})
    corpo = "".join(f"<p><i>{escape(p)}</i></p><ul>{''.join(fmt(x) for x in itens if (x.get('responsavel') or 'Sem responsável') == p)}</ul>" for p in pessoas)
    return f"<p><b>{titulo}</b> ({len(itens)})</p>{corpo}"


def main():
    db = json.loads(SRC.read_text(encoding="utf-8"))
    hoje = date.today()
    h, lim3 = hoje.isoformat(), mais_uteis(hoje, 3).isoformat()
    desde = anterior_util(hoje).isoformat()
    ab = [x for x in db["diagnosticos"] if x["fase"] not in FIM]
    dias = lambda d: (hoje - date.fromisoformat(d)).days if d else 0

    atrasadas = [x for x in ab if x["fase"] in PRE and x.get("prazo_entrega") and x["prazo_entrega"] < h]
    ids = {x["id"] for x in atrasadas}
    hoje_l = [x for x in ab if x["id"] not in ids and x.get("proxima_data") and x["proxima_data"] <= h]
    ids |= {x["id"] for x in hoje_l}
    entregas = [x for x in ab if x["id"] not in ids and x["fase"] in PRE and x.get("prazo_entrega") and h <= x["prazo_entrega"] <= lim3]
    ids |= {x["id"] for x in entregas}
    cliente = [x for x in ab if x["fase"] in ("documentos", "aprovacao") and dias(x.get("fase_desde")) > (5 if x["fase"] == "documentos" else 7)]
    parados = [x for x in ab if x["id"] not in ids and x["fase"] in SLA and dias(x.get("ultimo_movimento")) > SLA[x["fase"]]]
    sem_data = [x for x in ab if not x.get("proxima_data") and not (x["fase"] in PRE and x.get("prazo_entrega"))]
    novos = [x for x in db["diagnosticos"] if (x.get("criado_em") or "") >= desde]
    marcos = [x for x in db["diagnosticos"] if (x.get("entregue_em") or "") >= desde or (x.get("aprovado_em") or "") >= desde
              or (x["fase"] == "concluido" and (x.get("fase_desde") or "") >= desde)]

    p = [f"<p>🤖 <b>Plutus · agenda do consultivo prev ({DOW[hoje.weekday()]} {hoje:%d/%m})</b></p>"]
    if marcos:
        p.append("<p>🏆 <b>Marcos</b></p><ul>" + "".join(
            f"<li>{escape(x['cliente'])}: {'concluído' if x['fase'] == 'concluido' else 'aprovado' if (x.get('aprovado_em') or '') >= desde else 'diagnóstico entregue'}{' · ' + brl(valor(x)) if valor(x) else ''}</li>" for x in marcos) + "</ul>")
    if novos:
        p.append("<p>🆕 <b>Novos diagnósticos</b></p><ul>" + "".join(item(x, f" · {escape(x.get('responsavel') or 'sem responsável')}") for x in novos) + "</ul>")
    p.append(secao("🚨 Entrega atrasada", atrasadas, lambda x: item(x, f" · prometida para {x['prazo_entrega'][8:10]}/{x['prazo_entrega'][5:7]}")))
    p.append(secao("📅 Para hoje", hoje_l))
    p.append(secao("⏳ Entregas nos próximos 3 dias úteis", entregas, lambda x: item(x, f" · entrega {x['prazo_entrega'][8:10]}/{x['prazo_entrega'][5:7]}")))
    p.append(secao("📨 Esperando o cliente: cobrar", cliente, lambda x: item(x, f" · {'falta: ' + escape(', '.join(x.get('docs_pendentes') or ['documentos'])) if x['fase'] == 'documentos' else 'aprovação do diagnóstico'} · {dias(x.get('fase_desde'))}d")))
    p.append(secao("🧊 Parados com a gente", parados, lambda x: item(x, f" · {dias(x.get('ultimo_movimento'))}d parado")))
    if sem_data:
        p.append("<p>❓ <b>Sem data de próxima ação nem prazo de entrega</b></p><ul>" + "".join(f"<li>{escape(x['cliente'])}</li>" for x in sem_data) + "</ul>")
    if len([s for s in p if s]) == 1:
        p.append("<p>Nada atrasado e nada parado. 👏</p>" if ab else "<p>Nenhum diagnóstico no painel ainda. Postem os clientes em andamento no formato do Manual (#novo | CLIENTE | CNPJ | teses | responsável | crédito estimado).</p>")
    p.append(f'<p>Painel: <a href="{DASH}">{DASH}</a> · Atualize aqui: ATUALIZAÇÃO | CLIENTE | o que aconteceu | próximo passo | dd/mm #fase</p>')
    html = "\n".join(s for s in p if s)
    (ROOT / "private" / "digest.html").write_text(html, encoding="utf-8")
    print(html)


if __name__ == "__main__":
    main()
