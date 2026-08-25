import pandas as pd
import json
import os
import traceback
import calendar

# Cuotas anuales definidas
CUOTA_TOTAL_EQUIPO = 5000000
CUOTA_POR_FA = CUOTA_TOTAL_EQUIPO / 6  # 833,333.33

def obtener_datos_agrupados(df, periodo='mtd', is_global=False):
    if df.empty:
        return {"total": 0, "run_rate": 0, "plan_anual": 0, "plan_mensual": 0, "cumplimiento_ytd": 0, "cumplimiento_mtd": 0, "fa": {"labels": [], "values": []}, "ifa": {"labels": [], "values": [], "tooltips": []}, "cliente": {"labels": [], "values": []}, "fechas": {"labels": [], "values": []}, "ticker": [], "fa_detalles": {}, "ifa_detalles": {}, "cliente_detalles": {}, "ticker_detalles": {}}
    
    total = float(df['ComisionDolarizada'].sum())
    
    # --- CÁLCULOS GERENCIALES (Run Rate y Planes) ---
    run_rate = 0
    plan_objetivo_anual = CUOTA_TOTAL_EQUIPO if is_global else CUOTA_POR_FA
    plan_objetivo_mensual = plan_objetivo_anual / 12
    cumplimiento_ytd = 0
    cumplimiento_mtd = 0
    
    if 'FechaReal' in df.columns and not df.empty:
        ultima_fecha = df['FechaReal'].max()
        dia_actual = ultima_fecha.day
        mes_actual = ultima_fecha.month
        anio_actual = ultima_fecha.year
        dias_del_mes = calendar.monthrange(anio_actual, mes_actual)[1]
        
        if periodo == 'mtd':
            if dia_actual > 0:
                run_rate = (total / dia_actual) * dias_del_mes
            cumplimiento_mtd = (total / plan_objetivo_mensual) * 100 if plan_objetivo_mensual > 0 else 0
        else:
            cumplimiento_ytd = (total / plan_objetivo_anual) * 100 if plan_objetivo_anual > 0 else 0
            
    # ---------------------------------------------
    
    fa_group = df.groupby('FA')['ComisionDolarizada'].sum().sort_values(ascending=False)
    
    ifa_group_raw = df.groupby('Asesor').agg({'ComisionDolarizada': 'sum', 'FA': 'first'})
    ifa_group_sorted = ifa_group_raw.sort_values(by='ComisionDolarizada', ascending=False)
    
    cliente_group = df.groupby('Cliente')['ComisionDolarizada'].sum().sort_values(ascending=False)
    
    meses_dict = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}

    if periodo == 'ytd':
        fecha_group = df.groupby(df['FechaReal'].dt.month)['ComisionDolarizada'].sum().sort_index()
        fechas_labels = [meses_dict.get(m, str(m)) for m in fecha_group.index]
        fechas_values = fecha_group.tolist()
    else:
        fecha_group = df.groupby('FechaReal')['ComisionDolarizada'].sum().sort_index()
        fechas_labels = fecha_group.index.strftime('%d/%m').tolist()
        fechas_values = fecha_group.tolist()

    ticker_group = df.groupby('Ticker')['ComisionDolarizada'].sum().sort_values(ascending=False).head(40)
    ticker_list = [{"t": str(k), "v": float(v)} for k, v in ticker_group.items()]

    # ====================================================================
    # 🚀 OPTIMIZACIÓN EXTREMA: Agrupamos de una sola vez para evitar el cuelgue
    # ====================================================================
    
    fa_detalles = {}
    for fa, df_fa in df.groupby('FA'):
        fa_ifa = df_fa.groupby('Asesor')['ComisionDolarizada'].sum().sort_values(ascending=False).head(15)
        fa_detalles[str(fa)] = {"labels": fa_ifa.index.tolist(), "values": fa_ifa.tolist()}

    ifa_detalles = {}
    for ifa, df_ifa in df.groupby('Asesor'):
        cli_group = df_ifa.groupby('Cliente')['ComisionDolarizada'].sum().sort_values(ascending=False).head(15)
        ifa_detalles[str(ifa)] = {"labels": cli_group.index.tolist(), "values": cli_group.tolist()}

    cliente_detalles = {}
    for cli, df_cli in df.groupby('Cliente'):
        if periodo == 'ytd':
            cli_fecha = df_cli.groupby(df_cli['FechaReal'].dt.month)['ComisionDolarizada'].sum().sort_index()
            cli_fechas_labels = [meses_dict.get(m, str(m)) for m in cli_fecha.index]
            cli_fechas_values = cli_fecha.tolist()
        else:
            cli_fecha = df_cli.groupby('FechaReal')['ComisionDolarizada'].sum().sort_index()
            cli_fechas_labels = cli_fecha.index.strftime('%d/%m').tolist()
            cli_fechas_values = cli_fecha.tolist()
            
        cli_ticker = df_cli.groupby('Ticker')['ComisionDolarizada'].sum().sort_values(ascending=False).head(10)
        cliente_detalles[str(cli)] = {
            "fechas": {"labels": cli_fechas_labels, "values": cli_fechas_values},
            "ticker": [{"t": str(k), "v": float(v)} for k, v in cli_ticker.items()],
            "total": float(df_cli['ComisionDolarizada'].sum())
        }

    ticker_detalles = {}
    top_tickers = ticker_group.index
    # Filtramos la base solo a los 40 tickers principales para ahorrar peso
    df_top_tickers = df[df['Ticker'].isin(top_tickers)] 
    for tk, df_tk in df_top_tickers.groupby('Ticker'):
        tk_ifa = df_tk.groupby('Asesor')['ComisionDolarizada'].sum().sort_values(ascending=False).head(10)
        ticker_detalles[str(tk)] = {"labels": tk_ifa.index.tolist(), "values": tk_ifa.tolist()}

    return {
        "total": total,
        "run_rate": run_rate,
        "plan_anual": plan_objetivo_anual,
        "plan_mensual": plan_objetivo_mensual,
        "cumplimiento_ytd": cumplimiento_ytd,
        "cumplimiento_mtd": cumplimiento_mtd,
        "fa": {"labels": fa_group.index.tolist(), "values": fa_group.tolist()},
        "ifa": {
            "labels": ifa_group_sorted.index.tolist(), 
            "values": ifa_group_sorted['ComisionDolarizada'].tolist(),
            "tooltips": ifa_group_sorted['FA'].tolist()
        },
        "cliente": {"labels": cliente_group.index.tolist(), "values": cliente_group.tolist()},
        "fechas": {"labels": fechas_labels, "values": fechas_values},
        "ticker": ticker_list,
        "fa_detalles": fa_detalles,
        "ifa_detalles": ifa_detalles,
        "cliente_detalles": cliente_detalles,
        "ticker_detalles": ticker_detalles
    }

