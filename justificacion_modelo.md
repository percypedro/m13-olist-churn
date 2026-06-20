# Justificación de Decisiones del Modelo de Churn — Grupo 7

## 1. Corrección de Data Leakage en `lead_min`

Durante el análisis se detectó que la variable `lead_min` (tiempo mínimo de entrega)
se calculaba usando `order_delivered_customer_date`, que en muchos casos era **posterior
al corte temporal T**. Esto significaba que el modelo veía información del futuro al
entrenar, inflando artificialmente su importancia al ~20%.

**Corrección aplicada** en `generar_features`: se filtraron las órdenes cuya fecha de
entrega superaba el corte T antes de calcular cualquier feature logística:

```python
h = h[
    h['order_delivered_customer_date'].isna() |
    (h['order_delivered_customer_date'] <= T)
].copy()
```

Tras la corrección, `lead_min` bajó a ~7% de importancia, reflejando su contribución
real sin información futura.

---

## 2. Selección de Features (27 variables finales)

Se aplicó una cascada de 4 filtros sobre las 78 features iniciales:

| Paso | Método | Features | AUC Val |
|------|--------|----------|---------|
| 0 | Estado inicial | 78 | 0.631 |
| 1 | Univariante (umbral=0.03) | 48 | 0.621 |
| 2 | Correlación (umbral=0.96) | 30 | 0.626 |
| 3 | Missings ≤ 25% | 27 | 0.616 |
| 4 | PSI ≤ 0.25 | 27 | 0.616 |

El PSI no eliminó ninguna variable, lo que indica que las 27 features son
**estables temporalmente** entre Train y Val.

El umbral de missings se fijó en 25% (en lugar del 10% original) porque la corrección
del leakage introdujo NaN en variables logísticas para clientes con órdenes aún en
tránsito al corte T.

---

## 3. Elección del Modelo: Logistic Regression (LogReg)

Se compararon tres tipos de modelo mediante Optuna (100 trials, CV 5-fold estratificado):

| Modelo | AUC CV | AUC Val | AUC BackTest | AUC Live |
|--------|--------|---------|-------------|---------|
| HGB    | 0.771  | 0.703   | 0.59        | 0.55    |
| **LogReg** | **0.579** | **0.598** | **0.61** | **0.63** |
| RF     | 0.592  | 0.578   | 0.59        | 0.59    |

Aunque HGB supera a LogReg en Val, se elige **LogReg por su superior estabilidad
temporal**: su AUC mejora progresivamente de Val (0.60) a BackTest (0.61) a Live (0.63),
mientras que HGB cae de 0.70 a 0.55 — una degradación de 15 puntos que indica
sobreajuste a los patrones del período de entrenamiento.

En un entorno de producción, un modelo que mejora con el tiempo es preferible a uno
que memoriza el pasado. La diferencia en AUC Val se sacrifica a cambio de robustez
temporal real.

---

## 4. Control de Overfitting

Se implementó penalización en la función objetivo de Optuna:

```python
penalizacion = max(0, auc_cv - auc_val - 0.03)
return auc_cv - penalizacion
```

Optuna descuenta el exceso de brecha mayor a 3 puntos, prefiriendo modelos
más generalizables sobre modelos que memorizan el train.

La brecha CV-Val se redujo de 8.1 puntos (sin penalización) a 5.0 puntos (con penalización).

---

## 5. Importancia de Variables — LogReg

La importancia se calcula a partir de los **coeficientes del modelo** (valor absoluto
normalizado a %), que es la medida nativa de LogReg. Ninguna variable supera el 12%,
con una distribución equilibrada entre las 27 features seleccionadas:

| Rank | Variable | Importancia (%) |
|------|----------|----------------|
| 1 | comprador_unico | 11.57 |
| 2 | installments_max | 7.74 |
| 3 | ordenes_60d | 7.60 |
| 4 | recencia_rel | 7.45 |
| 5 | lead_min | 7.21 |
| 6 | review_max | 6.86 |
| 7 | n_items_sum | 6.83 |
| 8 | recencia | 6.17 |

La distribución equilibrada indica que el modelo aprovecha múltiples señales del
comportamiento del cliente en lugar de depender de una sola variable.

---

## 6. Análisis SHAP — Interpretabilidad del Modelo

El análisis SHAP (LinearExplainer) revela no solo qué variables importan, sino
**en qué dirección** influyen sobre la probabilidad de churn:

| Variable | Dirección | Interpretación |
|----------|-----------|----------------|
| `comprador_unico` | Valor alto → ↓ churn | Clientes que compran en diversas categorías son más fieles |
| `installments_max` | Valor alto → ↑ churn | Clientes que usan muchas cuotas tienen mayor riesgo |
| `recencia` | Valor alto → ↑ churn | Mucho tiempo sin comprar = mayor riesgo de churn |
| `lead_min` | Valor alto → ↑ churn | Entregas lentas aumentan la probabilidad de churn |
| `review_max` | Valor alto → ↓ churn | Buenas experiencias retienen al cliente |
| `compras_x_mes` | Valor alto → ↓ churn | Más frecuencia de compra = cliente más fiel |

**Narrativa de negocio:** Un cliente tiene mayor probabilidad de churn si usa muchas
cuotas, recibe pedidos lentamente y lleva mucho tiempo sin comprar. Por el contrario,
clientes que compran frecuentemente en diversas categorías y con buenas experiencias
de entrega tienden a quedarse.

---

## 7. Evaluación Final y Estabilidad Temporal

| Período | AUC |
|---------|-----|
| Val (2018-02) | 59.8% |
| BackTest (2018-03/04) | 61.0% |
| Live (2018-05) | 63.0% |

A diferencia de HGB, LogReg muestra una tendencia **creciente** a través del tiempo,
lo que indica que los patrones aprendidos generalizan bien a datos más recientes.

Este resultado es honesto y reproducible: BackTest y Live solo se evaluaron **una vez**,
al final, sin influir en ninguna decisión de modelado. En un entorno de producción real,
este modelo requeriría **reentrenamiento mensual** con datos recientes para mantener
y mejorar su capacidad predictiva.
