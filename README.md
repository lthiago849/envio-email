# Envio de formulários por e-mail

Envia um e-mail personalizado para cada pessoa do CSV, com o formulário individual dela em anexo.

## Arquivos que não estão no repositório

Por conterem dados pessoais (CPF, nome, e-mail), estes arquivos não vão para o GitHub e precisam ser recebidos por outro meio:

- **CSV com a lista de pessoas**, colocado nesta pasta. Colunas separadas por `;`: `cpf;nome;email` (outras colunas são ignoradas). Veja o formato em `e-mail_teste.csv`. O script usa `emails_especialistas_completo(1).csv` por padrão; outro arquivo pode ser passado como argumento.
- **Formulários**, dentro da pasta `formularios/`. O nome de cada arquivo deve conter o **CPF** (ex.: `formulario_78717353220.pdf`) **ou o nome** da pessoa (ex.: `ADAILTON MAGALHAES LIMA.pdf`). Acentos, maiúsculas, espaços, `_` e `-` são ignorados na comparação.
- **`.env`** com a senha de app do Gmail do remetente (veja abaixo).

## Configuração do remetente (`.env`)

Crie um arquivo `.env` nesta pasta:

```
EMAIL_CONTA=seu.email@gmail.com
EMAIL_SENHA=xxxx xxxx xxxx xxxx
```

`EMAIL_SENHA` é uma **senha de app** do Gmail (16 letras), não a senha normal da conta. Para gerar: myaccount.google.com → Segurança → Verificação em duas etapas (precisa estar ativa) → Senhas de app.

Sem `EMAIL_CONTA`, o remetente é `lthiago849@gmail.com`.

## Como usar (nesta ordem)

**1. Simulação.** Não envia nada; mostra quem receberia qual anexo e salva prévias `.eml` em `previa/`:

```bash
python3 enviar_formularios.py
```

Confira no final a lista de pessoas **sem formulário** ou com **mais de um formulário**. Essas pessoas não recebem o e-mail.

**2. Teste.** Envia todos os e-mails para o seu próprio endereço (o assunto mostra o destinatário real), para conferir texto e anexos:

```bash
python3 enviar_formularios.py --teste-para seu.email@gmail.com
```

**3. Envio real** para as pessoas do CSV:

```bash
python3 enviar_formularios.py --enviar
```

Cada envio é registrado em `enviados.csv`. Se o envio parar no meio, rode o mesmo comando de novo: quem já recebeu é pulado.

## Opções

| Opção | O que faz |
|---|---|
| `arquivo.csv` | usa outra lista (ex.: `python3 enviar_formularios.py lista.csv --enviar`) |
| `--pausa N` | segundos entre envios (padrão 2) |
| `--formularios PASTA` | outra pasta de formulários |
| `--modelo ARQUIVO` | outro modelo de e-mail (padrão `modelo_email.txt`) |

O texto do e-mail fica em `modelo_email.txt`. A primeira linha é `Assunto: ...`, e `{nome}`, `{primeiro_nome}`, `{email}` e `{cpf}` são substituídos pelos dados de cada pessoa.

O Gmail permite cerca de 500 destinatários por dia em contas comuns.
