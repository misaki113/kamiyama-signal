# %% [markdown]
# # ③ 前処理 — 移動平均でノイズを取る（解答例）
#
# `ecg_noisy.csv` には細かいノイズと電源のノイズ（60 Hz）が乗っている。
# 各点を「その点のまわり k 個の平均」に置き換えて、なめらかにする。
#
# 同じ結果を出す実装を 2 つ書いて、**計算量**を比べる。
#
# | 実装 | 考え方 | 計算量 |
# |------|--------|--------|
# | 素直な実装 | 点ごとに k 個を足し直す | O(n·k) |
# | 累積和の実装 | 先に「先頭からの合計」を作っておき、引き算 1 回で区間の合計を出す | O(n) |

# %%
import os
import time

import matplotlib.pyplot as plt

DATA_URL = ""  # Colab などデータが手元にない環境では、配布ページの URL + "data/" を入れる


# ---- ここから ①② の答え（そのまま使う） ----
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


def load_signal(name, column=1):
    """CSV を読み、(サンプリング周波数, 時間の配列, 値の配列) を返す"""
    meta = {}
    values = []
    header_seen = False
    with open(data_path(name)) as f:
        for line in f:
            line = line.strip()
            if line == "":
                continue
            if line.startswith("#"):
                key, value = line[1:].split(":", 1)
                meta[key.strip()] = value.strip()
            elif not header_seen:
                header_seen = True  # 列名の行
            else:
                values.append(float(line.split(",")[column]))
    fs = float(meta["sampling_rate_hz"])
    t = [i / fs for i in range(len(values))]
    return fs, t, values
# ---- ここまで ①② の答え ----


fs, t, ecg = load_signal("ecg_noisy.csv")
n = len(ecg)
print("fs =", fs, "Hz,  n =", n)

# %% [markdown]
# ## 素直な実装 — O(n·k)
#
# `i` 番目の点について、前後 `h = k // 2` 個ずつ（合わせて k 個）を足して割る。
# 端では窓がはみ出すので、はみ出さない範囲だけで平均する。
#
# ループが二重になっている。外側が n 回、内側が k 回なので、足し算は約 n·k 回。

# %%
def moving_average_naive(x, k):
    n = len(x)
    h = k // 2
    y = [0.0] * n
    for i in range(n):
        lo = max(0, i - h)
        hi = min(n - 1, i + h)
        total = 0.0
        for j in range(lo, hi + 1):  # 毎回 k 個を足し直す
            total += x[j]
        y[i] = total / (hi - lo + 1)
    return y


# %% [markdown]
# ## 累積和の実装 — O(n)
#
# となりの窓は、ほとんど同じ点を足している。足し直すのはもったいない。
#
# 先に累積和 `c[i] = x[0] + x[1] + ... + x[i-1]` を作っておくと、
# `lo` 番目から `hi` 番目までの合計は **`c[hi+1] - c[lo]`** の引き算 1 回で出る。
#
# 累積和を作るのに n 回、平均を出すのに n 回。k が大きくなっても手間は変わらない。

# %%
def moving_average_cumsum(x, k):
    n = len(x)
    h = k // 2
    c = [0.0] * (n + 1)
    for i in range(n):
        c[i + 1] = c[i] + x[i]
    y = [0.0] * n
    for i in range(n):
        lo = max(0, i - h)
        hi = min(n - 1, i + h)
        y[i] = (c[hi + 1] - c[lo]) / (hi - lo + 1)  # 引き算 1 回
    return y


# %% [markdown]
# ## 2 つの結果が同じか確かめる
#
# 速くなっても、答えが変わっていたら意味がない。差の最大値を見る
# （小数の計算なので、ごく小さな誤差は出る）。

# %%
a = moving_average_naive(ecg, 9)
b = moving_average_cumsum(ecg, 9)
max_diff = max(abs(a[i] - b[i]) for i in range(n))
print("2 つの実装の差の最大値:", max_diff)

# %% [markdown]
# ## 実行時間を比べる
#
# 窓の幅 k を変えて、それぞれの実行時間を測る。
# 素直な実装は k に比例して遅くなり、累積和の実装はほぼ変わらないはず。

# %%
window_sizes = [5, 25, 101, 401]
time_naive = []
time_cumsum = []
for k in window_sizes:
    start = time.perf_counter()
    moving_average_naive(ecg, k)
    time_naive.append(time.perf_counter() - start)

    start = time.perf_counter()
    moving_average_cumsum(ecg, k)
    time_cumsum.append(time.perf_counter() - start)

print("   k   素直な実装 [ms]   累積和 [ms]")
for k, tn, tc in zip(window_sizes, time_naive, time_cumsum):
    print(f"{k:4d}   {tn * 1000:12.1f}   {tc * 1000:10.1f}")

plt.figure(figsize=(6, 3.5))
plt.plot(window_sizes, [v * 1000 for v in time_naive], "o-", color="#045a64", label="naive  O(n k)")
plt.plot(window_sizes, [v * 1000 for v in time_cumsum], "s-", color="#d98a1f", label="cumulative sum  O(n)")
plt.xlabel("window size k [samples]")
plt.ylabel("time [ms]")
plt.title(f"moving average, n = {n}")
plt.legend()
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 窓の幅を変えると波形はどうなるか
#
# 1 拍分を拡大して、k = 9, 25, 75 を比べる。
#
# - k = 9（18 ms）: 細かいノイズが減り、R ピークの高さはほぼ残る
# - k = 25（50 ms）: 60 Hz のちょうど 3 周期分なので電源ノイズはきれいに消えるが、R ピークが低くなる
# - k = 75（150 ms）: R ピークが潰れて、T 波と区別がつかなくなる
#
# **窓を広げるほどノイズは減るが、見たいもの（R ピーク）も一緒に削れる。**

# %%
start = int(4.0 * fs)
stop = int(5.2 * fs)

plt.figure(figsize=(10, 6))
plt.subplot(4, 1, 1)
plt.plot(t[start:stop], ecg[start:stop], color="#97a5a8", linewidth=0.8)
plt.title("raw (ecg_noisy.csv)", fontsize=10)
plt.ylabel("[mV]")
plt.ylim(-0.5, 1.4)
row = 2
for k in [9, 25, 75]:
    smooth = moving_average_cumsum(ecg, k)
    plt.subplot(4, 1, row)
    plt.plot(t[start:stop], smooth[start:stop], color="#0c7885")
    plt.title(f"k = {k}  ({k / fs * 1000:.0f} ms),  peak = {max(smooth[start:stop]):.2f} mV", fontsize=10)
    plt.ylabel("[mV]")
    plt.ylim(-0.5, 1.4)
    row += 1
plt.xlabel("time [s]")
plt.tight_layout()
plt.show()
