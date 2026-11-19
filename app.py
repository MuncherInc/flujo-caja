# Flujo de Caja - Prototipo
# Permite importar movimientos, gestionar pagos programados y mover fechas.

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import io

import os
DB_PATH = Path(os.getenv("DATABASE_PATH", "flujo_caja.db"))

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Movimientos reales (importados)
    c.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            cuenta TEXT,
            concepto TEXT,
            monto REAL,
            tipificacion TEXT,
            tipo TEXT,  -- ingreso / egreso
            origen TEXT DEFAULT 'importado',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Pagos programados
    c.execute("""
        CREATE TABLE IF NOT EXISTS pagos_programados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_original TEXT,
            fecha_efectiva TEXT,
            concepto TEXT,
            monto REAL,
            tipificacion TEXT,
            proveedor TEXT,
            estado TEXT DEFAULT 'pendiente',  -- pendiente / movido / pagado / cancelado
            notas TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Overrides / historial de movimientos de pagos
    c.execute("""
        CREATE TABLE IF NOT EXISTS overrides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pago_id INTEGER,
            fecha_anterior TEXT,
            fecha_nueva TEXT,
            motivo TEXT,
            usuario TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pago_id) REFERENCES pagos_programados(id)
        )
    """)
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_PATH)

init_db()

st.set_page_config(page_title="Flujo de Caja - Prototipo", layout="wide")
st.title("💰 Flujo de Caja - Prototipo")
st.caption("Importar movimientos | Pagos programados | Mover pagos | Proyección")

tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Importar Movimientos",
    "📅 Pagos Programados",
    "🔄 Mover Pagos",
    "📊 Proyección de Caja"
])

# ---------- TAB 1: Importar ----------
with tab1:
    st.header("Importar movimientos (CSV)")
    st.markdown("""
    Formato esperado del CSV (separador `,` o `;`):
    - `fecha` (YYYY-MM-DD o DD/MM/YYYY)
    - `cuenta`
    - `concepto`
    - `monto` (positivo = ingreso, negativo = egreso, o usar columna tipo)
    - `tipificacion` (opcional)
    """)

    col_up, col_ej = st.columns(2)
    with col_up:
        uploaded = st.file_uploader("Sube el CSV de movimientos", type=["csv"])
    with col_ej:
        st.write("")
        st.write("")
        if st.button("📥 Cargar CSV de ejemplo", type="primary"):
            try:
                df_ej = pd.read_csv("ejemplo_movimientos.csv")
                conn = get_conn()
                cols = {c.lower().strip(): c for c in df_ej.columns}
                for _, row in df_ej.iterrows():
                    fecha = str(row.get(cols.get('fecha', 'fecha'), ''))[:10]
                    cuenta = str(row.get(cols.get('cuenta', 'cuenta'), ''))
                    concepto = str(row.get(cols.get('concepto', 'concepto'), ''))
                    monto = float(row.get(cols.get('monto', 'monto'), 0) or 0)
                    tip = str(row.get(cols.get('tipificacion', 'tipificacion'), ''))
                    tipo = "ingreso" if monto >= 0 else "egreso"
                    conn.execute(
                        "INSERT INTO movimientos (fecha, cuenta, concepto, monto, tipificacion, tipo) VALUES (?,?,?,?,?,?)",
                        (fecha, cuenta, concepto, monto, tip, tipo)
                    )
                conn.commit()
                conn.close()
                st.success(f"Importados {len(df_ej)} movimientos de ejemplo")
                st.rerun()
            except Exception as e:
                st.error(f"Error al cargar ejemplo: {e}")

    if uploaded:
        try:
            df = pd.read_csv(uploaded, sep=None, engine='python')
            st.write("Vista previa:", df.head(10))
            
            if st.button("Importar a base de datos"):
                conn = get_conn()
                # Normalizar columnas
                cols = {c.lower().strip(): c for c in df.columns}
                for _, row in df.iterrows():
                    fecha = str(row.get(cols.get('fecha', 'fecha'), ''))[:10]
                    cuenta = str(row.get(cols.get('cuenta', 'cuenta'), ''))
                    concepto = str(row.get(cols.get('concepto', 'concepto'), ''))
                    monto = float(row.get(cols.get('monto', 'monto'), 0) or 0)
                    tip = str(row.get(cols.get('tipificacion', 'tipificacion'), ''))
                    tipo = "ingreso" if monto >= 0 else "egreso"
                    conn.execute(
                        "INSERT INTO movimientos (fecha, cuenta, concepto, monto, tipificacion, tipo) VALUES (?,?,?,?,?,?)",
                        (fecha, cuenta, concepto, monto, tip, tipo)
                    )
                conn.commit()
                conn.close()
                st.success(f"Importados {len(df)} movimientos")
        except Exception as e:
            st.error(f"Error al leer CSV: {e}")

    # Mostrar últimos movimientos
    conn = get_conn()
    movs = pd.read_sql("SELECT * FROM movimientos ORDER BY fecha DESC LIMIT 50", conn)
    conn.close()
    if not movs.empty:
        st.subheader("Últimos movimientos importados")
        st.dataframe(movs, use_container_width=True)

# ---------- TAB 2: Pagos Programados ----------
with tab2:
    st.header("Pagos Programados")
    
    with st.form("nuevo_pago"):
        col1, col2 = st.columns(2)
        with col1:
            concepto = st.text_input("Concepto / Proveedor")
            monto = st.number_input("Monto (negativo = egreso)", value=-100000.0, step=1000.0)
            fecha = st.date_input("Fecha programada", value=datetime.today() + timedelta(days=7))
        with col2:
            tipificacion = st.text_input("Tipificación", value="Corporate Expenses")
            proveedor = st.text_input("Proveedor / Beneficiario")
            notas = st.text_area("Notas")
        if st.form_submit_button("Agregar pago programado"):
            conn = get_conn()
            conn.execute(
                """INSERT INTO pagos_programados 
                   (fecha_original, fecha_efectiva, concepto, monto, tipificacion, proveedor, notas)
                   VALUES (?,?,?,?,?,?,?)""",
                (str(fecha), str(fecha), concepto, monto, tipificacion, proveedor, notas)
            )
            conn.commit()
            conn.close()
            st.success("Pago agregado")
            st.rerun()

    conn = get_conn()
    pagos = pd.read_sql(
        "SELECT id, fecha_efectiva, concepto, monto, tipificacion, proveedor, estado, notas FROM pagos_programados WHERE estado != 'cancelado' ORDER BY fecha_efectiva",
        conn
    )
    conn.close()
    if not pagos.empty:
        st.dataframe(pagos, use_container_width=True)
    else:
        st.info("No hay pagos programados aún.")

# ---------- TAB 3: Mover Pagos ----------
with tab3:
    st.header("Mover Pagos")
    conn = get_conn()
    pagos_df = pd.read_sql(
        "SELECT id, fecha_efectiva, concepto, monto, tipificacion, estado FROM pagos_programados WHERE estado IN ('pendiente','movido') ORDER BY fecha_efectiva",
        conn
    )
    conn.close()
    
    if pagos_df.empty:
        st.info("No hay pagos para mover.")
    else:
        pago_sel = st.selectbox(
            "Selecciona el pago a mover",
            options=pagos_df['id'].tolist(),
            format_func=lambda x: f"ID {x} | {pagos_df[pagos_df['id']==x]['fecha_efectiva'].iloc[0]} | {pagos_df[pagos_df['id']==x]['concepto'].iloc[0]} | {pagos_df[pagos_df['id']==x]['monto'].iloc[0]:,.0f}"
        )
        nueva_fecha = st.date_input("Nueva fecha", value=datetime.today() + timedelta(days=14))
        motivo = st.text_input("Motivo del movimiento (ej. decisión jueves)")
        
        if st.button("Mover pago"):
            conn = get_conn()
            # Guardar override
            fecha_ant = pagos_df[pagos_df['id']==pago_sel]['fecha_efectiva'].iloc[0]
            conn.execute(
                "INSERT INTO overrides (pago_id, fecha_anterior, fecha_nueva, motivo) VALUES (?,?,?,?)",
                (pago_sel, fecha_ant, str(nueva_fecha), motivo)
            )
            # Actualizar fecha efectiva
            conn.execute(
                "UPDATE pagos_programados SET fecha_efectiva=?, estado='movido', updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (str(nueva_fecha), pago_sel)
            )
            conn.commit()
            conn.close()
            st.success(f"Pago {pago_sel} movido a {nueva_fecha}")
            st.rerun()
        
        # Historial de overrides
        conn = get_conn()
        hist = pd.read_sql("SELECT * FROM overrides ORDER BY created_at DESC LIMIT 20", conn)
        conn.close()
        if not hist.empty:
            st.subheader("Historial de movimientos de pagos")
            st.dataframe(hist, use_container_width=True)

# ---------- TAB 4: Proyección ----------
with tab4:
    st.header("Proyección de Caja")
    
    col_a, col_b = st.columns(2)
    with col_a:
        fecha_inicio = st.date_input("Desde", value=datetime.today())
    with col_b:
        dias = st.slider("Días a proyectar", 7, 90, 30)
    fecha_fin = fecha_inicio + timedelta(days=dias)
    
    conn = get_conn()
    # Movimientos reales en el rango
    movs = pd.read_sql(
        "SELECT fecha, SUM(monto) as total FROM movimientos WHERE fecha BETWEEN ? AND ? GROUP BY fecha",
        conn, params=(str(fecha_inicio), str(fecha_fin))
    )
    # Pagos programados en el rango (usando fecha_efectiva)
    pagos_proy = pd.read_sql(
        "SELECT fecha_efectiva as fecha, SUM(monto) as total FROM pagos_programados WHERE fecha_efectiva BETWEEN ? AND ? AND estado != 'cancelado' GROUP BY fecha_efectiva",
        conn, params=(str(fecha_inicio), str(fecha_fin))
    )
    conn.close()
    
    # Construir calendario
    fechas = pd.date_range(fecha_inicio, fecha_fin, freq='D')
    proy = pd.DataFrame({'fecha': fechas.strftime('%Y-%m-%d')})
    proy = proy.merge(movs, on='fecha', how='left').rename(columns={'total': 'movimientos'})
    proy = proy.merge(pagos_proy, on='fecha', how='left').rename(columns={'total': 'pagos_programados'})
    proy = proy.fillna(0)
    proy['flujo_dia'] = proy['movimientos'] + proy['pagos_programados']
    proy['saldo_acumulado'] = proy['flujo_dia'].cumsum()
    
    st.subheader("Resumen diario")
    st.dataframe(proy[['fecha','movimientos','pagos_programados','flujo_dia','saldo_acumulado']], use_container_width=True)
    
    # Gráfico simple
    if not proy.empty:
        st.line_chart(proy.set_index('fecha')[['flujo_dia','saldo_acumulado']])
    
    # Totales
    st.metric("Flujo neto del período", f"{proy['flujo_dia'].sum():,.0f}")
    st.metric("Saldo final proyectado", f"{proy['saldo_acumulado'].iloc[-1] if len(proy)>0 else 0:,.0f}")

st.sidebar.markdown("### Acciones")
if st.sidebar.button("Limpiar toda la base de datos"):
    conn = get_conn()
    conn.execute("DELETE FROM movimientos")
    conn.execute("DELETE FROM pagos_programados")
    conn.execute("DELETE FROM overrides")
    conn.commit()
    conn.close()
    st.sidebar.success("Base limpiada")
    st.rerun()

st.sidebar.info("""
**Cómo usar:**
1. Importa CSV de movimientos
2. Agrega pagos programados
3. Mueve pagos según decisiones de jueves
4. Revisa la proyección actualizada
""")
