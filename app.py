import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# Configuración de página
st.set_page_config(
    page_title="Control Financiero Personal",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo visual moderno y limpio (Modo Oscuro tipo app financiera)
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #fafafa; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# Configuración de Base de Datos SQLite Local
def init_db():
    conn = sqlite3.connect('finanzas_user.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Tabla de Movimientos / Gastos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            concepto TEXT,
            categoria TEXT,
            monto REAL,
            tipo TEXT
        )
    ''')
    
    # Tabla de Deudas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS deudas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            acreedor TEXT,
            saldo_total REAL,
            pago_minimo REAL,
            tasa_interes TEXT,
            prioridad TEXT
        )
    ''')
    
    # Verificar si la tabla está vacía para insertar tus datos reales corregidos
    cursor.execute('SELECT COUNT(*) FROM deudas')
    if cursor.fetchone()[0] == 0:
        deudas_reales = [
            ('BBVA (Azul)', 18509.15, 1500.0, 'Muy Alta (Intereses pesados)', 'CRÍTICA'),
            ('Ualá', 6995.34, 700.0, 'Alta', 'ALTA'),
            ('Coppel (Monitor/Ropa)', 5051.00, 850.0, 'Alta (Cargos por atraso)', 'ALTA'),
            ('Mercado Pago (MSI)', 2450.00, 815.82, 'Media (Mensualidad fija)', 'MEDIA'),
            ('Stori Card', 1975.00, 400.0, 'Alta', 'MEDIA'),
            ('Vexi', 1016.99, 250.0, 'Alta', 'MEDIA'),
            ('Universidad', 2500.00, 2500.0, 'Fijo Académico', 'CRÍTICA'),
            ('DiDi / Nu', 2000.00, 400.0, 'Variable', 'BAJA')
        ]
        cursor.executemany('INSERT INTO deudas (acreedor, saldo_total, pago_minimo, tasa_interes, prioridad) VALUES (?, ?, ?, ?, ?)', deudas_reales)
        conn.commit()
        
    conn.commit()
    return conn

conn = init_db()
cursor = conn.cursor()

# --- BARRA LATERAL ---
st.sidebar.title("⚙️ Configuración")
sueldo_semanal = st.sidebar.number_input("Ingreso Semanal Neto (MXN)", value=3200.0, step=100.0)
porcentaje_ahorro = st.sidebar.slider("Meta de Ahorro Preventivo (%)", 5, 30, 10)

menu = st.sidebar.selectbox(
    "Menú de Navegación",
    ["📊 Dashboard Principal", "💳 Control y Prioridad de Deudas", "⚡ Registro Rápido de Gastos", "📜 Historial de Movimientos"]
)

# Cálculos base
ahorro_semanal = sueldo_semanal * (porcentaje_ahorro / 100.0)

# Obtener datos de deudas de la BD
df_deudas = pd.read_sql("SELECT * FROM deudas", conn)
total_deuda = df_deudas['saldo_total'].sum()
total_minimos_mensuales = df_deudas['pago_minimo'].sum()
total_minimos_semanales = total_minimos_mensuales / 4.28

# Obtener gastos registrados
try:
    df_movs = pd.read_sql("SELECT * FROM movimientos", conn)
    gasto_total_registrado = df_movs['monto'].sum() if not df_movs.empty else 0.0
except:
    gasto_total_registrado = 0.0

dinero_libre_semanal = sueldo_semanal - ahorro_semanal - total_minimos_semanales

