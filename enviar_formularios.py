#!/usr/bin/env python3
"""
Envia e-mail personalizado para cada pessoa do CSV que tem e-mail,
anexando o formulário próprio de cada uma.

Como o formulário de cada pessoa é encontrado (dentro da pasta --formularios):
  o nome do arquivo deve conter o CPF  (ex: 78717353220.pdf, form_78717353220.docx)
  OU o nome da pessoa                 (ex: ADAILTON MAGALHAES LIMA.pdf, adailton_magalhaes_lima.pdf)
  (acentos, maiúsculas, espaços/_/- são ignorados na comparação)

Modos:
  (padrão)            SIMULAÇÃO: não envia nada, só mostra o que faria e salva
                      os e-mails como .eml na pasta previa/ (abre no Thunderbird/Outlook)
  --teste-para X      envia TODOS os e-mails para o endereço X (você), para conferir
  --enviar            envia de verdade para as pessoas
  --gerar-teste       cria formulários falsos na pasta de formulários para testar

SMTP: remetente padrão lthiago849@gmail.com (Gmail, smtp.gmail.com:587).
  A senha de app vem da variável EMAIL_SENHA (mesma do projeto Parcerias-UFPA)
  ou de um arquivo .env nesta pasta com a linha:  EMAIL_SENHA=xxxx xxxx xxxx xxxx
  Opcionais: EMAIL_CONTA (outro remetente), SMTP_HOST, SMTP_PORT
"""
import argparse, csv, mimetypes, os, re, smtplib, sys, time, unicodedata
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

PARTICULAS = {"de", "da", "do", "das", "dos", "e"}


