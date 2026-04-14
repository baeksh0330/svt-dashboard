import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv("data/tracks.csv")

# 1. 에너지 분포
plt.figure()
sns.histplot(df["energy"], bins=20)
plt.title("Energy Distribution")
plt.show()

# 2. danceability vs energy
plt.figure()
sns.scatterplot(data=df, x="danceability", y="energy")
plt.title("Danceability vs Energy")
plt.show()

# 3. valence
plt.figure()
sns.boxplot(y=df["valence"])
plt.title("Valence Distribution")
plt.show()