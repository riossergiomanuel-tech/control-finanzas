import streamlit as st
import pandas as pd
import sqlite3
import datetime
from datetime import date

# CONFIGURACIÓN
st.set_page_config(page_title="Control Financiero Personal", page_icon="💸", layout="wide")
DB_FILE = "finanzas.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS billetera (metodo TEXT PRIMARY KEY, saldo REAL)")
    cursor.execute("""CREATE TABLE IF NOT EXISTS deudas (
        id INTEGER PRIMARY KEY AUTOINCREMENT, acreedor TEXT UNIQUE, saldo REAL, 
        pago_minimo REAL, tasa_cat REAL, fecha_corte TEXT, activa INTEGER DEFAULT 1)
    """)
    cursor.execute("""CREATE TABLE IF NOT EXISTS movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, concepto TEXT, 
        categoria TEXT, tipo TEXT, monto REAL, metodo_pago TEXT)
    """)
    cursor.execute("INSERT OR IGNORE INTO configuracion VALUES ('ingreso_semanal', 4000.0)")
    cursor.execute("INSERT OR IGNORE INTO configuracion VALUES ('porcentaje_ahorro', 10.0)")
    cursor.execute("INSERT OR IGNORE INTO billetera VALUES ('Efectivo', 1000.0)")
    cursor.execute("INSERT OR IGNORE INTO billetera VALUES ('Banco', 5000.0)")
    if cursor.execute("SELECT COUNT(*) FROM deudas").fetchone()[0] == 0:
        deudas = [
            ("BBVA", 18509.15, 850.0, 48.0, "12"), ("Ualá", 6995.34, 400.0, 70.0, "25"),
            ("Mercado Pago MSI", 815.82, 815.82, 0.0, "20"), ("Nu", 8500.0, 650.0, 52.0, "18"),
            ("Coppel", 5000.0, 500.0, 65.0, "15"), ("DiDi", 3500.0, 700.0, 95.0, "10"),
            ("Vexi", 2800.0, 400.0, 78.0, "28"), ("Stori", 1200.0, 250.0, 99.0, "22")
        ]
        cursor.executemany("INSERT INTO deudas (acreedor, saldo, pago_minimo, tasa_cat, fecha_corte) VALUES (?,?,?,?,?)", deudas)
    conn.commit()
    conn.close()

init_db()

def update_billetera(metodo, monto, operacion="restar"):
    conn = get_db_connection()
    target = "Banco" if "Tarjeta" in metodo or "Transferencia" in metodo else "Efectivo"
    if operacion == "restar":
        conn.execute("UPDATE billetera SET saldo = saldo - ? WHERE metodo = ?", (monto, target))
    else:
        conn.execute("UPDATE billetera SET saldo = saldo + ? WHERE metodo = ?", (monto, target))
    conn.commit()
    conn.close()

menu = st.sidebar.radio("Navegación", ["📊 Dashboard", "👛 Mi Billetera", "⚡ Registro Rápido", "💳 Asesor de Pagos", "📉 Deudas"])

if menu == "📊 Dashboard":
    st.title("📊 Panel de Control Financiero")
    conn = get_db_connection()
    deudas_df = pd.read_sql_query("SELECT * FROM deudas WHERE activa=1", conn)
    billetera_df = pd.read_sql_query("SELECT sum(saldo) as total FROM billetera", conn)
    total_deuda = deudas_df['saldo'].sum()
    total_liquidez = billetera_df.iloc[0]['total']
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Deuda Total", f"${total_deuda:,.2f}", delta_color="inverse")
    c2.metric("Liquidez Total", f"${total_liquidez:,.2f}")
    c3.metric("Patrimonio Neto", f"${total_liquidez - total_deuda:,.2f}")
    conn.close()

elif menu == "👛 Mi Billetera":
    st.title("👛 Estado de Liquidez Real")
    conn = get_db_connection()
    saldos = pd.read_sql_query("SELECT * FROM billetera", conn)
    col1, col2 = st.columns(2)
    with col1: st.metric("💰 Banco / Débito", f"${saldos.iloc[1]['saldo']:,.2f}")
    with col2: st.metric("💵 Efectivo", f"${saldos.iloc[0]['saldo']:,.2f}")
    conn.close()

elif menu == "⚡ Registro Rápido":
    st.title("⚡ Registro y Descuento Dinámico")
    with st.form("registro"):
        conc = st.text_input("Concepto")
        mont = st.number_input("Monto", min_value=0.0)
        meto = st.selectbox("Método", ["Efectivo", "Tarjeta Débito", "Transferencia"])
        if st.form_submit_button("Guardar"):
            update_billetera(meto, mont)
            st.success("Gasto registrado y saldo de billetera actualizado.")

elif menu == "💳 Asesor de Pagos":
    st.title("🧠 Asesor Inteligente: ¿Qué pagar hoy?")
    df = pd.read_sql_query("SELECT * FROM deudas WHERE activa=1", get_db_connection())
    metodo = st.radio("Estrategia", ["Bola de Nieve (Paz Mental)", "Avalancha (Ahorro Interés)"])
    st.subheader("🔥 Foco de Ataque Táctico")
    orden = "saldo" if "Bola" in metodo else "tasa_cat"
    target = df.sort_values(orden, ascending=("saldo" in orden)).iloc[0]
    st.info(f"Prioridad máxima: Pagar el mínimo de todas y todo el sobrante a **{target['acreedor']}**")

elif menu == "📉 Deudas":
    st.title("📉 Gestión de Acreedores")
    df = pd.read_sql_query("SELECT acreedor, saldo, pago_minimo, tasa_cat, fecha_corte FROM deudas WHERE activa=1", get_db_connection())
    st.dataframe(df, use_container_width=True)
