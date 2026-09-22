"""Aggregate DB1BMarket fares over nonstop and connecting itineraries by route.

This secondary outcome uses the same quality filters as process_db1b.py, but
retains every coupon count. It reports one-coupon versus multi-coupon traffic
separately to show whether restricting the primary analysis to nonstop trips
changes the answer.
"""
from pathlib import Path
import sys
import zipfile
import pandas as pd

source = Path(sys.argv[1])
outdir = source.parent.parent / "db1b_all_itineraries"
outdir.mkdir(exist_ok=True)
cols = ["Year", "Quarter", "MktCoupons", "Origin", "Dest", "OriginCountry",
        "DestCountry", "BulkFare", "Passengers", "MktFare", "NonStopMiles"]
parts = []
counts = {"raw": 0, "filtered": 0}
with zipfile.ZipFile(source) as archive:
    name = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
    with archive.open(name) as stream:
        for chunk in pd.read_csv(stream, usecols=cols, chunksize=250_000, low_memory=False):
            counts["raw"] += len(chunk)
            d = chunk.loc[
                (chunk.MktCoupons >= 1)
                & (chunk.OriginCountry == "US") & (chunk.DestCountry == "US")
                & (chunk.BulkFare == 0)
                & chunk.Passengers.between(0.01, 10000)
                & chunk.MktFare.between(50, 2000)
                & chunk.NonStopMiles.between(50, 5000)
                & (chunk.Origin != chunk.Dest)
            ].copy()
            counts["filtered"] += len(d)
            d["route"] = d[["Origin", "Dest"]].min(axis=1) + "-" + d[["Origin", "Dest"]].max(axis=1)
            d["trip_type"] = d.MktCoupons.eq(1).map({True: "nonstop", False: "connecting"})
            d["fare_x_pax"] = d.MktFare * d.Passengers
            g = d.groupby(["Year", "Quarter", "route", "trip_type"], as_index=False).agg(
                passengers=("Passengers", "sum"), fare_x_pax=("fare_x_pax", "sum"),
                ticket_records=("MktFare", "size"))
            parts.append(g)
            if len(parts) >= 10:
                parts = [pd.concat(parts).groupby(
                    ["Year", "Quarter", "route", "trip_type"], as_index=False
                )[["passengers", "fare_x_pax", "ticket_records"]].sum()]

result = pd.concat(parts).groupby(
    ["Year", "Quarter", "route", "trip_type"], as_index=False
)[["passengers", "fare_x_pax", "ticket_records"]].sum()
result.to_csv(outdir / f"{source.stem}.csv.gz", index=False, compression="gzip")
print(source.name, counts, "route-type cells", len(result), flush=True)
