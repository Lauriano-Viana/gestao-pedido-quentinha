import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, time
import uuid
import urllib.parse
import locale


# Configurações iniciais do Streamlit
st.set_page_config(page_title="Pedido Quentinhas - Congresso RCC/PI", page_icon="🍲", layout="wide")

try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_TIME, '')

# --- Funções de Conexão com Google Sheets ---

@st.cache_resource
def connect_and_authorize():
    """Conecta e autoriza o acesso ao Google Sheets."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = st.secrets["google_credentials"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client_gs = gspread.authorize(creds)
    return client_gs

@st.cache_resource
def get_sheets(_client_gs):
    """Obtém as planilhas 'Pedidos' e 'Configuracoes'."""
    spreadsheet = _client_gs.open_by_key(st.secrets["GOOGLE_SHEETS_ID"])
    
    # Planilha de Pedidos
    try:
        sheet_pedidos = spreadsheet.worksheet("Pedidos")
    except gspread.WorksheetNotFound:
        # Cria a planilha de pedidos se não existir (apenas para segurança)
        sheet_pedidos = spreadsheet.add_worksheet(title="Pedidos", rows="100", cols="20")
        headers = [
            "ID", "Data/Hora", "Nome Cliente", "CPF", "Telefone Cliente", "Email",
            "Itens Pedido", "Total Pedido", "Observacoes", "Tipo Pagamento",
            "ID Transacao", "Status", "Aprovado por", "Valor Total Agrupado", "Entregue"
        ]
        sheet_pedidos.append_row(headers)

    # Planilha de Configurações
    try:
        sheet_config = spreadsheet.worksheet("Configuracoes")
    except gspread.WorksheetNotFound:
        sheet_config = spreadsheet.add_worksheet(title="Configuracoes", rows="10", cols="4")
        sheet_config.append_row(["data_evento", "prazo_data", "prazo_hora", "nome_amigavel"])

    return sheet_pedidos, sheet_config

client = connect_and_authorize()
sheet, config_sheet = get_sheets(client)


# --- Constantes e Configurações Globais ---

CARDAPIO = {
    "opcoes_principais": {
        "Isca (carne, frango e calabresa)": 20.00,
        "Frango assado e Toscana": 20.00,
        "Assado de panela e Toscana": 20.00
    }
}
DATAS_DISPONIVEIS = {
    "Sábado (02/08/2025)": "2025-08-02",
    "Domingo (03/08/2025)": "2025-08-03"
}

# --- Funções Utilitárias ---

@st.cache_data(ttl=60) # Cache de 1 minuto para os prazos
def get_deadlines():
    """Busca e processa os prazos da planilha de configurações."""
    records = config_sheet.get_all_records()
    deadlines = {}
    for record in records:
        try:
            deadline_str = f"{record['prazo_data']} {record['prazo_hora']}"
            # O formato do gspread pode ser 'DD/MM/YYYY' ou 'YYYY-MM-DD'
            # Vamos tentar ambos
            try:
                deadline_dt = datetime.strptime(deadline_str, '%d/%m/%Y %H:%M:%S')
            except ValueError:
                 deadline_dt = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M:%S')

            deadlines[record['data_evento']] = deadline_dt
        except (ValueError, KeyError):
            # Ignora linhas com formato inválido ou chaves faltando
            continue
    return deadlines

def autenticar_admin():
    st.subheader("🔐 Login de Administrador")
    login = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if login == st.secrets["admin_login"] and senha == st.secrets["admin_senha"]:
            st.session_state["autenticado"] = True
            st.success("Login bem-sucedido!")
            st.rerun()
        else:
            st.error("Credenciais inválidas.")

def gerar_link_whatsapp(telefone, mensagem):
    """Gera o link do WhatsApp com a mensagem pré-formatada"""
    telefone = ''.join(filter(str.isdigit, str(telefone)))
    if telefone and not telefone.startswith('55'):
        telefone = '55' + telefone
    return f"https://wa.me/{telefone}?text={urllib.parse.quote(mensagem)}"

def notificar_cliente(pedido_id, nome_cliente, telefone_cliente, data_pedido, itens_pedido):
    """Função para gerar e exibir o link de notificação do WhatsApp com a comanda simplificada"""
    
    data_formatada = data_pedido.strftime('%A, %d/%m').upper()
    itens_formatados = "- " + itens_pedido.replace(", ", "\n- ")

    mensagem = (
        f"*Congresso RCC Piauí - Comprovante de Quentinha* 🍲\n\n"
        f"Olá, {nome_cliente}!\n"
        f"Seu pedido foi APROVADO!\n\n"
        f"*Nº do Pedido:* #{pedido_id}\n"
        f"*Data:* {data_formatada}\n"
        f"*Itens:*\n{itens_formatados}\n\n"
        f"Apresente esta mensagem no local de retirada. Bom apetite!"
    )
    
    link_whatsapp = gerar_link_whatsapp(telefone_cliente, mensagem)
    
    st.markdown("### Notificação ao Cliente")
    st.markdown(f"**Mensagem pronta:**")
    st.text_area("Preview da Mensagem", value=mensagem, height=250, disabled=True)
    st.markdown(f"[👉 Clique aqui para enviar mensagem no WhatsApp]({link_whatsapp})", unsafe_allow_html=True)
    st.markdown(f"**Link completo:** `{link_whatsapp}`")
    
    return link_whatsapp

# --- Página de Pedidos (Usuário) ---

def pagina_pedidos():
    st.title("🍲 Agende seu Pedido de Quentinha")
    st.info("💡 **Observação:** Todos os pedidos de quentinhas referem-se ao **almoço**.")

    if 'pedido_finalizado' not in st.session_state:
        st.session_state.pedido_finalizado = False

    if st.session_state.pedido_finalizado:
        st.success("Pedido(s) registrado(s) com sucesso!\n\nVocê receberá uma confirmação via WhatsApp após aprovação.")
        st.balloons()
        st.markdown("---")
        st.subheader("⚠️ Próximo Passo para Aprovar seu Pedido")

        ultimo_pagamento = st.session_state.get('ultimo_pagamento')

        if ultimo_pagamento == "Pix":
            st.info(
                "**LEMBRETE IMPORTANTE (PIX):**\n\n"
                "Para que seu pedido seja APROVADO, você precisa enviar o comprovante de pagamento junto com seu nome completo para o WhatsApp **86-98828-2470**.\n\n"
                "**Chave PIX:** `86988282470`\n"
                "**Nome:** Lauriano Costa Viana\n"
                "**Instituição:** Banco do Brasil"
            )
        elif ultimo_pagamento == "Dinheiro":
            st.warning("**LEMBRETE IMPORTANTE (DINHEIRO):**\n\nPara que seu pedido seja APROVADO, dirija-se ao caixa do evento para efetuar o pagamento.")
        
        if st.button("➕ Fazer um Novo Pedido"):
            st.session_state.pedido_finalizado = False
            if 'carrinho' in st.session_state: del st.session_state.carrinho
            if 'ultimo_pagamento' in st.session_state: del st.session_state.ultimo_pagamento
            st.rerun()
        return

    # --- Lógica de Prazos ---
    deadlines = get_deadlines()
    now = datetime.now()
    
    DATAS_EXIBICAO = {}
    for nome_original, valor_data in DATAS_DISPONIVEIS.items():
        data_obj = datetime.strptime(valor_data, '%Y-%m-%d')
        dia_semana = nome_original.split(' ')[0]
        data_formatada = data_obj.strftime('%d/%m/%Y')
        texto_final_exibicao = f"{dia_semana} ({data_formatada})"
        DATAS_EXIBICAO[texto_final_exibicao] = valor_data

    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = {data_valor: {opcao: 0 for opcao in CARDAPIO["opcoes_principais"]} for data_valor in DATAS_EXIBICAO.values()}

    st.subheader("1. Para quais dias você quer agendar?")
    
    escolhas_datas = {}
    datas_para_pedir = []

    for nome_data_formatado, valor_data in DATAS_EXIBICAO.items():
        deadline = deadlines.get(valor_data)
        
        if deadline and now > deadline:
            st.error(f"**Pedidos para {nome_data_formatado} estão encerrados.**")
        else:
            if deadline:
                st.info(f"Pedidos para {nome_data_formatado} se encerram em {deadline.strftime('%d/%m/%Y às %H:%M')}.")
            else:
                 st.warning(f"O prazo para {nome_data_formatado} ainda não foi definido pelo administrador.")

            escolha = st.radio(
                f"Pedido para **{nome_data_formatado}**:",
                ["Sem Pedido", "Quero Pedir"],
                key=f"choice_{valor_data}",
                horizontal=True
            )
            if escolha == "Quero Pedir":
                datas_para_pedir.append(valor_data)

    if not datas_para_pedir:
        st.info("Selecione 'Quero Pedir' em uma das datas disponíveis para montar sua quentinha.")
        return

    grand_total = 0
    pedidos_finais = {}
    st.info("**Atenção:** Todas as opções acompanham Baião de dois, Macarrão, Farofa e Salada cozida.")

    for data_pedido in datas_para_pedir:
        nome_amigavel_data = [nome for nome, valor in DATAS_EXIBICAO.items() if valor == data_pedido][0]
        st.markdown("---")
        st.subheader(f"🛒 Pedido para: {nome_amigavel_data}")
        total_dia = 0
        itens_dia_obj = []
        for opcao, preco in CARDAPIO["opcoes_principais"].items():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{opcao}** - R$ {preco:.2f}")
            with col2:
                st.session_state.carrinho[data_pedido][opcao] = st.number_input(
                    "Qtd", min_value=0, max_value=20, step=1, key=f"qtd_{opcao}_{data_pedido}", label_visibility="collapsed"
                )

        for opcao, quantidade in st.session_state.carrinho[data_pedido].items():
            if quantidade > 0:
                total_dia += quantidade * CARDAPIO["opcoes_principais"][opcao]
                itens_dia_obj.append({"nome": opcao, "qtd": quantidade})

        st.markdown(f"<p style='text-align: right; font-weight: bold;'>Subtotal para {nome_amigavel_data}: R$ {total_dia:.2f}</p>", unsafe_allow_html=True)
        grand_total += total_dia
        if total_dia > 0:
            pedidos_finais[data_pedido] = {"itens_obj": itens_dia_obj, "total": total_dia}

    if grand_total > 0:
        st.markdown("---")
        st.markdown(f"## Valor Total do Pedido: **R$ {grand_total:.2f}**")
        st.markdown("---")
        
        tipo_pagamento = st.selectbox("Forma de Pagamento:", ["Pix", "Dinheiro"])
        if tipo_pagamento == "Pix":
            st.info("🔑 **Chave PIX:** `86988282470`\n\n👤 **Lauriano Costa Viana - Banco do Brasil**\n\n📨 Após finalizar o pedido, envie o seu nome completo e o comprovante para 86-98828-2470 via WhatsApp.")
        else:
            st.warning("Após finalizar o pedido, dirija-se ao caixa para realizar o pagamento e aprovar seu pedido.")

        with st.form("final_form"):
            nome_cliente = st.text_input("Seu Nome Completo*")
            telefone_cliente = st.text_input("Seu Celular/WhatsApp com DDD*", placeholder="Ex: 86999998888")
            observacoes = st.text_area("Observações")
            submitted = st.form_submit_button("✔ Finalizar Pedido")

            if submitted:
                numeros_telefone = "".join(filter(str.isdigit, telefone_cliente))
                if not nome_cliente or not telefone_cliente:
                    st.warning("Por favor, preencha seu Nome Completo e Celular.")
                elif len(numeros_telefone) != 11:
                    st.warning(f"O número '{telefone_cliente}' parece inválido. Por favor, insira um celular com DDD (11 dígitos). Ex: 86999998888")
                else:
                    with st.spinner('Registrando seu pedido, por favor aguarde...'):
                        for data_pedido, detalhes in pedidos_finais.items():
                            id_por_data = f"{data_pedido.replace('-', '')}-{uuid.uuid4().hex[:6].upper()}"
                            itens_fmt = ", ".join([f"[{item['qtd']}x] {item['nome']}" for item in detalhes["itens_obj"]])
                            new_order_data = [
                                id_por_data, f"{data_pedido} {datetime.now().strftime('%H:%M:%S')}",
                                nome_cliente, "", numeros_telefone, "",
                                itens_fmt, f"{detalhes['total']:.2f}",
                                observacoes, tipo_pagamento, "", "Pendente", "",
                                f"{grand_total:.2f}", ""
                            ]
                            sheet.append_row(new_order_data, value_input_option='USER_ENTERED')
                    
                    st.session_state.ultimo_pagamento = tipo_pagamento
                    st.session_state.pedido_finalizado = True
                    st.rerun()

# --- Página de Administração ---

def pagina_admin():
    if not st.session_state.get("autenticado"):
        autenticar_admin()
        return

    tab1, tab2, tab3 = st.tabs(["Gerenciar Pedidos", "Relatórios", "Prazos e Configurações"])

    # Carrega dados para as abas 1 e 2
    all_data = sheet.get_all_records()
    if not all_data:
        df = pd.DataFrame()
    else:
        df = pd.DataFrame(all_data)
        df['Data/Hora'] = pd.to_datetime(df['Data/Hora'], errors='coerce')
    
    # --- Aba 1: Gerenciar Pedidos ---
    with tab1:
        st.title("👑 Gerenciamento de Pedidos Pendentes")
        
        if st.button("🔄 Atualizar Pedidos"): 
            st.rerun()

        if df.empty or 'Status' not in df.columns:
            st.info("Nenhum pedido para gerenciar.")
        else:
            st.subheader("🔍 Buscar Pedidos Pendentes")
            col1, col2, col3 = st.columns(3)
            with col1: busca_id = st.text_input("Buscar por ID do Pedido")
            with col2: busca_nome = st.text_input("Buscar por Nome do Cliente")
            with col3: busca_telefone = st.text_input("Buscar por Telefone")

            df_pendentes = df[df['Status'] == 'Pendente'].copy()

            if busca_id: df_pendentes = df_pendentes[df_pendentes['ID'].astype(str).str.contains(busca_id, case=False, na=False)]
            if busca_nome: df_pendentes = df_pendentes[df_pendentes['Nome Cliente'].str.contains(busca_nome, case=False, na=False)]
            if busca_telefone: df_pendentes = df_pendentes[df_pendentes['Telefone Cliente'].astype(str).str.contains(busca_telefone, case=False, na=False)]

            if df_pendentes.empty:
                st.info("✅ Nenhum pedido pendente encontrado com os critérios de busca.")
            else:
                st.markdown(f"**Pedidos pendentes encontrados:** {len(df_pendentes)}")
                for _, row in df_pendentes.iterrows():
                    with st.expander(f"Pedido #{row['ID']} - {row['Nome Cliente']} - R$ {row['Total Pedido']}"):
                        data_formatada = row['Data/Hora'].strftime('%d/%m/%Y %H:%M:%S') if pd.notna(row['Data/Hora']) else "Data inválida"
                        st.write(f"**Data/Hora:** {data_formatada}")
                        st.write(f"**Itens:** {row['Itens Pedido']}")
                        st.write(f"**Telefone:** {row['Telefone Cliente']}")
                        st.write(f"**Pagamento:** {row['Tipo Pagamento']}")
                        st.write(f"**Observações:** {row['Observacoes'] or 'Nenhuma'}")
                        
                        st.markdown("---")
                        col_btn1, col_btn2 = st.columns(2)

                        with col_btn1:
                            if st.button("Gerar Notificação (WhatsApp)", key=f"notify_{row['ID']}"):
                                st.session_state[f"show_notify_{row['ID']}"] = True
                        with col_btn2:
                            if st.button("Aprovar Pedido e Remover", key=f"approve_{row['ID']}", type="primary"):
                                cell = sheet.find(str(row['ID']))
                                if cell:
                                    sheet.update_cell(cell.row, 12, "Aprovado")
                                    st.success(f"Pedido #{row['ID']} aprovado! A lista será atualizada.")
                                    if f"show_notify_{row['ID']}" in st.session_state: del st.session_state[f"show_notify_{row['ID']}"]
                                    st.rerun()
                                else:
                                    st.error(f"Não foi possível encontrar o pedido #{row['ID']} na planilha para aprovação.")
                        
                        if st.session_state.get(f"show_notify_{row['ID']}", False):
                            with st.container(border=True):
                                notificar_cliente(
                                    pedido_id=row['ID'], nome_cliente=row['Nome Cliente'],
                                    telefone_cliente=row['Telefone Cliente'], data_pedido=row['Data/Hora'],
                                    itens_pedido=row['Itens Pedido']
                                )
                                if st.button("Ocultar Notificação", key=f"hide_{row['ID']}"):
                                    del st.session_state[f"show_notify_{row['ID']}"]
                                    st.rerun()

    # --- Aba 2: Relatórios ---
    with tab2:
        st.title("📈 Relatórios e Entregas")
        if df.empty:
            st.info("Nenhum dado para gerar relatórios.")
        else:
            data_relatorio = st.date_input("Selecione a data do pedido:", value=datetime.now(), format="YYYY-MM-DD")
            st.info("Altere para a data que deseja consultar (ex: 02/08/2025 ou 03/08/2025).")

            df['Data'] = df['Data/Hora'].dt.date
            df.dropna(subset=['Data'], inplace=True)
            df['Total Pedido'] = pd.to_numeric(df['Total Pedido'], errors='coerce').fillna(0)

            df_aprovados_do_dia = df[(df['Data'] == data_relatorio) & (df['Status'] == 'Aprovado')]

            if 'Entregue' in df_aprovados_do_dia.columns:
                df_para_entrega = df_aprovados_do_dia[df_aprovados_do_dia['Entregue'] != 'Sim'].copy()
            else:
                df_para_entrega = df_aprovados_do_dia.copy()

            st.subheader("🔍 Buscar Pedidos para Entrega")
            col1, col2, col3 = st.columns(3)
            with col1: busca_id_entrega = st.text_input("Buscar por ID", key="busca_id_entrega")
            with col2: busca_nome_entrega = st.text_input("Buscar por Nome", key="busca_nome_entrega")
            with col3: busca_item_entrega = st.text_input("Buscar por Item", key="busca_item_entrega")

            if busca_id_entrega: df_para_entrega = df_para_entrega[df_para_entrega['ID'].astype(str).str.contains(busca_id_entrega, case=False, na=False)]
            if busca_nome_entrega: df_para_entrega = df_para_entrega[df_para_entrega['Nome Cliente'].str.contains(busca_nome_entrega, case=False, na=False)]
            if busca_item_entrega: df_para_entrega = df_para_entrega[df_para_entrega['Itens Pedido'].str.contains(busca_item_entrega, case=False, na=False)]

            st.markdown("---")
            st.subheader(f"📋 Lista de Entregas Pendentes ({len(df_para_entrega)})")

            if df_para_entrega.empty:
                st.success("🎉 Todos os pedidos para esta data foram entregues!")
            else:
                opcoes_ordenacao = st.multiselect("Ordenar por:", options=["Nome Cliente", "Data/Hora"], default=["Nome Cliente"])
                if opcoes_ordenacao: df_para_entrega = df_para_entrega.sort_values(by=opcoes_ordenacao)

                for _, row in df_para_entrega.iterrows():
                    with st.expander(f"Pedido #{row['ID']} - {row['Nome Cliente']}"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            data_formatada = row['Data/Hora'].strftime('%d/%m/%Y %H:%M:%S') if pd.notna(row['Data/Hora']) else "N/A"
                            st.write(f"**Data/Hora:** {data_formatada}")
                            st.write(f"**Itens:** {row['Itens Pedido']}")
                            st.write(f"**Telefone:** {row['Telefone Cliente']}")
                        with col2:
                            if st.button(f"Marcar como Entregue", key=f"entregue_{row['ID']}"):
                                cell = sheet.find(str(row['ID']))
                                if cell:
                                    sheet.update_cell(cell.row, 15, "Sim") 
                                    st.success(f"Pedido #{row['ID']} marcado como entregue!")
                                    st.rerun()
                                else:
                                    st.error(f"Não foi possível encontrar o pedido #{row['ID']} na planilha.")
            
            st.markdown("---")
            st.subheader("💰 Resumo Financeiro do Dia (Pedidos Aprovados)")

            if df_aprovados_do_dia.empty:
                st.info("Nenhum pedido aprovado para a data selecionada.")
            else:
                st.write("#### Resumo por Item Vendido")
                contagem = {}
                for _, row in df_aprovados_do_dia.iterrows():
                    itens = str(row['Itens Pedido']).split(',')
                    for item in itens:
                        item = item.strip()
                        if '] ' in item:
                            try:
                                qtd_str, nome_item = item.split('] ')
                                qtd = int(qtd_str.replace('[','').replace('x','').strip())
                                contagem[nome_item] = contagem.get(nome_item, 0) + qtd
                            except ValueError:
                                st.warning(f"Não foi possível processar o item: '{item}' do pedido #{row['ID']}")
                for k, v in contagem.items(): st.write(f"- {k}: {v} unidades")

                st.write("#### Fechamento de Caixa")
                total_vendido = df_aprovados_do_dia["Total Pedido"].sum()
                st.markdown(f"**Total Arrecadado ({data_relatorio.strftime('%d/%m/%Y')}): R$ {total_vendido:.2f}**")
                
                valores_por_pagamento = df_aprovados_do_dia.groupby("Tipo Pagamento")["Total Pedido"].sum()
                st.write("##### Totais por forma de pagamento:")
                for metodo, valor in valores_por_pagamento.items(): st.write(f"- {metodo}: R$ {valor:.2f}")

    # --- Aba 3: Prazos e Configurações ---
    with tab3:
        st.title("⚙️ Prazos e Configurações")
        st.subheader("Definir Data e Hora Limite para Pedidos")
        st.warning("Atenção: Após o horário definido para uma data, os usuários não poderão mais fazer pedidos para aquele dia.")

        # Carrega as configurações atuais
        config_records = config_sheet.get_all_records()
        configs = {rec['data_evento']: rec for rec in config_records}

        with st.form("deadlines_form"):
            new_configs = {}
            for nome_amigavel, data_evento in DATAS_DISPONIVEIS.items():
                st.markdown("---")
                st.markdown(f"#### Prazo para **{nome_amigavel}**")
                
                # Valores padrão
                default_date = datetime.strptime(data_evento, '%Y-%m-%d').date()
                default_time = time(10, 0) # 10:00 como padrão

                # Carrega valores salvos, se existirem
                if data_evento in configs:
                    try:
                        saved_date_str = configs[data_evento]['prazo_data']
                        saved_time_str = configs[data_evento]['prazo_hora']
                        # Tenta formatos diferentes que o gspreads pode retornar
                        try:
                            default_date = datetime.strptime(saved_date_str, '%d/%m/%Y').date()
                        except ValueError:
                            default_date = datetime.strptime(saved_date_str, '%Y-%m-%d').date()
                        default_time = datetime.strptime(saved_time_str, '%H:%M:%S').time()
                    except (ValueError, KeyError):
                        st.error(f"Formato de data/hora salvo para {nome_amigavel} é inválido. Usando valores padrão.")

                # Inputs para o admin
                col1, col2 = st.columns(2)
                with col1:
                    prazo_data = st.date_input("Data limite", value=default_date, key=f"date_{data_evento}", format="DD/MM/YYYY")
                with col2:
                    prazo_hora = st.time_input("Hora limite", value=default_time, key=f"time_{data_evento}")

                new_configs[data_evento] = {
                    "prazo_data": prazo_data,
                    "prazo_hora": prazo_hora,
                    "nome_amigavel": nome_amigavel
                }

            submitted = st.form_submit_button("💾 Salvar Todos os Prazos", type="primary")
            if submitted:
                with st.spinner("Salvando configurações..."):
                    for data_evento, config_data in new_configs.items():
                        # Procura se a configuração para esta data já existe
                        cell = config_sheet.find(data_evento)
                        
                        prazo_data_str = config_data['prazo_data'].strftime('%Y-%m-%d')
                        prazo_hora_str = config_data['prazo_hora'].strftime('%H:%M:%S')

                        if cell:
                            # Atualiza a linha existente
                            row_index = cell.row
                            config_sheet.update_cell(row_index, 2, prazo_data_str)
                            config_sheet.update_cell(row_index, 3, prazo_hora_str)
                        else:
                            # Adiciona uma nova linha se não existir
                            config_sheet.append_row([
                                data_evento,
                                prazo_data_str,
                                prazo_hora_str,
                                config_data['nome_amigavel']
                            ])
                st.success("Prazos salvos com sucesso!")
                # Limpa o cache para forçar a releitura dos prazos
                st.cache_data.clear()
                st.rerun()

# --- Configuração do menu principal ---
menu = st.sidebar.radio("Escolha a página:", ["Fazer Pedido", "Painel de Administração"])
if menu == "Fazer Pedido":
    pagina_pedidos()
else:
    pagina_admin()