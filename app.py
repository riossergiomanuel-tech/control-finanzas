import streamlit as st
import pandas as pd
import sqlite3
import datetime
from datetime import date, timedelta

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
# ESTILOS FINTECH
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
        margin-bottom: 20px;
        font-size: 15px;
        line-height: 1.5;
    }
    .vencimiento-card {
        background-color: #261313;
        border: 1px solid #f85149;
        border-radius: 10px;
        padding: 16px 20px;
        color: #f0f6fc;
        margin-bottom: 20px;
    }
    .freedom-card {
        background-color: #0d2119;
        border: 1px solid #2ea043;
        border-radius: 10px;
        padding: 18px 22px;
        color: #f0f6fc;
        margin-bottom: 20px;
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
    c.execute("""CREATE TABLE IF NOT EXISTS movimientos_ahorro (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        fecha TEXT, 
        tipo TEXT, 
        monto REAL, 
        origen_destino TEXT, 
        motivo TEXT)
    """)
    
    # Migración segura
    cols_d = [r[1] for r in c.execute("PRAGMA table_info(deudas)").fetchall()]
    if "fecha_corte" in cols_d and "dia_corte" not in cols_d:
        try: c.execute("ALTER TABLE deudas ADD COLUMN dia_corte INTEGER DEFAULT 15")
        except: pass
    if "tipo_cuenta" not in cols_d:
        try: c.execute("ALTER TABLE deudas ADD COLUMN tipo_cuenta TEXT DEFAULT 'Tarjeta Crédito'")
        except: pass

    defaults = [
        ('ingreso_base', 3200.0),
        ('horas_extras_semana', 0.0),
        ('descuentos_semana', 0.0),
        ('porcentaje_ahorro', 10.0),
        ('gasto_esencial_semanal', 1000.0),
        ('fondo_ahorro_acumulado', 320.0),
        ('presupuesto_hormiga_semanal', 400.0)
    ]
    for k, v in defaults:
        c.execute("INSERT OR IGNORE INTO configuracion VALUES (?, ?)", (k, v))
        
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
        try:
            c.executemany("INSERT INTO deudas (acreedor, saldo, pago_minimo, tasa_cat, dia_corte, tipo_cuenta) VALUES (?,?,?,?,?,?)", deudas)
        except:
            pass

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

def update_billetera_delta(metodo, monto, operacion="restar"):
    conn = get_db()
    target = "Banco" if ("Banco" in metodo or "Tarjeta" in metodo or "Transferencia" in metodo) else "Efectivo"
    signo = "-" if operacion == "restar" else "+"
    conn.execute(f"UPDATE billetera SET saldo = saldo {signo} ? WHERE metodo = ?", (monto, target))
    conn.commit()
    conn.close()

def get_ahorro_semana():
    conn = get_db()
    hace_7 = str(date.today() - timedelta(days=7))
    df = pd.read_sql_query("SELECT * FROM movimientos_ahorro WHERE fecha >= ?", conn, params=(hace_7,))
    conn.close()
    aportes = df[df['tipo'] == 'Aporte']['monto'].sum() if not df.empty else 0.0
    retiros = df[df['tipo'] == 'Retiro']['monto'].sum() if not df.empty else 0.0
    return aportes - retiros

def add_movimiento_ahorro(tipo, monto, origen_destino, motivo):
    conn = get_db()
    hoy = str(date.today())
    conn.execute("INSERT INTO movimientos_ahorro (fecha, tipo, monto, origen_destino, motivo) VALUES (?,?,?,?,?)",
                 (hoy, tipo, monto, origen_destino, motivo))
    if tipo == "Aporte":
        conn.execute("UPDATE configuracion SET valor = valor + ? WHERE clave = 'fondo_ahorro_acumulado'", (monto,))
        conn.commit()
        conn.close()
        update_billetera_delta(origen_destino, monto, "restar")
    else:
        conn.execute("UPDATE configuracion SET valor = valor - ? WHERE clave = 'fondo_ahorro_acumulado'", (monto,))
        conn.commit()
        conn.close()
        update_billetera_delta(origen_destino, monto, "sumar")

def get_movimientos_ahorro():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM movimientos_ahorro ORDER BY id DESC", conn)
    conn.close()
    return df

def get_deudas():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM deudas WHERE activa=1", conn)
    conn.close()
    if "dia_corte" not in df.columns:
        if "fecha_corte" in df.columns:
            df["dia_corte"] = pd.to_numeric(df["fecha_corte"].astype(str).str.extract(r"(\d+)")[0], errors="coerce").fillna(15).astype(int)
        else:
            df["dia_corte"] = 15
    if "tipo_cuenta" not in df.columns:
        df["tipo_cuenta"] = "Tarjeta Crédito"
    return df

def save_edited_deudas(edited_df):
    conn = get_db()
    for _, row in edited_df.iterrows():
        conn.execute("""
            UPDATE deudas 
            SET saldo = ?, pago_minimo = ?, dia_corte = ?, tasa_cat = ?
            WHERE acreedor = ?
        """, (
            float(row['Saldo Total ($)']),
            float(row['Pago Mínimo ($)']),
            int(row['Día de Pago (1-31)']),
            float(row.get('CAT (%)', 50.0)),
            row['Cuenta']
        ))
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
    update_billetera_delta(met, m, "restar")

# ---------------------------------------------------------
# BARRA LATERAL (SUELDO VARIABLE Y BILLETERA)
# ---------------------------------------------------------
cfg = get_cfg()
ingreso_base = cfg.get("ingreso_base", 3200.0)
horas_extras = cfg.get("horas_extras_semana", 0.0)
descuentos = cfg.get("descuentos_semana", 0.0)
pct_ahorro = cfg.get("porcentaje_ahorro", 10.0)
reserva_esencial = cfg.get("gasto_esencial_semanal", 1000.0)
presupuesto_hormiga = cfg.get("presupuesto_hormiga_semanal", 400.0)
fondo_ahorro_total = cfg.get("fondo_ahorro_acumulado", 320.0)

ingreso_neto_semana = max(0.0, ingreso_base + horas_extras - descuentos)

billetera = get_billetera()
saldo_banco = billetera.get("Banco", 2200.0)
saldo_efectivo = billetera.get("Efectivo", 800.0)

with st.sidebar:
    st.title("⚙️ Sueldo de Esta Semana")
    nuevo_base = st.number_input("Sueldo Base ($):", min_value=0.0, value=float(ingreso_base), step=100.0)
    
    c_side1, c_side2 = st.columns(2)
    with c_side1:
        nuevas_extras = st.number_input("➕ Horas Extras:", min_value=0.0, value=float(horas_extras), step=50.0)
    with c_side2:
        nuevos_descuentos = st.number_input("➖ Faltas/Salud:", min_value=0.0, value=float(descuentos), step=50.0)
        
    calc_neto = max(0.0, nuevo_base + nuevas_extras - nuevos_descuentos)
    st.metric("💵 Total Esta Semana", f"${calc_neto:,.2f} MXN")
    
    nuevo_pct = st.slider("Meta Ahorro (%):", min_value=0, max_value=30, value=int(pct_ahorro), step=1)
    nuevo_tope_hormiga = st.number_input("Tope Gastos Hormiga ($):", min_value=50.0, value=float(presupuesto_hormiga), step=50.0)
    
    if (nuevo_base != ingreso_base or nuevas_extras != horas_extras or 
        nuevos_descuentos != descuentos or nuevo_pct != pct_ahorro or 
        nuevo_tope_hormiga != presupuesto_hormiga):
        set_cfg("ingreso_base", nuevo_base)
        set_cfg("horas_extras_semana", nuevas_extras)
        set_cfg("descuentos_semana", nuevos_descuentos)
        set_cfg("porcentaje_ahorro", nuevo_pct)
        set_cfg("presupuesto_hormiga_semanal", nuevo_tope_hormiga)
        st.rerun()

    st.markdown("---")
    menu = st.radio(
        "Navegación:",
        ["Dashboard", "💎 Fondo de Ahorro", "📅 Vencimientos y Fechas", "Mi Billetera", "Registro Rápido", "Asesor de Pagos", "Deudas"],
        index=0
    )
    st.markdown("---")
    st.caption(f"🏦 Banco: ${saldo_banco:,.2f} | 💵 Efectivo: ${saldo_efectivo:,.2f}")
    st.caption(f"💎 Fondo Guardado: ${fondo_ahorro_total:,.2f}")

# ---------------------------------------------------------
# VISTA 1: DASHBOARD
# ---------------------------------------------------------
if menu == "Dashboard":
    st.title("🎯 Tu Panel Financiero Personal")
    
    df_deudas = get_deudas()
    df_movs = get_movimientos()
    hoy = date.today()
    
    total_deuda = df_deudas['saldo'].sum()
    minimos_totales = df_deudas['pago_minimo'].sum()
    minimos_semana = minimos_totales / 4.0
    ahorro_meta = ingreso_neto_semana * (pct_ahorro / 100.0)
    ahorrado_esta_semana = get_ahorro_semana()
    
    gastos_variables = 0.0
    gastos_hormiga = 0.0
    if not df_movs.empty:
        df_movs['fecha_dt'] = pd.to_datetime(df_movs['fecha'])
        hace_7 = pd.to_datetime(hoy - timedelta(days=7))
        movs_7 = df_movs[df_movs['fecha_dt'] >= hace_7]
        gastos_variables = movs_7[movs_7['tipo'] == 'Variable']['monto'].sum()
        gastos_hormiga = movs_7[movs_7['categoria'] == 'Gasto Hormiga']['monto'].sum()
        
    dinero_libre = max(0.0, ingreso_neto_semana - ahorro_meta - minimos_semana - reserva_esencial - gastos_variables)

    # 4 TARJETAS KPI
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(label="💵 Ingreso Esta Semana", value=f"${ingreso_neto_semana:,.2f}", delta=f"Base: ${ingreso_base:,.2f}")
    with c2:
        st.metric(label="💡 ¿Cuánto puedes gastar?", value=f"${dinero_libre:,.2f}", delta="↑ Libre tras mínimos y ahorro")
    with c3:
        if (ahorrado_esta_semana >= ahorro_meta and ahorro_meta > 0) or fondo_ahorro_total >= ahorro_meta:
            st.metric(label="💎 Ahorro Semanal", value=f"${ahorro_meta:,.2f}", delta="✅ ¡Meta Cumplida!")
        else:
            falta = max(0.0, ahorro_meta - ahorrado_esta_semana)
            st.metric(label="💎 Ahorro Sugerido", value=f"${ahorro_meta:,.2f}", delta=f"Faltan ${falta:,.2f}", delta_color="inverse")
    with c4:
        st.metric(label="🚨 Deuda Total Acumulada", value=f"${total_deuda:,.2f}", delta=f"${minimos_totales:,.2f} mínimos/mes", delta_color="inverse")

    # ALERTA DE VENCIMIENTOS SEMANALES
    proximos_7_dias = [(hoy + timedelta(days=i)).day for i in range(8)]
    vencimientos_semana = []
    total_minimos_semana = 0.0
    for _, r in df_deudas.iterrows():
        dia_c = int(r.get('dia_corte', 15))
        if dia_c in proximos_7_dias:
            vencimientos_semana.append(f"• **{r['acreedor']}**: ${r['pago_minimo']:,.2f} MXN (Día {dia_c})")
            total_minimos_semana += r['pago_minimo']

    if vencimientos_semana:
        st.markdown(f"""
        <div class="vencimiento-card">
            <h4>📅 ¡Atención! Deudas que vencen en los próximos 7 días:</h4>
            {'<br>'.join(vencimientos_semana)}<br><br>
            <b>Total a apartar de este sueldo para estos pagos:</b> ${total_minimos_semana:,.2f} MXN
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="freedom-card">
            <b>📅 Vencimientos Semanales:</b> No tienes tarjetas que venzan en los próximos 7 días. ¡Buen momento para avanzar en abonos a capital!
        </div>
        """, unsafe_allow_html=True)

    # PROYECCIÓN DE LIBERTAD FINANCIERA
    pago_semanal_estimado = max(200.0, minimos_semana + dinero_libre * 0.5)
    semanas_libertad = int(total_deuda / pago_semanal_estimado) if pago_semanal_estimado > 0 else 52
    fecha_libertad = hoy + timedelta(weeks=semanas_libertad)
    meses_libertad = round(semanas_libertad / 4.33, 1)

    st.markdown(f"""
    <div class="freedom-card">
        <h3>⏳ Proyección de Libertad Financiera (Deuda Cero)</h3>
        Con tu plan de abonos y frenando el bicicleteo, se proyecta liquidar tus $40,497.48 en aproximadamente <b>{semanas_libertad} semanas (~{meses_libertad} meses)</b>.<br>
        🎯 <b>Fecha estimada en que quedarás en $0 de deuda:</b> <u>{fecha_libertad.strftime('%d de %B de %Y')}</u>.
    </div>
    """, unsafe_allow_html=True)

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.subheader("📊 Distribución de tus Deudas por Entidad")
        st.bar_chart(df_deudas.set_index("acreedor")['saldo'])
    with col_g2:
        st.subheader("⚡ Semáforo de Gastos Hormiga")
        pct_hormiga = min(1.0, float(gastos_hormiga / presupuesto_hormiga)) if presupuesto_hormiga > 0 else 0.0
        st.progress(pct_hormiga)
        
        if gastos_hormiga < presupuesto_hormiga * 0.7:
            estado_semaforo = f"🟢 <b>Semáforo Verde:</b> Vas excelente. Has gastado ${gastos_hormiga:,.2f} de ${presupuesto_hormiga:,.2f}. Te quedan <b>${(presupuesto_hormiga - gastos_hormiga):,.2f}</b> para el fin de semana."
        elif gastos_hormiga < presupuesto_hormiga:
            estado_semaforo = f"🟡 <b>Semáforo Amarillo:</b> Precaución. Has gastado ${gastos_hormiga:,.2f} de ${presupuesto_hormiga:,.2f}. Te quedan solo <b>${(presupuesto_hormiga - gastos_hormiga):,.2f}</b>."
        else:
            estado_semaforo = f"🔴 <b>Semáforo Rojo:</b> ¡Tope alcanzado! Has gastado ${gastos_hormiga:,.2f} de ${presupuesto_hormiga:,.2f}. Detén los antojos hasta el siguiente cobro."

        st.markdown(f"""
        <div class="hormiga-card">
            {estado_semaforo}<br><br>
            • <b>Gasto hormiga últimos 7 días:</b> ${gastos_hormiga:,.2f} MXN<br>
            • <b>Proyección mensual:</b> ${(gastos_hormiga * 4.33):,.2f} MXN<br>
            • <b>Proyección anual:</b> ${(gastos_hormiga * 52):,.2f} MXN
        </div>
        """, unsafe_allow_html=True)

# ---------------------------------------------------------
# VISTA 2: FONDO DE AHORRO
# ---------------------------------------------------------
elif menu == "💎 Fondo de Ahorro":
    st.title("💎 Mi Fondo de Ahorro (Dinero Guardado)")
    st.caption("Administra tu alcancía digital intocable. Cada peso apartado o retirado queda registrado.")
    
    ahorro_meta_sem = ingreso_neto_semana * (pct_ahorro / 100.0)
    ahorrado_esta_semana = get_ahorro_semana()

    col_ah1, col_ah2, col_ah3 = st.columns(3)
    with col_ah1:
        st.metric("🏦 Total Guardado Acumulado", f"${fondo_ahorro_total:,.2f} MXN")
    with col_ah2:
        st.metric("🎯 Meta de Ahorro Esta Semana", f"${ahorro_meta_sem:,.2f} MXN")
    with col_ah3:
        if (ahorrado_esta_semana >= ahorro_meta_sem and ahorro_meta_sem > 0) or fondo_ahorro_total >= ahorro_meta_sem:
            st.metric("Estado de la Semana", "¡Cumplida! 🎉", delta=f"${ahorrado_esta_semana:,.2f} aportados")
        else:
            diff = max(0.0, ahorro_meta_sem - ahorrado_esta_semana)
            st.metric("Estado de la Semana", f"Pendiente ${diff:,.2f}", delta="Aún no guardado", delta_color="inverse")

    st.markdown("---")
    t_aporte, t_retiro = st.tabs(["🟢 Guardar Dinero (Aportar)", "🔴 Retirar Dinero (Emergencia)"])
    
    with t_aporte:
        st.subheader("➕ Apartar Dinero para mi Fondo")
        with st.form("form_aportar"):
            col_ap1, col_ap2 = st.columns(2)
            with col_ap1:
                monto_aporte = st.number_input("Monto a guardar ($ MXN):", min_value=0.0, value=float(ahorro_meta_sem), step=50.0)
                origen_aporte = st.selectbox("¿De dónde sale el dinero?", ["Banco / Débito", "Efectivo"])
            with col_ap2:
                motivo_aporte = st.text_input("Motivo / Etiqueta:", value="Ahorro semanal (Págate a ti primero)")
                
            if st.form_submit_button("💎 Confirmar y Guardar Dinero", use_container_width=True):
                if monto_aporte > 0:
                    add_movimiento_ahorro("Aporte", monto_aporte, origen_aporte, motivo_aporte)
                    st.success(f"✅ ¡Excelente! Guardaste ${monto_aporte:,.2f} MXN. Se descontaron de tu {origen_aporte}.")
                    st.rerun()
                else:
                    st.error("Ingresa un monto mayor a cero.")
                    
    with t_retiro:
        st.subheader("➖ Retirar Dinero de mi Fondo por Emergencia")
        with st.form("form_retirar"):
            col_ret1, col_ret2 = st.columns(2)
            with col_ret1:
                monto_retiro = st.number_input("Monto a retirar ($ MXN):", min_value=0.0, max_value=float(max(0.0, fondo_ahorro_total)), step=50.0)
                destino_retiro = st.selectbox("¿A dónde entra el dinero?", ["Banco / Débito", "Efectivo"])
            with col_ret2:
                motivo_retiro = st.text_input("Motivo de la emergencia:", placeholder="Ej: Compra de medicamento, imprevisto moto")
                
            if st.form_submit_button("⚠️ Confirmar Retiro de Ahorro", use_container_width=True):
                if 0 < monto_retiro <= fondo_ahorro_total:
                    add_movimiento_ahorro("Retiro", monto_retiro, destino_retiro, motivo_retiro)
                    st.warning(f"Se retiraron ${monto_retiro:,.2f} MXN de tu Fondo. Se sumaron a tu {destino_retiro}.")
                    st.rerun()
                else:
                    st.error("Monto inválido o superior al fondo disponible.")

    st.markdown("---")
    st.subheader("📜 Historial de Movimientos de Ahorro")
    df_ah = get_movimientos_ahorro()
    if not df_ah.empty:
        st.dataframe(
            df_ah[['fecha', 'tipo', 'monto', 'origen_destino', 'motivo']],
            column_config={
                "fecha": "Fecha",
                "tipo": "Tipo",
                "monto": st.column_config.NumberColumn("Monto", format="$%.2f MXN"),
                "origen_destino": "Cuenta",
                "motivo": "Motivo / Descripción"
            },
            use_container_width=True,
            hide_index=True
        )

# ---------------------------------------------------------
# VISTA 3: TABLA EDITABLE DIRECTA (VENCIMIENTOS Y FECHAS)
# ---------------------------------------------------------
elif menu == "📅 Vencimientos y Fechas":
    st.title("📅 Calendario y Edición Directa de Fechas")
    st.caption("✏️ Haz doble clic en cualquier celda para cambiar el día de corte, saldo o pago mínimo como en Excel, y presiona el botón verde:")
    
    df_deudas = get_deudas()
    
    # Tabla editable directa
    tabla_editable = pd.DataFrame({
        "Cuenta": df_deudas['acreedor'],
        "Día de Pago (1-31)": df_deudas['dia_corte'].astype(int),
        "Pago Mínimo ($)": df_deudas['pago_minimo'].astype(float),
        "Saldo Total ($)": df_deudas['saldo'].astype(float),
        "CAT (%)": df_deudas['tasa_cat'].astype(float)
    })
    
    cambios_df = st.data_editor(
        tabla_editable,
        column_config={
            "Cuenta": st.column_config.TextColumn("Cuenta / Tarjeta", disabled=True),
            "Día de Pago (1-31)": st.column_config.NumberColumn("Día de Pago (1-31)", min_value=1, max_value=31, step=1, help="Día del mes en que vence"),
            "Pago Mínimo ($)": st.column_config.NumberColumn("Pago Mínimo ($)", format="$%.2f", min_value=0.0, step=20.0),
            "Saldo Total ($)": st.column_config.NumberColumn("Saldo Total ($)", format="$%.2f", min_value=0.0, step=50.0),
            "CAT (%)": st.column_config.NumberColumn("Tasa CAT (%)", min_value=0.0, step=1.0)
        },
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("💾 Guardar Todas las Fechas y Montos Modificados", use_container_width=True):
        save_edited_deudas(cambios_df)
        st.success("✅ ¡Todas las fechas, saldos y pagos mínimos se guardaron exitosamente en tu base de datos!")
        st.rerun()

    st.markdown("---")
    st.subheader("📆 Recordatorio de Pagos Ordenados por Urgencia:")
    hoy = date.today()
    dia_actual = hoy.day
    st.write(f"Hoy es **{hoy.strftime('%d/%m/%Y')}** (Día {dia_actual} del mes)")
    
    pagos_lista = []
    for _, r in df_deudas.iterrows():
        dia_pago = int(r.get('dia_corte', 15))
        dias_para_pago = dia_pago - dia_actual if dia_pago >= dia_actual else (30 - dia_actual) + dia_pago
        pagos_lista.append({
            "Cuenta": r['acreedor'],
            "Día Límite": dia_pago,
            "Faltan": dias_para_pago,
            "Pago Mínimo": r['pago_minimo'],
            "Saldo Total": r['saldo']
        })
        
    df_urg = pd.DataFrame(pagos_lista).sort_values(by="Faltan", ascending=True)
    st.dataframe(
        df_urg,
        column_config={
            "Cuenta": "Entidad",
            "Día Límite": st.column_config.NumberColumn("Día de Pago", format="Día %d"),
            "Faltan": st.column_config.NumberColumn("Días Restantes", format="%d días"),
            "Pago Mínimo": st.column_config.NumberColumn("Mínimo a Pagar", format="$%.2f MXN"),
            "Saldo Total": st.column_config.NumberColumn("Saldo Actual", format="$%.2f MXN")
        },
        use_container_width=True,
        hide_index=True
    )

# ---------------------------------------------------------
# VISTA 4: MI BILLETERA
# ---------------------------------------------------------
elif menu == "Mi Billetera":
    st.title("👛 Estado de Liquidez Real (Mi Billetera)")
    st.caption("Dinero disponible en tus cuentas y efectivo para gastos del día a día.")
    
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
# VISTA 5: REGISTRO RÁPIDO
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
                "Gimnasio", "Abono a Deuda", "Otros"
            ])
            f_tipo = st.selectbox("Tipo:", ["Variable", "Fijo", "Deuda"])
            f_metodo = st.selectbox("¿De dónde salió el dinero?", ["Banco / Tarjeta Débito", "Efectivo", "Tarjeta de Crédito"])
            
        if st.form_submit_button("💾 Guardar y Descontar de Billetera", use_container_width=True):
            if f_concepto.strip() and f_monto > 0:
                add_movimiento(f_fecha, f_concepto, f_cat, f_tipo, f_monto, f_metodo)
                st.success(f"✅ Registrado: {f_concepto} por ${f_monto:,.2f}. Saldo actualizado.")
                st.rerun()
            else:
                st.error("Por favor completa concepto y monto.")