def generar_datos_dashboard():
    print("Procesando base de datos completa sin límites para buscadores...")
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

        lista_fas_global = sorted(df['FA'].unique().tolist())

        views = {
            "EQUIPO": {
                "mtd": obtener_datos_agrupados(df_mtd, 'mtd', True),
                "ytd": obtener_datos_agrupados(df_ytd, 'ytd', True)
            }
        }

        print("Calculando las vistas por Equipo (FA)...")
        for fa in lista_fas_global:
            df_mtd_fa = df_mtd[df_mtd['FA'] == fa].copy()
            df_ytd_fa = df_ytd[df_ytd['FA'] == fa].copy()
            views[fa] = {
                "mtd": obtener_datos_agrupados(df_mtd_fa, 'mtd', False),
                "ytd": obtener_datos_agrupados(df_ytd_fa, 'ytd', False)
            }

        data_maestra = {
            "ultima_actualizacion": fecha_actualizacion_str,
            "lista_fas": lista_fas_global,
            "vistas": views
        }
        
        with open(ruta_js, 'w', encoding='utf-8') as f:
            f.write(f"const datosDashboard = {json.dumps(data_maestra, ensure_ascii=False)};")
            
        print("\n✅ ¡Éxito! Dashboard generado y listo para búsquedas exhaustivas.")
    except Exception as e:
        print("\n❌ Ocurrió un error:")
        print(traceback.format_exc())

generar_datos_dashboard()
input("\nPresioná Enter para cerrar...")