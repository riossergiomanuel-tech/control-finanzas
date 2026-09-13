import streamlit as st
import pandas as pd
import sqlite3
import datetime
from datetime import date

# ---------------------------------------------------------
# CONFIGURACIÓN DE PÁGINA
# ---------------------------------------------------------
st.set_page_config(
    page_title="Control Financiero Personal",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------
# ESTILO VISUAL MODERNO (Modo Oscuro Fintech)
# ---------------------------------------------------------
st.markdown("""
<style>
    .main { 
        background-color: #0e1117; 
        color: #fafafa; 
    }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        padding: 16px 20px;
        border-radius: 12px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stMetric"] label {
        color: #8b949e !important;
        font-size: 14px !important;
        font-weight: 500;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #f0f6fc !important;
        font-size: 28px !important;
        font-weight: 700;
    }
    .alert-card {
        background-color: #2e1a05;
        border: 1px solid #d29922;
        border-radius: 10px;
        padding: 16px 20px;
        color: #f0f6fc;
        margin-top: 15px;
        margin-bottom: 25px;
        font-size: 15px;
        line-height: 1.5;
    }
    .hormiga-card {
        background-color: #0c2135;
        border: 1px solid #388bfd;
        border-radius: 10px;
        padding: 18px;
        color: #f0f6fc;
        line-height: 1.6;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# BASE DE DATOS (SQLite)
# ---------------------------------------------------------
DB_FILE = "finanzas.db"

def get_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS billetera (metodo TEXT PRIMARY KEY, saldo REAL)")
    c.execute("""CREATE TABLE IF NOT EXISTS deudas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        acreedor TEXT UNIQUE, 
        saldo REAL, 
        pago_minimo REAL, 
        tasa_cat REAL, 
        dia_corte INTEGER, 
        tipo_cuenta TEXT,
        activa INTEGER DEFAULT 1)
    """)
    c.execute("""CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        fecha TEXT, 
        concepto TEXT, 
        categoria TEXT, 
        tipo TEXT, 
        monto REAL, 
        metodo_pago TEXT)
    """)
    c.execute("INSERT OR IGNORE INTO configuracion VALUES ('ingreso_semanal', 3200.0)")
    c.execute("INSERT OR IGNORE INTO configuracion VALUES ('porcentaje_ahorro', 10.0)")
    c.execute("INSERT OR IGNORE INTO configuracion VALUES ('gasto_esencial_semanal', 1000.0)")
    c.execute("INSERT OR IGNORE INTO billetera VALUES ('Banco', 2200.0)")
    c.execute("INSERT OR IGNORE INTO billetera VALUES ('Efectivo', 800.0)")
    
    c.execute("SELECT COUNT(*) FROM deudas")
    if c.fetchone()[0] == 0:
        deudas = [
            ("BBVA", 18509.15, 950.0, 48.0, 12, "Tarjeta Crédito"),
            ("Ualá", 6995.34, 550.0, 70.0, 25, "Tarjeta Crédito"),
            ("Mercado Pago (MSI)", 815.82, 815.82, 0.0, 20, "Meses sin Intereses"),
            ("Coppel", 4200.0, 450.0, 65.0, 15, "Departamental"),
            ("Nu", 3400.0, 350.0, 52.0, 18, "Tarjeta Crédito"),
            ("DiDi", 2600.0, 450.0, 95.0, 10, "Préstamo / Tarjeta"),
            ("Vexi", 2500.0, 350.0, 78.0, 28, "Tarjeta Crédito"),
            ("Stori", 1477.17, 250.0, 99.0, 22, "Tarjeta Crédito")
        ]
        c.executemany("INSERT INTO deudas (acreedor, saldo, pago_minimo, tasa_cat, dia_corte, tipo_cuenta) VALUES (?,?,?,?,?,?)", deudas)

    conn.commit()
    conn.close()

init_db()

def get_cfg():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT clave, valor FROM configuracion")
    d = {r['clave']: r['valor'] for r in c.fetchall()}
    conn.close()
    return d

def set_cfg(k, v):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO configuracion VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()

def get_billetera():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM billetera", conn)
    conn.close()
    return {r['metodo']: r['saldo'] for _, r in df.iterrows()}

def set_billetera(banco, efectivo):
    conn = get_db()
    conn.execute("UPDATE billetera SET saldo = ? WHERE metodo = 'Banco'", (banco,))
    conn.execute("UPDATE billetera SET saldo = ? WHERE metodo = 'Efectivo'", (efectivo,))
    conn.commit()
    conn.close()

def update_billetera_delta(metodo, monto):
    conn = get_db()
    target = "Banco" if ("Banco" in metodo or "Tarjeta" in metodo or "Transferencia" in metodo) else "Efectivo"
    conn.execute("UPDATE billetera SET saldo = saldo - ? WHERE metodo = ?", (monto, target))
    conn.commit()
    conn.close()

def get_deudas():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM deudas WHERE activa=1", conn)
    conn.close()
    return df

def update_deuda_val(did, saldo, pago_min, cat, dia):
    conn = get_db()
    conn.execute("UPDATE deudas SET saldo=?, pago_minimo=?, tasa_cat=?, dia_corte=? WHERE id=?", (saldo, pago_min, cat, dia, did))
    conn.commit()
    conn.close()

def get_movimientos():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM movimientos ORDER BY fecha DESC, id DESC", conn)
    conn.close()
    return df

def add_movimiento(f, c, cat, t, m, met):
    conn = get_db()
    conn.execute("INSERT INTO movimientos (fecha, concepto, categoria, tipo, monto, metodo_pago) VALUES (?,?,?,?,?,?)",
                 (str(f), c, cat, t, m, met))
    conn.commit()
    conn.close()
    update_billetera_delta(met, m)

# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
cfg = get_cfg()
ingreso_sem = cfg.get("ingreso_semanal", 3200.0)
pct_ahorro = cfg.get("porcentaje_ahorro", 10.0)
esencial_sem = cfg.get("gasto_esencial_semanal", 1000.0)

billetera = get_billetera()
saldo_banco = billetera.get("Banco", 2200.0)
saldo_efectivo = billetera.get("Efectivo", 800.0)

with st.sidebar:
    st.title("⚙️ Configuración")
    nuevo_ingreso = st.number_input("Ingreso Semanal Neto (MXN):", min_value=0.0, value=float(ingreso_sem), step=100.0)
    nuevo_pct = st.slider("Meta de Ahorro Preventivo (%):", min_value=0, max_value=30, value=int(pct_ahorro), step=1)
    
    if nuevo_ingreso != ingreso_sem or nuevo_pct != pct_ahorro:
        set_cfg("ingreso_semanal", nuevo_ingreso)
        set_cfg("porcentaje_ahorro", nuevo_pct)
        st.rerun()

    st.markdown("---")
    menu = st.radio(
        "Menú de Navegación:",
        ["Dashboard", "Mi Billetera", "Registro Rápido", "Asesor de Pagos", "Deudas"],
        index=0
    )
    st.markdown("---")
    st.caption(f"🏦 Banco: ${saldo_banco:,.2f} | 💵 Efectivo: ${saldo_efectivo:,.2f}")

# ---------------------------------------------------------
# VISTA 1: DASHBOARD
# ---------------------------------------------------------
if menu == "Dashboard":
    st.title("🎯 Tu Panel Financiero Personal")
    
    df_deudas = get_deudas()
    df_movs = get_movimientos()
    
    total_deuda = df_deudas['saldo'].sum()
    minimos_totales = df_deudas['pago_minimo'].sum()
    minimos_semana = minimos_totales / 4.0
    ahorro_meta = nuevo_ingreso * (nuevo_pct / 100.0)
    
    gastos_variables = 0.0
    gastos_hormiga = 0.0
    if not df_movs.empty:
        df_movs['fecha_dt'] = pd.to_datetime(df_movs['fecha'])
        hace_7 = pd.to_datetime(date.today() - datetime.timedelta(days=7))
        movs_7 = df_movs[df_movs['fecha_dt'] >= hace_7]
        gastos_variables = movs_7[movs_7['tipo'] == 'Variable']['monto'].sum()
        gastos_hormiga = movs_7[movs_7['categoria'] == 'Gasto Hormiga']['monto'].sum()
        
    dinero_libre = max(0.0, nuevo_ingreso - ahorro_meta - minimos_semana - esencial_sem - gastos_variables)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="💵 Ingreso Semanal", value=f"${nuevo_ingreso:,.2f}")
    with c2:
        st.metric(label="💡 ¿Cuánto puedes gastar?", value=f"${dinero_libre:,.2f}", delta="↑ Libre tras mínimos y ahorro")
    with c3:
        st.metric(label="🛡️ Ahorro Sugerido/Semana", value=f"${ahorro_meta:,.2f}", delta=f"{nuevo_pct:.0f}% regla inicial")
    with c4:
        st.metric(label="🚨 Deuda Total Acumulada", value=f"${total_deuda:,.2f}", delta=f"${minimos_totales:,.2f} mínimos/mes", delta_color="inverse")

    st.markdown("### 🔥 Alerta de Intereses y Prioridades")
    st.markdown(f"""
    <div class="alert-card">
        <b>⚠️ Atención con BBVA ($18,509.15) y Ualá ($6,995.34):</b> Son tus cuentas más pesadas. 
        El plan es cubrir los mínimos de las demás tarjetas (incluyendo tus MSI de Mercado Pago de $815.82) para evitar comisiones, 
        e inyectar cualquier excedente de tu sueldo semanal directo a BBVA o a liquidar la cuenta más chica primero.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Distribución de tus Deudas por Entidad")
        st.bar_chart(df_deudas.set_index("acreedor")['saldo'])
    with col2:
        st.subheader("⚡ Control de Gastos Hormiga")
        st.markdown(f"""
        <div class="hormiga-card">
            <b>Tus gustos de fin de semana (Monster, tacos, salidas) deben salir estrictamente del dinero libre calculado arriba (${dinero_libre:,.2f}), jamás usando crédito.</b><br><br>
            • <b>Gasto hormiga últimos 7 días:</b> ${gastos_hormiga:,.2f} MXN<br>
            • <b>Costo mensual proyectado:</b> ${(gastos_hormiga * 4.33):,.2f} MXN<br>
            • <b>Costo anual proyectado:</b> ${(gastos_hormiga * 52):,.2f} MXN<br><br>
            <i>💡 Si reduces a la mitad este gasto, liberas dinero suficiente para liquidar Stori o DiDi por completo en un mes.</i>
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------
# VISTA 2: MI BILLETERA
# ---------------------------------------------------------
elif menu == "Mi Billetera":
    st.title("👛 Estado de Liquidez Real (Mi Billetera)")
    st.caption("Controla el dinero que tienes físicamente en tu cuenta de banco y en tu cartera.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🏦 Banco / Tarjeta Débito", f"${saldo_banco:,.2f} MXN")
    with col2:
        st.metric("💵 Dinero en Efectivo", f"${saldo_efectivo:,.2f} MXN")
    with col3:
        st.metric("💰 Dinero Físico Total", f"${(saldo_banco + saldo_efectivo):,.2f} MXN")

    st.markdown("---")
    st.subheader("✏️ Ajustar Saldos Actuales de Billetera")
    with st.form("form_billetera"):
        c1, c2 = st.columns(2)
        with c1:
            nb = st.number_input("Saldo en Banco ($):", min_value=0.0, value=float(saldo_banco), step=50.0)
        with c2:
            ne = st.number_input("Saldo en Efectivo ($):", min_value=0.0, value=float(saldo_efectivo), step=50.0)
        if st.form_submit_button("Guardar Cambios de Billetera", use_container_width=True):
            set_billetera(nb, ne)
            st.success("¡Billetera actualizada!")
            st.rerun()

# ---------------------------------------------------------
# VISTA 3: REGISTRO RÁPIDO
# ---------------------------------------------------------
elif menu == "Registro Rápido":
    st.title("⚡ Registro Rápido de Movimientos")
    st.caption("Cada gasto se descuenta automáticamente de tu Banco o Efectivo según el método elegido.")
    
    with st.form("form_reg", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            f_fecha = st.date_input("Fecha:", value=date.today())
            f_concepto = st.text_input("Concepto:", placeholder="Ej: Monster, Tacos, Gasolina, Pago BBVA")
            f_monto = st.number_input("Monto ($ MXN):", min_value=0.0, step=10.0)
        with c2:
            f_cat = st.selectbox("Categoría:", [
                "Gasto Hormiga", "Comida / Salidas", "Transporte / Gasolina / Moto",
                "Gimnasio", "Abono a Deuda", "Ahorro", "Otros"
            ])
            f_tipo = st.selectbox("Tipo:", ["Variable", "Fijo", "Deuda", "Ahorro"])
            f_metodo = st.selectbox("¿De dónde salió el dinero?", ["Banco / Tarjeta Débito", "Efectivo", "Tarjeta de Crédito"])
            
        if st.form_submit_button("💾 Guardar y Descontar de Billetera", use_container_width=True):
            if f_concepto.strip() and f_monto > 0:
                add_movimiento(f_fecha, f_concepto, f_cat, f_tipo, f_monto, f_metodo)
                st.success(f"✅ Registrado: {f_concepto} por ${f_monto:,.2f}. Saldo actualizado.")
                st.rerun()
            else:
                st.error("Por favor completa concepto y monto.")

# ---------------------------------------------------------
# VISTA 4: ASESOR DE PAGOS
# ---------------------------------------------------------
elif menu == "Asesor de Pagos":
    st.title("🎯 Asesor Inteligente: ¿Qué pagar primero esta semana?")
    st.caption("Plan táctico semanal para liquidar deudas con tu dinero real sin quedarte sin comida ni bicicletear.")
    
    df_deudas = get_deudas()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("💰 Dinero Disponible Hoy", f"${(saldo_banco + saldo_efectivo):,.2f} MXN")
    with c2:
        st.metric("🛡️ Reserva de Comida/Gasolina", f"${esencial_sem:,.2f} MXN")
    with c3:
        disponible_abonos = max(0.0, (saldo_banco + saldo_efectivo) - esencial_sem)
        st.metric("⚔️ Dinero Real para Deudas", f"${disponible_abonos:,.2f} MXN")

    st.markdown("---")
    metodo = st.radio("Estrategia de Ataque:", ["🎯 Bola de Nieve (Liquidar primero la cuenta más chica)", "🔥 Avalancha (Ahorrar en intereses)"])
    
    if "Bola de Nieve" in metodo:
        df_ord = df_deudas.sort_values(by="saldo", ascending=True).copy()
        criterio = "menor saldo actual para eliminarla rápido y tacharla de tu lista"
    else:
        df_ord = df_deudas.sort_values(by="tasa_cat", ascending=False).copy()
        criterio = "mayor tasa de interés/CAT para evitar cobros sobrecargados"
        
    target = df_ord.iloc[0]
    
    st.info(f"""
    ### 🥊 Plan de Acción Inmediato:
    1. **Protege tus ${esencial_sem:,.2f} MXN:** Déjalos apartados para tus comidas y transporte de la semana. **No los toques para tarjetas.**
    2. **Cubre los mínimos indispensables:** Paga el mínimo de todas las tarjetas para evitar comisiones por mora o intereses moratorios (incluyendo tus MSI de Mercado Pago).
    3. **FOCO DE ATAQUE PRINCIPAL: `{target['acreedor'].upper()}`**
       * Saldo: **${target['saldo']:,.2f} MXN** | Pago mínimo: **${target['pago_minimo']:,.2f} MXN**
       * Motivo: Es tu cuenta con {criterio}.
       * Todo dinero extra de tu sueldo semanal debe abonarse directo a capital de **{target['acreedor']}**.
    4. **Freno total al bicicleteo:** Si una semana no completas para liquidar una tarjeta, paga únicamente el mínimo de tu propio dinero. **No saques dinero de otra para pagar.**
    """)
    
    st.subheader("📋 Orden de Liquidación Sugerido:")
    st.dataframe(
        df_ord[['acreedor', 'saldo', 'pago_minimo', 'tasa_cat', 'dia_corte', 'tipo_cuenta']],
        column_config={
            "acreedor": "Cuenta / Tarjeta",
            "saldo": st.column_config.NumberColumn("Saldo Actual", format="$%.2f MXN"),
            "pago_minimo": st.column_config.NumberColumn("Pago Mínimo", format="$%.2f MXN"),
            "tasa_cat": st.column_config.NumberColumn("CAT %", format="%.1f%%"),
            "dia_corte": st.column_config.NumberColumn("Día Límite", format="Día %d"),
            "tipo_cuenta": "Tipo"
        },
        use_container_width=True,
        hide_index=True
    )

# ---------------------------------------------------------
# VISTA 5: DEUDAS
# ---------------------------------------------------------
elif menu == "Deudas":
    st.title("💳 Administrar Saldos de Deudas")
    st.caption("Actualiza aquí los saldos cada vez que des un abono:")
    
    df_deudas = get_deudas()
    c_sel = st.selectbox("Selecciona la cuenta:", df_deudas['acreedor'])
    fila_d = df_deudas[df_deudas['acreedor'] == c_sel].iloc[0]
    
    with st.form("form_edit_deuda"):
        c1, c2 = st.columns(2)
        with c1:
            ns = st.number_input("Saldo Total Actual ($):", value=float(fila_d['saldo']), step=50.0)
            nm = st.number_input("Pago Mínimo ($):", value=float(fila_d['pago_minimo']), step=20.0)
        with c2:
            nc = st.number_input("Tasa CAT (%):", value=float(fila_d['tasa_cat']), step=1.0)
            nd = st.number_input("Día de Pago (1-31):", min_value=1, max_value=31, value=int(fila_d['dia_corte']))
        if st.form_submit_button("Guardar Cambios de la Cuenta", use_container_width=True):
            update_deuda_val(int(fila_d['id']), ns, nm, nc, nd)
            st.success(f"¡{c_sel} actualizada!")
            st.rerun()
