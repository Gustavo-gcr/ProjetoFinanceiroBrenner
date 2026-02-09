import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import time

# --- FIREBASE SETUP ---
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão Confeitaria", layout="wide", page_icon="🍰")

# ==========================================
# 🔐 CONFIGURAÇÃO DE ACESSO (ADMIN)
# ==========================================
# Defina aqui o login do dono do sistema
ADMIN_EMAIL = "brenerstephano2@gmail.com"  # <--- SEU EMAIL DE ACESSO
ADMIN_SENHA = "33979864"                # <--- SUA SENHA
# ==========================================

# --- INICIALIZAÇÃO FIREBASE COM SECRETS ---
if not firebase_admin._apps:
    try:
        key_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erro ao conectar no Firebase: {e}")
        st.stop()

db = firestore.client()

# ==========================================
# 🎨 TEMA E ESTILO (DARK/LIGHT MODE)
# ==========================================
if "tema_claro" not in st.session_state:
    st.session_state.tema_claro = False

def aplicar_estilo(tema_light):
    if tema_light:
        bg_color = "#FFFFFF"
        text_color = "#1F2937"
        card_bg = "#F3F4F6"
        card_border = "#E5E7EB"
        metric_label = "#4B5563"
        metric_value = "#111827"
        input_text = "#000000"
    else:
        bg_color = "#0E1117"
        text_color = "#F3F4F6"
        card_bg = "#1A1C24"
        card_border = "#2D2F3B"
        metric_label = "#9CA3AF"
        metric_value = "#FFFFFF"
        input_text = "#FFFFFF"

    st.markdown(f"""
        <style>
        .stApp {{ background-color: {bg_color}; }}
        
        h1, h2, h3, h4, p, label, .stMarkdown, .stRadio label {{ color: {text_color} !important; font-family: 'Inter', sans-serif; }}
        
        /* Inputs */
        .stTextInput > div > div > input, 
        .stSelectbox > div > div > div, 
        .stNumberInput > div > div > input,
        .stTextArea > div > div > textarea {{
            color: {input_text} !important;
            background-color: {card_bg} !important;
            border-color: {card_border} !important;
        }}
        
        /* Cards de Métricas e Pedidos */
        div[data-testid="stMetric"], .card-pedido {{
            background-color: {card_bg} !important; 
            border: 1px solid {card_border} !important;
            padding: 20px; border-radius: 12px; 
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }}
        div[data-testid="stMetricLabel"] {{ color: {metric_label} !important; }}
        div[data-testid="stMetricValue"] {{ color: {metric_value} !important; font-weight: 700; }}
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {{ gap: 15px; background-color: transparent; padding-bottom: 10px; }}
        .stTabs [data-baseweb="tab"] {{
            height: 45px; background-color: transparent; border: 1px solid #4B5563;
            border-radius: 30px; color: {metric_label}; font-weight: 600;
            padding: 0 20px; transition: all 0.3s ease;
        }}
        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            background-color: #C62828; color: white !important; border: 1px solid #C62828;
            box-shadow: 0 4px 10px rgba(198, 40, 40, 0.3);
        }}
        
        /* Botões */
        .stButton > button {{
            background-color: #C62828; color: white !important; border-radius: 8px;
            border: none; font-weight: bold; height: 45px; transition: 0.3s;
            width: 100%;
        }}
        .stButton > button:hover {{ background-color: #B71C1C; box-shadow: 0 2px 8px rgba(198, 40, 40, 0.4); }}
        
        </style>
        """, unsafe_allow_html=True)

aplicar_estilo(st.session_state.tema_claro)

