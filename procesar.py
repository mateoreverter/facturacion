import pandas as pd
import json
import os
import traceback

def obtener_datos_agrupados(df):
    if df.empty:
        return {"total": 0, "fa": {"labels": [], "values": []}, "ifa": {"labels": [], "values": []}, "cliente": {"labels": [], "values": []}, "fechas": {"labels": [], "values": []}, "ticker": [], "fa_detalles": {}, "ifa_detalles": {}, "cliente_detalles": {}, "ticker_detalles": {}}
    
    total = float(df['ComisionDolarizada'].sum())
    
    fa_group = df.groupby('FA')['ComisionDolarizada'].sum().sort_values(ascending=False)
    ifa_group = df.groupby('Asesor')['ComisionDolarizada'].sum().sort_values(ascending=False).head(15)
    cliente_group = df.groupby('Cliente')['ComisionDolarizada'].sum().sort_values(ascending=False).head(15)
    fecha_group = df.groupby('FechaReal')['ComisionDolarizada'].sum().sort_index()
    fechas_labels = fecha_group.index.strftime('%d/%m').tolist()
    ticker_group = df.groupby('Ticker')['ComisionDolarizada'].sum().sort_values(ascending=False).head(40)
    ticker_list = [{"t": str(k), "v": float(v)} for k, v in ticker_group.items()]

    fa_detalles = {}
    for fa in fa_group.index:
        df_fa = df[df['FA'] == fa]
        fa_ifa = df_fa.groupby('Asesor')['ComisionDolarizada'].sum().sort_values(ascending=False).head(15)
        fa_detalles[fa] = {"labels": fa_ifa.index.tolist(), "values": fa_ifa.tolist()}

    ifa_detalles = {}
    for ifa in ifa_group.index:
        df_ifa = df[df['Asesor'] == ifa]
        cli_group = df_ifa.groupby('Cliente')['ComisionDolarizada'].sum().sort_values(ascending=False).head(15)
        ifa_detalles[ifa] = {"labels": cli_group.index.tolist(), "values": cli_group.tolist()}

    top_clientes = df.groupby('Cliente')['ComisionDolarizada'].sum().sort_values(ascending=False).head(150).index
    cliente_detalles = {}
    for cli in top_clientes:
        df_cli = df[df['Cliente'] == cli]
        cli_fecha = df_cli.groupby('FechaReal')['ComisionDolarizada'].sum().sort_index()
        cli_ticker = df_cli.groupby('Ticker')['ComisionDolarizada'].sum().sort_values(ascending=False).head(10)
        cliente_detalles[cli] = {
            "fechas": {"labels": cli_fecha.index.strftime('%d/%m').tolist(), "values": cli_fecha.tolist()},
            "ticker": [{"t": str(k), "v": float(v)} for k, v in cli_ticker.items()],
            "total": float(df_cli['ComisionDolarizada'].sum())
        }

    ticker_detalles = {}
    for tk in ticker_group.index:
        df_tk = df[df['Ticker'] == tk]
        tk_ifa = df_tk.groupby('Asesor')['ComisionDolarizada'].sum().sort_values(ascending=False).head(10)
        ticker_detalles[tk] = {"labels": tk_ifa.index.tolist(), "values": tk_ifa.tolist()}

    return {
        "total": total,
        "fa": {"labels": fa_group.index.tolist(), "values": fa_group.tolist()},
        "ifa": {"labels": ifa_group.index.tolist(), "values": ifa_group.tolist()},
        "cliente": {"labels": cliente_group.index.tolist(), "values": cliente_group.tolist()},
        "fechas": {"labels": fechas_labels, "values": fecha_group.tolist()},
        "ticker": ticker_list,
        "fa_detalles": fa_detalles,
        "ifa_detalles": ifa_detalles,
        "cliente_detalles": cliente_detalles,
        "ticker_detalles": ticker_detalles
    }

def generar_datos_dashboard():
    print("Procesando datos para exportar a JS...")
    try:
        carpeta_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_excel = os.path.join(carpeta_actual, 'comision_actualizada.xlsx')
        ruta_js = os.path.join(carpeta_actual, 'datos_facturacion.js')
        
        df = pd.read_excel(ruta_excel)
        df['ComisionDolarizada'] = pd.to_numeric(df['ComisionDolarizada'], errors='coerce').fillna(0)
        df['FA'] = df['Equipo'].astype(str).apply(lambda x: x.split('/')[0].strip() if pd.notnull(x) else 'N/A')
        df['Asesor'] = df['Asesor'].fillna('Sin Asesor') if 'Asesor' in df.columns else 'Sin Asesor'
        col_cliente = 'Cuenta' if 'Cuenta' in df.columns else 'Cliente' if 'Cliente' in df.columns else 'Comitente'
        df['Cliente'] = df[col_cliente].fillna('Sin Cliente') if col_cliente in df.columns else 'Sin Cliente'
        df['Ticker'] = df['Ticker'].fillna('Sin Ticker') if 'Ticker' in df.columns else 'Sin Ticker'
        
        if 'FechaConcertacion' in df.columns:
            df['FechaReal'] = pd.to_datetime(df['FechaConcertacion'], errors='coerce')
            df = df.dropna(subset=['FechaReal'])
            fecha_maxima = df['FechaReal'].max()
            año_actual = fecha_maxima.year
            mes_actual = fecha_maxima.month
            fecha_actualizacion_str = fecha_maxima.strftime('%d/%m/%Y')
            
            df_ytd = df[df['FechaReal'].dt.year == año_actual].copy()
            df_mtd = df_ytd[df_ytd['FechaReal'].dt.month == mes_actual].copy()
        else:
            fecha_actualizacion_str = "N/D"
            df_ytd = df_mtd = df.copy()

        data = {
            "ultima_actualizacion": fecha_actualizacion_str,
            "mtd": obtener_datos_agrupados(df_mtd),
            "ytd": obtener_datos_agrupados(df_ytd)
        }
        
        contenido_js = f"const datosDashboard = {json.dumps(data, ensure_ascii=False)};"
        with open(ruta_js, 'w', encoding='utf-8') as f:
            f.write(contenido_js)
            
        print(f"\n✅ ¡Éxito! Archivo generado: {ruta_js}")
    except Exception as e:
        print("\n❌ Ocurrió un error:")
        print(traceback.format_exc())

generar_datos_dashboard()
input("\nPresioná Enter para cerrar...")