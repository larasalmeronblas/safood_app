
import streamlit as st
import pandas as pd
import gspread
import json

st.set_page_config(page_title="CALCULADORA NUTRICIONAL SAFOOD", layout="wide")

st.image("logo.png", width=150)
st.title("CALCULADORA NUTRICIONAL SAFOOD")

# Leer secretos
sa_info = json.loads(st.secrets["SERVICE_ACCOUNT_JSON"])
sheet_id = st.secrets["GOOGLE_SHEET_ID"]
gc = gspread.service_account_from_dict(sa_info)
sheet = gc.open_by_key(sheet_id)

# Acceso a hojas
try:
    ingredientes_ws = sheet.worksheet("Ingredientes")
    recetas_ws = sheet.worksheet("Recetas")
except Exception as e:
    st.error("No se encontraron las hojas 'Ingredientes' o 'Recetas'.")
    st.stop()

ingredientes_df = pd.DataFrame(ingredientes_ws.get_all_records())
recetas_df = pd.DataFrame(recetas_ws.get_all_records())

tab1, tab2 = st.tabs(["➕ Cargar ingredientes", "🧪 Crear y analizar receta"])

# TAB 1: Ingredientes
with tab1:
    st.subheader("Añadir nuevo ingrediente")
    with st.form("ingrediente_form"):
        col1, col2 = st.columns(2)
        with col1:
            cliente = st.text_input("Cliente", "")
            nombre = st.text_input("Nombre del ingrediente")
            proveedor = st.text_input("Proveedor")
            referencia = st.text_input("Referencia")
            composicion = st.text_area("Composición detallada", "")
        with col2:
            alergenos = st.text_input("Alérgenos (separados por coma)", "")
            energia = st.number_input("Energía (kcal/100g)", 0.0)
            proteinas = st.number_input("Proteínas (g)", 0.0)
            grasas = st.number_input("Grasas (g)", 0.0)
            saturadas = st.number_input("Ácidos grasos saturados (g)", 0.0)
            hidratos = st.number_input("Hidratos de carbono (g)", 0.0)
            azucares = st.number_input("de los cuales azúcares (g)", 0.0)
            fibra = st.number_input("Fibra alimentaria (g)", 0.0)
            sal = st.number_input("Sal (g)", 0.0)
        submitted = st.form_submit_button("Guardar ingrediente")

        if submitted:
            nuevo = [cliente, nombre, proveedor, referencia, composicion, alergenos,
                     energia, proteinas, grasas, saturadas, hidratos, azucares, fibra, sal]
            ingredientes_ws.append_row(nuevo)
            st.success("Ingrediente guardado correctamente.")

# TAB 2: Recetas
with tab2:
    st.subheader("Crear y analizar receta")

    clientes_disponibles = sorted(set(ingredientes_df.get("Cliente", []).dropna().unique().tolist()))

    st.markdown("### Crear nueva receta")
    if clientes_disponibles:
        cliente_sel = st.selectbox("Selecciona cliente", options=clientes_disponibles)
    else:
        st.warning("No hay clientes disponibles. Agrega ingredientes primero.")
        st.stop()

    ingredientes_cliente = ingredientes_df[ingredientes_df["Cliente"] == cliente_sel]

    with st.form("receta_form"):
        receta_nombre = st.text_input("Nombre de la receta")
        ing_sel = st.multiselect("Selecciona ingredientes", ingredientes_cliente["Nombre"].tolist())
        cantidades = {}
        for ing in ing_sel:
            cantidad = st.number_input(f"Cantidad de {ing} (g)", 0.0, 1000.0, step=1.0)
            cantidades[ing] = cantidad
        guardar = st.form_submit_button("Guardar receta")

        if guardar and receta_nombre and ing_sel:
            for ing in ing_sel:
                fila = ingredientes_cliente[ingredientes_cliente["Nombre"] == ing].iloc[0]
                recetas_ws.append_row([
                    cliente_sel, receta_nombre, ing, fila["Proveedor"],
                    cantidades[ing]
                ])
            st.success("Receta guardada correctamente. Recarga para analizarla.")

    st.markdown("### Analizar receta existente")
    cliente_analisis = st.selectbox("Selecciona cliente para analizar", options=clientes_disponibles)
    recetas_cliente = recetas_df[recetas_df["Cliente"] == cliente_analisis]
    recetas_unicas = recetas_cliente["Receta"].dropna().unique().tolist()
    receta_sel = st.selectbox("Selecciona receta", recetas_unicas)

    receta_df = recetas_cliente[recetas_cliente["Receta"] == receta_sel]

    if not receta_df.empty:
        receta_merge = receta_df.merge(
            ingredientes_df,
            left_on=["Ingrediente", "Proveedor"],
            right_on=["Nombre", "Proveedor"],
            how="left"
        )
        nutrientes = ["Energía", "Proteínas", "Grasas", "Saturadas", "Hidratos", "Azúcares", "Fibra", "Sal"]
        for n in nutrientes:
            receta_merge[n] = receta_merge[n] * receta_merge["Cantidad"] / 100
        suma_total = receta_merge[nutrientes].sum()
        peso_total = receta_merge["Cantidad"].sum()
        por_100g = (suma_total / peso_total) * 100

        st.subheader("📊 Información nutricional por 100 g")
        st.dataframe(por_100g.round(2).astype(str).str.replace(".", ","))

        st.subheader("🧾 Lista de ingredientes")
        lista_ordenada = receta_merge.groupby(["Ingrediente", "Composición", "Alérgenos"], dropna=False)["Cantidad"].sum().reset_index()
        lista_ordenada = lista_ordenada.sort_values(by="Cantidad", ascending=False)

        def resaltar_alergenos(texto, alergenos):
            for alergeno in alergenos:
                if alergeno:
                    texto = texto.replace(alergeno.lower(), f"**{alergeno.upper()}**")
            return texto

        alergenos_list = receta_merge["Alérgenos"].dropna().str.lower().str.split(",")
        lista_alergenos = sorted(set(a.strip() for sublist in alergenos_list for a in sublist if a.strip()))

        texto_ingredientes = ", ".join([
            resaltar_alergenos(
                f"{row['Ingrediente']} ({row['Composición']})" if pd.notna(row['Composición']) and row['Composición'].strip() else row['Ingrediente'],
                lista_alergenos
            )
            for _, row in lista_ordenada.iterrows()
        ])
        st.markdown("**Ingredientes (orden descendente por cantidad):**")
        st.markdown(texto_ingredientes)

        st.markdown("**Alérgenos presentes:**")
        st.markdown(", ".join([f"**{a.upper()}**" for a in lista_alergenos]))
    else:
        st.warning("No se encontraron registros de esa receta para ese cliente.")
