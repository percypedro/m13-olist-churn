import json, re

path = r"C:\Repositorios\m13-olist-churn\Churm_Olist_sprint_3_grupo_7_Percy Fuentes.ipynb"

with open(path, "r", encoding="utf-8") as f:
    nb = json.load(f)

OLD_LINES = [
    "# PASO 10 — RESULTADOS TRIAL POR TRIAL (CV + Val + BackTest + Live)\n",
    "# =====================================================================\n",
    "filas = []\n",
    "for t in study.trials:\n",
    "    if t.value is None:\n",
    "        continue\n",
    "    p = t.params\n",
    "    est = construir_estimador(p)\n",
    "    est.fit(X_tr, y_tr)   # el pipeline balancea internamente\n",
    "\n",
    "    auc_val  = roc_auc_score(va[TARGET], est.predict_proba(_sane(va[F]))[:, 1])\n",
    "    auc_bt   = roc_auc_score(bt[TARGET], est.predict_proba(_sane(bt[F]))[:, 1])\n",
    "    auc_live = roc_auc_score(lv[TARGET], est.predict_proba(_sane(lv[F]))[:, 1])\n",
    "\n",
    "    filas.append({\n",
    "        'trial':   t.number,\n",
    "        'modelo':  p.get('modelo', '-'),\n",
    "        'auc_cv':  round(t.value, 4),\n",
    "        'auc_val': round(auc_val, 4),\n",
    "        'auc_backtest': round(auc_bt, 4),\n",
    "        'auc_live': round(auc_live, 4),\n",
    "    })\n",
    "\n",
    "trials_df = pd.DataFrame(filas).sort_values('auc_cv', ascending=False).reset_index(drop=True)\n",
    "mejor_trial = study.best_trial.number\n",
    "trials_df['mejor'] = trials_df['trial'].apply(lambda x: '★' if x == mejor_trial else '')\n",
    "\n",
    "print(f\"=== HISTORIAL DE TRIALS — CV vs Val vs BackTest vs Live ===\\n\")\n",
    "pd.set_option('display.max_rows', None)\n",
    "pd.set_option('display.width', 200)\n",
    "print(trials_df.to_string(index=False))\n",
    "pd.reset_option('display.max_rows')\n",
    "\n",
    "trials_df.to_csv(os.path.join(PATH, 'optuna_trials_completo.csv'), index=False)\n",
    "print(f\"\\nGuardado: optuna_trials_completo.csv  |  Mejor trial CV: #{mejor_trial}\")",
]

NEW_LINES = [
    "# PASO 10 — RESULTADOS TRIAL POR TRIAL (CV + Val)\n",
    "# NOTA: BackTest y Live se reservan exclusivamente para la evaluación del modelo final.\n",
    "# =====================================================================\n",
    "filas = []\n",
    "for t in study.trials:\n",
    "    if t.value is None:\n",
    "        continue\n",
    "    p = t.params\n",
    "    est = construir_estimador(p)\n",
    "    est.fit(X_tr, y_tr)   # el pipeline balancea internamente\n",
    "\n",
    "    auc_val = roc_auc_score(va[TARGET], est.predict_proba(_sane(va[F]))[:, 1])\n",
    "\n",
    "    filas.append({\n",
    "        'trial':   t.number,\n",
    "        'modelo':  p.get('modelo', '-'),\n",
    "        'auc_cv':  round(t.value, 4),\n",
    "        'auc_val': round(auc_val, 4),\n",
    "    })\n",
    "\n",
    "trials_df = pd.DataFrame(filas).sort_values('auc_cv', ascending=False).reset_index(drop=True)\n",
    "mejor_trial = study.best_trial.number\n",
    "trials_df['mejor'] = trials_df['trial'].apply(lambda x: '★' if x == mejor_trial else '')\n",
    "\n",
    "print(f\"=== HISTORIAL DE TRIALS — CV vs Val ===\\n\")\n",
    "pd.set_option('display.max_rows', None)\n",
    "pd.set_option('display.width', 200)\n",
    "print(trials_df.to_string(index=False))\n",
    "pd.reset_option('display.max_rows')\n",
    "\n",
    "trials_df.to_csv(os.path.join(PATH, 'optuna_trials_completo.csv'), index=False)\n",
    "print(f\"\\nGuardado: optuna_trials_completo.csv  |  Mejor trial CV: #{mejor_trial}\")",
]

changed = False
for cell in nb["cells"]:
    if cell["cell_type"] != "code":
        continue
    src = cell["source"]
    # Buscar la celda que contiene el comentario del paso 10 trial por trial
    combined = "".join(src)
    if "PASO 10 — RESULTADOS TRIAL POR TRIAL" in combined and "auc_backtest" in combined:
        # Reconstruir la fuente: mantener la primera línea (separador ===) y reemplazar el resto
        # Encontrar índice de la línea del título
        new_src = []
        i = 0
        while i < len(src):
            if "PASO 10 — RESULTADOS TRIAL POR TRIAL" in src[i]:
                # Insertar nuevas líneas desde este punto
                new_src.extend(NEW_LINES)
                # Saltar hasta el final de la celda (ya tenemos todo)
                break
            else:
                new_src.append(src[i])
            i += 1
        cell["source"] = new_src
        # Limpiar outputs para que no muestre datos viejos con backtest
        cell["outputs"] = []
        cell["execution_count"] = None
        changed = True
        print(f"✓ Celda modificada: {len(new_src)} líneas")
        break

if not changed:
    print("✗ No se encontró la celda objetivo.")

with open(path, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print("✓ Notebook guardado.")
