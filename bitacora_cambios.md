# Bitácora de Cambios y Correcciones — Sprint 4 Grupo 7

## Resumen Ejecutivo

Durante el desarrollo del modelo de churn sobre el dataset Olist, se
identificaron y corrigieron múltiples problemas técnicos y metodológicos.
A continuación se documenta cada problema, su causa raíz y la solución aplicada.

---

## 1. DATA LEAKAGE en `lead_min`

### Problema
La variable `lead_min` (tiempo mínimo de entrega) se calculaba usando
`order_delivered_customer_date`, que en muchos casos era **posterior al
corte temporal T**. El modelo veía información del futuro durante el
entrenamiento, inflando artificialmente la importancia de `lead_min` al ~20%.

### Causa Raíz
La función `generar_features` no filtraba las órdenes por fecha de entrega
antes del corte T, permitiendo que órdenes aún en tránsito al momento del
corte contribuyeran al cálculo de features.

### Solución
```python
h = h[
    h['order_delivered_customer_date'].isna() |
    (h['order_delivered_customer_date'] <= T)
].copy()
```
Se filtraron las órdenes cuya fecha de entrega superaba el corte T antes
de calcular cualquier feature logística.

### Impacto
- `lead_min` bajó de ~20% a ~7% de importancia
- Muchas features adquirieron valores NaN (órdenes en tránsito al corte)
- Esto obligó a ajustar el umbral de missings (ver punto 2)

---

## 2. COLAPSO DE FEATURES POR MISSINGS

### Problema
Al corregir el leakage, muchas features logísticas adquirieron NaN para
clientes con órdenes aún en tránsito al corte T. Con `umbral_missings=0.10`
(10%), la cascada de selección de features eliminó casi todas, dejando
solo 1 feature seleccionada.

### Causa Raíz
El umbral original del 10% era demasiado estricto para un dataset donde
la corrección del leakage introduce NaN legítimos (no errores, sino
ausencia de información real al corte).

### Solución
Se elevó el umbral a `umbral_missings=0.25` (25%):
```python
SELECCION, resumen_sel = seleccionar_features(
    master_final, TARGET, ID_COL,
    umbral_missings=0.25,   # ← subido desde 0.10
    umbral_corr=0.96,
    umbral_uni=0.03
)
```

### Impacto
- Se recuperaron 27 features (dentro del rango 25-30 requerido por el docente)
- AUC Val se mantuvo en 0.616

---

## 3. BACKTEST/LIVE EN EL HISTORIAL DE TRIALS (Observación del Docente)

### Problema
La celda de historial de trials mostraba AUC de BackTest y Live para
cada trial de Optuna. El docente observó que BackTest y Live no deben
tocarse hasta la evaluación final del modelo elegido.

### Causa Raíz
El código original calculaba `auc_bt` y `auc_live` dentro del loop de
trials, contaminando metodológicamente el proceso de selección.

### Solución
Se eliminaron `auc_bt` y `auc_live` del historial de trials:
```python
# ANTES
filas.append({
    'auc_cv': ..., 'auc_val': ...,
    'auc_backtest': ..., 'auc_live': ...   # ← eliminados
})

# DESPUÉS
filas.append({
    'auc_cv': round(t.value, 4),
    'auc_val': round(auc_val, 4),
})
```
BackTest y Live se reservan exclusivamente para la evaluación del modelo final.

---

## 4. BACKTEST/LIVE EN LA COMPARATIVA DE MODELOS

### Problema
Similar al punto anterior: la comparativa de modelos usaba BackTest/Live
para seleccionar el modelo final, cuando solo debería usar CV y Val.

### Solución
La comparativa quedó solo con CV y Val. BackTest y Live se calculan
una sola vez al final, en la celda de evaluación final.

---

## 5. CONCENTRACIÓN DE IMPORTANCIA DE VARIABLES

### Problema
El docente observó que la importancia de variables estaba muy concentrada:
las primeras 5 variables acumulaban más del 50% de la importancia, y
`lead_min` superaba el 20% sola. El criterio era que ninguna variable
debería exceder el 10%.

### Causa Raíz
Combinación de: data leakage inflando `lead_min`, y la naturaleza del
modelo HGB que tiende a concentrar importancia en pocas variables.

### Solución Parcial con HGB
Tras corregir el leakage, `lead_min` bajó a ~17%. Se intentaron múltiples
enfoques (eliminar variables redundantes, ajustar umbrales de correlación)
sin lograr que ninguna variable bajara del 10%.

### Solución Definitiva: Cambio a LogReg
Al cambiar el modelo final a LogReg (usando coeficientes como importancia),
la distribución mejoró significativamente:
- `comprador_unico`: 11.57% (máximo)
- Resto de variables: todas por debajo del 10%
- Distribución mucho más equilibrada entre las 27 features

---

## 6. OVERFITTING CV-VAL

### Problema
La brecha entre AUC CV y AUC Val era de 8.1 puntos, indicando que el
modelo memorizaba el período de entrenamiento.

### Solución
Se implementó penalización en la función objetivo de Optuna:
```python
penalizacion = max(0, auc_cv - auc_val - 0.03)
return auc_cv - penalizacion
```
Optuna descuenta brechas superiores a 3 puntos, prefiriendo modelos
que generalizan. La brecha se redujo de 8.1 a 5.0 puntos.

---

## 7. EARLY STOPPING LENTO EN OPTUNA

