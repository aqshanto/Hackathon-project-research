#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, math, pickle, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 20260830

def import_sklearn():
    global ColumnTransformer, ExtraTreesRegressor, HistGradientBoostingRegressor
    global RandomForestRegressor, SimpleImputer, LinearRegression
    global mean_absolute_error, mean_squared_error, median_absolute_error, r2_score
    global Pipeline, OneHotEncoder, StandardScaler, DecisionTreeRegressor
    try:
        from sklearn.compose import ColumnTransformer
        from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error, r2_score
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
        from sklearn.tree import DecisionTreeRegressor
    except ModuleNotFoundError as e:
        raise RuntimeError(
            "scikit-learn is not installed in the current container. "
            "Build/use fincluster-regression:1.0 before running screen."
        ) from e


def now_utc():
    return datetime.now(timezone.utc).isoformat()

def find_col(df, names):
    m = {str(c).lower(): c for c in df.columns}
    for n in names:
        if n.lower() in m:
            return m[n.lower()]
    return None

def detect_tx(df):
    c = find_col(df, ["transaction_id", "tx_id", "transaction_uuid", "uuid"])
    if c is None:
        raise RuntimeError(f"transaction id column not found: {list(df.columns)}")
    return c

def detect_target(df):
    c = find_col(df, ["service_time_ms","median_service_time_ms","service_time_ms_median","service_time_median_ms","median_service_ms","median_ms"])
    if c is not None:
        return c
    for col in df.columns:
        lc = str(col).lower()
        if "median" in lc and ("service" in lc or "time" in lc):
            return col
    raise RuntimeError(f"target column not found: {list(df.columns)}")

def detect_type(df):
    c = find_col(df, ["type","transaction_type","tx_type"])
    if c is None:
        raise RuntimeError("transaction type column not found")
    return c

def detect_node(df):
    c = find_col(df, ["node_profile","node","node_label","profile"])
    if c is not None:
        return c
    for col in df.columns:
        lc = str(col).lower()
        if "node" in lc and ("profile" in lc or "label" in lc):
            return col
    raise RuntimeError("node profile column not found")

def optional(df, names):
    return find_col(df, names)

def normalize_node(v):
    s = str(v).strip().lower()
    return {"low":"Low","medium":"Medium","high":"High"}.get(s, str(v).strip())

def safe_ohe():
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)

def validate_split(train, val):
    tx = detect_tx(train)
    if detect_tx(val) != tx:
        raise RuntimeError("train/validation transaction-id column mismatch")
    if len(train) != 2100 or train[tx].nunique() != 700:
        raise RuntimeError(f"unexpected train shape: rows={len(train)} tx={train[tx].nunique()}")
    if len(val) != 450 or val[tx].nunique() != 150:
        raise RuntimeError(f"unexpected validation shape: rows={len(val)} tx={val[tx].nunique()}")
    overlap = set(train[tx].astype(str)) & set(val[tx].astype(str))
    if overlap:
        raise RuntimeError(f"group leakage detected: {len(overlap)} shared transaction ids")
    if not (train.groupby(tx).size() == 3).all():
        raise RuntimeError("train does not have exactly three node rows per transaction")
    if not (val.groupby(tx).size() == 3).all():
        raise RuntimeError("validation does not have exactly three node rows per transaction")
    return tx

def feature_policy(df):
    typ = detect_type(df)
    node = detect_node(df)
    amount = optional(df, ["amount"])
    old_org = optional(df, ["oldbalanceOrg","oldbalanceorig","old_balance_org"])
    old_dest = optional(df, ["oldbalanceDest","oldbalancedest","old_balance_dest"])
    step = optional(df, ["step"])
    missing = [name for name,col in [("amount",amount),("oldbalanceOrg",old_org),("oldbalanceDest",old_dest)] if col is None]
    if missing:
        raise RuntimeError(f"missing required pre-routing features: {missing}")
    sets = {
        "node_only":[node],
        "type_node":[typ,node],
        "full_no_step":[typ,amount,old_org,old_dest,node],
    }
    if step is not None:
        sets["full_with_step"]=[typ,amount,old_org,old_dest,step,node]
    return {
        "type_col":typ,
        "node_col":node,
        "amount_col":amount,
        "oldbalanceOrg_col":old_org,
        "oldbalanceDest_col":old_dest,
        "step_col":step,
        "feature_sets":sets,
    }

def split_cols(features, typ, node):
    cats = [c for c in features if c in (typ,node)]
    nums = [c for c in features if c not in cats]
    return cats, nums

