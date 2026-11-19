# %% [markdown]
# # ④ R ピーク検出 — 心拍数を求める（解答例）
#
# 心電図でいちばん高くとがった山が **R ピーク**。となり合う R ピークの間隔（RR 間隔）が
# 1 拍の時間なので、心拍数は `60 / RR` [bpm] で出せる。
#
# R ピークを見つける手順を、素朴な方法から 3 段階で改良する。
#
# | 版 | 方法 | 残る失敗 |
# |----|------|----------|
# | 版 1 | しきい値を超えた点を全部拾う | 1 拍で何点も拾う |
# | 版 2 | 超えている区間ごとに、いちばん高い点を 1 つ拾う | ノイズで区間が割れると 2 回拾う |
# | 版 3 | 版 2 + 不応期（直前のピークから 200 ms 以内は同じ拍とみなす） | 基線が揺れると、しきい値そのものが合わない |
#
# 最後に、③ の移動平均を前処理に使って、難しいデータ（`ecg_hard.csv`）でも通るようにする。

# %%
import os

import matplotlib.pyplot as plt

DATA_URL = ""  # Colab などデータが手元にない環境では、配布ページの URL + "data/" を入れる


# ---- ここから ①〜③ の答え（そのまま使う） ----
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
                header_seen = True
            else:
                values.append(float(line.split(",")[column]))
    fs = float(meta["sampling_rate_hz"])
    t = [i / fs for i in range(len(values))]
    return fs, t, values


def moving_average(x, k):
    """移動平均（累積和の実装、O(n)）"""
    n = len(x)
    h = k // 2
    c = [0.0] * (n + 1)
    for i in range(n):
        c[i + 1] = c[i] + x[i]
    y = [0.0] * n
    for i in range(n):
        lo = max(0, i - h)
        hi = min(n - 1, i + h)
        y[i] = (c[hi + 1] - c[lo]) / (hi - lo + 1)
    return y
# ---- ここまで ①〜③ の答え ----


# %% [markdown]
# ## 版 1: しきい値を超えた点を全部拾う
#
# いちばん素朴な方法。配列を先頭から順に見て（線形探索）、しきい値より大きい点の番号を集める。

# %%
def detect_v1(x, threshold):
    peaks = []
    for i in range(len(x)):
        if x[i] > threshold:
            peaks.append(i)
    return peaks


# %% [markdown]
# ## 版 2: 超えている区間ごとに、いちばん高い点を 1 つ拾う
#
# 版 1 は、1 つの山の中で何点も拾ってしまう。
# 「しきい値を超えてから下回るまで」を 1 つの区間とみなし、その中の最大値の位置を 1 つだけ残す。
#
# 「いま区間の中にいるか」を覚えておく変数 `inside` を 1 つ持つのがポイント。

# %%
def detect_v2(x, threshold):
    peaks = []
    inside = False  # いま、しきい値を超えている区間の中か
    best = 0  # 区間の中で、これまででいちばん高い点の番号
    for i in range(len(x)):
        if x[i] > threshold:
            if not inside:
                inside = True  # 区間に入った
                best = i
            elif x[i] > x[best]:
                best = i  # 最大値を更新
        else:
            if inside:
                peaks.append(best)  # 区間を出た。最大値の位置を記録
                inside = False
    if inside:
        peaks.append(best)  # データの終わりが区間の途中だったとき
    return peaks


# %% [markdown]
# ## 版 3: 不応期を入れる
#
# 心臓は、1 回打った直後にはもう 1 回打てない（不応期）。
# そこで「直前のピークから 200 ms 以内に出た候補は、同じ拍の一部」とみなす。
# 2 つのうち高い方を残す。

# %%
def detect_v3(x, threshold, fs, refractory_ms=200):
    candidates = detect_v2(x, threshold)
    gap = int(refractory_ms / 1000 * fs)  # 200 ms は何点分か
    peaks = []
    for i in candidates:
        if len(peaks) == 0 or i - peaks[-1] > gap:
            peaks.append(i)  # 十分離れている。新しい拍
        elif x[i] > x[peaks[-1]]:
            peaks[-1] = i  # 近すぎる。高い方に置き換える
    return peaks


# %% [markdown]
# ## 心拍数を出す
#
# となり合うピークの番号の差を `fs` で割ると RR 間隔 [秒]。心拍数は `60 / RR` [bpm]。

# %%
def heart_rates(peaks, fs):
    bpm = []
    for k in range(len(peaks) - 1):
        rr = (peaks[k + 1] - peaks[k]) / fs
        bpm.append(60.0 / rr)
    return bpm