# --- FUNÇÕES FIRESTORE (Compartilhadas) ---
def load_collection(collection_name, mes_ref=None, order_by=None):
    try:
        ref = db.collection(collection_name)
        if collection_name in ['materia_prima', 'produtos_finais', 'clientes']:
            query = ref
        elif mes_ref:
            query = ref.where('mes_referencia', '==', mes_ref)
        else:
            query = ref 
            
        docs = query.stream()
        data = []
        for doc in docs:
            d = doc.to_dict()
            d['id'] = doc.id
            data.append(d)
        df = pd.DataFrame(data)
        if not df.empty and order_by and order_by in df.columns:
            df = df.sort_values(by=order_by, ascending=False)
        return df
    except Exception as e:
        st.error(f"Erro ao ler {collection_name}: {e}")
        return pd.DataFrame()

def add_doc(collection_name, data):
    db.collection(collection_name).add(data)

def update_doc(collection_name, doc_id, data):
    if doc_id: db.collection(collection_name).document(doc_id).update(data)

def delete_doc(collection_name, doc_id):
    if doc_id: db.collection(collection_name).document(doc_id).delete()

def get_doc(collection_name, doc_id):
    doc = db.collection(collection_name).document(doc_id).get()
    if doc.exists:
        d = doc.to_dict()
        d['id'] = doc.id
        return d
    return None

# ==========================================
# 🛒 ROTEAMENTO (O QUE MOSTRAR NA TELA)
# ==========================================
query_params = st.query_params
modo_visualizacao = query_params.get("view", ["admin"]) 
if isinstance(modo_visualizacao, list): modo_visualizacao = modo_visualizacao[0]

# --- 1. SE FOR CATÁLOGO CLIENTE (ACESSO PÚBLICO) ---
if modo_visualizacao == "catalogo_cliente":
    st.markdown("<h2 style='text-align: center;'>🍰 Faça seu Pedido</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; opacity: 0.7;'>Preencha os dados abaixo para solicitar</p>", unsafe_allow_html=True)
    
    # Carregar produtos com estoque
    df_prods = load_collection('produtos_finais')
    if not df_prods.empty:
        df_disponiveis = df_prods[df_prods['estoque_pronto'] > 0].copy()
    else:
        df_disponiveis = pd.DataFrame()

    if df_disponiveis.empty:
        st.info("No momento estamos sem estoque disponível. Volte em breve! ❤️")
        st.stop()

    st.subheader("1. Seus Dados")
    c_nome, c_tel = st.columns(2)
    with c_nome: cli_nome = st.text_input("Seu Nome Completo")
    with c_tel: cli_tel = st.text_input("Seu WhatsApp/Telefone")

    st.subheader("2. Escolha o Produto")
    opcoes = {}
    for idx, row in df_disponiveis.iterrows():
        qtd_real = int(row['estoque_pronto'])
        label = f"{row['nome']} | R$ {row['preco_venda']:.2f} (Disponível: {qtd_real})"
        opcoes[label] = row

    produto_selecionado_label = st.selectbox("Selecione uma delícia:", list(opcoes.keys()))
    produto_obj = opcoes[produto_selecionado_label]
    
    qtd_cliente = st.number_input("Quantidade desejada", min_value=1, step=1)
    
    st.subheader("3. Pagamento")
    forma_pag = st.selectbox("Como deseja pagar?", ["Pix", "Dinheiro", "Cartão Crédito/Débito", "A Combinar"])
    
    obs = st.text_area("Observações (Opcional)", placeholder="Ex: Retiro às 15h, troco para 50...")

    st.markdown("---")
    
    if st.button("✅ ENVIAR PEDIDO AGORA", use_container_width=True):
        if not cli_nome or not cli_tel:
            st.error("⚠️ Por favor, preencha seu NOME e TELEFONE antes de enviar.")
            st.stop()

        item_atualizado = get_doc('produtos_finais', produto_obj['id'])
        if not item_atualizado:
            st.error("Erro: Produto não encontrado ou removido.")
            st.stop()
        
        estoque_real = int(item_atualizado['estoque_pronto'])
        
        if qtd_cliente > estoque_real:
            st.error(f"🛑 ATENÇÃO: Você pediu {qtd_cliente}, mas só temos {estoque_real} unidades no estoque.")
            st.warning("Por favor, diminua a quantidade e tente novamente.")
            st.stop() 

        total_pedido = item_atualizado['preco_venda'] * qtd_cliente
        mes_atual = date.today().strftime("%Y-%m")

        add_doc('vendas', {
            'produto_final_id': item_atualizado['id'], 
            'produto_nome': item_atualizado['nome'], 
            'cliente_nome': cli_nome, 
            'cliente_telefone': cli_tel,
            'quantidade': qtd_cliente, 
            'total_venda': total_pedido, 
            'custo_producao_momento': item_atualizado['custo_producao'], 
            'data_criacao': datetime.now().isoformat(), 
            'data_finalizacao': None, 
            'forma_pagamento': forma_pag, 
            'status': 'Pendente', 
            'mes_referencia': mes_atual,
            'origem': 'Link Online',
            'obs': obs
        })
        
        update_doc('produtos_finais', item_atualizado['id'], {
            'estoque_pronto': estoque_real - qtd_cliente
        })
        
        st.balloons()
        st.success(f"Pedido Realizado com Sucesso! Obrigado, {cli_nome}.")
        time.sleep(2)
        st.rerun()

    st.markdown("---")
    st.caption("Sistema de Pedidos Confeitaria")
    st.stop() 


