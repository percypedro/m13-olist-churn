# Modelo Churn Predicción de Churn en E-Commerce (Olist Dataset) - M13

# Maestrante: Ing. Percy Pedro Fuentes Ramos

Este repositorio contiene el desarrollo completo de un modelo de Machine Learning robusto y profesional enfocado en la **predicción de abandono de clientes (Churn)** utilizando datos históricos de transacciones del comercio electrónico **Olist**. 

El proyecto implementa un enfoque de ingeniería de software para Ciencia de Datos mediante la creación de **mecanismos totalmente reusables**, una fábrica de variables estructurada (*Point-in-Time* sin fuga de información), una cascada rigurosa de selección de atributos y la optimización de hiperparámetros multimodelo.

---

## Arquitectura y Flujo del Proyecto

El notebook `Churm_Olist.ipynb` está estructurado en 14 pasos secuenciales divididos en cuatro grandes etapas:

### 1. Fundación, Limpieza y Horizonte Temporal ($H$)
* **Carga de Fuentes:** Consolidación de datos transaccionales, perfiles de clientes, ítems, métodos de pago, reseñas y datos logísticos.
* **Criterio Estadístico ($H$):** Identificación automática del horizonte crítico de retorno de los usuarios. Se determinó a través del **Percentil 90 (P90) del intervalo entre recompras** que el $90\%$ de los clientes recurrentes regresan en **280 días o menos**.
* **Estructura Temporal Dinámica:** División de la población en ventanas temporales estables para los conjuntos de datos: Entrenamiento (Train), Validación (Validation), Pruebas Fuera de Tiempo (Live / Out-of-Time) y Predicción Ex-Ante.

### 2. Fábrica de Features *Point-in-Time* (77 Variables Predictivas)
Para evitar la **fuga de información (Data Leakage)**, las variables se calculan de manera retroactiva con respecto a un mes de corte específico ($T$). Las variables predictivas generadas se agrupan en las siguientes familias de negocio:
* **RFM / Temporales:** Recencia, frecuencia, intervalos (*gaps*) de compra y evolución temporal.
* **Monetario:** Volúmenes de gasto acumulado, valores promedio y máximos de compra.
* **Logística:** Tiempos de entrega calculados frente a fechas estimadas y demoras reales.
* **Comportamiento del Pedido:** Cantidad de artículos (*items*), diversidad de vendedores (*sellers*), categorías compradas y costos de flete.
* **Pagos & Reseñas:** Métodos de financiamiento (cuotas) y satisfacción acumulada (Reviews).

### 3. Selección de Variables y Entrenamiento
* **Pipeline de Limpieza Reutilizable (`clean_MT`):** Tratamiento controlado de datos faltantes (*missings*) y acotamiento de valores atípicos (*outliers/clipping*) calculados exclusivamente sobre el set de entrenamiento para su replicación en el entorno productivo.
* **Cascada de Reducción Filtro-Wrapper:**
  1. Filtros de tasas de nulos y estabilidad (*PSI - Population Stability Index*).
  2. Análisis de correlación y varianza univariada.
  3. Proceso Wrapper basado en importancia de variables mediante *Random Forest* para seleccionar el top $K$ de atributos más predictivos y estables.
* **Optimización Multimodelo con Optuna:** Búsqueda bayesiana de hiperparámetros evaluando competitivamente tres familias de algoritmos:
  * *Random Forest Classifier*
  * *HistGradientBoosting Classifier*
  * *Logistic Regression* (con Coeficientes Estandarizados para extraer los **Drivers de Churn** del negocio).

### 4. Empaquetado y Predicción Autónoma (Despliegue)
* **Serialización del Artefacto:** Almacenamiento mediante `pickle` de un diccionario maestro (`modelo_churn.pkl`) que congela el modelo ganador, la lista de variables seleccionadas y todos los parámetros de transformación matemática (`clean_params`).
* **Inferencia Limpia:** Script automatizado que toma datos nuevos en frío, ejecuta las transformaciones con cero recálculo y exporta el archivo estructurado `predicciones_churn.csv` ordenado por score de riesgo.

---

## Tecnologías y Librerías Utilizadas

* **Python 3.x**
* **Pandas & NumPy:** Manipulación masiva de matrices de datos y series de tiempo.
* **Scikit-Learn:** Modelado predictivo, transformaciones de datos y métricas de evaluación.
* **Optuna:** Framework de optimización hiperparamétrica automatizada.
* **Matplotlib & Seaborn:** Gráficos estéticos y reportes visuales de la evolución mensual.
* **Openpyxl:** Exportación estructurada de los diccionarios de variables predictivas hacia formatos ejecutivos de Excel.

---

## Resultados del Modelo y Reportes Generados

Al ejecutar el flujo analítico completo, el ecosistema produce los siguientes entregables listos para su consumo por el área de negocio o marketing:

1. **`modelo_churn.pkl`:** El artefacto consolidado con los mejores parámetros encontrados para su despliegue inmediato.
2. **`predicciones_churn.csv`:** Listado oficial de clientes con sus probabilidades individuales de abandono (`prob_churn`), ordenados de manera descendente para enfocar campañas de retención efectivas.
3. **Diccionario de Variables:** Reporte en Excel formateado con la clasificación por familias y la descripción técnica de los 77 inputs de datos procesados.

---

## 🔧 Instrucciones de Configuración y Uso

### 1. Clonar el repositorio e instalar dependencias:
```bash
git clone https://github.com/percypedro/m13-olist-churn.git
cd TU_REPOSITORIO
pip install pandas numpy scikit-learn optuna openpyxl matplotlib seaborn