# --- 1. DASHBOARD PRINCIPAL ---
if menu == "📊 Dashboard Principal":
    st.title("🎯 Tu Panel Financiero Personal")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💵 Ingreso Semanal", f"${sueldo_semanal:,.2f}")
    with col2:
        st.metric("💡 ¿Cuánto puedes gastar?", f"${max(0, dinero_libre_semanal):,.2f}", delta="Libre tras mínimos y ahorro")
    with col3:
        st.metric("🛡️ Ahorro Sugerido/Semana", f"${ahorro_semanal:,.2f}")
    with col4:
        st.metric("🚨 Deuda Total Acumulada", f"${total_deuda:,.2f}")

    st.markdown("### 🔥 Alerta de Intereses y Prioridades")
    st.warning("⚠️ **Atención con BBVA ($18,509.15) y Ualá ($6,995.34):** Son tus cuentas más pesadas. El plan es cubrir los mínimos de las demás tarjetas (incluyendo tus MSI de Mercado Pago de $815.82) para evitar comisiones, e inyectar cualquier excedente de tu sueldo semanal directo a BBVA.")

    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("📊 Distribución de tus Deudas por Entidad")
        if not df_deudas.empty:
            st.bar_chart(df_deudas.set_index('acreedor')['saldo_total'])
            
    with col_b:
        st.subheader("⚡ Control de Gastos Hormiga")
        st.info("Tus gustos de fin de semana (Monster, tacos, salidas) deben salir estrictamente del dinero libre calculado arriba, jamás usando crédito.")
        
        monster = st.number_input("Gasto semanal en Monster / Bebidas", value=250.0, step=50.0)
        tacos_fin = st.number_input("Gasto semanal en Tacos / Salidas", value=400.0, step=50.0)
        total_hormiga_mes = (monster + tacos_fin) * 4
        st.write(f"💸 Al mes estás destinando **${total_hormiga_mes:,.2f} MXN** a gastos hormiga. ¡Controlar esto te libera liquidez para bajarle más rápido a BBVA!")

# --- 2. CONTROL Y PRIORIDAD DE DEUDAS ---
elif menu == "💳 Control y Prioridad de Deudas":
    st.title("💳 Matriz de Deudas y Estrategia")
    st.markdown("Tus cuentas con montos reales sincronizados:")
    
    st.dataframe(df_deudas[['acreedor', 'saldo_total', 'pago_minimo', 'tasa_interes', 'prioridad']], use_container_width=True)

    st.markdown("---")
    st.subheader("✏️ Actualizar Saldo o Pago Mínimo")
    
    with st.form("form_actualizar_deuda"):
        cuenta_sel = st.selectbox("Selecciona cuenta", df_deudas['acreedor'].tolist())
        nuevo_saldo = st.number_input("Nuevo Saldo Total (MXN)", value=0.0, step=100.0)
        nuevo_minimo = st.number_input("Nuevo Pago Mínimo / Mensualidad (MXN)", value=0.0, step=50.0)
        
        submit_deuda = st.form_submit_button("Actualizar Cuenta")
        if submit_deuda:
            cursor.execute("UPDATE deudas SET saldo_total = ?, pago_minimo = ? WHERE acreedor = ?", (nuevo_saldo, nuevo_minimo, cuenta_sel))
            conn.commit()
            st.success(f"¡Cuenta {cuenta_sel} actualizada con éxito!")
            st.rerun()

# --- 3. REGISTRO RÁPIDO DE GASTOS ---
elif menu == "⚡ Registro Rápido de Gastos":
    st.title("⚡ Registro Exprés (Optimizado para Celular)")
    st.markdown("Anota tus consumos diarios en segundos.")

    with st.form("form_gasto", clear_on_submit=True):
        fecha = st.date_input("Fecha", datetime.now())
        concepto = st.text_input("Concepto (ej. Tacos, Monster, Gasolina)")
        categoria = st.selectbox("Categoría", ["Gasto Hormiga / Antojo", "Comida / Universidad", "Transporte / DiDi", "Pago de Deuda", "Otro"])
        monto = st.number_input("Monto (MXN)", min_value=0.0, step=10.0)
        tipo = st.selectbox("Tipo de Gasto", ["Variable", "Fijo"])

        submitted = st.form_submit_button("Guardar Movimiento")
        if submitted:
            cursor.execute("INSERT INTO movimientos (fecha, concepto, categoria, monto, tipo) VALUES (?, ?, ?, ?, ?)",
                           (str(fecha), concepto, categoria, monto, tipo))
            conn.commit()
            st.success("¡Gasto guardado correctamente!")

# --- 4. HISTORIAL DE MOVIMIENTOS ---
elif menu == "📜 Historial de Movimientos":
    st.title("📜 Historial de Tus Movimientos")
    if not df_movs.empty:
        st.dataframe(df_movs, use_container_width=True)
        total_gastado = df_movs['monto'].sum()
        st.metric("Total Registrado", f"${total_gastado:,.2f} MXN")
    else:
        st.info("Aún no tienes movimientos registrados. Usa la sección de Registro Rápido.")