# ---------------------------------------------------------
# VISTA 6: ASESOR DE PAGOS
# ---------------------------------------------------------
elif menu == "Asesor de Pagos":
    st.title("🎯 Asesor Inteligente: ¿Qué pagar primero esta semana?")
    st.caption("Plan táctico semanal para liquidar deudas con tu dinero real sin quedarte sin comida ni bicicletear.")
    
    df_deudas = get_deudas()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("💰 Dinero Disponible Hoy", f"${(saldo_banco + saldo_efectivo):,.2f} MXN")
    with c2:
        st.metric("🛡️ Reserva de Comida/Gasolina", f"${reserva_esencial:,.2f} MXN")
    with c3:
        disponible_abonos = max(0.0, (saldo_banco + saldo_efectivo) - reserva_esencial)
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
    1. **Protege tus ${reserva_esencial:,.2f} MXN:** Déjalos apartados para tus comidas y transporte de la semana. **No los toques para tarjetas.**
    2. **Cubre los mínimos indispensables:** Paga el mínimo de todas las tarjetas para evitar comisiones por mora o intereses moratorios (incluyendo tus MSI de Mercado Pago).
    3. **FOCO DE ATAQUE PRINCIPAL: `{target['acreedor'].upper()}`**
       * Saldo: **${target['saldo']:,.2f} MXN** | Pago mínimo: **${target['pago_minimo']:,.2f} MXN**
       * Motivo: Es tu cuenta con {criterio}.
       * Todo dinero extra de tu sueldo semanal debe abonarse directo a capital de **{target['acreedor']}**.
    4. **Freno total al bicicleteo:** Si una semana no completas para liquidar una tarjeta, paga únicamente el mínimo de tu propio dinero. **No saques dinero de otra para pagar.**
    """)

# ---------------------------------------------------------
# VISTA 7: DEUDAS Y RESPALDO EXCEL/CSV
# ---------------------------------------------------------
elif menu == "Deudas":
    st.title("💳 Administrar Saldos y Fechas de Deudas")
    st.caption("Actualiza aquí las fechas y saldos de cada cuenta o descarga tu respaldo:")
    
    df_deudas = get_deudas()
    c_sel = st.selectbox("Selecciona la cuenta que quieres modificar:", df_deudas['acreedor'])
    fila_d = df_deudas[df_deudas['acreedor'] == c_sel].iloc[0]
    
    dia_val = int(fila_d.get('dia_corte', 15))
    saldo_val = float(fila_d.get('saldo', 0.0))
    pago_min_val = float(fila_d.get('pago_minimo', 0.0))
    cat_val = float(fila_d.get('tasa_cat', 0.0))
    
    with st.form("form_edit_deuda"):
        c1, c2 = st.columns(2)
        with c1:
            ns = st.number_input("Saldo Total Actual ($):", value=saldo_val, step=50.0)
            nm = st.number_input("Pago Mínimo ($):", value=pago_min_val, step=20.0)
        with c2:
            nc = st.number_input("Tasa CAT (%):", value=cat_val, step=1.0)
            nd = st.number_input("Día de Pago Límite del Mes (1-31):", min_value=1, max_value=31, value=dia_val)
        if st.form_submit_button("Guardar Cambios de la Cuenta", use_container_width=True):
            conn = get_db()
            conn.execute("UPDATE deudas SET saldo=?, pago_minimo=?, tasa_cat=?, dia_corte=? WHERE id=?", (ns, nm, nc, nd, int(fila_d['id'])))
            conn.commit()
            conn.close()
            st.success(f"¡{c_sel} actualizada correctamente!")
            st.rerun()

    st.markdown("---")
    st.subheader("📥 Respaldo de Seguridad")
    csv_deudas = df_deudas.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Respaldo de Mis Deudas en Excel/CSV",
        data=csv_deudas,
        file_name=f"deudas_{date.today()}.csv",
        mime="text/csv",
        use_container_width=True
    )
