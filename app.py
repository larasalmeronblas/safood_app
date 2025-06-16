
import streamlit as st
import pandas as pd
import gspread
import json

st.set_page_config(page_title="SAFood Nutricional (Google Sheets)", layout="wide")
st.title("📊 SAFood – Calculadora Nutricional")

# Leer credenciales desde secrets
sa_info = json.loads(st.secrets["SERVICE_ACCOUNT_JSON"])
sheet_id = st.secrets["GOOGLE_SHEET_ID"]

# Conectar con Google Sheets
gc = gspread.service_account_from_dict(sa_info)
sheet = gc.open_by_key(sheet_id)

# Cargar datos
try:
    ingredientes_df = pd.DataFrame(sheet.worksheet("Ingredientes").get_all_records())
    recetas_df = pd.DataFrame(sheet.worksheet("Recetas").get_all_records())
except Exception as e:
    st.error("No se pudieron cargar los datos. Verifica las hojas 'Ingredientes' y 'Recetas'")
    st.stop()

cliente_sel = st.selectbox("Selecciona cliente", ingredientes_df["Cliente"].unique())
ingredientes_cliente = ingredientes_df[ingredientes_df["Cliente"] == cliente_sel]

st.subheader("📦 Ingredientes del cliente")
st.dataframe(ingredientes_cliente)

st.subheader("🧪 Crear y analizar receta")
receta_sel = st.selectbox("Selecciona receta", recetas_df["Receta"].unique())
receta_df = recetas_df[(recetas_df["Cliente"] == cliente_sel) & (recetas_df["Receta"] == receta_sel)]

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