def normalizar(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def nome_bonito(nome):
    partes = nome.strip().lower().split()
    return " ".join(p if (p in PARTICULAS and i > 0) else p.capitalize()
                    for i, p in enumerate(partes))


def ler_pessoas(caminho_csv):
    with open(caminho_csv, encoding="utf-8-sig", newline="") as f:
        amostra = f.read(4096); f.seek(0)
        delim = ";" if amostra.count(";") > amostra.count(",") else ","
        pessoas = []
        for linha in csv.DictReader(f, delimiter=delim):
            email = (linha.get("email") or "").strip()
            if email and "@" in email:
                pessoas.append({"cpf": (linha.get("cpf") or "").strip(),
                                "nome": (linha.get("nome") or "").strip(),
                                "email": email})
        return pessoas


def achar_formulario(pessoa, arquivos):
    cpf = re.sub(r"\D", "", pessoa["cpf"])
    nome_n = normalizar(pessoa["nome"])
    achados = []
    for arq in arquivos:
        base = normalizar(arq.stem)
        if (cpf and cpf in re.sub(r"\D", "", arq.stem)) or (nome_n and nome_n in base):
            achados.append(arq)
    return achados


def ler_modelo(caminho):
    texto = Path(caminho).read_text(encoding="utf-8")
    primeira, _, corpo = texto.partition("\n")
    if not primeira.lower().startswith("assunto:"):
        sys.exit("A primeira linha do modelo deve ser 'Assunto: ...'")
    return primeira.split(":", 1)[1].strip(), corpo.strip() + "\n"


def montar_email(remetente, destino, assunto, corpo, anexo):
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = remetente, destino, assunto
    msg["Date"], msg["Message-ID"] = formatdate(localtime=True), make_msgid()
    msg.set_content(corpo)
    tipo, _ = mimetypes.guess_type(anexo.name)
    maintype, subtype = (tipo or "application/octet-stream").split("/", 1)
    msg.add_attachment(anexo.read_bytes(), maintype=maintype, subtype=subtype,
                       filename=anexo.name)
    return msg


def gerar_formularios_teste(pessoas, pasta, n):
    pasta.mkdir(parents=True, exist_ok=True)
    for i, p in enumerate(pessoas[:n]):
        # alterna os dois jeitos de nomear, para testar os dois
        nome_arq = f"formulario_{p['cpf']}.txt" if i % 2 else f"Formulario - {p['nome']}.txt"
        (pasta / nome_arq).write_text(
            f"FORMULÁRIO DE TESTE\nNome: {p['nome']}\nCPF: {p['cpf']}\nE-mail: {p['email']}\n",
            encoding="utf-8")
    print(f"Criados {min(n, len(pessoas))} formulários de teste em {pasta}/")


def carregar_env(pasta):
    env = pasta / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.strip().startswith("#"):
                k, v = linha.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"\''))


def main():
    aqui = Path(__file__).resolve().parent
    carregar_env(aqui)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", default=aqui / "e-mail_teste.csv",
                    help="CSV com colunas cpf;nome;email (padrão: e-mail_teste.csv)")
    ap.add_argument("--formularios", default=aqui / "formularios", type=Path)
    ap.add_argument("--modelo", default=aqui / "modelo_email.txt", type=Path)
    ap.add_argument("--enviar", action="store_true", help="envia de verdade")
    ap.add_argument("--teste-para", metavar="EMAIL", help="manda tudo para este e-mail")
    ap.add_argument("--limite", type=int, help="processa só as N primeiras pessoas")
    ap.add_argument("--gerar-teste", type=int, nargs="?", const=5, metavar="N",
                    help="cria N formulários falsos (padrão 5) e sai")
    ap.add_argument("--pausa", type=float, default=2.0, help="segundos entre envios")
    a = ap.parse_args()

    pessoas = ler_pessoas(a.csv)
    print(f"{len(pessoas)} pessoas com e-mail no CSV.")

    if a.gerar_teste is not None:
        gerar_formularios_teste(pessoas, a.formularios, a.gerar_teste)
        return

    if not a.formularios.is_dir():
        sys.exit(f"Pasta de formulários não existe: {a.formularios}  (use --gerar-teste para testar)")
    arquivos = [f for f in a.formularios.iterdir() if f.is_file() and not f.name.startswith(".")]
    assunto_m, corpo_m = ler_modelo(a.modelo)
    if a.limite:
        pessoas = pessoas[:a.limite]

    real = a.enviar or a.teste_para
    smtp = None
    remetente = os.environ.get("EMAIL_CONTA", "lthiago849@gmail.com")
    if real:
        if not os.environ.get("EMAIL_SENHA"):
            sys.exit("Defina EMAIL_SENHA (senha de app) no ambiente ou no arquivo .env desta pasta.")
        smtp = smtplib.SMTP(os.environ.get("SMTP_HOST", "smtp.gmail.com"),
                            int(os.environ.get("SMTP_PORT", 587)))
        smtp.starttls()
        smtp.login(remetente, os.environ["EMAIL_SENHA"])

    log_path = aqui / "enviados.csv"
    ja_enviados = set()
    if a.enviar and log_path.exists():
        ja_enviados = {l.split(";")[0] for l in log_path.read_text(encoding="utf-8").splitlines()}
    previa = aqui / "previa"
    previa.mkdir(exist_ok=True)

    ok, sem_form, ambiguos, pulados = 0, [], [], 0
    for p in pessoas:
        if a.enviar and p["email"] in ja_enviados:
            pulados += 1
            continue
        achados = achar_formulario(p, arquivos)
        if not achados:
            sem_form.append(p); continue
        if len(achados) > 1:
            ambiguos.append((p, achados)); continue

        dados = {"nome": nome_bonito(p["nome"]),
                 "primeiro_nome": nome_bonito(p["nome"]).split()[0],
                 "email": p["email"], "cpf": p["cpf"]}
        destino = a.teste_para or p["email"]
        assunto = assunto_m.format(**dados)
        if a.teste_para:
            assunto = f"[TESTE -> {p['email']}] {assunto}"
        msg = montar_email(remetente, destino, assunto, corpo_m.format(**dados), achados[0])

        if smtp:
            smtp.send_message(msg)
            print(f"  ENVIADO  {destino:40} anexo: {achados[0].name}")
            if a.enviar:
                with open(log_path, "a", encoding="utf-8") as lf:
                    lf.write(f"{p['email']};{p['nome']};{achados[0].name};{time.strftime('%F %T')}\n")
            time.sleep(a.pausa)
        else:
            (previa / f"{normalizar(p['nome'])}.eml").write_bytes(bytes(msg))
            print(f"  [simulação] {destino:40} anexo: {achados[0].name}")
        ok += 1

    if smtp:
        smtp.quit()
    print(f"\n{'Enviados' if real else 'Prontos (simulação)'}: {ok}")
    if pulados:
        print(f"Pulados (já enviados antes, ver enviados.csv): {pulados}")
    if not real:
        print(f"Prévias .eml salvas em {previa}/")
    if ambiguos:
        print(f"\n{len(ambiguos)} com MAIS DE UM formulário (não enviados):")
        for p, fs in ambiguos:
            print(f"  {p['nome']}: {[f.name for f in fs]}")
    if sem_form:
        print(f"\n{len(sem_form)} sem formulário encontrado (não enviados):")
        for p in sem_form:
            print(f"  {p['nome']} <{p['email']}>")


if __name__ == "__main__":
    main()
