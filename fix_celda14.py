"""
fix_celda14.py  ──  Corrige el overfitting en PASO 8 (celda 14) de Churm_Olist.ipynb
Ejecuta este script desde Jupyter con:  %run fix_celda14.py
o desde terminal con:                   python fix_celda14.py
"""

import json, pathlib, textwrap

NOTEBOOK = pathlib.Path("Churm_Olist.ipynb")
CELL_ID  = "85677f21"          # id de la celda PASO 8

NUEVO_SOURCE = textwrap.dedent("""\
    # =====================================================================
    # PASO 8 — Wrapper (refina las features finales por importancia + AUC-val)
    #   Correcciones anti-overfitting aplicadas:
    #   · max_depth  8 → 5        (menos profundidad = menos memorización)
    #   · min_samples_leaf = 50   (hojas con más muestras = más generalización)
    #   · max_features = 0.5      (más diversidad entre árboles = menos varianza)
    #   · columna 'gap' = auc_train − auc_val  (diagnóstico de overfitting directo)
    # =====================================================================
    def wrapper_importancia(df, features, target=TARGET, ks=None, seed=42):
        tr, _ = _tv(df)
        rf = RandomForestClassifier(
            n_estimators=200,
            max_depth=5,            # ← reducido de 8 (principal causa de overfitting)
            min_samples_leaf=50,    # ← regularización: evita hojas con pocos ejemplos
            max_features=0.5,       # ← decorrelaciona los árboles (reduce varianza)
            class_weight='balanced_subsample',
            n_jobs=-1,
            random_state=seed,
        )
        rf.fit(_sane(tr[features]), tr[target])
        imp = pd.Series(rf.feature_importances_, index=features).sort_values(ascending=False)
        if ks is None:
            ks = sorted({k for k in [5, 8, 10, 12, 15, 20, len(features)] if k <= len(features)})
        filas = []
        for k in ks:
            at, av = evaluar_rf(df, imp.head(k).index.tolist(), seed=seed)
            gap = round(at - av, 3) if (at == at and av == av) else float('nan')  # nan-safe
            filas.append((k, at, av, gap))
        return imp, pd.DataFrame(filas, columns=['k_features', 'auc_train', 'auc_val', 'gap'])

    imp, tabla_wrapper = wrapper_importancia(master_clean, features_finales)
    print("Ranking de importancia (RF regularizado — max_depth=5, min_samples_leaf=50):")
    print(imp.round(4).to_string())
""")

# ── lectura ──────────────────────────────────────────────────────────
nb = json.loads(NOTEBOOK.read_text(encoding="utf-8"))

# ── búsqueda y reemplazo ─────────────────────────────────────────────
encontrado = False
for cell in nb["cells"]:
    if cell.get("id") == CELL_ID:
        lineas_nuevas = [l + "\n" for l in NUEVO_SOURCE.splitlines()]
        lineas_nuevas[-1] = lineas_nuevas[-1].rstrip("\n")  # última sin \n final
        cell["source"] = lineas_nuevas
        cell["outputs"] = []          # limpia salida anterior (queda lista para reejecutar)
        cell["execution_count"] = None
        encontrado = True
        break

if not encontrado:
    raise RuntimeError(f"No se encontró la celda con id='{CELL_ID}'. "
                       "¿Cambió el notebook?")

# ── escritura ─────────────────────────────────────────────────────────
NOTEBOOK.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("✓ Celda 14 (PASO 8) actualizada en", NOTEBOOK)
print("  Cambios aplicados:")
print("    max_depth       : 8  →  5")
print("    min_samples_leaf: —  →  50")
print("    max_features    : —  →  0.5")
print("    columna 'gap'   : nueva (auc_train − auc_val)")
print()
print("  Ahora re-ejecuta la celda 14 en Jupyter para ver los nuevos resultados.")
