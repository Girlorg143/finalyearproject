# =====================================
# 1. IMPORT LIBRARIES
# =====================================
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import matplotlib.pyplot as plt
import seaborn as sns

# =====================================
# 2. LOAD DATA
# =====================================
from google.colab import files
uploaded = files.upload()
file_path = list(uploaded.keys())[0]

df = pd.read_csv(file_path)

# Backup for visualization
df_original = df.copy()

# =====================================
# 3. HANDLE MISSING VALUES
# =====================================
df.ffill(inplace=True)

# =====================================
# 4. DEBUG: CHECK VARIATION
# =====================================
print("\nVariation Check:")
print(df.groupby(["Crop", "Season"])["Max_Shelf_Life_Days"].nunique())

# =====================================
# 5. CREATE MEAN FEATURES (IMPORTANT)
# =====================================
# Crop-season mean
group_mean = df.groupby(["Crop", "Season"])["Max_Shelf_Life_Days"].mean()

# Crop overall mean
crop_mean_map = df.groupby("Crop")["Max_Shelf_Life_Days"].mean()

# =====================================
# 6. FEATURES & TARGET
# =====================================
X = df[["Crop", "Season"]]
y = df["Max_Shelf_Life_Days"]

# One-hot encoding
X = pd.get_dummies(X, columns=["Crop", "Season"])

# =====================================
# 7. TRAIN-TEST SPLIT
# =====================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# =====================================
# 8. TRAIN MODEL
# =====================================
model = RandomForestRegressor(
    n_estimators=300,
    max_depth=12,
    random_state=42
)
model.fit(X_train, y_train)

# =====================================
# 9. EVALUATION
# =====================================
y_pred = model.predict(X_test)

print("\nModel Performance:")
print("MAE:", mean_absolute_error(y_test, y_pred))
print("R2 Score:", r2_score(y_test, y_pred))

# =====================================
# 10. FINAL PREDICTION FUNCTION
# =====================================
def predict_shelf_life(crop, season):

    # Crop-season mean
    try:
        cs_mean = group_mean[(crop, season)]
    except:
        cs_mean = df["Max_Shelf_Life_Days"].mean()

    # Crop mean
    try:
        c_mean = crop_mean_map[crop]
    except:
        c_mean = df["Max_Shelf_Life_Days"].mean()

    # ML input
    new_data = pd.DataFrame({
        "Crop": [crop],
        "Season": [season]
    })

    new_data = pd.get_dummies(new_data)
    new_data = new_data.reindex(columns=X.columns, fill_value=0)

    # ML prediction
    ml_pred = model.predict(new_data)[0]

    # =====================================
    # FINAL HYBRID FORMULA (KEY)
    # =====================================
    final_pred = (0.5 * ml_pred) + (0.3 * cs_mean) + (0.2 * c_mean)

    return round(final_pred, 2)

# =====================================
# 11. TEST PREDICTIONS
# =====================================
print("\nPredictions:")
print("Grapes (Kharif):", predict_shelf_life("grapes", "Kharif"))
print("Grapes (Rabi):", predict_shelf_life("grapes", "Rabi"))
print("Rice (Kharif):", predict_shelf_life("rice", "Kharif"))
print("Wheat (Rabi):", predict_shelf_life("wheat", "Rabi"))

# =====================================
# 12. FEATURE IMPORTANCE (VIVA)
# =====================================

sns.barplot(x="Crop", y="Max_Shelf_Life_Days", data=df_original)
plt.xticks(rotation=45)
plt.title("Crop vs Shelf Life")
plt.show()
