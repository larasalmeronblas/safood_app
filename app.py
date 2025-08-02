
import streamlit as st
import pandas as pd
import os
from pathlib import Path
import re

st.set_page_config(page_title="Calculadora Nutricional", layout="wide")

st.image("logo.png", width=150)
st.markdown("## Calculadora Nutricional por Cliente")

DATA_DIR = "data_excel"
os.makedirs(DATA_DIR, exist_ok=True)

clientes_existentes = [f.stem for f in Path(DATA_DIR).glob("*.xlsx")]

cliente_sel = st.selectbox("Selecciona cliente", [""] + clientes_existentes)
nuevo_cliente = st.text_input("O crea nuevo cliente")

cliente_activo = nuevo_cliente if nuevo_cliente else cliente_sel

if cliente_activo:
    pagina = st.sidebar.radio("📋 Menú", ["➕ Añadir ingredientes", "🧪 Crear y analizar receta"])

    def cargar_datos(cliente):
        ruta = os.path.join(DATA_DIR, f"{cliente}.xlsx")
        if os.path.exists(ruta):
            xls = pd.ExcelFile(ruta)
            ingredientes = pd.read_excel(xls, "Ingredientes")
            recetas = pd.read_excel(xls, "Recetas")
        else:
            ingredientes = pd.DataFrame(columns=["Cliente", "Nombre", "Proveedor", "Referencia", "Composición",
                                                 "Alérgenos", "Energía", "Proteínas", "Grasas", "Saturadas",
                                                 "Hidratos", "Azúcares", "Fibra", "Sal"])
            recetas = pd.DataFrame(columns=["Cliente", "Receta", "Ingrediente", "Proveedor", "Cantidad"])
        return ingredientes, recetas

    def guardar_datos(cliente, df_ingredientes, df_recetas):
        ruta = os.path.join(DATA_DIR, f"{cliente}.xlsx")
        with pd.ExcelWriter(ruta, engine="openpyxl", mode="w") as writer:
            df_ingredientes.to_excel(writer, sheet_name="Ingredientes", index=False)
            df_recetas.to_excel(writer, sheet_name="Recetas", index=False)

    ingredientes_df, recetas_df = cargar_datos(cliente_activo)

    if pagina == "➕ Añadir ingredientes":
        st.subheader("➕ Añadir ingrediente")
        with st.form("form_ing"):
            nombre = st.text_input("Nombre del ingrediente")
            proveedor = st.text_input("Proveedor")
            referencia = st.text_input("Referencia interna")
            composicion = st.text_area("Subingredientes / composición")
            alergenos = st.text_input("Alérgenos")
            energia = st.number_input("Energía (kcal)", 0.0)
            proteinas = st.number_input("Proteínas (g)", 0.0)
            grasas = st.number_input("Grasas (g)", 0.0)
            saturadas = st.number_input("Saturadas (g)", 0.0)
            hidratos = st.number_input("Hidratos carbono (g)", 0.0)
            azucares = st.number_input("Azúcares (g)", 0.0)
            fibra = st.number_input("Fibra (g)", 0.0)
            sal = st.number_input("Sal (g)", 0.0)
            guardar = st.form_submit_button("Guardar ingrediente")
            if guardar:
                nuevo = pd.DataFrame([{
                    "Cliente": cliente_activo, "Nombre": nombre, "Proveedor": proveedor, "Referencia": referencia,
                    "Composición": composicion, "Alérgenos": alergenos.lower(), "Energía": energia,
                    "Proteínas": proteinas, "Grasas": grasas, "Saturadas": saturadas, "Hidratos": hidratos,
                    "Azúcares": azucares, "Fibra": fibra, "Sal": sal
                }])
                ingredientes_df = pd.concat([ingredientes_df, nuevo], ignore_index=True)
                guardar_datos(cliente_activo, ingredientes_df, recetas_df)
                st.success("Ingrediente guardado")

        st.subheader("📦 Ingredientes registrados")
        st.dataframe(ingredientes_df)

    if pagina == "🧪 Crear y analizar receta":
        st.subheader("🧪 Crear receta")
        with st.form("form_receta"):
            nombre_receta = st.text_input("Nombre de receta")
            ingr = st.selectbox("Ingrediente", ingredientes_df["Nombre"].unique())
            proveedores_filtrados = ingredientes_df[ingredientes_df["Nombre"] == ingr]["Proveedor"].unique()
            proveedor_ingr = st.selectbox("Proveedor", proveedores_filtrados)
            cantidad = st.number_input("Cantidad (g)", 0.1)
            agregar = st.form_submit_button("Añadir a receta")
            if agregar:
                nueva_fila = pd.DataFrame([{
                    "Cliente": cliente_activo, "Receta": nombre_receta, "Ingrediente": ingr,
                    "Proveedor": proveedor_ingr, "Cantidad": cantidad
                }])
                recetas_df = pd.concat([recetas_df, nueva_fila], ignore_index=True)
                guardar_datos(cliente_activo, ingredientes_df, recetas_df)
                st.success("Ingrediente añadido a receta")

        st.subheader("📋 Recetas registradas")
        st.dataframe(recetas_df)

        st.subheader("🔍 Seleccionar receta para análisis")
        receta_sel = st.selectbox("Selecciona una receta", sorted(recetas_df["Receta"].unique()))
        if receta_sel:
            receta_df = recetas_df[recetas_df["Receta"] == receta_sel]
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

            alergenos_list = receta_merge["Alérgenos"].dropna().str.lower().str.split(",")
            lista_alergenos = sorted(set(a.strip() for sublist in alergenos_list for a in sublist if a.strip()))

            def resaltar_alergenos(texto, alergenos):
                for alergeno in alergenos:
                    if alergeno:
                        pattern = re.compile(rf"\b({alergeno})\b", re.IGNORECASE)
                        texto = pattern.sub(lambda m: f"**{m.group(1).upper()}**", texto)
                return texto

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
