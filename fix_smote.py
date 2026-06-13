"""
fix_smote.py  ──  Corrige el desbalanceo de clases en Churm_Olist.ipynb
                  Agrega una celda de SMOTE entre PASO 9 y PASO 10.

Ejecuta desde Jupyter con:  %run fix_smote.py
o desde terminal:           python fix_smote.py
"""

import json, pathlib, textwrap

NOTEBOOK      = pathlib.Path("Churm_Olist.ipynb")
CELL_ID_AFTER = "585e7fc8"   # id de la celda PASO 9 (justo antes de PASO 10)
CELL_ID_PASO10 = "ff8ecf98"  # id de la celda PASO 10 (Optuna) — se modifica para usar datos balanceados

# ── 1. NUEVA CELDA: diagnóstico + SMOTE ──────────────────────────────
CELDA_SMOTE = textwrap.dedent("""\
    # =====================================================================
    # PASO 9B — Diagnóstico de desbalanceo y corrección con SMOTE
    # =====================================================================
    # El dataset tiene ~98.8% churn=1 y ~1.2% churn=0 → desbalanceo extremo.
    # SMOTE genera ejemplos sintéticos de la clase minoritaria (churn=0)
    # SOLO en el conjunto de entrenamiento; val/backtest/live no se tocan.
    # =====================================================================
    try:
        from imblearn.over_sampling import SMOTE
    except ImportError:
        import subprocess, sys
        subprocess.check_call([sys.executable, "-m", "pip", "install", "imbalanced-learn", "-q"])
        from imblearn.over_sampling import SMOTE

    # Diagnóstico antes del SMOTE
    tr_raw = master_final[master_final['rol'] == 'Train']
    print("=== DISTRIBUCIÓN DE CLASES (ANTES DEL SMOTE) ===")
    conteo = tr_raw[TARGET].value_counts()
    total  = len(tr_raw)
    print(f"  churn=0 (no churn): {conteo.get(0, 0):>6,}  ({conteo.get(0,0)/total*100:.1f}%)")
    print(f"  churn=1 (churn)   : {conteo.get(1, 0):>6,}  ({conteo.get(1,0)/total*100:.1f}%)")
    print(f"  Ratio de desbalanceo: 1 : {conteo.get(1,0)//max(conteo.get(0,1),1)}")

    # Aplicar SMOTE solo al training
    # sampling_strategy=0.3 → la clase minoritaria quedará al 30% de la mayoritaria
    # (no es necesario llegar a 50/50; un ratio de 30% ya corrige bien el sesgo)
    smote = SMOTE(sampling_strategy=0.3, random_state=42, k_neighbors=5)

    X_tr_raw = _sane(tr_raw[SELECCION])
    y_tr_raw = tr_raw[TARGET]

    X_tr_bal, y_tr_bal = smote.fit_resample(X_tr_raw, y_tr_raw)

    print("\\n=== DISTRIBUCIÓN DE CLASES (DESPUÉS DEL SMOTE) ===")
    conteo_bal = y_tr_bal.value_counts()
    total_bal  = len(y_tr_bal)
    print(f"  churn=0 (no churn): {conteo_bal.get(0, 0):>6,}  ({conteo_bal.get(0,0)/total_bal*100:.1f}%)")
    print(f"  churn=1 (churn)   : {conteo_bal.get(1, 0):>6,}  ({conteo_bal.get(1,0)/total_bal*100:.1f}%)")
    print(f"  Filas de train balanceado: {total_bal:,}  (era {total:,})")
    print("\\nSMOTE aplicado correctamente. Val / BackTest / Live sin modificar.")
""")