def preprocessor(cats, nums):
    parts=[]
    if nums:
        parts.append(("num", Pipeline([
            ("imputer",SimpleImputer(strategy="median")),
            ("scale",StandardScaler()),
        ]), nums))
    if cats:
        parts.append(("cat", Pipeline([
            ("imputer",SimpleImputer(strategy="most_frequent")),
            ("onehot",safe_ohe()),
        ]), cats))
    return ColumnTransformer(parts, remainder="drop")

def models():
    return {
        "LinearRegression": lambda: LinearRegression(),
        "DecisionTree": lambda: DecisionTreeRegressor(random_state=SEED),
        "RandomForest": lambda: RandomForestRegressor(n_estimators=300,random_state=SEED,n_jobs=1),
        "ExtraTrees": lambda: ExtraTreesRegressor(n_estimators=300,random_state=SEED,n_jobs=1),
        "HistGradientBoosting": lambda: HistGradientBoostingRegressor(max_iter=200,random_state=SEED),
    }

def calc(y,p):
    y=np.asarray(y,float); p=np.asarray(p,float)
    ae=np.abs(y-p)
    return {
        "MAE_ms":float(mean_absolute_error(y,p)),
        "RMSE_ms":float(math.sqrt(mean_squared_error(y,p))),
        "R2":float(r2_score(y,p)),
        "MedianAE_ms":float(median_absolute_error(y,p)),
        "P95_AE_ms":float(np.percentile(ae,95)),
        "MaxAE_ms":float(ae.max()),
    }