# ==========================================
# 🔐 ÁREA DO VENDEDOR (ADMIN) - PROTEGIDA
# ==========================================

# --- VERIFICAÇÃO DE LOGIN ---
if 'admin_logado' not in st.session_state:
    st.session_state.admin_logado = False

if not st.session_state.admin_logado:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        st.markdown("<h3 style='text-align: center;'>🔐 Acesso Restrito</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>Identifique-se para acessar o painel</p>", unsafe_allow_html=True)
        
        # --- FORMULÁRIO DE LOGIN ---
        email_digitado = st.text_input("E-mail de Acesso")
        senha_digitada = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema", use_container_width=True):
            if email_digitado == ADMIN_EMAIL and senha_digitada == ADMIN_SENHA:
                st.session_state.admin_logado = True
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")
    st.stop() # PARA AQUI SE NÃO TIVER LOGADO

# --- SE CHEGOU AQUI, É O ADMIN ---

# Sidebar com Configurações
st.sidebar.title("⚙️ Configurações")
toggle_tema = st.sidebar.toggle("☀️ Modo Claro (Light Mode)", value=st.session_state.tema_claro)
if toggle_tema != st.session_state.tema_claro:
    st.session_state.tema_claro = toggle_tema
    st.rerun() 

if st.sidebar.button("🔒 Sair / Logout"):
    st.session_state.admin_logado = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Painel do Vendedor")

# --- DATAS ---
def get_month_options():
    today = date.today()
    months = []
    for i in range(-12, 13):
        d = today + timedelta(days=30*i)
        months.append(d.strftime("%Y-%m"))
    return sorted(list(set(months)), reverse=True)

# --- DIALOGS (POPUPS) ---
@st.dialog("Novo Insumo")
def popup_novo_insumo():
    c1, c2 = st.columns(2)
    with c1: nome = st.text_input("Nome do Insumo")
    with c2: unidade = st.selectbox("Unidade", ["Un", "Kg", "L", "Cx"])
    custo = st.number_input("Custo de Compra (R$)", min_value=0.0)
    
    if st.button("Salvar Insumo"):
        if not nome.strip():
            st.error("O nome do insumo não pode ser vazio.")
            return

        exists = db.collection('materia_prima').where('nome', '==', nome).stream()
        if list(exists):
            st.error(f"O insumo '{nome}' já está cadastrado!")
            return

        add_doc('materia_prima', {
            'nome': nome, 
            'unidade': unidade, 
            'custo_compra': custo, 
            'estoque_atual': 0,
            'mes_referencia': 'GLOBAL'
        })
        st.success("Salvo!")
        st.rerun()