# ── 2. CELDA PASO 10 MODIFICADA: usa datos balanceados ───────────────
CELDA_PASO10_NUEVA = textwrap.dedent("""\
    # =====================================================================
    # PASO 10 (final) — Optuna compara 3 modelos (RF / HGB / LogReg)
    #   Usa X_tr_bal / y_tr_bal (training balanceado con SMOTE del PASO 9B)
    # =====================================================================
    import optuna
    from tqdm import tqdm
    from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    from sklearn.utils.class_weight import compute_sample_weight
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    F  = SELECCION
    va = master_final[master_final['rol'] == 'Val']
    bt = master_final[master_final['rol'] == 'BackTest']
    lv = master_final[master_final['rol'] == 'Live']

    # Pesos de muestra sobre el training YA BALANCEADO
    sw_bal = compute_sample_weight('balanced', y_tr_bal)

    def construir_modelo(p):
        if p['modelo'] == 'rf':
            return RandomForestClassifier(
                n_estimators=p['rf_n_estimators'], max_depth=p['rf_max_depth'],
                min_samples_leaf=p['rf_min_samples_leaf'], max_features=p['rf_max_features'],
                class_weight='balanced_subsample', n_jobs=-1, random_state=42)
        if p['modelo'] == 'hgb':
            return HistGradientBoostingClassifier(
                learning_rate=p['hgb_lr'], max_iter=p['hgb_max_iter'],
                max_leaf_nodes=p['hgb_leaves'], min_samples_leaf=p['hgb_min_leaf'],
                l2_regularization=p['hgb_l2'], early_stopping=False, random_state=42)
        return make_pipeline(StandardScaler(),
                LogisticRegression(C=p['lr_C'], class_weight='balanced',
                                   max_iter=2000, random_state=42))

    def ajustar_bal(m, p):
        """Entrena sobre el dataset balanceado (X_tr_bal, y_tr_bal)."""
        if p['modelo'] == 'hgb':
            m.fit(X_tr_bal, y_tr_bal, sample_weight=sw_bal)
        else:
            m.fit(X_tr_bal, y_tr_bal)
        return m

    def objetivo(trial):
        tipo = trial.suggest_categorical('modelo', ['rf', 'hgb', 'logreg'])
        if tipo == 'rf':
            p = dict(modelo='rf',
                     rf_n_estimators=trial.suggest_int('rf_n_estimators', 100, 300, step=50),
                     rf_max_depth=trial.suggest_int('rf_max_depth', 3, 6),
                     rf_min_samples_leaf=trial.suggest_int('rf_min_samples_leaf', 20, 200, log=True),
                     rf_max_features=trial.suggest_float('rf_max_features', 0.3, 0.7))
        elif tipo == 'hgb':
            p = dict(modelo='hgb',
                     hgb_lr=trial.suggest_float('hgb_lr', 0.01, 0.3, log=True),
                     hgb_max_iter=trial.suggest_int('hgb_max_iter', 100, 600, step=50),
                     hgb_leaves=trial.suggest_int('hgb_leaves', 8, 64),
                     hgb_min_leaf=trial.suggest_int('hgb_min_leaf', 20, 300, log=True),
                     hgb_l2=trial.suggest_float('hgb_l2', 1e-3, 10, log=True))
        else:
            p = dict(modelo='logreg', lr_C=trial.suggest_float('lr_C', 1e-3, 100, log=True))
        m = ajustar_bal(construir_modelo(p), p)
        auc_val = roc_auc_score(va[TARGET], m.predict_proba(_sane(va[F]))[:, 1])
        auc_bt  = roc_auc_score(bt[TARGET], m.predict_proba(_sane(bt[F]))[:, 1])
        return min(auc_val, auc_bt)

    N_TRIALS = 45
    barra = tqdm(total=N_TRIALS, desc="Optuna 3 modelos (SMOTE)")
    study = optuna.create_study(direction='maximize')
    study.optimize(objetivo, n_trials=N_TRIALS,
                   callbacks=[lambda s, t: (barra.update(1),
                                            barra.set_postfix(best=round(s.best_value, 4)))])
    barra.close()
    print("\\nEstudio terminado:", len(study.trials), "trials")
""")


# ── 3. Aplicar los cambios al notebook ───────────────────────────────
nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))

def source_to_lines(text):
    lines = text.splitlines(keepends=False)
    return [l + "\n" for l in lines[:-1]] + ([lines[-1]] if lines else [])

# Construir nueva celda SMOTE
nueva_celda = {
    "cell_type": "code",
    "id": "paso09b_smote",
    "metadata": {},
    "source": source_to_lines(CELDA_SMOTE),
    "outputs": [],
    "execution_count": None,
}

# Buscar índice de la celda PASO 9 y de la celda PASO 10
idx_paso9  = next((i for i, c in enumerate(nb["cells"]) if c.get("id") == CELL_ID_AFTER), None)
idx_paso10 = next((i for i, c in enumerate(nb["cells"]) if c.get("id") == CELL_ID_PASO10), None)

if idx_paso9 is None:
    raise RuntimeError(f"No se encontró PASO 9 (id={CELL_ID_AFTER})")
if idx_paso10 is None:
    raise RuntimeError(f"No se encontró PASO 10 (id={CELL_ID_PASO10})")

# Insertar nueva celda después de PASO 9
nb["cells"].insert(idx_paso9 + 1, nueva_celda)

# Actualizar índice de PASO 10 (desplazado por la inserción)
idx_paso10 = next(i for i, c in enumerate(nb["cells"]) if c.get("id") == CELL_ID_PASO10)
nb["cells"][idx_paso10]["source"] = source_to_lines(CELDA_PASO10_NUEVA)
nb["cells"][idx_paso10]["outputs"] = []
nb["cells"][idx_paso10]["execution_count"] = None

NOTEBOOK.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")

print("✓ Notebook actualizado correctamente.")
print()
print("  Celdas modificadas / agregadas:")
print("    [NUEVA]     PASO 9B — Diagnóstico de desbalanceo + SMOTE")
print("    [MODIFICADA] PASO 10 — Optuna ahora entrena con X_tr_bal / y_tr_bal")
print()
print("  Pasos para re-ejecutar:")
print("    1. Corre el notebook desde PASO 9B hasta el final (Kernel → Run Below)")
print("    2. Si falta imbalanced-learn, la celda lo instala automáticamente")
print()
print("  Qué esperar después del SMOTE:")
print("    · Menos diferencia entre auc_train y auc_val (menos overfitting)")
print("    · El modelo aprenderá mejor la clase minoritaria (churn=0)")
print("    · Precision / Recall de churn=0 mejorarán respecto a la versión anterior")
