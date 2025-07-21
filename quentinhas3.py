import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
import urllib.parse
import locale

# Configurações iniciais do Streamlit
st.set_page_config(page_title="Pedido Quentinhas - Congresso RCC/PI", page_icon="🍲", layout="wide")

@st.cache_resource
def connect_and_authorize():
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds_dict = st.secrets["google_credentials"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client_gs = gspread.authorize(creds)
    spreadsheet = client_gs.open_by_key(st.secrets["GOOGLE_SHEETS_ID"])
    sheet = spreadsheet.worksheet("Pedidos")
    return sheet

sheet = connect_and_authorize()

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

def notificar_cliente(pedido_id, nome_cliente, telefone_cliente):
    """Função para gerar e exibir o link de notificação do WhatsApp"""
    mensagem = f"Olá, {nome_cliente}! Seu pedido *#{pedido_id}* foi APROVADO!"
    link_whatsapp = gerar_link_whatsapp(telefone_cliente, mensagem)
    
    st.markdown("### Notificação ao Cliente")
    st.markdown(f"**Mensagem pronta:** `{mensagem}`")
    st.markdown(f"[👉 Clique aqui para enviar mensagem no WhatsApp]({link_whatsapp})", unsafe_allow_html=True)
    st.markdown(f"**Link completo:** `{link_whatsapp}`")
    
    return link_whatsapp

def extrair_data_do_datetime(data_hora_str):
    """Extrai a data de uma string de data/hora"""
    try:
        # Tenta diferentes formatos de data
        if ' ' in str(data_hora_str):
            data_parte = str(data_hora_str).split(' ')[0]
        else:
            data_parte = str(data_hora_str)
        
        # Converte para datetime e depois para date
        return pd.to_datetime(data_parte).date()
    except:
        return None
    
    #########################

def pagina_pedidos():
    st.title("🍲 Agende seu Pedido de Quentinha")

    # --- INÍCIO DA CORREÇÃO ---
    # Define a localidade para português para garantir que os dias da semana fiquem corretos
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
    except locale.Error:
        # Fallback para o caso de o sistema não ter a localidade pt_BR
        locale.setlocale(locale.LC_TIME, '')

    # Cria um novo dicionário de exibição com as datas formatadas corretamente
    # Isso garante que sempre usaremos o formato DD/MM/YYYY
    DATAS_EXIBICAO = {}
    for nome_original, valor_data in DATAS_DISPONIVEIS.items():
        data_obj = datetime.strptime(valor_data, '%Y-%m-%d')
        # Pega o dia da semana ("Sábado", "Domingo", etc.) do nome da chave original
        dia_semana = nome_original.split(' ')[0]
        # Formata a data para o padrão DD/MM/YYYY
        data_formatada = data_obj.strftime('%d/%m/%Y')
        # Cria o texto final para exibição
        texto_final_exibicao = f"{dia_semana} ({data_formatada})"
        DATAS_EXIBICAO[texto_final_exibicao] = valor_data

    # --- FIM DA CORREÇÃO ---

    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = {data_valor: {opcao: 0 for opcao in CARDAPIO["opcoes_principais"]} for data_valor in DATAS_EXIBICAO.values()}

    st.subheader("1. Para quais dias você quer agendar?")
    # Agora usamos o novo dicionário DATAS_EXIBICAO para mostrar as opções
    escolhas_datas = {
        valor_data: st.radio(
            f"Pedido para **{nome_data_formatado}**:",
            ["Sem Pedido", "Quero Pedir"],
            key=f"choice_{valor_data}",
            horizontal=True
        )
        for nome_data_formatado, valor_data in DATAS_EXIBICAO.items()
    }
    datas_para_pedir = [data for data, escolha in escolhas_datas.items() if escolha == "Quero Pedir"]

    if not datas_para_pedir:
        st.info("Selecione 'Quero Pedir' em uma das datas para montar sua quentinha.")
        return

    grand_total = 0
    pedidos_finais = {}
    st.info("**Atenção:** Todas as opções acompanham Baião de dois, Macarrão, Farofa e Salada cozida.")

    for data_pedido in datas_para_pedir:
        # Encontra o nome amigável formatado no nosso novo dicionário
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

        st.markdown(
            f"<p style='text-align: right; font-weight: bold;'>Subtotal para {nome_amigavel_data}: R$ {total_dia:.2f}</p>",
            unsafe_allow_html=True
        )
        grand_total += total_dia
        if total_dia > 0:
            pedidos_finais[data_pedido] = {"itens_obj": itens_dia_obj, "total": total_dia}

    if grand_total > 0:
        st.markdown("---")
        st.markdown(f"## Valor Total do Pedido: **R$ {grand_total:.2f}**")
        st.markdown("---")
        
        tipo_pagamento = st.selectbox("Forma de Pagamento:", ["Pix", "Dinheiro"])
        if tipo_pagamento == "Pix":
            st.info(
                "🔑 **Chave PIX:** `86988282470`\n\n"
                "👤 **Lauriano Costa Viana - Banco do Brasil**\n\n"
                "📨 Após finalizar o pedido, envie o seu nome completo e o comprovante para 86-98828-2470 via WhatsApp."
            )
        else:
            st.warning("Após finalizar o pedido, dirija-se ao caixa para realizar o pagamento e aprovar seu pedido.")

        with st.form("final_form"):
            nome_cliente = st.text_input("Seu Nome Completo*")
            telefone_cliente = st.text_input("Seu Telefone/WhatsApp com DDD*", placeholder="Ex: 86999998888")
            observacoes = st.text_area("Observações")
            submitted = st.form_submit_button("✔ Finalizar Pedido")

            if submitted:
                if not nome_cliente or not telefone_cliente:
                    st.warning("Por favor, preencha Nome e Telefone.")
                else:
                    for data_pedido, detalhes in pedidos_finais.items():
                        id_por_data = f"{data_pedido.replace('-', '')}-{uuid.uuid4().hex[:6].upper()}"
                        itens_fmt = ", ".join([f"[{item['qtd']}x] {item['nome']}" for item in detalhes["itens_obj"]])
                        new_order_data = [
                            id_por_data, f"{data_pedido} {datetime.now().strftime('%H:%M:%S')}",
                            nome_cliente, "", telefone_cliente, "",
                            itens_fmt, f"{detalhes['total']:.2f}",
                            observacoes, tipo_pagamento, "", "Pendente", "",
                            f"{grand_total:.2f}", ""
                        ]
                        sheet.append_row(new_order_data, value_input_option='USER_ENTERED')
                    st.success(
                        "Pedido(s) registrado(s) com sucesso!"
                        "\n\n Você receberá uma confirmação via WhatsApp após aprovação. \n\n"
                    )
                    del st.session_state.carrinho

###########
def pagina_admin():
    if not st.session_state.get("autenticado"):
        autenticar_admin()
        return

    tab1, tab2 = st.tabs(["Gerenciar Pedidos", "Relatórios"])

    # Carrega todos os dados e converte a coluna de data/hora para o tipo datetime
    all_data = sheet.get_all_records()
    if not all_data:
        st.info("Nenhum pedido encontrado na planilha.")
        # Adicionado para evitar erro se a planilha estiver vazia em ambas as abas
        with tab1:
            st.title("👑 Gerenciamento de Pedidos Pendentes")
            st.info("Nenhum pedido para gerenciar.")
        with tab2:
            st.title("📈 Relatórios e Entregas")
            st.info("Nenhum dado para gerar relatórios.")
        return

    df = pd.DataFrame(all_data)
    # <-- ALTERAÇÃO 1: Converte a coluna inteira para datetime de uma vez.
    # Isso garante que o Python, e não o Google Sheets, controle o formato.
    df['Data/Hora'] = pd.to_datetime(df['Data/Hora'], errors='coerce')

    with tab1:
        st.title("👑 Gerenciamento de Pedidos Pendentes")
        
        if st.button("🔄 Atualizar Pedidos"): 
            st.rerun()

        st.subheader("🔍 Buscar Pedidos Pendentes")
        col1, col2, col3 = st.columns(3)
        with col1:
            busca_id = st.text_input("Buscar por ID do Pedido")
        with col2:
            busca_nome = st.text_input("Buscar por Nome do Cliente")
        with col3:
            busca_telefone = st.text_input("Buscar por Telefone")

        if 'Status' not in df.columns:
            st.error("A coluna 'Status' não foi encontrada na sua planilha. Verifique os cabeçalhos.")
            return

        df_pendentes = df[df['Status'] == 'Pendente'].copy()

        if busca_id:
            df_pendentes = df_pendentes[df_pendentes['ID'].astype(str).str.contains(busca_id, case=False, na=False)]
        if busca_nome:
            df_pendentes = df_pendentes[df_pendentes['Nome Cliente'].str.contains(busca_nome, case=False, na=False)]
        if busca_telefone:
            df_pendentes = df_pendentes[df_pendentes['Telefone Cliente'].astype(str).str.contains(busca_telefone, case=False, na=False)]

        if df_pendentes.empty:
            st.info("✅ Nenhum pedido pendente encontrado com os critérios de busca.")
        else:
            st.markdown(f"**Pedidos pendentes encontrados:** {len(df_pendentes)}")
            for _, row in df_pendentes.iterrows():
                with st.expander(f"Pedido #{row['ID']} - {row['Nome Cliente']} - R$ {row['Total Pedido']}"):
                    # <-- ALTERAÇÃO 2: Formata a data para o padrão BR antes de exibir
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
                                
                                if f"show_notify_{row['ID']}" in st.session_state:
                                    del st.session_state[f"show_notify_{row['ID']}"]

                                st.rerun()
                            else:
                                st.error(f"Não foi possível encontrar o pedido #{row['ID']} na planilha para aprovação.")
                    
                    if st.session_state.get(f"show_notify_{row['ID']}", False):
                        with st.container(border=True):
                            notificar_cliente(
                                pedido_id=row['ID'],
                                nome_cliente=row['Nome Cliente'],
                                telefone_cliente=row['Telefone Cliente']
                            )
                            if st.button("Ocultar Notificação", key=f"hide_{row['ID']}"):
                                del st.session_state[f"show_notify_{row['ID']}"]
                                st.rerun()

    with tab2:
        st.title("📈 Relatórios e Entregas")
        data_relatorio = st.date_input("Selecione a data do pedido:", value=datetime.now(), format="YYYY-MM-DD")
        
        st.info("Por padrão, a data de hoje é selecionada. Altere para a data que deseja consultar (ex: 02/08/2025 ou 03/08/2025).")

        # <-- ALTERAÇÃO 3: Simplificamos a criação da coluna 'Data', pois 'Data/Hora' já é um datetime.
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
        with col1:
            busca_id_entrega = st.text_input("Buscar por ID do Pedido", key="busca_id_entrega")
        with col2:
            busca_nome_entrega = st.text_input("Buscar por Nome do Cliente", key="busca_nome_entrega")
        with col3:
            busca_item_entrega = st.text_input("Buscar por Item do Pedido", key="busca_item_entrega")

        if busca_id_entrega:
            df_para_entrega = df_para_entrega[df_para_entrega['ID'].astype(str).str.contains(busca_id_entrega, case=False, na=False)]
        if busca_nome_entrega:
            df_para_entrega = df_para_entrega[df_para_entrega['Nome Cliente'].str.contains(busca_nome_entrega, case=False, na=False)]
        if busca_item_entrega:
            df_para_entrega = df_para_entrega[df_para_entrega['Itens Pedido'].str.contains(busca_item_entrega, case=False, na=False)]

        st.markdown("---")
        st.subheader(f"📋 Lista de Entregas Pendentes ({len(df_para_entrega)})")

        if df_para_entrega.empty:
            st.success("🎉 Todos os pedidos para esta data foram entregues!")
        else:
            opcoes_ordenacao = st.multiselect(
                "Ordenar entregas por:",
                options=["Nome Cliente", "Data/Hora"],
                default=["Nome Cliente"],
                key="ordenacao_entregas"
            )

            if opcoes_ordenacao:
                df_para_entrega = df_para_entrega.sort_values(by=opcoes_ordenacao)

            for _, row in df_para_entrega.iterrows():
                with st.expander(f"Pedido #{row['ID']} - {row['Nome Cliente']}"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        # <-- ALTERAÇÃO 4: Formata a data aqui também para consistência
                        data_formatada = row['Data/Hora'].strftime('%d/%m/%Y %H:%M:%S') if pd.notna(row['Data/Hora']) else "Data inválida"
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
                                st.error(f"Não foi possível encontrar o pedido #{row['ID']} na planilha para entrega.")
        
        st.markdown("---")
        st.subheader("💰 Resumo Financeiro do Dia (Todos os Pedidos Aprovados)")

        if df_aprovados_do_dia.empty:
            st.info("Nenhum pedido aprovado para a data selecionada para gerar relatórios.")
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
            
            for k, v in contagem.items():
                st.write(f"- {k}: {v} unidades")

            st.write("#### Fechamento de Caixa")
            total_vendido = df_aprovados_do_dia["Total Pedido"].sum()
            valores_por_pagamento = df_aprovados_do_dia.groupby("Tipo Pagamento")["Total Pedido"].sum()
            
            st.markdown(f"**Total Arrecadado (Aprovados em {data_relatorio.strftime('%d/%m/%Y')}): R$ {total_vendido:.2f}**")

            st.write("##### Totais por forma de pagamento:")
            for metodo, valor in valores_por_pagamento.items():
                st.write(f"- {metodo}: R$ {valor:.2f}")

            st.write("##### Número de pedidos por forma de pagamento:")
            total_por_pagamento = df_aprovados_do_dia["Tipo Pagamento"].value_counts()
            for metodo, count in total_por_pagamento.items():
                st.write(f"- {metodo}: {count} pedido(s)")

# Configuração do menu principal
menu = st.sidebar.radio("Escolha a página:", ["Fazer Pedido", "Painel de Administração"])
if menu == "Fazer Pedido":
    pagina_pedidos()
else:
    pagina_admin()