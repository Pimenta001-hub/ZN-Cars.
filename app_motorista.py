import datetime
import unicodedata
import gspread
import pandas as pd
import streamlit as st

st.set_page_config(page_title="ZN Cars - Agendamento", layout="centered")


def segredo(chave, padrao=None):
  try:
    return st.secrets[chave] if chave in st.secrets else padrao
  except Exception:
    return padrao


ID_DA_PLANILHA = segredo(
    "ID_DA_PLANILHA", "1CITsbiBwcg_XQeq47JktPpYC5En3AxR6zoKq2dTf084"
)


@st.cache_resource
def conectar_google_sheets():
  conta = segredo("gcp_service_account")
  if conta:
    gc = gspread.service_account_from_dict(dict(conta))
  else:
    gc = gspread.service_account(filename="credenciais.json")
  return gc.open_by_key(ID_DA_PLANILHA)


try:
  sheet = conectar_google_sheets()
except Exception as e:
  st.error(f"Erro ao conectar ao sistema: {e}")
  st.stop()


def carregar_opcoes():
  try:
    v_veic = sheet.worksheet("Veiculos").get_all_values()
    v_serv = sheet.worksheet("Base_Servicos").get_all_values()
    v_mec = sheet.worksheet("Base_Mecanicos").get_all_values()

    placas = (
        sorted({str(l[0]).strip().upper() for l in v_veic[1:] if l})
        if len(v_veic) > 1
        else []
    )
    servicos = (
        sorted({str(l[0]).strip().upper() for l in v_serv if l})
        if v_serv
        else ["ÓLEO", "REVISÃO GERAL"]
    )
    mecanicos = (
        sorted({str(l[0]).strip().upper() for l in v_mec if l})
        if v_mec
        else ["BIEL", "JORGINHO"]
    )

    return placas, servicos, mecanicos
  except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    return [], [], []


placas, lista_servicos, lista_mecanicos = carregar_opcoes()

st.title("🚗 ZN Cars - Agendamento de Serviços")
st.caption("Preencha os dados abaixo para agendar a manutenção do seu veículo")
st.markdown("---")

with st.form("form_agendamento_publico"):
  col1, col2 = st.columns(2)
  f_placa = col1.selectbox("Placa do Veículo", placas)
  f_motorista = col2.text_input("Nome do Motorista")

  col3, col4 = st.columns(2)
  f_data = col3.date_input("Data Pretendida", value=datetime.date.today())
  f_mec = col4.selectbox("Mecânico Preferencial", lista_mecanicos)

  f_servicos = st.multiselect("Serviços Necessários", lista_servicos)
  f_obs = st.text_area("Observações / Problemas identificados")

  enviar = st.form_submit_button("📅 Confirmar Agendamento", type="primary")

  if enviar:
    if not f_placa or not f_motorista.strip():
      st.warning("Por favor, preencha a placa e o seu nome.")
    else:
      try:
        sheet.worksheet("Agenda").append_row([
            str(f_placa).strip().upper(),
            str(f_motorista).strip().upper(),
            f_data.strftime("%d/%m/%Y"),
            str(f_mec).strip().upper(),
            ", ".join(f_servicos).upper() if f_servicos else "NENHUM",
            str(f_obs).strip().upper(),
            "PENDENTE",
        ])
        st.success("✅ Agendamento enviado com sucesso!")
      except Exception as err:
        st.error(f"Erro ao registar o agendamento: {err}")