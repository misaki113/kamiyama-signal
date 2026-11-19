# %% [markdown]
# # ⑤ 研究紹介 — 位置を微分して、速度・加速度・躍度を求める（デモ）
#
# `motion_reach.csv` は、手を 200 mm 先の目標へ伸ばす運動（到達運動）の手先の位置。
# 100 Hz で記録した想定の**合成データ**（躍度最小軌道にノイズを足したもの）。
#
# 位置を時間で微分すると速度、もう 1 回で加速度、さらにもう 1 回で**躍度**（加速度の変化の速さ）。
# 躍度が小さいほど「滑らかな動き」。
#
# データは飛び飛びの点なので、微分は**となりの点との差**で近似する（数値微分）。
#
# | 方法 | 式 | 特徴 |
# |------|----|------|
# | 前進差分 | `(x[i+1] - x[i]) / dt` | 簡単。ただし「i と i+1 の真ん中」の傾きなので半点分ずれる |
# | 中心差分 | `(x[i+1] - x[i-1]) / (2·dt)` | i 番目を中心に両側を使うのでずれない。ノイズも少し小さい |

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


fs, t, x = load_signal("motion_reach.csv", column=1)  # x 方向の位置 [mm]
dt = 1.0 / fs
n = len(x)
print("fs =", fs, "Hz,  dt =", dt, "s,  n =", n)

# %% [markdown]
# ## 前進差分と中心差分
#
# どちらも配列を 1 回なめるだけ（O(n)）。端の点はとなりが無いので、となりの値で埋めておく。

# %%
def diff_forward(x, dt):
    n = len(x)
    v = [0.0] * n
    for i in range(n - 1):
        v[i] = (x[i + 1] - x[i]) / dt
    v[n - 1] = v[n - 2]
    return v


def diff_central(x, dt):
    n = len(x)
    v = [0.0] * n
    for i in range(1, n - 1):
        v[i] = (x[i + 1] - x[i - 1]) / (2 * dt)
    v[0] = v[1]
    v[n - 1] = v[n - 2]
    return v


# %% [markdown]
# ## 比べる
#
# 最初の 0.5 秒は手が止まっているので、速度は本当は 0。そこでのばらつきがノイズの大きさになる。

# %%
def spread(values):
    """標準偏差（ばらつきの大きさ）"""
    mean = sum(values) / len(values)
    return (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5


v_forward = diff_forward(x, dt)
v_central = diff_central(x, dt)
rest = int(0.5 * fs)  # 静止している区間の点数

print("静止中の速度のばらつき（本当は 0 のはず）")
print("  前進差分:", round(spread(v_forward[:rest]), 1), "mm/s")
print("  中心差分:", round(spread(v_central[1:rest]), 1), "mm/s")

plt.figure(figsize=(10, 3.5))
plt.plot(t, v_forward, color="#d98a1f", linewidth=1, label="forward difference")
plt.plot(t, v_central, color="#045a64", linewidth=1, label="central difference")
plt.xlabel("time [s]")
plt.ylabel("velocity [mm/s]")
plt.title("velocity from position (no smoothing)")
plt.legend()
plt.tight_layout()
plt.show()

# %% [markdown]
# 速度は、**山が 1 つのベル型**になっている。これがヒトの到達運動の特徴。

# %% [markdown]
# ## 微分をくり返す — ノイズがどんどん増える
#
# 位置 → 速度 → 加速度 → 躍度と、中心差分を 3 回かける。
#
# 位置のノイズはたった 0.2 mm ほどで、グラフでは見えない。
# ところが微分のたびに `dt = 0.01` で割るので、ノイズは 1 回ごとに数十倍になる。
# 躍度まで行くと、ノイズに埋もれて何も読み取れない。
#
# 灰色の線は、このデータを作るときに使ったノイズなしの式（躍度最小軌道）から計算した値。

# %%
def ideal_curves(t):
    """ノイズなしの躍度最小軌道（データを作るときに使った式）"""
    t0, tf, dist = 0.6, 0.8, 200.0
    pos, vel, acc, jerk = [], [], [], []
    for ti in t:
        s = min(max((ti - t0) / tf, 0.0), 1.0)
        pos.append(100.0 + dist * (10 * s**3 - 15 * s**4 + 6 * s**5))
        vel.append(dist / tf * (30 * s**2 - 60 * s**3 + 30 * s**4))
        acc.append(dist / tf**2 * (60 * s - 180 * s**2 + 120 * s**3))
        jerk.append(dist / tf**3 * (60 - 360 * s + 360 * s**2) if 0.0 < s < 1.0 else 0.0)
    return pos, vel, acc, jerk


def plot_four(t, curves, ideal, title):
    labels = ["position [mm]", "velocity [mm/s]", "acceleration [mm/s$^2$]", "jerk [mm/s$^3$]"]
    fig, axes = plt.subplots(4, 1, figsize=(9, 8), sharex=True)
    for ax, y, y0, label in zip(axes, curves, ideal, labels):
        ax.plot(t, y, color="#0c7885", linewidth=1)
        ax.plot(t, y0, color="#97a5a8", linewidth=1, linestyle="--")
        ax.set_ylabel(label)
    axes[0].set_title(title, fontsize=10, loc="left")
    axes[3].set_xlabel("time [s]")
    fig.align_ylabels(axes)
    fig.tight_layout()
    plt.show()


ideal = ideal_curves(t)

vel = diff_central(x, dt)
acc = diff_central(vel, dt)
jerk = diff_central(acc, dt)
plot_four(t, [x, vel, acc, jerk], ideal, "no smoothing: noise grows with every derivative (dashed: ideal)")

# %% [markdown]
# ## 前処理してから微分する
#
# 微分の前に移動平均（③ と同じ関数）をかける。ここでは微分のたびに k = 9（90 ms）でならした。
#
# 躍度の形が見えるようになる。ただし山の高さは本来の値より低くなり、角も丸くなる。
# 心電図の R ピークと同じで、**ならしすぎると見たいものも削れる**。
# 研究では、この「どこまでならすか」を決めるのが大事な仕事になる。

# %%
K = 9
x_s = moving_average(x, K)
vel_s = moving_average(diff_central(x_s, dt), K)
acc_s = moving_average(diff_central(vel_s, dt), K)
jerk_s = moving_average(diff_central(acc_s, dt), K)
plot_four(t, [x_s, vel_s, acc_s, jerk_s], ideal, f"moving average (k = {K}) before each derivative (dashed: ideal)")

# %% [markdown]
# ## 滑らかさを 1 つの数字にする
#
# 躍度を 2 乗して、時間で足し合わせた値（躍度の 2 乗の積分）が小さいほど滑らかな動き。
# 書字の研究では、この値を使って字を書く動作の滑らかさを評価している。
#
# 前処理なしだと、ノイズのせいで桁違いに大きな値になってしまう。

# %%
def jerk_cost(jerk, dt):
    total = 0.0
    for j in jerk:
        total += j * j * dt
    return total


print("躍度の 2 乗の積分 [mm^2/s^5]")
print(f"  ノイズなしの式      : {jerk_cost(ideal[3], dt):.3e}")
print(f"  前処理なしで微分    : {jerk_cost(jerk, dt):.3e}")
print(f"  前処理してから微分  : {jerk_cost(jerk_s, dt):.3e}")
