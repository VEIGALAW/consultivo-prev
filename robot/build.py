"""Base do painel do consultivo previdenciário: puxar, validar, calcular prazo de entrega, criptografar e publicar.

  python robot/build.py --pull     git pull + decripta data/diagnosticos.enc.json em private/diagnosticos.json
  python robot/build.py            valida, calcula prazo de entrega e gera data/diagnosticos.enc.json
  python robot/build.py --push     idem + commit + push
"""
import json, subprocess, sys
from datetime import date, datetime, timedelta, timezone

from lib import OUT, ROOT, decrypt, encrypt, senha

SRC = ROOT / "private" / "diagnosticos.json"
FASES = ["contratacao", "documentos", "conferencia", "levantamento", "revisao", "entrega",
         "aprovacao", "execucao", "concluido", "cancelado"]
# SLA de entrega do diagnóstico: dias úteis contados do recebimento completo dos documentos
SLA_ENTREGA = 20

git = lambda *a, **kw: subprocess.run(["git", *a], cwd=ROOT, **kw)


def load():
    return json.loads(SRC.read_text(encoding="utf-8"))


def save(db):
    SRC.write_text(json.dumps(db, ensure_ascii=False, indent=1), encoding="utf-8")


def mais_uteis(d, n):
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def validar(db):
    erros, ids = [], set()
    for x in db["diagnosticos"]:
        i = x.get("id")
        if not i or i in ids:
            erros.append(f"id ausente ou repetido: {i}")
        ids.add(i)
        if x.get("fase") not in FASES:
            erros.append(f"{i}: fase inválida {x.get('fase')}")
        for c in ("contratado_em", "docs_solicitados_em", "docs_recebidos_em", "prazo_entrega", "entregue_em",
                  "aprovado_em", "proxima_data", "ultimo_movimento", "fase_desde", "responsavel_desde", "criado_em"):
            v = x.get(c)
            if v:
                try:
                    date.fromisoformat(v)
                except ValueError:
                    erros.append(f"{i}: {c} fora do formato AAAA-MM-DD: {v}")
        for c in ("credito_estimado", "credito_identificado", "credito_aprovado", "honorarios_pct"):
            v = x.get(c)
            if v is not None and not isinstance(v, (int, float)):
                erros.append(f"{i}: {c} deve ser número, veio {v!r}")
    if erros:
        sys.exit("diagnosticos.json inválido:\n  " + "\n  ".join(erros))


def trilha(x, hoje):
    """Registra cada mudança de fase e de responsável (tempo por fase, por pessoa e lead time)."""
    t = x.setdefault("trilha", [])
    mudou_fase = not t or t[-1]["fase"] != x["fase"]
    mudou_resp = not t or t[-1].get("responsavel") != x.get("responsavel")
    if not (mudou_fase or mudou_resp):
        return
    ultimo = t[-1]["data"] if t else ""
    def data_de(c):
        v = x.get(c) or ""
        return v if (not t or v > ultimo) else hoje
    if mudou_fase:
        x["fase_desde"] = data_de("fase_desde") or hoje
    if mudou_resp:
        x["responsavel_desde"] = data_de("responsavel_desde") or x.get("fase_desde") or hoje
    t.append({"fase": x["fase"], "responsavel": x.get("responsavel"),
              "data": x["fase_desde"] if mudou_fase else x["responsavel_desde"]})


def pull():
    git("pull", "--rebase", "--autostash", "-q", check=True)
    remoto = decrypt(json.loads(OUT.read_text(encoding="utf-8")), senha())
    SRC.parent.mkdir(exist_ok=True)
    local = load() if SRC.exists() else {}
    if local.get("publicado_em", "") > remoto.get("publicado_em", ""):
        print(f"local ({local['publicado_em']}) é mais novo que o publicado: mantido o local")
        return
    save(remoto)
    print(f"base atualizada a partir do publicado em {remoto.get('publicado_em')} ({len(remoto['diagnosticos'])} diagnósticos)")


def build(push):
    db = load()
    validar(db)
    hoje = date.today().isoformat()
    calc = 0
    for x in db["diagnosticos"]:
        x.setdefault("criado_em", hoje)
        x.setdefault("ultimo_movimento", x["criado_em"])
        trilha(x, hoje)
        if x.get("docs_recebidos_em") and (not x.get("prazo_entrega") or x.get("prazo_entrega_auto")):
            x["prazo_entrega"] = mais_uteis(date.fromisoformat(x["docs_recebidos_em"]), SLA_ENTREGA).isoformat()
            x["prazo_entrega_auto"] = True
            calc += 1
    db["publicado_em"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    save(db)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(encrypt(json.dumps(db, ensure_ascii=False).encode(), senha())), encoding="utf-8")
    print(f"{len(db['diagnosticos'])} diagnósticos publicados ({calc} prazos de entrega calculados)")
    if push:
        git("add", "data/diagnosticos.enc.json", check=True)
        git("commit", "-q", "-m", f"dados: sync {datetime.now():%Y-%m-%d %H:%M}", check=True)
        if git("push", "-q").returncode:
            git("pull", "--rebase", "-X", "theirs", "-q", check=True)
            git("push", "-q", check=True)
        print("publicado no GitHub")


if __name__ == "__main__":
    pull() if "--pull" in sys.argv else build("--push" in sys.argv)