# --- SIDEBAR FILTROS ---
meses_disponiveis = get_month_options()
mes_atual_default = date.today().strftime("%Y-%m")
if mes_atual_default not in meses_disponiveis:
    meses_disponiveis.append(mes_atual_default)
    meses_disponiveis.sort(reverse=True)
mes_selecionado = st.sidebar.selectbox("📅 Mês de Competência", meses_disponiveis, index=meses_disponiveis.index(mes_atual_default) if mes_atual_default in meses_disponiveis else 0)
st.sidebar.info(f"Mês Ativo: **{mes_selecionado}**")

# --- GERADOR DE LINK ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔗 Link para Clientes")
link_para_copiar = "https://projetofinanceirobrener.streamlit.app/?view=catalogo_cliente"
st.sidebar.markdown("Clique no ícone **no canto direito** abaixo para copiar:")
st.sidebar.code(link_para_copiar, language="text") 


# --- ABAS ---
aba1, aba2, aba3, aba4, aba5 = st.tabs([
    "📊 Dashboards", "📦 Estoque MP", "🍩 Produtos", "📝 Novo Pedido", "✅ Pedidos Abertos" 
])

# --- ABA 1: DASHBOARDS ---
with aba1:
    st.markdown("### 🚀 Resultados do Mês")
    df_entradas = load_collection('entradas_mp', mes_selecionado)
    df_vendas = load_collection('vendas', mes_selecionado)
    gastos_mp = df_entradas['custo_total'].sum() if not df_entradas.empty else 0.0
    
    df_finalizados = df_vendas[df_vendas['status'] == 'Finalizado'] if not df_vendas.empty else pd.DataFrame()
    receita_vendas = df_finalizados['total_venda'].sum() if not df_finalizados.empty else 0.0
    saldo_caixa = receita_vendas - gastos_mp
    
    lucro_operacional = 0.0
    if not df_finalizados.empty:
        custo_vendidos = (df_finalizados['quantidade'] * df_finalizados['custo_producao_momento']).sum()
        lucro_operacional = receita_vendas - custo_vendidos

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Faturamento", f"R$ {receita_vendas:,.2f}")
    col2.metric("Compras Insumos", f"R$ {gastos_mp:,.2f}")
    col3.metric("Saldo Líquido", f"R$ {saldo_caixa:,.2f}", delta="Caixa")
    col4.metric("Lucro Operacional", f"R$ {lucro_operacional:,.2f}", delta="Produção")
    
    st.divider()
    if not df_finalizados.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Entradas vs Saídas")
            fig = px.bar(x=['Vendas', 'Compras MP'], y=[receita_vendas, gastos_mp], 
                         color=['Vendas', 'Compras MP'], color_discrete_sequence=['#4ADE80', '#EF4444'], text_auto='$.2f')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", showlegend=False, yaxis_title="R$")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.subheader("Top Produtos")
            top = df_finalizados.groupby('produto_nome')['quantidade'].sum().reset_index()
            fig2 = px.pie(top, values='quantidade', names='produto_nome', hole=0.6, color_discrete_sequence=px.colors.sequential.Redor)
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sem dados finalizados para gráficos.")