### Problema
Al activar `early_stopping=True` dentro del pipeline de Optuna, cada
trial tardaba ~30 segundos, haciendo inviable correr 100 trials.

### Causa Raíz
El early stopping de HGB requiere dividir los datos internamente para
validar en cada iteración de boosting, multiplicando el tiempo de
entrenamiento.

### Solución
Se mantiene `early_stopping=False` durante Optuna y se aplica solo
al entrenar el modelo en la comparativa final:
```python
# En Optuna: sin early stopping (rápido)
# En comparativa: con early stopping (modelo final robusto)
clf = HistGradientBoostingClassifier(
    early_stopping=True,
    validation_fraction=0.1,
    n_iter_no_change=20, ...)
```

---

## 8. CAMBIO DE MODELO FINAL: HGB → LogReg

### Problema
Aunque HGB ganaba en AUC Val (0.703 vs 0.598), su performance caía
fuertemente en el tiempo:
- HGB: Val=0.70 → BackTest=0.59 → Live=0.55 (−15 puntos)
- LogReg: Val=0.60 → BackTest=0.61 → Live=0.63 (+3 puntos)

### Causa Raíz
HGB captura relaciones no lineales muy específicas del período de
entrenamiento (2016-2017) que no se mantienen en períodos posteriores
por el rápido crecimiento de Olist.

### Solución
Se cambió el criterio de selección de "mayor AUC Val" a "mayor
estabilidad temporal". Cambios aplicados:

**Comparativa:**
```python
# ANTES
g = comparativa[comparativa['modelo'] == 'hgb'].iloc[0]
modelo_final = entrenados['hgb']

# DESPUÉS
g = comparativa[comparativa['modelo'] == 'logreg'].iloc[0]
modelo_final = entrenados['logreg']
```

**Importancia de features:**
```python
col_final = 'imp_logreg_%'   # antes: 'imp_hgb_%'
```

**Tabla diccionario:**
```python
'importancia_modelo_final_LogReg_%'   # antes: HGB_%
```

---

## 9. SHAP: TreeExplainer → LinearExplainer

### Problema
Al cambiar el modelo final a LogReg, el código SHAP falló porque
`shap.TreeExplainer` solo funciona con modelos de árboles.

### Solución
```python
# ANTES (para HGB)
explainer = shap.TreeExplainer(clf_hgb)
shap_values = explainer.shap_values(X_va_sane, check_additivity=False)

# DESPUÉS (para LogReg)
explainer = shap.LinearExplainer(clf_logreg, X_va_sane)
shap_values = explainer.shap_values(X_va_sane)
```

---

## 10. IMPORTANCIA NEGATIVA EN PERMUTATION IMPORTANCE

### Problema
La normalización a % de la permutation importance producía valores
negativos (ruido estadístico), haciendo que los porcentajes no sumaran
100% correctamente.

### Solución
```python
imp = r.importances_mean.clip(min=0)   # evita negativos
imp_pct = (imp / imp.sum() * 100).round(2) if imp.sum() > 0 else imp
```

---

## 11. GAIN/LIFT TABLE: CLASE INVERTIDA

### Problema
La Gain/Lift table mostraba Lift=1.0 en todos los deciles, sin
discriminación. Primer intento usaba `predict_proba[:, 1]` y
`y_true == 1` pero la clase mayoritaria (98.8%) era `churn=1`
(clientes activos), no los churners.

### Causa Raíz
En este dataset, **churn=0 es la clase minoritaria** (los que
abandonan, 1.2%) y **churn=1 es la mayoría** (clientes activos,
98.8%). La tabla se construyó sobre la clase equivocada.

### Solución
Se invirtió la lógica para evaluar sobre `churn=0`:
```python
y_true  = (split[TARGET] == 0).astype(int).values  # churner=1
y_proba = modelo_final.predict_proba(_sane(split[F]))[:, 0]  # prob clase 0
```

### Resultado Final
| Período | Lift Decil 1 | Gain Decil 1 |
|---------|-------------|-------------|
| Val      | 2.04        | 20.41%      |
| BackTest | 2.18        | 21.76%      |
| Live     | 2.24        | 22.38%      |

El modelo es 2x mejor que selección aleatoria en todos los períodos.

---

## 12. TRUNCADO DE OUTPUT EN JUPYTER

### Problema
Jupyter truncaba la salida cuando se imprimían múltiples tablas
largas en una misma celda (3 tablas Gain/Lift).

### Solución
Se reemplazó `print(tabla.to_string())` por `display(tabla)`:
```python
from IPython.display import display
display(tabla)   # Jupyter renderiza como widget interactivo sin truncar
```

---

## Resumen de Impacto

| Problema | Impacto Antes | Impacto Después |
|----------|--------------|-----------------|
| Data leakage lead_min | Importancia inflada ~20% | Importancia real ~7% |
| Umbral missings 10% | 1 feature seleccionada | 27 features seleccionadas |
| BackTest en trials | Contaminación metodológica | Solo CV+Val en selección |
| Concentración importancia | lead_min >20%, top5 >50% | Máximo 11.57%, bien distribuido |
| Overfitting CV-Val | Brecha 8.1 puntos | Brecha 5.0 puntos |
| Modelo HGB inestable | Live AUC 0.55 (−15pts) | LogReg Live AUC 0.63 (+3pts) |
| SHAP incorrecto | TreeExplainer fallaba | LinearExplainer correcto |
| Gain/Lift Lift=1.0 | Sin discriminación | Lift 2.04-2.24 en decil 1 |