def report(name, peaks, fs):
    bpm = heart_rates(peaks, fs)
    mean_rr = (peaks[-1] - peaks[0]) / fs / (len(peaks) - 1)
    print(
        f"{name:28s} ピーク {len(peaks):4d} 個   平均心拍数 {60 / mean_rr:6.1f} bpm"
        f"   （1 拍ごとの最小 {min(bpm):6.1f} / 最大 {max(bpm):7.1f}）"
    )


# %% [markdown]
# ## きれいなデータで試す（`ecg_clean.csv`）
#
# しきい値は、グラフを見て「R ピークだけが超える高さ」に決める。ここでは最大値の半分にした。

# %%
fs, t, ecg = load_signal("ecg_clean.csv")
threshold = 0.5 * max(ecg)
print("しきい値 =", round(threshold, 3), "mV")

report("clean  版1", detect_v1(ecg, threshold), fs)
report("clean  版2", detect_v2(ecg, threshold), fs)
report("clean  版3", detect_v3(ecg, threshold, fs), fs)

# %% [markdown]
# 版 1 はピークの数が多すぎる（1 つの山で何点も拾っている）。
# となりの点どうしの間隔は 2 ms なので、「心拍数 30000 bpm」というあり得ない値が出る。
# 版 2 で 1 拍 1 個になり、心拍数が 60〜80 bpm に収まる。


# %%
def plot_peaks(ax, t, x, peaks, threshold, title, t_from, t_to, fs):
    a = int(t_from * fs)
    b = int(t_to * fs)
    ax.plot(t[a:b], x[a:b], color="#0c7885", linewidth=0.8)
    ax.axhline(threshold, color="#97a5a8", linestyle="--", linewidth=0.8)
    shown = [i for i in peaks if a <= i < b]
    ax.plot([t[i] for i in shown], [x[i] for i in shown], "v", color="#c1121f", markersize=5)
    ax.set_title(f"{title}   ({len(shown)} peaks in view)", fontsize=10, loc="left")
    ax.set_ylabel("[mV]")


fig, axes = plt.subplots(2, 1, figsize=(10, 4.5), sharex=True)
plot_peaks(axes[0], t, ecg, detect_v1(ecg, threshold), threshold, "v1: every point above threshold", 2.0, 6.0, fs)
plot_peaks(axes[1], t, ecg, detect_v2(ecg, threshold), threshold, "v2: one maximum per segment", 2.0, 6.0, fs)
axes[1].set_xlabel("time [s]")
fig.suptitle("ecg_clean.csv")
fig.tight_layout()
plt.show()

# %% [markdown]
# ## ノイズのあるデータで試す（`ecg_noisy.csv`）
#
# 前処理なしで版 2 を使うと、ノイズのせいで山の途中でしきい値を何度もまたぐ。
# 区間が割れるので、1 拍で 2 回以上拾ってしまう。版 3（不応期）でまとめられる。

# %%
fs, t, noisy = load_signal("ecg_noisy.csv")
threshold = 0.5 * max(noisy)
print("しきい値 =", round(threshold, 3), "mV")

report("noisy  版2", detect_v2(noisy, threshold), fs)
report("noisy  版3", detect_v3(noisy, threshold, fs), fs)

fig, axes = plt.subplots(2, 1, figsize=(10, 4.5), sharex=True)
plot_peaks(axes[0], t, noisy, detect_v2(noisy, threshold), threshold, "v2: one maximum per segment", 2.0, 6.0, fs)
plot_peaks(axes[1], t, noisy, detect_v3(noisy, threshold, fs), threshold, "v3: v2 + refractory period 200 ms", 2.0, 6.0, fs)
axes[1].set_xlabel("time [s]")
fig.suptitle("ecg_noisy.csv (no smoothing)")
fig.tight_layout()
plt.show()

# %% [markdown]
# ## 難しいデータで試す（`ecg_hard.csv`）
#
# 基線（波形の土台）がゆっくり上下していて、T 波も大きい。
# しきい値を 1 本の横線で決めているので、
#
# - 基線が**下がった**ところでは、R ピークがしきい値に届かない（見落とし）
# - 基線が**上がった**ところでは、T 波までしきい値を超える（拾いすぎ）
#
# 不応期を入れた版 3 でも直らない。T 波は R ピークの約 300 ms 後に来るので、200 ms の不応期の外にある。