# --- ABA 2: ESTOQUE MP ---
with aba2:
    st.subheader("Gerenciamento de Estoque e Insumos")
    
    col_btn, col_blank = st.columns([1, 4])
    with col_btn:
        if st.button("➕ Cadastrar Novo Insumo"):
            popup_novo_insumo()

    st.divider()
    
    df_mp = load_collection('materia_prima')
    mp_map = {row['nome']: row for _, row in df_mp.iterrows()} if not df_mp.empty else {}
    
    c_form, c_view = st.columns([1, 1])
    with c_form:
        st.markdown("##### Registrar Compra (Entrada)")
        sel_mp_nome = st.selectbox("Selecione o Item", list(mp_map.keys()) if mp_map else [])
        qtd_ent = st.number_input("Quantidade Comprada", 0.1)
        
        if st.button("Registrar Gasto e Atualizar Estoque"):
            if mp_map:
                item = mp_map[sel_mp_nome]
                custo_total = item['custo_compra'] * qtd_ent
                
                update_doc('materia_prima', item['id'], {'estoque_atual': item['estoque_atual'] + qtd_ent})
                
                add_doc('entradas_mp', {
                    'mp_id': item['id'], 
                    'mp_nome': item['nome'], 
                    'quantidade': qtd_ent, 
                    'custo_total': custo_total, 
                    'data_entrada': datetime.now().isoformat(), 
                    'mes_referencia': mes_selecionado
                })
                st.success("Compra salva!")
                st.rerun()

    with c_view:
        st.markdown("##### ✏️ Editar Insumos (Nome/Custo)")
        if not df_mp.empty:
            df_mp_view = load_collection('materia_prima')
            df_mp_view['Total Investido'] = df_mp_view['estoque_atual'] * df_mp_view['custo_compra']
            
            edited_mp = st.data_editor(
                df_mp_view,
                key="editor_mp",
                hide_index=True,
                use_container_width=True,
                column_config={
                    "id": None,
                    "mes_referencia": None,
                    "nome": st.column_config.TextColumn("Nome"),
                    "unidade": st.column_config.SelectboxColumn("Unidade", options=["Un", "Kg", "L", "Cx"]),
                    "custo_compra": st.column_config.NumberColumn("Custo Compra (R$)", format="%.2f"),
                    "estoque_atual": st.column_config.NumberColumn("Estoque (Fixo)", disabled=True),
                    "Total Investido": st.column_config.NumberColumn("Total Investido", format="R$ %.2f", disabled=True)
                }
            )

            if st.button("💾 Salvar Alterações nos Insumos"):
                if not df_mp_view.equals(edited_mp):
                    for index, row in edited_mp.iterrows():
                        original_row = df_mp_view[df_mp_view['id'] == row['id']].iloc[0]
                        if (row['nome'] != original_row['nome'] or 
                            row['custo_compra'] != original_row['custo_compra'] or 
                            row['unidade'] != original_row['unidade']):
                            update_doc('materia_prima', row['id'], {
                                'nome': row['nome'], 
                                'custo_compra': row['custo_compra'],
                                'unidade': row['unidade']
                            })
                    st.success("Insumos atualizados com sucesso!")
                    st.rerun()
                else:
                    st.info("Nenhuma alteração para salvar.")
        else:
            st.info("Nenhum insumo cadastrado.")

    st.divider()
    with st.expander("🗑️ Excluir Insumo (Cuidado)"):
        if not df_mp.empty:
            mp_dict_del = {row['nome']: row['id'] for _, row in df_mp.iterrows()}
            sel_del = st.selectbox("Apagar item do cadastro:", list(mp_dict_del.keys()))
            if st.button("Confirmar Exclusão"):
                delete_doc('materia_prima', mp_dict_del[sel_del])
                st.success("Removido!")
                st.rerun()

