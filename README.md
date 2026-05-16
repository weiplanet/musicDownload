
基于 [musicdl](https://github.com/CharlesPikachu/musicdl) 项目开发的音乐下载器桌面客户端，使用 PySide6 构建界面。

### 软件截图

<table align="center" border="0" cellpadding="10">
  <tr>
    <td align="center">
      <img src="images/1.png" width="350"><br>
      <b>搜索结果</b>
    </td>
    <td align="center">
      <img src="images/2.png" width="350"><br>
      <b>搜索中</b>
    </td>
    <td align="center">
      <img src="images/3.png" width="350"><br>
      <b>歌单解析</b>
    </td>
  </tr>
</table>

### 功能特性

- 支持 **17 个音乐平台** 同时搜索（默认：酷我 + 酷狗）
- 两种搜索模式：**关键词搜索** / **歌单链接解析**
- 搜索结果显示专辑封面、歌手、专辑、格式、大小、时长、来源
- 勾选单首或批量下载，支持按"勾选 / 全选 / 未勾选"范围下载
- 下载进度实时显示（X / Y 首），支持**取消**进行中的下载
- 搜索后可选择**自动下载全部**
- 文件按 `歌名-歌手-专辑.格式` 命名保存，同步保存 `.lrc` 歌词文件
- 自定义保存目录

### 支持平台

苹果音乐、Deezer、5sing、Jamendo、Joox、酷我音乐、酷狗音乐、咪咕音乐、网易云音乐、QQ音乐、千千音乐、Qobuz、SoundCloud、StreetVoice、汽水音乐、Spotify、TIDAL

### 环境要求

- Python 3.13
- Windows

### 安装与运行

```bash
git clone https://github.com/MrsEWE44/musicDownload.git
cd musicDownload

python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
python musicdownload.py
```
