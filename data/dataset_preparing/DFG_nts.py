from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Set, Tuple

import numpy as np
import pandas as pd
from pm4py import read_ocel2_json
from pm4py.algo.discovery.dfg import algorithm as dfg_discovery
from pm4py.objects.ocel.util.flattening import flatten
from pm4py.visualization.dfg import visualizer as dfg_vis


# --- MODIFIED: single NTS OCEL input; comparison paths removed ---
NTS_OCEL_PATH = "./Data/Order_management/outputs/NTS_OCEL_2026.json"
OUT_DIR = "./Results/NTS-ocdfg/"

os.environ["PATH"] += os.pathsep + "C:\\Program Files\\Graphviz\\bin"


# DFG extraction

def dfg_from_eventlog(event_log) -> Tuple[Set[str], Set[Tuple[str, str]], Dict[Tuple[str, str], float]]:
    """
    Binary DFG using PM4Py:
      nodes = activity labels present
      edges = directly-follows pairs present
    """
    if isinstance(event_log, pd.DataFrame):
        ts_col = "time:timestamp" if "time:timestamp" in event_log.columns else None
        if ts_col and not pd.api.types.is_datetime64_any_dtype(event_log[ts_col]):
            event_log = event_log.copy()
            event_log[ts_col] = pd.to_datetime(event_log[ts_col], errors="coerce", utc=True)

    dfg_raw = dfg_discovery.apply(event_log, variant=dfg_discovery.Variants.FREQUENCY)
    if isinstance(dfg_raw, tuple):
        dfg_raw = dfg_raw[0]

    nodes: Set[str] = set()
    edges: Set[Tuple[str, str]] = set()
    for (a, b) in dfg_raw.keys():
        aa = str(a)
        bb = str(b)
        edges.add((aa, bb))
        nodes.add(aa)
        nodes.add(bb)

    return nodes, edges, dfg_raw


# Utility helpers

def safe_filename(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text)


def save_dfg_png(dfg: Dict[Tuple[str, str], float], event_log, path: str) -> None:
    if not dfg:
        return
    gviz = dfg_vis.apply(
        dfg,
        log=event_log,
        variant=dfg_vis.Variants.FREQUENCY,
        parameters={"format": "png"},
    )
    gviz.graph_attr["dpi"] = "300"
    dfg_vis.save(gviz, path)


# All PM4Py settings and parameters are preserved.

def discover_ocdfg(
    ocel_path: str,
    out_dir: str,
) -> List[Dict[str, Any]]:
    """
    Load one OCEL, flatten per object type, discover a DFG for each,
    save PNG visualizations, and return per-object-type analysis rows.

    """
    ocel = read_ocel2_json(ocel_path)

    obj_counts_series = ocel.objects["ocel:type"].astype(str).value_counts()
    obj_types: List[str] = sorted(obj_counts_series.index.astype(str).tolist())

    analysis_rows: List[Dict[str, Any]] = []

    for obj_type in obj_types:
        obj_count = int(obj_counts_series.get(obj_type, 0))

        # Flatten OCEL to per-object-type event log 
        flat_log = flatten(ocel, obj_type)

        # Discover DFG 
        nodes, edges, dfg_raw = dfg_from_eventlog(flat_log)

        # Save PNG visualization 
        safe_type = safe_filename(obj_type)
        viz_dir = os.path.join(out_dir, "visualizations")
        os.makedirs(viz_dir, exist_ok=True)
        png_path = os.path.join(viz_dir, f"{safe_type}__dfg.png")
        save_dfg_png(dfg_raw, flat_log, png_path)

        # Build directly-follows edge list with frequencies
        df_edges = [
            {"source": str(a), "target": str(b), "frequency": int(freq)}
            for (a, b), freq in dfg_raw.items()
        ]

        # Object lifecycle: activity set observed for this object type
        activity_set = sorted(nodes)

        # Object interaction: which other object types co-occur in events
        # touching this object type's flattened log event IDs
        event_ids_for_type: Set[str] = set()
        if "ocel:eid" in flat_log.columns:
            event_ids_for_type = set(flat_log["ocel:eid"].astype(str))

        cooccurring_types: List[str] = []
        if not ocel.relations.empty and event_ids_for_type:
            rels = ocel.relations.copy()
            rels["ocel:eid"] = rels["ocel:eid"].astype(str)
            rels["ocel:type"] = rels["ocel:type"].astype(str)
            mask = rels["ocel:eid"].isin(event_ids_for_type)
            types_in_scope = set(rels.loc[mask, "ocel:type"].unique())
            cooccurring_types = sorted(types_in_scope - {obj_type})

        row: Dict[str, Any] = {
            "object_type":          obj_type,
            "object_instance_count": obj_count,
            "n_activities":         len(nodes),
            "n_df_edges":           len(edges),
            "activities":           activity_set,
            "directly_follows":     df_edges,
            "cooccurring_object_types": cooccurring_types,
            "dfg_png":              png_path,
        }

        analysis_rows.append(row)

        print(
            f"[{obj_type}] instances={obj_count}  "
            f"activities={len(nodes)}  df_edges={len(edges)}  "
            f"co-occurring types={len(cooccurring_types)}"
        )

    return analysis_rows


# Output directory creation, CSV export pattern, visualization file structure.

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    if not os.path.isfile(NTS_OCEL_PATH):
        raise FileNotFoundError(f"NTS OCEL file not found: {NTS_OCEL_PATH}")

    analysis_rows = discover_ocdfg(
        ocel_path=NTS_OCEL_PATH,
        out_dir=OUT_DIR,
    )

    # Export per-object-type summary CSV (same output pattern as before)
    summary_records = []
    for row in analysis_rows:
        summary_records.append({
            "object_type":              row["object_type"],
            "object_instance_count":    row["object_instance_count"],
            "n_activities":             row["n_activities"],
            "n_df_edges":               row["n_df_edges"],
            "cooccurring_object_types": "; ".join(row["cooccurring_object_types"]),
            "dfg_png":                  row["dfg_png"],
        })

    summary_df = pd.DataFrame(summary_records)
    summary_csv = os.path.join(OUT_DIR, "object_type_summary.csv")
    summary_df.to_csv(summary_csv, index=False)
    print(f"\nSummary saved → {summary_csv}")

    # Export full OCDFG analysis as JSON (activities, edges, interactions)
    analysis_json_path = os.path.join(OUT_DIR, "ocdfg_analysis.json")
    with open(analysis_json_path, "w", encoding="utf-8") as f:
        json.dump(analysis_rows, f, ensure_ascii=False, indent=2)
    print(f"OCDFG analysis saved → {analysis_json_path}")


if __name__ == "__main__":
    main()