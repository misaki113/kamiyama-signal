# %% [markdown]
# # ② 描画 — 配列の番号を時刻に直して描く（解答例）
#
# データには「何番目か」しか入っていない。サンプリング周波数 `fs` を使って、
# 番号 `i` を時刻 `t = i / fs` [秒] に直す。

# %%
import os

import matplotlib.pyplot as plt

DATA_URL = ""  # Colab などデータが手元にない環境では、配布ページの URL + "data/" を入れる


# ---- ここから ① の答え（そのまま使う） ----
def data_path(name):
    for folder in ["data", "../data", "."]:
        path = os.path.join(folder, name)
        if os.path.exists(path):
            return path
    if DATA_URL != "":
        import urllib.request

        urllib.request.urlretrieve(DATA_URL + name, name)
        return name
    raise FileNotFoundError(name + " が見つかりません。data フォルダの場所を確かめてください")


def read_signal_csv(path):
    meta = {}
    columns = None
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line == "":
                continue
            if line.startswith("#"):
                key, value = line[1:].split(":", 1)
                meta[key.strip()] = value.strip()
            elif columns is None:
                columns = line.split(",")
            else:
                rows.append(line.split(","))
    return meta, columns, rows
# ---- ここまで ① の答え ----


meta, columns, rows = read_signal_csv(data_path("ecg_clean.csv"))
fs = float(meta["sampling_rate_hz"])
ecg = [float(row[1]) for row in rows]
n = len(ecg)

# %% [markdown]
# ## 時間の配列を作る
#
# `fs = 500` Hz は「1 秒に 500 個」。となり合う点の間隔は `1 / fs = 0.002` 秒。
# だから `i` 番目の点の時刻は `i / fs`。

# %%
t = [0.0] * n
for i in range(n):
    t[i] = i / fs

print("t[0] =", t[0], " t[1] =", t[1], " t[500] =", t[500], " t[n-1] =", t[n - 1])

# %% [markdown]
# ## 全体を描く
#
# 横軸に単位を書く。番号のまま描くと「500 って何秒？」となる。

# %%
plt.figure(figsize=(10, 3))
plt.plot(t, ecg, linewidth=0.8, color="#0c7885")
plt.xlabel("time [s]")
plt.ylabel("ECG [mV]")
plt.title("ecg_clean.csv (30 s)")
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 1 秒分だけ切り出す
#
# 「5.0 秒から 1 秒間」を取り出したい。**時刻を番号に戻す**には `fs` を掛ける。
#
# - 始まりの番号: `5.0 × fs = 2500`
# - 個数: `1.0 × fs = 500`
#
# 番号は整数でないといけないので、整数に直す。

# %%
start = int(5.0 * fs)
count = int(1.0 * fs)
stop = start + count  # stop 番目は含まない

t_cut = t[start:stop]
ecg_cut = ecg[start:stop]
print("切り出した点数:", len(ecg_cut), "（番号", start, "〜", stop - 1, "）")

plt.figure(figsize=(6, 3))
plt.plot(t_cut, ecg_cut, color="#0c7885")
plt.xlabel("time [s]")
plt.ylabel("ECG [mV]")
plt.title("1 second (one beat)")
# 山の名前を書き込む（位置はグラフを見て決めた）
plt.text(5.11, 0.20, "P", ha="center")
plt.text(5.32, 0.95, "R", ha="left")
plt.text(5.26, -0.22, "Q", ha="right")
plt.text(5.33, -0.30, "S", ha="left")
plt.text(5.59, 0.36, "T", ha="center")
plt.tight_layout()
plt.show()

# %% [markdown]
# ## おまけ: イベントの位置に印を付ける
#
# ① で取り出したイベント（文字列の列）も、番号を時刻に直せば同じ図に描ける。

# %%
events = [(int(row[0]), row[2]) for row in rows if row[2] != ""]

plt.figure(figsize=(10, 3))
plt.plot(t, ecg, linewidth=0.8, color="#0c7885")
for index, name in events:
    plt.axvline(index / fs, color="#d98a1f", linestyle="--")
    plt.text(index / fs, 1.1, name, fontsize=8, rotation=90, va="top")
plt.xlabel("time [s]")
plt.ylabel("ECG [mV]")
plt.tight_layout()
plt.show()