# --- ABA 3: PRODUTOS ---
with aba3:
    st.subheader("Cadastro e Gestão de Produtos")
    
    with st.expander("➕ Criar Novo Produto"):
        c1, c2, c3, c4 = st.columns(4)
        with c1: pf_nome = st.text_input("Nome do Produto", key="pf_nome_input")
        with c2: pf_custo = st.number_input("Custo Prod. (R$)", 0.0)
        with c3: pf_preco = st.number_input("Venda (R$)", 0.0)
        with c4: pf_est = st.number_input("Estoque Inicial", 0)
        
        if st.button("Salvar Produto"):
            exists = db.collection('produtos_finais').where('nome', '==', pf_nome).stream()
            if list(exists):
                st.warning(f"⚠️ O produto '{pf_nome}' já existe! Por favor, adicione unidades no painel 'Gerir Produtos' abaixo.")
            else:
                add_doc('produtos_finais', {
                    'nome': pf_nome, 
                    'custo_producao': pf_custo, 
                    'preco_venda': pf_preco, 
                    'estoque_pronto': pf_est, 
                    'data_cadastro': date.today().isoformat(), 
                    'mes_referencia': 'GLOBAL'
                })
                st.success("Produto Criado!")
                st.rerun()

    st.divider()

    st.markdown("### 📝 Gerir Produtos (Alterar Preço/Estoque)")
    
    df_pf = load_collection('produtos_finais')
    
    if not df_pf.empty:
        edited_pf = st.data_editor(
            df_pf, 
            hide_index=True, 
            use_container_width=True, 
            key="edit_pf_table",
            column_config={
                "id": st.column_config.TextColumn(disabled=True),
                "mes_referencia": None,
                "data_cadastro": st.column_config.DateColumn(
                    label="Data de Cadastro", 
                    format="DD/MM/YYYY",
                    disabled=True
                ),
                "custo_producao": st.column_config.NumberColumn(format="R$ %.2f"), 
                "preco_venda": st.column_config.NumberColumn(format="R$ %.2f")
            }
        )
        
        if st.button("💾 Salvar Alterações nos Produtos"):
            if not df_pf.equals(edited_pf):
                for index, row in edited_pf.iterrows():
                    original_row = df_pf[df_pf['id'] == row['id']].iloc[0]
                    
                    if (row['estoque_pronto'] != original_row['estoque_pronto'] or 
                        row['preco_venda'] != original_row['preco_venda'] or 
                        row['custo_producao'] != original_row['custo_producao']):
                        
                        update_doc('produtos_finais', row['id'], {
                            'nome': row['nome'], 
                            'custo_producao': row['custo_producao'], 
                            'preco_venda': row['preco_venda'], 
                            'estoque_pronto': row['estoque_pronto'],
                        })
                st.success("Produtos atualizados com sucesso!")
                st.rerun()
            else:
                st.info("Nenhuma alteração detectada para salvar.")

# --- ABA 4: NOVO PEDIDO ---
with aba4:
    st.subheader("📝 Criar Pedido (Balcão)")
    df_pf_global = load_collection('produtos_finais')
    pf_map = {row['nome']: row for _, row in df_pf_global.iterrows()} if not df_pf_global.empty else {}
    
    df_clientes = load_collection('clientes', order_by='nome')
    lista_clientes = df_clientes['nome'].tolist() if not df_clientes.empty else []
    lista_clientes.insert(0, "➕ Novo Cliente...")
    
    with st.container():
        c1, c2, c3 = st.columns([3, 1, 3])
        with c1: v_prod = st.selectbox("Produto", list(pf_map.keys()) if pf_map else [])
        with c2: v_qtd = st.number_input("Qtd", 1)
        with c3:
            cli_sel = st.selectbox("Cliente", lista_clientes)
            nome_cli_final = cli_sel
            if cli_sel == "➕ Novo Cliente...":
                nome_cli_final = st.text_input("Nome do Cliente:")
        
        c4, c5 = st.columns(2)
        with c4: v_pag = st.selectbox("Pagamento", ["Pix", "Dinheiro", "Cartão", "A Combinar"])
        with c5: v_data = st.date_input("Data", value=date.today())
        
        st.write("")
        if st.button("🚀 Criar Pedido (Reservar Estoque)"):
            if not nome_cli_final: st.error("Informe o cliente.")
            elif pf_map:
                if cli_sel == "➕ Novo Cliente...":
                    if not list(db.collection('clientes').where('nome', '==', nome_cli_final).stream()):
                        add_doc('clientes', {'nome': nome_cli_final})
                
                item = pf_map[v_prod]
                if item['estoque_pronto'] >= v_qtd:
                    total = item['preco_venda'] * v_qtd
                    
                    add_doc('vendas', {
                        'produto_final_id': item['id'], 'produto_nome': v_prod, 
                        'cliente_nome': nome_cli_final, 'quantidade': v_qtd, 
                        'total_venda': total, 'custo_producao_momento': item['custo_producao'], 
                        'data_criacao': v_data.isoformat(), 'data_finalizacao': None, 
                        'forma_pagamento': v_pag, 'status': 'Pendente', 
                        'mes_referencia': mes_selecionado,
                        'origem': 'Balcão'
                    })
                    
                    update_doc('produtos_finais', item['id'], {'estoque_pronto': item['estoque_pronto'] - v_qtd})
                    st.success(f"Pedido para {nome_cli_final} criado!")
                    st.rerun()
                else: st.error(f"Estoque insuficiente! Disponível: {item['estoque_pronto']}")

