import datetime
import hmac
import json

import gspread
import streamlit as st

st.set_page_config(page_title="ZN Cars - Agendamento", layout="centered")


def segredo(chave, padrao=None):
    try:
        return st.secrets[chave] if chave in st.secrets else padrao
    except Exception:
        return padrao


ID_DA_PLANILHA = segredo("ID_DA_PLANILHA", "1CITsbiBwcg_XQeq47JktPpYC5En3AxR6zoKq2dTf084")
CODIGO_ACESSO = str(segredo("CODIGO_ACESSO", "") or "")  # opcional, defina nos secrets


@st.cache_resource
def conectar_google_sheets():
    conta = segredo("gcp_service_account")
    if conta:
        conta = json.loads(conta) if isinstance(conta, str) else dict(conta)
        gc = gspread.service_account_from_dict(conta)
    else:
        gc = gspread.service_account(filename="credenciais.json")
    return gc.open_by_key(ID_DA_PLANILHA)


try:
    sheet = conectar_google_sheets()
except Exception:
    st.error("Sistema indisponível no momento. Tente novamente em instantes.")
    st.stop()


def lista_base(valores, padrao):
    r = sorted({str(l[0]).strip().upper() for l in valores if l and str(l[0]).strip()})
    return r or padrao


@st.cache_data(ttl=300, show_spinner="Carregando...")
def carregar_opcoes():
    """Uma única chamada à API para as 3 abas."""
    resp = sheet.values_batch_get(["Veiculos", "Base_Servicos", "Base_Mecanicos"])
    v = [r.get("values", []) for r in resp["valueRanges"]]
    placas = set()
    if v[0]:
        cab = [str(c).strip().upper() for c in v[0][0]]
        ip = cab.index("PLACA") if "PLACA" in cab else 0
        placas = {str(l[ip]).strip().upper() for l in v[0][1:] if len(l) > ip and str(l[ip]).strip()}
    return placas, lista_base(v[1], ["ÓLEO", "REVISÃO GERAL"]), lista_base(v[2], ["BIEL", "JORGINHO"])


try:
    placas_validas, lista_servicos, lista_mecanicos = carregar_opcoes()
except Exception:
    st.error("Não foi possível carregar os dados. Tente novamente em instantes.")
    st.stop()


def ja_existe_pendente(placa, data_txt):
    try:
        linhas = sheet.values_get("Agenda").get("values", [])[1:]
    except Exception:
        return False
    for l in linhas:
        l = list(l) + [""] * 7
        if (l[0].strip().upper() == placa and l[2].strip() == data_txt
                and "PENDENTE" in l[6].strip().upper()):
            return True
    return False


st.title("🚗 ZN Cars - Agendamento de Serviços")
st.caption("Preencha os dados abaixo para agendar a manutenção do seu veículo")
st.markdown("---")

if st.session_state.get("agendado"):
    st.success("✅ Agendamento enviado com sucesso! Aguarde o contato da oficina.")

n = st.session_state.get("form_n", 0)  # muda a chave do form para limpá-lo após o envio
with st.form(f"form_agendamento_publico_{n}"):
    col1, col2 = st.columns(2)
    f_placa = col1.text_input("Placa do Veículo", placeholder="ABC1D23")
    f_motorista = col2.text_input("Nome do Motorista")

    col3, col4 = st.columns(2)
    f_data = col3.date_input("Data Pretendida", value=datetime.date.today(), min_value=datetime.date.today())
    f_mec = col4.selectbox("Mecânico Preferencial", lista_mecanicos)

    f_servicos = st.multiselect("Serviços Necessários", lista_servicos)
    f_obs = st.text_area("Observações / Problemas identificados", max_chars=500)
    f_codigo = st.text_input("Código de acesso", type="password") if CODIGO_ACESSO else ""

    enviar = st.form_submit_button("📅 Confirmar Agendamento", type="primary")

if enviar:
    placa = f_placa.strip().upper().replace("-", "").replace(" ", "")
    nome = f_motorista.strip()
    data_txt = f_data.strftime("%d/%m/%Y")

    if CODIGO_ACESSO and not hmac.compare_digest(f_codigo.encode(), CODIGO_ACESSO.encode()):
        st.warning("Código de acesso inválido.")
    elif len(nome) < 3:
        st.warning("Informe o seu nome completo.")
    elif placa not in placas_validas:
        st.warning("Placa não encontrada. Confira os dados ou fale com a oficina.")
    elif not f_servicos and not f_obs.strip():
        st.warning("Escolha ao menos um serviço ou descreva o problema.")
    elif ja_existe_pendente(placa, data_txt):
        st.info("Já existe um agendamento pendente para esta placa nesta data.")
    else:
        try:
            sheet.worksheet("Agenda").append_row(
                [placa, nome.upper(), data_txt, str(f_mec).strip().upper(),
                 ", ".join(f_servicos).upper() if f_servicos else "NENHUM",
                 f_obs.strip().upper(), "PENDENTE"],
                value_input_option="RAW",  # evita que texto vire fórmula
            )
            st.session_state["agendado"] = True
            st.session_state["form_n"] = n + 1
            st.rerun()
        except Exception:
            st.error("Não foi possível registar o agendamento. Tente novamente.")
else:
    st.session_state.pop("agendado", None)
