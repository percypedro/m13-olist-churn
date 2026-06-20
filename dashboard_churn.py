"""
Dashboard de Predicción de Churn — Olist — Grupo 7
Instalar: pip install streamlit plotly
Ejecutar: streamlit run dashboard_churn.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import pickle
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─── CONFIGURACIÓN ────────────────────────────────────────
st.set_page_config(
    page_title="Churn Olist — Grupo 7",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── PATH DE ARCHIVOS ─────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── CARGA DE DATOS ───────────────────────────────────────
@st.cache_resource
def cargar_modelo():
    path = os.path.join(BASE_DIR, "modelo_churn.pkl")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        artefacto = pickle.load(f)
    # Parche de compatibilidad sklearn: añadir multi_class si no existe
    try:
        clf_lr = artefacto['modelo'].named_steps['clf']
        if not hasattr(clf_lr, 'multi_class'):
            clf_lr.multi_class = 'auto'
    except Exception:
        pass
    return artefacto

@st.cache_data
def cargar_predicciones():
    path = os.path.join(BASE_DIR, "predicciones_churn.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def cargar_importancia():
    path = os.path.join(BASE_DIR, "importancia_por_modelo.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def cargar_lift(periodo):
    path = os.path.join(BASE_DIR, f"gain_lift_{periodo.lower()}.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def cargar_drivers():
    path = os.path.join(BASE_DIR, "drivers_churn.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)

@st.cache_data
def cargar_shap():
    p_vals = os.path.join(BASE_DIR, "shap_values.csv")
    p_data = os.path.join(BASE_DIR, "shap_data.csv")
    if not os.path.exists(p_vals) or not os.path.exists(p_data):
        return None, None
    return pd.read_csv(p_vals), pd.read_csv(p_data)

# ─── ESTILOS CSS ──────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1E3A5F, #2E86AB);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin: 5px;
    }
    .metric-value { font-size: 2.5em; font-weight: bold; }
    .metric-label { font-size: 0.9em; opacity: 0.85; margin-top: 4px; }
    .risk-alto    { background: #E74C3C; color: white; padding: 6px 14px;
                    border-radius: 20px; font-weight: bold; font-size: 0.85em; }
    .risk-medio   { background: #F18F01; color: white; padding: 6px 14px;
                    border-radius: 20px; font-weight: bold; font-size: 0.85em; }
    .risk-bajo    { background: #1AB374; color: white; padding: 6px 14px;
                    border-radius: 20px; font-weight: bold; font-size: 0.85em; }
    .section-title {
        font-size: 1.4em; font-weight: bold; color: #1E3A5F;
        border-left: 5px solid #F18F01; padding-left: 12px; margin: 20px 0 10px 0;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background: #F0F4F8; border-radius: 8px 8px 0 0;
        padding: 8px 20px; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ─── SIDEBAR ──────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/color/96/combo-chart.png", width=60)
    st.title("Churn Olist")
    st.caption("Grupo 7 · Sprint 4 · Percy Fuentes")
    st.divider()

    pagina = st.radio(
        "Navegación",
        ["📊 Resumen Ejecutivo",
         "🎯 Predicciones",
         "🔍 Importancia de Variables",
         "🧠 SHAP — Explicabilidad",
         "📈 Gain & Lift",
         "🤖 Predicción Individual",
         "💰 Impacto Económico"],
        index=0
    )
    st.divider()

    artefacto = cargar_modelo()
    if artefacto:
        st.success("✓ Modelo cargado")
        st.caption(f"Features: {len(artefacto['features'])}")
        st.caption(f"Modelo: {type(artefacto['modelo'].named_steps['clf']).__name__}")
    else:
        st.error("modelo_churn.pkl no encontrado")

    pred_df = cargar_predicciones()
    if pred_df is not None:
        st.success(f"✓ {len(pred_df):,} predicciones")
    else:
        st.warning("predicciones_churn.csv no encontrado")

    st.divider()
    st.markdown("#### 📂 Cargar CSV manual")
    st.caption("Respaldo: sube tu propio archivo de predicciones")
    csv_upload = st.file_uploader(
        "predicciones_churn.csv",
        type=["csv"],
        help="Columnas requeridas: customer_unique_id, mes, prob_churn"
    )
    if csv_upload is not None:
        try:
            df_up = pd.read_csv(csv_upload)
            required = {"customer_unique_id", "mes", "prob_churn"}
            if required.issubset(df_up.columns):
                st.session_state["pred_manual"] = df_up
                st.success(f"✓ {len(df_up):,} filas cargadas")
            else:
                missing = required - set(df_up.columns)
                st.error(f"Faltan columnas: {missing}")
        except Exception as e:
            st.error(f"Error al leer CSV: {e}")
    elif "pred_manual" in st.session_state:
        if st.button("🗑️ Quitar CSV manual"):
            del st.session_state["pred_manual"]

# ─── FUENTE DE PREDICCIONES (manual > automático) ─────────
pred_df = st.session_state.get("pred_manual", cargar_predicciones())

# ══════════════════════════════════════════════════════════
# PÁGINA 1 — RESUMEN EJECUTIVO
# ══════════════════════════════════════════════════════════
if pagina == "📊 Resumen Ejecutivo":
    st.title("📊 Resumen Ejecutivo — Modelo de Churn")
    st.caption("Dataset Olist · Logistic Regression · Sprint 4")

    # ── KPIs del modelo ──
    st.markdown('<div class="section-title">Métricas del Modelo</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown("""<div class="metric-card">
            <div class="metric-value">59.8%</div>
            <div class="metric-label">AUC Val</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class="metric-card">
            <div class="metric-value">61.0%</div>
            <div class="metric-label">AUC BackTest</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""<div class="metric-card" style="background:linear-gradient(135deg,#1AB374,#0D7A52)">
            <div class="metric-value">63.0%</div>
            <div class="metric-label">AUC Live ↑</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown("""<div class="metric-card" style="background:linear-gradient(135deg,#F18F01,#C17000)">
            <div class="metric-value">2.24x</div>
            <div class="metric-label">Lift Decil 1</div></div>""", unsafe_allow_html=True)
    with c5:
        st.markdown("""<div class="metric-card">
            <div class="metric-value">27</div>
            <div class="metric-label">Features</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Evolución AUC ──
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown('<div class="section-title">Estabilidad Temporal por Modelo</div>', unsafe_allow_html=True)
        df_auc = pd.DataFrame({
            "Período": ["Val", "BackTest", "Live"] * 3,
            "AUC":     [0.703, 0.59, 0.55, 0.598, 0.61, 0.63, 0.578, 0.59, 0.59],
            "Modelo":  ["HGB"] * 3 + ["LogReg"] * 3 + ["RF"] * 3
        })
        fig = px.line(df_auc, x="Período", y="AUC", color="Modelo",
                      markers=True,
                      color_discrete_map={"HGB": "#E74C3C", "LogReg": "#1AB374", "RF": "#2E86AB"},
                      title="AUC por período temporal")
        fig.update_layout(
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family="Calibri", size=13),
            yaxis=dict(range=[0.50, 0.75], gridcolor="#E8EFF8"),
            legend=dict(orientation="h", y=-0.2)
        )
        fig.add_annotation(x="Live", y=0.63, text="LogReg elegido ✓",
                           showarrow=True, arrowhead=2, bgcolor="#1AB374",
                           font=dict(color="white", size=11))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">Decisión de Modelo</div>', unsafe_allow_html=True)
        st.info("""
**¿Por qué LogReg y no HGB?**

HGB tiene mejor AUC Val (0.703) pero cae
15 puntos en Live (0.55).

LogReg sube progresivamente:
- Val: 0.60
- BackTest: 0.61
- Live: **0.63** ✓

En producción, la **estabilidad temporal**
es más valiosa que el pico en validación.
        """)
        st.success(f"**Modelo elegido:** Logistic Regression")
        st.metric("AUC Live LogReg", "63.0%", "+3.2 pts vs Val")
        st.metric("Lift Decil 1 (Live)", "2.24x", "vs selección aleatoria")

    # ── Distribución de predicciones ──
    if pred_df is not None:
        st.markdown('<div class="section-title">Distribución de Riesgo — Sept 2018</div>',
                    unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)

        alto  = (pred_df["prob_churn"] >= 0.8).sum()
        medio = ((pred_df["prob_churn"] >= 0.6) & (pred_df["prob_churn"] < 0.8)).sum()
        bajo  = (pred_df["prob_churn"] < 0.6).sum()

        with col1:
            st.metric("🔴 Riesgo Alto (≥0.80)", f"{alto:,}",
                      f"{alto/len(pred_df)*100:.1f}% de clientes")
        with col2:
            st.metric("🟠 Riesgo Medio (0.60-0.80)", f"{medio:,}",
                      f"{medio/len(pred_df)*100:.1f}% de clientes")
        with col3:
            st.metric("🟢 Riesgo Bajo (<0.60)", f"{bajo:,}",
                      f"{bajo/len(pred_df)*100:.1f}% de clientes")

        fig2 = px.histogram(pred_df, x="prob_churn", nbins=40,
                            title="Distribución de probabilidades de churn",
                            color_discrete_sequence=["#2E86AB"])
        fig2.add_vline(x=0.8, line_dash="dash", line_color="#E74C3C",
                       annotation_text="Alto riesgo")
        fig2.add_vline(x=0.6, line_dash="dash", line_color="#F18F01",
                       annotation_text="Riesgo medio")
        fig2.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                           xaxis_title="Probabilidad de Churn",
                           yaxis_title="N° Clientes")
        st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════
# PÁGINA 2 — PREDICCIONES
# ══════════════════════════════════════════════════════════
elif pagina == "🎯 Predicciones":
    st.title("🎯 Predicciones — Septiembre 2018")

    if pred_df is None:
        st.error("No se encontró predicciones_churn.csv")
        st.stop()

    # Filtros
    col1, col2, col3 = st.columns(3)
    with col1:
        umbral_min = st.slider("Probabilidad mínima", 0.0, 1.0, 0.5, 0.05)
    with col2:
        n_top = st.selectbox("Mostrar top N clientes", [50, 100, 200, 500, 1000, "Todos"], index=1)
    with col3:
        orden = st.selectbox("Ordenar por", ["Mayor riesgo primero", "Menor riesgo primero"])

    # Filtrar
    df_f = pred_df[pred_df["prob_churn"] >= umbral_min].copy()
    df_f = df_f.sort_values("prob_churn",
                             ascending=(orden == "Menor riesgo primero"))

    if n_top != "Todos":
        df_f = df_f.head(int(n_top))

    # Etiqueta de riesgo
    def nivel_riesgo(p):
        if p >= 0.8: return "🔴 Alto"
        elif p >= 0.6: return "🟠 Medio"
        else: return "🟢 Bajo"

    df_f["nivel_riesgo"] = df_f["prob_churn"].apply(nivel_riesgo)
    df_f["prob_churn_%"] = (df_f["prob_churn"] * 100).round(1).astype(str) + "%"

    # Métricas del filtro
    c1, c2, c3 = st.columns(3)
    c1.metric("Clientes en vista", f"{len(df_f):,}")
    c2.metric("Prob. promedio", f"{df_f['prob_churn'].mean()*100:.1f}%")
    c3.metric("Total predicciones", f"{len(pred_df):,}")

    st.dataframe(
        df_f[["customer_unique_id", "mes", "prob_churn_%", "nivel_riesgo"]].rename(columns={
            "customer_unique_id": "ID Cliente",
            "mes": "Período",
            "prob_churn_%": "Prob. Churn",
            "nivel_riesgo": "Nivel Riesgo"
        }),
        use_container_width=True,
        height=450
    )

    # Descarga
    csv = df_f[["customer_unique_id", "mes", "prob_churn", "nivel_riesgo"]].to_csv(index=False)
    st.download_button(
        "⬇️ Descargar CSV filtrado",
        data=csv,
        file_name="clientes_en_riesgo.csv",
        mime="text/csv"
    )

# ══════════════════════════════════════════════════════════
# PÁGINA 3 — IMPORTANCIA DE VARIABLES
# ══════════════════════════════════════════════════════════
elif pagina == "🔍 Importancia de Variables":
    st.title("🔍 Importancia de Variables")

    imp_df = cargar_importancia()
    drivers_df = cargar_drivers()

    tab1, tab2 = st.tabs(["📊 Comparativa por Modelo", "🎯 Drivers LogReg (Dirección)"])

    with tab1:
        if imp_df is None:
            st.warning("No se encontró importancia_por_modelo.csv")
        else:
            n_vars = st.slider("Número de variables a mostrar", 5, len(imp_df), 15)
            col_logreg = [c for c in imp_df.columns if "logreg" in c.lower()]
            col_hgb    = [c for c in imp_df.columns if "hgb" in c.lower()]
            col_rf     = [c for c in imp_df.columns if "rf" in c.lower()]

            col_final = col_logreg[0] if col_logreg else imp_df.columns[1]
            top = imp_df.nlargest(n_vars, col_final)

            fig = go.Figure()
            colors = {"LogReg": "#1AB374", "HGB": "#E74C3C", "RF": "#2E86AB"}

            if col_logreg:
                fig.add_trace(go.Bar(name="LogReg ✓",
                    x=top[col_logreg[0]], y=top["feature"],
                    orientation="h", marker_color="#1AB374"))
            if col_hgb:
                fig.add_trace(go.Bar(name="HGB",
                    x=top[col_hgb[0]], y=top["feature"],
                    orientation="h", marker_color="#E74C3C", opacity=0.7))
            if col_rf:
                fig.add_trace(go.Bar(name="RF",
                    x=top[col_rf[0]], y=top["feature"],
                    orientation="h", marker_color="#2E86AB", opacity=0.7))

            fig.update_layout(
                barmode="group",
                title=f"Top {n_vars} variables — importancia por modelo (%)",
                xaxis_title="Importancia (%)",
                plot_bgcolor="white", paper_bgcolor="white",
                height=500,
                legend=dict(orientation="h", y=-0.15),
                font=dict(family="Calibri")
            )
            if col_logreg:
                fig.add_vline(x=10, line_dash="dash", line_color="orange",
                              annotation_text="10% threshold")
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Importancia calculada con permutation importance para RF y HGB, "
                       "coeficientes absolutos para LogReg.")

            st.markdown("---")
            st.markdown("#### 📖 Interpretación de negocio")
            col_n1, col_n2 = st.columns(2)
            with col_n1:
                st.success("""
**✅ Distribución equilibrada**
Ninguna variable supera el 12% de importancia.
El modelo aprovecha **múltiples señales** del
comportamiento del cliente en lugar de depender
de una sola variable — señal de robustez.
""")
            with col_n2:
                st.info("""
**🔎 Variables con < 1% de importancia**
`meses_activo`, `n_sellers_sum`, `freight_ratio_sum`
aportan muy poco. En una próxima iteración podrían
eliminarse para simplificar el modelo sin perder AUC.
""")
            st.markdown("""
| Variable | Importancia | Interpretación de negocio |
|----------|------------|--------------------------|
| `comprador_unico` | 11.57% | Compra en una sola categoría → mayor riesgo de churn |
| `installments_max` | 7.74% | Más cuotas → posible estrés financiero del cliente |
| `ordenes_60d` | 7.60% | Actividad reciente: menos órdenes → más riesgo |
| `recencia_rel` / `recencia` | 7.45% / 6.17% | Tiempo sin comprar — señal clásica RFM |
| `lead_min` | 7.21% | Entregas lentas aumentan la insatisfacción |
| `review_max` | 6.86% | Buenas reseñas retienen al cliente |
""")

    with tab2:
        if drivers_df is None:
            st.warning("No se encontró drivers_churn.csv")
        else:
            n_drivers = st.slider("Variables a mostrar", 5, min(20, len(drivers_df)), 15)
            df_d = drivers_df.head(n_drivers).copy()

            if "coef" in df_d.columns:
                df_d = df_d.sort_values("coef")
                df_d["color"] = df_d["coef"].apply(
                    lambda x: "#1AB374" if x < 0 else "#E74C3C")
                df_d["direccion"] = df_d["coef"].apply(
                    lambda x: "↓ Reduce churn" if x < 0 else "↑ Sube churn")

                fig2 = go.Figure(go.Bar(
                    x=df_d["coef"],
                    y=df_d["feature"],
                    orientation="h",
                    marker_color=df_d["color"],
                    text=df_d["direccion"],
                    textposition="outside"
                ))
                fig2.add_vline(x=0, line_color="black", line_width=1)
                fig2.update_layout(
                    title="Drivers de Churn — Coeficientes LogReg (dirección e impacto)",
                    xaxis_title="Coeficiente (+ sube churn / − baja churn)",
                    plot_bgcolor="white", paper_bgcolor="white",
                    height=500, font=dict(family="Calibri")
                )
                st.plotly_chart(fig2, use_container_width=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.error("**↑ Factores que AUMENTAN el churn:**")
                    sube = drivers_df[drivers_df["coef"] > 0].head(6)
                    for _, r in sube.iterrows():
                        st.write(f"• **{r['feature']}** (coef: {r['coef']:.3f})")
                with col2:
                    st.success("**↓ Factores que REDUCEN el churn:**")
                    baja = drivers_df[drivers_df["coef"] < 0].head(6)
                    for _, r in baja.iterrows():
                        st.write(f"• **{r['feature']}** (coef: {r['coef']:.3f})")

                st.markdown("---")
                st.markdown("#### 🧠 Narrativa del modelo")
                st.info("""
**¿Qué perfil de cliente tiene mayor riesgo de churn?**

Un cliente tiene **alta probabilidad de abandono** si:
- Compra siempre en la misma categoría (`comprador_unico` alto)
- Lleva mucho tiempo sin comprar (`recencia` alta)
- Sus pedidos llegan tarde (`lead_min` alto)
- Usa muchas cuotas para pagar (`installments_max` alto)

Por el contrario, un cliente tiene **bajo riesgo** si:
- Compra con frecuencia en los últimos 60 días (`ordenes_60d` alto)
- Tiene buenas experiencias de entrega y reseñas (`review_max` alto)
- Compra en diversas categorías (`comprador_unico` bajo)

**Acción recomendada:** Priorizar retención de clientes con alta recencia,
entregas lentas y poca diversidad de categorías.
""")

# ══════════════════════════════════════════════════════════
# PÁGINA 4 — SHAP
# ══════════════════════════════════════════════════════════
elif pagina == "🧠 SHAP — Explicabilidad":
    st.title("🧠 SHAP — Explicabilidad del Modelo")
    st.caption("LinearExplainer sobre Logistic Regression · Período de Validación")

    shap_vals, shap_data = cargar_shap()

    if shap_vals is None:
        st.warning("No se encontraron shap_values.csv o shap_data.csv")
        st.stop()

    features = list(shap_vals.columns)

    # ── Tab 1: Importancia SHAP (mean |SHAP|) ──
    tab1, tab2 = st.tabs(["📊 Importancia SHAP", "🔵 Beeswarm (dispersión)"])

    with tab1:
        st.markdown("#### Importancia media |SHAP| por variable")
        st.caption("Cuánto contribuye en promedio cada variable a la predicción — sin importar dirección.")

        mean_abs = shap_vals.abs().mean().sort_values(ascending=True)
        n_show = st.slider("Variables a mostrar", 5, len(mean_abs), 15, key="shap_bar")
        mean_abs = mean_abs.tail(n_show)

        fig_bar = go.Figure(go.Bar(
            x=mean_abs.values,
            y=mean_abs.index,
            orientation="h",
            marker_color="#2E86AB",
            text=[f"{v:.4f}" for v in mean_abs.values],
            textposition="outside"
        ))
        fig_bar.update_layout(
            title="Mean |SHAP value| — impacto promedio sobre predicción",
            xaxis_title="Mean |SHAP|",
            plot_bgcolor="white", paper_bgcolor="white",
            height=500, font=dict(family="Calibri")
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.info("""
**Cómo leer este gráfico:**
Barra más larga = variable más influyente en las predicciones del modelo.
A diferencia de la importancia por coeficientes, SHAP mide el impacto
real sobre cada predicción individual y luego los promedia.
        """)

    with tab2:
        st.markdown("#### Dispersión SHAP por variable (beeswarm)")
        st.caption("Cada punto es un cliente. Color = valor de la feature (rojo=alto, azul=bajo).")

        # Ordenar por mean |SHAP| descendente
        order = shap_vals.abs().mean().sort_values(ascending=False)
        n_bee = st.slider("Variables a mostrar", 5, min(20, len(order)), 12, key="shap_bee")
        max_pts = st.slider("Máx. puntos por variable", 100, min(1000, len(shap_vals)), 300, step=100, key="shap_pts")
        top_feats = order.head(n_bee).index.tolist()

        import numpy as np
        # Muestra fija para velocidad
        sample_idx = shap_vals.sample(min(max_pts, len(shap_vals)), random_state=42).index
        fig_bee = go.Figure()

        for i, feat in enumerate(reversed(top_feats)):
            sv   = shap_vals[feat].iloc[sample_idx].values
            fv   = shap_data[feat].iloc[sample_idx].values if feat in shap_data.columns else np.zeros(len(sample_idx))

            # Normalizar color 0-1
            fv_norm = (fv - fv.min()) / (fv.max() - fv.min() + 1e-9)
            colors  = [f"rgb({int(255*v)},{int(80*(1-v))},{int(180*(1-v))})" for v in fv_norm]

            # Jitter vertical
            jitter = np.random.uniform(-0.3, 0.3, size=len(sv))

            fig_bee.add_trace(go.Scatter(
                x=sv,
                y=[i + j for j in jitter],
                mode="markers",
                marker=dict(color=colors, size=4, opacity=0.6),
                name=feat,
                showlegend=False,
                hovertemplate=f"<b>{feat}</b><br>SHAP: %{{x:.4f}}<br>Valor feature: %{{customdata:.3f}}",
                customdata=fv
            ))

        fig_bee.add_vline(x=0, line_color="black", line_width=1.5)
        fig_bee.update_layout(
            title="Beeswarm SHAP — distribución por cliente",
            xaxis_title="SHAP value (impacto en predicción)",
            yaxis=dict(
                tickvals=list(range(n_bee)),
                ticktext=list(reversed(top_feats)),
                showgrid=False
            ),
            plot_bgcolor="white", paper_bgcolor="white",
            height=550, font=dict(family="Calibri")
        )
        st.plotly_chart(fig_bee, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.error("**Puntos a la derecha (SHAP > 0):** aumentan probabilidad de churn")
        with col2:
            st.success("**Puntos a la izquierda (SHAP < 0):** reducen probabilidad de churn")

        st.info("""
**Cómo leer el color:**
🔴 Rojo = valor alto de la feature · 🔵 Azul = valor bajo de la feature

Ejemplo: si `recencia` tiene puntos **rojos a la derecha** → clientes con
alta recencia (mucho tiempo sin comprar) tienen mayor riesgo de churn.
        """)

# ══════════════════════════════════════════════════════════
# PÁGINA 5 — GAIN & LIFT
# ══════════════════════════════════════════════════════════
elif pagina == "📈 Gain & Lift":
    st.title("📈 Gain & Lift Table")
    st.caption("Capacidad del modelo para concentrar churners en los primeros deciles")

    periodo_sel = st.selectbox("Período", ["Val", "BackTest", "Live"], index=2)
    lift_df = cargar_lift(periodo_sel)

    if lift_df is None:
        st.warning(f"No se encontró gain_lift_{periodo_sel.lower()}.csv")
        st.stop()

    col1, col2 = st.columns([3, 2])

    with col1:
        # Rename columns for display
        col_map = {}
        for c in lift_df.columns:
            cl = c.lower()
            if "decil" in cl: col_map[c] = "Decil"
            elif "caso" in cl: col_map[c] = "N° Casos"
            elif "lift" in cl: col_map[c] = "Lift Acumulado"
            elif "gain" in cl: col_map[c] = "Gain %"
            elif "respuesta" in cl and "acum" not in cl: col_map[c] = "N° Respuestas"
            elif "acum" in cl: col_map[c] = "Resp. Acumuladas"
            elif "evento" in cl: col_map[c] = "% Eventos"
        lift_show = lift_df.rename(columns=col_map)
        st.dataframe(lift_show, use_container_width=True, hide_index=True)

    with col2:
        lift_col = [c for c in lift_df.columns if "lift" in c.lower()]
        gain_col = [c for c in lift_df.columns if "gain" in c.lower() and "%" not in c.lower()]
        decil_col = [c for c in lift_df.columns if "decil" in c.lower()]

        if lift_col and decil_col:
            lift1 = lift_df[lift_col[0]].iloc[0]
            gain1 = lift_df[gain_col[0]].iloc[0] if gain_col else "N/A"
            st.metric(f"Lift Decil 1 ({periodo_sel})", f"{lift1}x",
                      "vs selección aleatoria (1.0x)")
            st.metric("Gain Decil 1", f"{gain1}%",
                      "churners capturados en el top 10%")
            st.info(f"""
**Interpretación:**
Contactando solo el **10% superior** de
clientes (Decil 1), se captura el
**{gain1}% de todos los churners** reales.

El modelo es **{lift1}x más eficiente**
que una campaña aleatoria.
            """)

    # Gráfico Gain & Lift
    tab1, tab2 = st.tabs(["Curva de Gain", "Curva de Lift"])

    with tab1:
        gain_col_name = [c for c in lift_df.columns if "gain" in c.lower() and "%" not in c.lower()]
        decil_col_name = [c for c in lift_df.columns if "decil" in c.lower()]
        if gain_col_name and decil_col_name:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=lift_df[decil_col_name[0]], y=lift_df[gain_col_name[0]],
                mode="lines+markers", name=f"Modelo ({periodo_sel})",
                line=dict(color="#1AB374", width=3),
                marker=dict(size=8)
            ))
            fig.add_trace(go.Scatter(
                x=[1, 10], y=[10, 100],
                mode="lines", name="Aleatorio",
                line=dict(color="#CCCCCC", dash="dash")
            ))
            fig.update_layout(
                title=f"Curva de Gain — {periodo_sel}",
                xaxis_title="Decil", yaxis_title="Gain (%)",
                plot_bgcolor="white", paper_bgcolor="white",
                font=dict(family="Calibri")
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        lift_col_name = [c for c in lift_df.columns if "lift" in c.lower()]
        if lift_col_name and decil_col_name:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=lift_df[decil_col_name[0]], y=lift_df[lift_col_name[0]],
                mode="lines+markers", name=f"Lift ({periodo_sel})",
                line=dict(color="#F18F01", width=3),
                marker=dict(size=8)
            ))
            fig2.add_hline(y=1.0, line_dash="dash", line_color="#CCCCCC",
                           annotation_text="Baseline (1.0x)")
            fig2.update_layout(
                title=f"Curva de Lift — {periodo_sel}",
                xaxis_title="Decil", yaxis_title="Lift Acumulado",
                plot_bgcolor="white", paper_bgcolor="white",
                font=dict(family="Calibri")
            )
            st.plotly_chart(fig2, use_container_width=True)

# ══════════════════════════════════════════════════════════
# PÁGINA 5 — PREDICCIÓN INDIVIDUAL
# ══════════════════════════════════════════════════════════
elif pagina == "🤖 Predicción Individual":
    st.title("🤖 Predicción Individual de Churn")
    st.caption("Ingresa los datos de un cliente para obtener su probabilidad de churn")

    if artefacto is None:
        st.error("No se encontró modelo_churn.pkl. Ejecuta el notebook primero.")
        st.stop()

    modelo = artefacto["modelo"]
    features = artefacto["features"]

    st.info(f"El modelo usa **{len(features)} features**. "
            f"Completa los valores del cliente:")

    # Organizar en columnas
    vals = {}
    cols = st.columns(3)

    DESCRIPCIONES = {
        "comprador_unico":    ("Comprador único", "1 si compra a un solo vendedor, 0 si diversifica"),
        "installments_max":   ("Cuotas máximas", "Número máximo de cuotas usado"),
        "ordenes_60d":        ("Órdenes 60 días", "Número de órdenes en últimos 60 días"),
        "recencia_rel":       ("Recencia relativa", "Días relativos sin comprar"),
        "lead_min":           ("Lead time mínimo", "Tiempo mínimo de entrega en días"),
        "review_max":         ("Review máxima", "Calificación máxima de reseñas (1-5)"),
        "n_items_sum":        ("Total ítems", "Total de ítems comprados"),
        "recencia":           ("Recencia", "Días desde última compra"),
        "monto_sum":          ("Monto total", "Gasto total histórico en BRL"),
        "cat_div_ratio":      ("Diversidad categorías", "Ratio de diversidad de categorías"),
        "monto_60d":          ("Monto 60 días", "Gasto en últimos 60 días"),
        "compras_x_mes":      ("Compras por mes", "Frecuencia mensual de compras"),
        "monto_rango":        ("Rango de montos", "Diferencia max-min de montos"),
        "frequency":          ("Frecuencia", "Número total de órdenes"),
        "freight_total_sum":  ("Flete total", "Suma total de fletes pagados"),
        "ordenes_30d":        ("Órdenes 30 días", "Órdenes en últimos 30 días"),
        "n_items_max":        ("Ítems máximos", "Máximo de ítems en una sola orden"),
        "reviews_buenas":     ("Reseñas buenas", "Número de reseñas ≥ 4 estrellas"),
        "monto_90d":          ("Monto 90 días", "Gasto en últimos 90 días"),
        "cat_div_ratio":      ("Diversidad categorías", "Ratio categorías distintas"),
        "dow_distintos":      ("Días distintos", "Días de la semana distintos que compra"),
        "meses_activo":       ("Meses activo", "Meses desde la primera compra"),
        "n_items_max":        ("Ítems máx orden", "Máximo ítems en una orden"),
        "ordenes_60d":        ("Órdenes 60d", "Órdenes en últimos 60 días"),
        "ordenes_30d":        ("Órdenes 30d", "Órdenes en últimos 30 días"),
        "ordenes_180d":       ("Órdenes 180d", "Órdenes en últimos 180 días"),
        "ordenes_90d":        ("Órdenes 90d", "Órdenes en últimos 90 días"),
        "cuotas_uso_ratio":   ("Ratio cuotas", "Proporción de compras con cuotas"),
        "freight_ratio_sum":  ("Ratio flete", "Ratio flete/monto total"),
        "n_categorias_sum":   ("N° categorías", "Categorías distintas compradas"),
        "n_sellers_sum":      ("N° vendedores", "Número de vendedores distintos"),
        "monto_rango":        ("Rango montos", "Variabilidad en montos de compra"),
        "recencia_rel":       ("Recencia relativa", "Recencia normalizada"),
    }

    DEFAULTS = {
        "comprador_unico": 1, "installments_max": 1, "ordenes_60d": 0,
        "recencia_rel": 60, "lead_min": 7, "review_max": 4,
        "n_items_sum": 2, "recencia": 90, "monto_sum": 150.0,
        "cat_div_ratio": 0.5, "monto_60d": 0.0, "compras_x_mes": 0.3,
        "monto_rango": 50.0, "frequency": 1, "freight_total_sum": 20.0,
        "ordenes_30d": 0, "n_items_max": 2, "reviews_buenas": 1,
        "monto_90d": 50.0, "dow_distintos": 2, "meses_activo": 6,
        "ordenes_60d": 0, "ordenes_30d": 0, "ordenes_180d": 1,
        "ordenes_90d": 0, "cuotas_uso_ratio": 0.0, "freight_ratio_sum": 0.15,
        "n_categorias_sum": 1, "n_sellers_sum": 1,
    }

    for i, feat in enumerate(features):
        col = cols[i % 3]
        label, help_txt = DESCRIPCIONES.get(feat, (feat, feat))
        default = DEFAULTS.get(feat, 0.0)
        with col:
            vals[feat] = st.number_input(label, value=float(default),
                                         help=help_txt, key=feat)

    st.divider()
    if st.button("🔮 Calcular Probabilidad de Churn", type="primary", use_container_width=True):
        try:
            X = pd.DataFrame([vals])[features]
            prob = modelo.predict_proba(X)[0][0]  # prob de clase 0 (churn)

            st.markdown("---")
            col1, col2, col3 = st.columns(3)

            with col2:
                if prob >= 0.8:
                    st.error(f"### 🔴 RIESGO ALTO\n## {prob*100:.1f}%\nprobabilidad de churn")
                    st.error("**Acción recomendada:** Contacto inmediato + descuento personalizado")
                elif prob >= 0.6:
                    st.warning(f"### 🟠 RIESGO MEDIO\n## {prob*100:.1f}%\nprobabilidad de churn")
                    st.warning("**Acción recomendada:** Campaña preventiva por email")
                else:
                    st.success(f"### 🟢 RIESGO BAJO\n## {prob*100:.1f}%\nprobabilidad de churn")
                    st.success("**Acción recomendada:** Monitoreo estándar")

                # Gauge
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=prob * 100,
                    domain={"x": [0, 1], "y": [0, 1]},
                    title={"text": "Prob. Churn (%)"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "#E74C3C" if prob >= 0.8 else
                                         "#F18F01" if prob >= 0.6 else "#1AB374"},
                        "steps": [
                            {"range": [0, 60],   "color": "#E8F8F0"},
                            {"range": [60, 80],  "color": "#FEF3E2"},
                            {"range": [80, 100], "color": "#FDECEA"},
                        ],
                        "threshold": {"line": {"color": "black", "width": 3},
                                      "thickness": 0.8, "value": prob * 100}
                    }
                ))
                fig.update_layout(height=280, margin=dict(t=30, b=10))
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error al predecir: {e}")
            st.caption("Verifica que todos los campos estén completos.")

# ══════════════════════════════════════════════════════════
# PÁGINA 6 — IMPACTO ECONÓMICO
# ══════════════════════════════════════════════════════════
elif pagina == "💰 Impacto Económico":
    st.title("💰 Impacto Económico del Modelo")
    st.caption("Comparación: campaña masiva sin modelo vs. campaña dirigida con modelo")

    st.markdown('<div class="section-title">Parámetros del Negocio</div>', unsafe_allow_html=True)

    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        clv = st.number_input(
            "💵 CLV por cliente retenido (USD)",
            min_value=10, max_value=10000, value=300, step=10,
            help="Valor de vida del cliente que evitas perder"
        )
    with col_p2:
        costo_contacto = st.number_input(
            "📧 Costo por contacto (USD)",
            min_value=1, max_value=500, value=5, step=1,
            help="Email, descuento, llamada u otra acción de retención"
        )
    with col_p3:
        total_clientes = st.number_input(
            "👥 Total clientes a evaluar",
            min_value=100, max_value=500000, value=10000, step=100,
            help="Base total sobre la que se aplica la campaña"
        )

    # Parámetros fijos del modelo
    TASA_CHURN      = 0.012        # 1.2% churn=0 en el dataset
    GAIN_MODELO     = 0.2238       # Gain Decil 1 Live = 22.38%
    DECIL           = 0.10         # contactamos el top 10%
    TASA_RETENCION  = 0.30         # asumimos 30% de retención exitosa con acción

    # ── Cálculos ──
    n_contactar_modelo  = int(total_clientes * DECIL)
    n_contactar_masivo  = n_contactar_modelo        # mismo presupuesto, mismo nro contactos

    churners_reales     = int(total_clientes * TASA_CHURN)

    # Con modelo: captura GAIN_MODELO % de todos los churners en el decil 1
    churners_modelo     = int(churners_reales * GAIN_MODELO)
    retenidos_modelo    = int(churners_modelo * TASA_RETENCION)
    costo_modelo        = n_contactar_modelo * costo_contacto
    valor_modelo        = retenidos_modelo * clv
    roi_modelo          = valor_modelo - costo_modelo

    # Sin modelo: en el mismo 10% aleatorio capturas ~10% de los churners (proporcional)
    churners_aleatorio  = int(churners_reales * DECIL)
    retenidos_aleatorio = int(churners_aleatorio * TASA_RETENCION)
    costo_aleatorio     = n_contactar_masivo * costo_contacto
    valor_aleatorio     = retenidos_aleatorio * clv
    roi_aleatorio       = valor_aleatorio - costo_aleatorio

    ahorro_neto         = roi_modelo - roi_aleatorio
    mejora_pct          = ((roi_modelo - roi_aleatorio) / max(abs(roi_aleatorio), 1)) * 100

    st.markdown('<div class="section-title">Comparativa: Con Modelo vs. Sin Modelo</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"""<div class="metric-card" style="background:linear-gradient(135deg,#6c757d,#495057)">
            <div class="metric-value">{n_contactar_modelo:,}</div>
            <div class="metric-label">Clientes contactados (10%)</div></div>""",
            unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="metric-card" style="background:linear-gradient(135deg,#E74C3C,#922B21)">
            <div class="metric-value">{churners_reales:,}</div>
            <div class="metric-label">Churners reales en la base</div></div>""",
            unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card" style="background:linear-gradient(135deg,#1AB374,#0D7A52)">
            <div class="metric-value">${ahorro_neto:,.0f}</div>
            <div class="metric-label">Ganancia adicional con modelo</div></div>""",
            unsafe_allow_html=True)

    st.markdown("---")
    col_sin, col_con = st.columns(2)

    with col_sin:
        st.markdown("### 🎲 Sin Modelo — Campaña Aleatoria")
        st.markdown(f"""
| Métrica | Valor |
|---------|-------|
| Clientes contactados | {n_contactar_masivo:,} |
| Churners capturados | {churners_aleatorio:,} ({DECIL*100:.0f}% del total) |
| Clientes retenidos | {retenidos_aleatorio:,} ({TASA_RETENCION*100:.0f}% éxito) |
| Costo campaña | ${costo_aleatorio:,.0f} |
| Valor recuperado | ${valor_aleatorio:,.0f} |
| **ROI neto** | **${roi_aleatorio:,.0f}** |
""")

    with col_con:
        st.markdown("### 🤖 Con Modelo — Campaña Dirigida (Decil 1)")
        st.markdown(f"""
| Métrica | Valor |
|---------|-------|
| Clientes contactados | {n_contactar_modelo:,} |
| Churners capturados | {churners_modelo:,} ({GAIN_MODELO*100:.1f}% del total) |
| Clientes retenidos | {retenidos_modelo:,} ({TASA_RETENCION*100:.0f}% éxito) |
| Costo campaña | ${costo_modelo:,.0f} |
| Valor recuperado | ${valor_modelo:,.0f} |
| **ROI neto** | **${roi_modelo:,.0f}** |
""")

    st.markdown('<div class="section-title">Visualización del Impacto</div>', unsafe_allow_html=True)

    fig_bar = go.Figure()
    categorias = ["Churners<br>capturados", "Clientes<br>retenidos", "Valor<br>recuperado (USD)", "ROI<br>neto (USD)"]
    vals_sin   = [churners_aleatorio, retenidos_aleatorio, valor_aleatorio, roi_aleatorio]
    vals_con   = [churners_modelo,    retenidos_modelo,    valor_modelo,    roi_modelo]

    fig_bar.add_trace(go.Bar(name="Sin Modelo", x=categorias, y=vals_sin,
                             marker_color="#6c757d"))
    fig_bar.add_trace(go.Bar(name="Con Modelo", x=categorias, y=vals_con,
                             marker_color="#1AB374"))
    fig_bar.update_layout(
        barmode="group",
        title="Comparativa de Impacto",
        height=380,
        legend=dict(orientation="h", y=1.1),
        yaxis_title="Valor",
        plot_bgcolor="white",
        paper_bgcolor="white"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.info(f"""
**Supuestos del cálculo:**
- Tasa de churn real en dataset: **{TASA_CHURN*100:.1f}%** (churn=0, clase minoritaria)
- Gain Decil 1 del modelo (período Live): **{GAIN_MODELO*100:.1f}%** de churners capturados contactando solo el 10%
- Tasa de retención exitosa con acción: **{TASA_RETENCION*100:.0f}%** (estándar de industria e-commerce)
- Ambas estrategias contactan el **mismo número de clientes** (10% de la base)
    """)

# ─── FOOTER ───────────────────────────────────────────────
st.markdown("---")
st.caption("Churn Prediction · Olist Dataset · Grupo 7 · Sprint 4 · Percy Fuentes")