# %%
fs, t, hard = load_signal("ecg_hard.csv")
threshold = 0.5 * max(hard)
print("しきい値 =", round(threshold, 3), "mV")

report("hard   版1", detect_v1(hard, threshold), fs)
report("hard   版2", detect_v2(hard, threshold), fs)
report("hard   版3", detect_v3(hard, threshold, fs), fs)

# %% [markdown]
# ## 前処理を足す — ③ の移動平均をもう一度使う
#
# 失敗の原因は検出の手順ではなく、**基線が揺れていること**。検出の前に基線を取り除く。
#
# 1. 幅の狭い移動平均（k = 9）で細かいノイズを取る
# 2. 幅の広い移動平均（0.6 秒 = 301 点）をかけると、R ピークは潰れて**基線のゆっくりした動きだけ**が残る
# 3. 1 から 2 を引く
#
# ③ で「窓を広げすぎると R ピークが潰れる」と分かった。その性質を逆に利用している。
# 窓が 301 点でも、累積和の実装なら手間は変わらない。

# %%
def preprocess(x, fs):
    smooth = moving_average(x, 9)
    k_wide = int(0.6 * fs) + 1  # 0.6 秒分。奇数にする
    baseline = moving_average(x, k_wide)
    return [smooth[i] - baseline[i] for i in range(len(x))]


hard_clean = preprocess(hard, fs)
threshold_clean = 0.5 * max(hard_clean)
peaks_final = detect_v3(hard_clean, threshold_clean, fs)
report("hard   前処理 + 版3", peaks_final, fs)

# %% [markdown]
# ## どこで失敗し、どう直ったか
#
# 上から順に、版 1 → 版 2 → 版 3 → 前処理 + 版 3。赤い印が検出した点。

# %%
T_FROM, T_TO = 9.0, 21.0
fig, axes = plt.subplots(4, 1, figsize=(12, 6.2), sharex=True)
plot_peaks(axes[0], t, hard, detect_v1(hard, threshold), threshold, "v1: every point above threshold", T_FROM, T_TO, fs)
plot_peaks(axes[1], t, hard, detect_v2(hard, threshold), threshold, "v2: one maximum per segment", T_FROM, T_TO, fs)
plot_peaks(axes[2], t, hard, detect_v3(hard, threshold, fs), threshold, "v3: v2 + refractory period 200 ms", T_FROM, T_TO, fs)
plot_peaks(axes[3], t, hard_clean, peaks_final, threshold_clean, "preprocessing (smoothing + baseline removal) + v3", T_FROM, T_TO, fs)
axes[3].set_xlabel("time [s]")
fig.suptitle("ecg_hard.csv")
fig.tight_layout()
plt.show()

# %% [markdown]
# ## 1 拍ごとの心拍数を見る — 17 秒付近に何かある
#
# 前処理 + 版 3 で 1 拍 1 個になったのに、1 か所だけ心拍数が跳ね上がり、次の拍で大きく下がる。
#
# これは検出の失敗ではない。波形を見ると、**1 拍だけ早く打っている**（期外収縮）。
# そのあと 1 拍分の休みが入っている。
#
# 「おかしな値が出た」とき、アルゴリズムの誤りなのか、データが本当にそうなっているのかは、
# 数字だけでは決められない。**元の波形に戻って確かめる。**

# %%
bpm = heart_rates(peaks_final, fs)
beat_time = [t[i] for i in peaks_final[1:]]

fig, axes = plt.subplots(2, 1, figsize=(10, 5.5))
axes[0].plot(beat_time, bpm, "o-", color="#045a64")
axes[0].set_xlabel("time [s]")
axes[0].set_ylabel("heart rate [bpm]")
axes[0].set_title("beat-by-beat heart rate (ecg_hard.csv)", fontsize=10, loc="left")
plot_peaks(axes[1], t, hard_clean, peaks_final, threshold_clean, "around 17 s: one early beat", 15.0, 19.5, fs)
axes[1].set_xlabel("time [s]")
fig.tight_layout()
plt.show()

# %% [markdown]
# ## まとめ: 3 つのデータすべてに同じ手順をかける
#
# 「前処理 → 版 3 → 心拍数」を 1 本の手順にして、3 つのファイルにかける。
# どれも平均心拍数は約 70 bpm になる。

# %%
for name in ["ecg_clean.csv", "ecg_noisy.csv", "ecg_hard.csv"]:
    fs, t, x = load_signal(name)
    y = preprocess(x, fs)
    peaks = detect_v3(y, 0.5 * max(y), fs)
    report(name, peaks, fs)
