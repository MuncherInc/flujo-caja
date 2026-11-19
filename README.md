# Prototipo Flujo de Caja
Python + Streamlit + SQLite

## Requisitos
```bash
pip install streamlit pandas
```

## Ejecutar
```bash
streamlit run app.py
```

## Funcionalidades
- Importar movimientos desde CSV
- Crear pagos programados
- Mover pagos (cambia fecha_efectiva y registra override)
- Proyección de caja diaria combinando movimientos reales + pagos programados

## Formato CSV de importación
Columnas esperadas (case-insensitive):
- fecha
- cuenta
- concepto
- monto
- tipificacion (opcional)

## Próximos pasos
- Conectar a SIESA (Hub o Data Platform)
- Multi-moneda y tasas
- Tipificaciones automáticas
- Escenarios
- Export a Google Sheets
