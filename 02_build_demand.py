import pandas as pd, numpy as np

df = pd.read_csv("salesdaily_cleaned.csv", parse_dates=["date"])
skus = ["M01AB","M01AE","N02BA","N02BE","N05B","N05C","R03","R06"]

# Convert wide data to long format: one row per date and ATC category.
long = df.melt(id_vars=["date", "all_zero_sales"], value_vars=skus,
               var_name="sku_id", value_name="qty")
rng = np.random.default_rng(42)

def stochastic_round(x):
    base = np.floor(x)
    return (base + (rng.random(len(x)) < (x - base))).astype(int)

long["qty"] = stochastic_round(long["qty"].to_numpy())

# Split category quantities across three fictional distributors reproducibly.
rng = np.random.default_rng(42)
shares = {"DIST_GHY": 0.45, "DIST_DIB": 0.30, "DIST_SIL": 0.25}

rows = []
for r in long.itertuples():
    parts = rng.multinomial(r.qty, list(shares.values()))
    for loc, q in zip(shares, parts):
        rows.append((r.date, r.sku_id, loc, q, r.all_zero_sales))

demand = pd.DataFrame(rows, columns=["date","sku_id","location_id",
                                     "demand_qty","all_zero_sales"])
demand.to_csv("daily_demand.csv", index=False)
print(demand.shape)                      # Row count depends on the source date range.
print(demand.groupby("location_id")["demand_qty"].sum())