# --- ABA 5: PEDIDOS ABERTOS (COM AUTO-REFRESH) ---
with aba5:
    st.subheader("✅ Gerenciar Entregas")
    st.caption("Esta tela atualiza sozinha a cada 15 segundos.")

    @st.fragment(run_every=15)
    def mostrar_pedidos_abertos():
        ref_vendas = db.collection('vendas')
        query = ref_vendas.where('mes_referencia', '==', mes_selecionado).where('status', '==', 'Pendente')
        pendentes = [{'id': d.id, **d.to_dict()} for d in query.stream()]
        pendentes.sort(key=lambda x: x['data_criacao'], reverse=True)
        
        if pendentes:
            st.info(f"Pendentes Agora: {len(pendentes)}")
            for ped in pendentes:
                with st.container():
                    st.markdown(f"""
                    <div class="card-pedido">
                        <h4 style="margin:0;">{ped['cliente_nome']}</h4>
                        <p style="margin:0; opacity: 0.7; font-size: 14px;">📞 {ped.get('cliente_telefone', 'Sem fone')}</p>
                        <p style="margin:5px 0; font-weight: bold;">{ped['quantidade']}x {ped['produto_nome']} | R$ {ped['total_venda']:.2f}</p>
                        <p style="margin:0; font-size: 12px; opacity: 0.6;">Pagamento: {ped['forma_pagamento']} | Origem: {ped.get('origem', 'Link Online')}</p>
                        {f'<p style="color: #F87171; font-size: 12px;">Obs: {ped["obs"]}</p>' if ped.get('obs') else ''}
                    </div>
                    """, unsafe_allow_html=True)

                    c_btn_ok, c_btn_can = st.columns([1, 1])
                    with c_btn_ok:
                        if st.button("Concluir ✅", key=f"ok_{ped['id']}", use_container_width=True):
                            update_doc('vendas', ped['id'], {'status': 'Finalizado', 'data_finalizacao': date.today().isoformat()})
                            st.toast("Finalizado!")
                            st.rerun()
                    with c_btn_can:
                        if st.button("Cancelar ❌", key=f"can_{ped['id']}", use_container_width=True):
                            prod = get_doc('produtos_finais', ped['produto_final_id'])
                            if prod: update_doc('produtos_finais', ped['produto_final_id'], {'estoque_pronto': prod['estoque_pronto'] + ped['quantidade']})
                            delete_doc('vendas', ped['id'])
                            st.warning("Cancelado e estornado.")
                            st.rerun()
                    st.write("")
        else:
            st.success("Tudo entregue! Aguardando novos pedidos...")

    mostrar_pedidos_abertos()
    
    st.markdown("---")
    with st.expander("Histórico de Entregues"):
        df_fin = load_collection('vendas', mes_selecionado)
        if not df_fin.empty:
            df_fin = df_fin[df_fin['status'] == 'Finalizado']
            st.dataframe(df_fin[['data_finalizacao', 'cliente_nome', 'produto_nome', 'total_venda']], use_container_width=True, hide_index=True)