def inspect(root, out):
    frozen=root/"data/final_training_data_v1/splits"
    train_path=frozen/"train.csv"; val_path=frozen/"validation.csv"; test_path=frozen/"test.csv"
    for p in [train_path,val_path,test_path]:
        if not p.exists(): raise FileNotFoundError(p)
    train=pd.read_csv(train_path); val=pd.read_csv(val_path)
    tx=validate_split(train,val)
    target=detect_target(train)
    if detect_target(val)!=target: raise RuntimeError("target mismatch train/validation")
    pol=feature_policy(train)
    if any(target in cols for cols in pol["feature_sets"].values()):
        raise RuntimeError("target leakage in feature policy")
    report={
        "created_utc":now_utc(),
        "test_set_loaded":False,
        "train_rows":len(train),
        "validation_rows":len(val),
        "train_transactions":int(train[tx].nunique()),
        "validation_transactions":int(val[tx].nunique()),
        "group_leakage":0,
        "target":target,
        "transaction_id":tx,
        "feature_policy":pol,
        "notes":[
            "transaction_id is grouping metadata only and forbidden as predictor",
            "newbalance*, fraud labels, names, target-derived timing fields, and future runtime state are excluded",
            "node_profile is treated as a composite categorical node descriptor",
            "step is an explicit ablation candidate if present",
        ]
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"feature_policy.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    pd.DataFrame({"column":train.columns,"dtype":[str(train[c].dtype) for c in train.columns]}).to_csv(out/"train_schema.csv",index=False)
    print("="*72)
    print("FinCluster REGRESSION v1 | INSPECT")
    print("="*72)
    print(f"Train rows / transactions      = {len(train)} / {train[tx].nunique()}")
    print(f"Validation rows / transactions = {len(val)} / {val[tx].nunique()}")
    print("Train-validation group leakage = 0")
    print("TEST_SET_LOADED = FALSE")
    print(f"Target = {target}")
    print(f"Transaction ID = {tx} [GROUPING ONLY; FORBIDDEN AS PREDICTOR]")
    print("FEATURE SETS:")
    for k,v in pol["feature_sets"].items():
        print(f"  {k}: {v}")
    print("INSPECT_STATUS = PASS")
    print(f"Output: {out}")
    print("="*72)

def screen(root,out):
    import_sklearn()
    frozen=root/"data/final_training_data_v1/splits"
    train_path=frozen/"train.csv"; val_path=frozen/"validation.csv"; test_path=frozen/"test.csv"
    if not test_path.exists(): raise FileNotFoundError(test_path)
    train=pd.read_csv(train_path); val=pd.read_csv(val_path)
    tx=validate_split(train,val)
    target=detect_target(train)
    typ=detect_type(train); node=detect_node(train); pol=feature_policy(train)
    ytr=pd.to_numeric(train[target],errors="raise").to_numpy(float)
    yv=pd.to_numeric(val[target],errors="raise").to_numpy(float)

    out.mkdir(parents=True,exist_ok=True)
    model_dir=out/"screening_models"; pred_dir=out/"validation_predictions"
    model_dir.mkdir(exist_ok=True); pred_dir.mkdir(exist_ok=True)
    rows=[]; node_rows=[]; type_rows=[]

    for fs,features in pol["feature_sets"].items():
        cats,nums=split_cols(features,typ,node)
        for mname,factory in models().items():
            pipe=Pipeline([("preprocess",preprocessor(cats,nums)),("model",factory())])
            Xtr=train[features].copy(); Xv=val[features].copy()
            t0=time.perf_counter(); pipe.fit(Xtr,ytr); fit_s=time.perf_counter()-t0
            p0=time.perf_counter(); pred=pipe.predict(Xv); pred_s=time.perf_counter()-p0
            train_pred=pipe.predict(Xtr)
            vm=calc(yv,pred); tm=calc(ytr,train_pred)
            model_path=model_dir/f"{fs}__{mname}__SCREENING_ONLY.pkl"
            with model_path.open("wb") as f: pickle.dump(pipe,f)
            size_kb=model_path.stat().st_size/1024
            rows.append({
                "feature_set":fs,"model":mname,**vm,
                "Train_MAE_ms":tm["MAE_ms"],"Train_RMSE_ms":tm["RMSE_ms"],
                "fit_time_s":fit_s,
                "validation_mean_inference_ms_per_row":pred_s/len(val)*1000,
                "serialized_model_kb":size_kb,
                "features":"|".join(features),
            })
            pdf=pd.DataFrame({
                "transaction_id":val[tx].astype(str),
                "type":val[typ].astype(str),
                "node_profile":val[node].map(normalize_node),
                "y_true_ms":yv,
                "y_pred_ms":pred,
                "abs_error_ms":np.abs(yv-pred),
            })
            pdf.to_csv(pred_dir/f"{fs}__{mname}.csv",index=False)
            for n,g in pdf.groupby("node_profile"):
                node_rows.append({"feature_set":fs,"model":mname,"node_profile":n,"count":len(g),**calc(g["y_true_ms"],g["y_pred_ms"])})
            for t,g in pdf.groupby("type"):
                type_rows.append({"feature_set":fs,"model":mname,"type":t,"count":len(g),**calc(g["y_true_ms"],g["y_pred_ms"])})
            print(f"{fs:16s} | {mname:20s} | MAE={vm['MAE_ms']:.4f} RMSE={vm['RMSE_ms']:.4f} R2={vm['R2']:.4f} P95AE={vm['P95_AE_ms']:.4f}")

    res=pd.DataFrame(rows).sort_values(["MAE_ms","RMSE_ms","P95_AE_ms"]).reset_index(drop=True)
    res.insert(0,"validation_rank_by_MAE",np.arange(1,len(res)+1))
    res.to_csv(out/"validation_screening_results.csv",index=False)
    pd.DataFrame(node_rows).to_csv(out/"validation_metrics_by_node.csv",index=False)
    pd.DataFrame(type_rows).to_csv(out/"validation_metrics_by_type.csv",index=False)
    best=(res.sort_values(["feature_set","MAE_ms","RMSE_ms"]).groupby("feature_set",as_index=False).first())
    best.to_csv(out/"ablation_best_per_feature_set.csv",index=False)

    top=res.iloc[0]
    manifest={
        "created_utc":now_utc(),
        "test_set_loaded":False,
        "test_set_used_for_selection":False,
        "group_leakage_check":"PASS",
        "random_seed":SEED,
        "target":target,
        "models":list(models().keys()),
        "feature_policy":pol,
        "selection_rule":"Primary validation MAE; RMSE and P95AE secondary. Screening only.",
        "top_validation_screening_candidate":{
            "feature_set":top["feature_set"],"model":top["model"],
            "MAE_ms":float(top["MAE_ms"]),"RMSE_ms":float(top["RMSE_ms"]),
            "R2":float(top["R2"]),"MedianAE_ms":float(top["MedianAE_ms"]),
            "P95_AE_ms":float(top["P95_AE_ms"]),
        },
    }
    (out/"screening_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print("")
    print("="*72)
    print("REGRESSION v1 SCREENING COMPLETE")
    print("="*72)
    print("TEST_SET_LOADED = FALSE")
    print("GROUP_LEAKAGE_CHECK = PASS")
    print(f"Models evaluated = {len(res)}")
    print(f"Top validation screening candidate: {top['feature_set']} + {top['model']}")
    print(f"Validation MAE={top['MAE_ms']:.4f} ms | RMSE={top['RMSE_ms']:.4f} ms | R2={top['R2']:.4f} | P95AE={top['P95_AE_ms']:.4f} ms")
    print("SCREENING_STATUS = PASS")
    print("STOP HERE and review results before tuning or opening the held-out test set.")
    print("="*72)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("mode",choices=["inspect","screen"])
    ap.add_argument("--root",required=True)
    args=ap.parse_args()
    root=Path(args.root).resolve()
    out=root/"results/regression_v1"
    if args.mode=="inspect": inspect(root,out)
    else: screen(root,out)

if __name__=="__main__":
    main()
