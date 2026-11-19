# %% [markdown]
# # ① 読み込み — メタデータ付き CSV を読む（解答例）
#
# 計測器が出す CSV は、先頭に `#` で始まる説明の行（メタデータ）が付いていることが多い。
# ここでは 1 行ずつ読んで、**メタデータ / 列名 / データ**の 3 つに仕分ける。
#
# - データは授業用に計算で作った**合成データ**（実際の人の計測ではない）
# - 解答例は Python だが、やっていることは「1 行ずつ読んで場合分け」だけ。どの言語でも同じ手順で書ける

# %%
import os

DATA_URL = ""  # Colab などデータが手元にない環境では、配布ページの URL + "data/" を入れる


def data_path(name):
    """データファイルの場所を探す。見つからなければ DATA_URL から取ってくる。"""
    for folder in ["data", "../data", "."]:
        path = os.path.join(folder, name)
        if os.path.exists(path):
            return path
    if DATA_URL != "":
        import urllib.request

        urllib.request.urlretrieve(DATA_URL + name, name)
        return name
    raise FileNotFoundError(name + " が見つかりません。data フォルダの場所を確かめてください")


# %% [markdown]
# ## まず中身をそのまま見る
#
# いきなり読み込む関数を書かない。先頭の十数行を表示して、形を確かめる。

# %%
with open(data_path("ecg_clean.csv")) as f:
    for line_number in range(14):
        print(f.readline(), end="")

# %% [markdown]
# 分かること:
#
# - `#` で始まる行が 9 行。`キー: 値` の形をしている
# - その次の 1 行が列名（`index,ecg_mV,event`）
# - それより下がデータ。区切りはカンマ
# - 3 列目 `event` は文字列で、ほとんどの行は空


# %% [markdown]
# ## 読み込む関数
#
# 行の先頭を見て 3 通りに場合分けする。「何行読み飛ばす」と数を決め打ちしないので、
# メタデータの行数が違うファイルでもそのまま使える。

# %%
def read_signal_csv(path):
    meta = {}  # メタデータ（キー -> 値）
    columns = None  # 列名のリスト
    rows = []  # データ。1 行 = 文字列のリスト

    with open(path) as f:
        for line in f:
            line = line.strip()  # 行末の改行を取る
            if line == "":
                continue  # 空行は飛ばす
            if line.startswith("#"):
                # "# sampling_rate_hz: 500" -> キー "sampling_rate_hz"、値 "500"
                # 値の中にも ":" がある行（計測日時）があるので、最初の ":" でだけ分ける
                key, value = line[1:].split(":", 1)
                meta[key.strip()] = value.strip()
            elif columns is None:
                columns = line.split(",")  # # でない最初の行は列名
            else:
                rows.append(line.split(","))  # それ以外はデータ
    return meta, columns, rows


meta, columns, rows = read_signal_csv(data_path("ecg_clean.csv"))

print("メタデータ:")
for key in meta:
    print("  ", key, "=", meta[key])
print("列名:", columns)
print("データの行数:", len(rows))
print("最初の 3 行:", rows[:3])

# %% [markdown]
# ## 文字列を数値に直す
#
# ここまでの中身は全部**文字列**。`"500"` と `500` は別物なので、計算に使うものは数値に直す。
#
# - サンプリング周波数: メタデータから取り出して数値にする
# - 心電図の列: 小数にする
# - イベントの列: 文字列のまま。空でない行だけ「何番目に何が起きたか」を取り出す

# %%
fs = float(meta["sampling_rate_hz"])  # サンプリング周波数 [Hz]

ecg = []
events = []
for row in rows:
    ecg.append(float(row[1]))
    if row[2] != "":
        events.append((int(row[0]), row[2]))

print("サンプリング周波数 fs =", fs, "Hz")
print("データ点数 n =", len(ecg))
print("計測の長さ =", len(ecg) / fs, "秒")
print("イベント:", events)

# %% [markdown]
# ## 確かめる
#
# メタデータの `n_samples` と、実際に読めた行数が合っているかを見る。
# 合っていなければ、読み飛ばしや場合分けのどこかがおかしい。

# %%
assert len(ecg) == int(meta["n_samples"]), "行数がメタデータと合わない"
print("OK: 行数はメタデータの n_samples と一致")
