"""Aggregate official DB1B Market ticket records to carrier-route-quarter cells.

The aggregation is deliberately narrow: domestic nonstop airport-pair tickets,
positive passenger weights, and market fares in [50, 2000] dollars. The output
preserves carrier-level cells while avoiding redistribution of the raw 10%
sample. Run with a BTS PREZIP DB1BMarket zip as the single argument.
"""
from pathlib import Path
import sys
import zipfile
import pandas as pd

source = Path(sys.argv[1])
outdir = source.parent.parent / "db1b_aggregated"
outdir.mkdir(exist_ok=True)
cols = ["Year", "Quarter", "MktCoupons", "Origin", "Dest", "OriginCountry",
        "DestCountry", "OpCarrier", "TkCarrier", "BulkFare", "Passengers", "MktFare", "NonStopMiles"]
parts = []
counts = {"raw": 0, "filtered": 0}
with zipfile.ZipFile(source) as archive:
    name = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
    with archive.open(name) as stream:
        for chunk in pd.read_csv(stream, usecols=cols, chunksize=250_000,
                                 low_memory=False):
            counts["raw"] += len(chunk)
            d = chunk.loc[
                (chunk.MktCoupons == 1)
                & (chunk.OriginCountry == "US") & (chunk.DestCountry == "US")
                & (chunk.BulkFare == 0)
                & chunk.Passengers.between(0.01, 10000)
                & chunk.MktFare.between(50, 2000)
                & chunk.NonStopMiles.between(50, 5000)
                & chunk.OpCarrier.notna() & (chunk.OpCarrier != "99")
                & (chunk.Origin != chunk.Dest)
            ].copy()
            counts["filtered"] += len(d)
            a = d[["Origin", "Dest"]].min(axis=1)
            b = d[["Origin", "Dest"]].max(axis=1)
            d["route"] = a + "-" + b
            d["fare_x_pax"] = d.MktFare * d.Passengers
            d["distance_x_pax"] = d.NonStopMiles * d.Passengers
            g = d.groupby(["Year", "Quarter", "route", "OpCarrier"],
                          as_index=False).agg(
                passengers=("Passengers", "sum"),
                fare_x_pax=("fare_x_pax", "sum"),
                distance_x_pax=("distance_x_pax", "sum"),
                ticket_records=("MktFare", "size"))
            parts.append(g)
            if len(parts) >= 10:
                parts = [pd.concat(parts).groupby(
                    ["Year", "Quarter", "route", "OpCarrier"], as_index=False
                )[["passengers", "fare_x_pax", "distance_x_pax", "ticket_records"]].sum()]

result = pd.concat(parts).groupby(
    ["Year", "Quarter", "route", "OpCarrier"], as_index=False
)[["passengers", "fare_x_pax", "distance_x_pax", "ticket_records"]].sum()
result.rename(columns={"OpCarrier": "carrier"}, inplace=True)
result.to_csv(outdir / f"{source.stem}.csv.gz", index=False, compression="gzip")
print(source.name, counts, "cells", len(result), "routes", result.route.nunique(), flush=True)
