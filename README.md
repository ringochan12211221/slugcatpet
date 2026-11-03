Windows 桌面宠物：让 Rain World 的蛞蝓猫住在你的屏幕上。exe 见 release 压缩包。

演示视频合集：https://space.bilibili.com/1810584454/lists?sid=8504199

RainWorld里控制蛞蝓猫各个bodychunk拼接和行动的质点系统是C#写的，反编译后参考常量和主要函数就能足够相似的模拟。但粒子shader等效果难以复现原游戏渲染，又为了提升桌宠性能，所以我做了大量简化。

## 关于本 fork（魔改版）

这是 [lingxiaojun/slugcatpet](https://github.com/lingxiaojun/slugcatpet) 的 fork，基于上游 v1.2.0 做的个人魔改。
上游代码以 MIT 许可发布，本仓库沿用同一许可（见 [LICENSE](LICENSE)），版权归原作者所有。

在原版基础上新增 / 改动：

| 功能 | 版本 | 说明 |
| --- | --- | --- |
| 概率追光标 | v1.2.1 | 猫按好感度决定要不要追你的鼠标 |
| 植物再生 | v1.2.1 | 果子 / 黏菌被吃掉后原地再长；被猫摘走也仍在原地长，不会长到猫脚边去 |
| 爬窗口 | v1.3.0 → v1.3.2 | 窗口边框当虚拟杆（左右竖杆、顶部横杆、底边），所有猫种都能爬，能站也能倒挂；杆只覆盖真实可见的边框，贴地的一端接地 |
| 性能优化 | v1.4.0 | 每帧重绘范围从包围盒改成精确矩形列表（合并到 16 条），雪从 40Hz 降到 24Hz |
| 插矛搭脚点 | v1.5.0 | 没舌头的猫也能靠插矛自己登高 |
| 珍珠 | v1.6.0 → v1.6.1 | 把原「光萤」换成雨世界官方珍珠：逐格还原官方贴图、33 色官方色表随机（白最常见）、偶尔闪光、手感调沉；按官方截图实测把直径定为 9px。猫会去拍飞它、叼起来扔、追着跟随型跑 |
| 听歌摇摆 | v1.7.0 → v1.7.1 | 零依赖检测系统音频会话（`IAudioSessionManager2` + ctypes），有别程序在放声音且猫站着发呆时跟着晃，摇 8~12 秒歇 3~5 秒，幅度按性格 activity 缩放，设置面板可调开关 / BPM / 幅度 |
| 左键打断光标劫持 | v1.7.2 | 猫抢光标或超度时鼠标会被锁住，现在左键一按立刻松手（打游戏时特别有用）；顺带修了「进全屏收起前没还光标」导致鼠标可能永久锁死的问题 |
| 被摸（享受） | v1.8.0 | 光标在猫身上上下来回搓几下，猫眯眼、微微抬头、慢慢晃起来；好感上涨（有封顶）；摸久了会腻，抖一下甩开你并躲一阵 |

当前版本 **v1.8.0**。改完跑 `python tests/behavior_check.py check` 确认原有猫行为没变，发布包同样不含任何游戏素材。

## 运行要求

- Windows 10 / 11
- Python 3.12+
- 电脑上装了 Rain World 和 Downpour DLC。第一次启动时要从游戏里读取图像。

## 安装与运行

```powershell
pip install PySide6 UnityPy numpy Pillow
python run_slugcatpet.py
```

也可以用 uv：`uv sync` 后 `uv run run_slugcatpet.py`。

第一次启动时选一下 Rain World 的安装目录，程序会把要用的图像和几首游戏配乐提取到 `~/.slugcatpet/assets`。

## 皮肤

可以用 Dress My Slugcat 的皮肤。创意工坊里订阅的会自动出现，别人发给你的放进皮肤文件夹（设置 → 打开皮肤文件夹）就行。
在设置里点猫旁边的「外观」，可以换皮肤、改颜色、开关配件（疤、鳃）。头、脸、身体、手臂、臀、腿、尾巴还能各用不同的皮肤，也能单独设颜色、调尾巴形状。皮肤格式和画法见 [Dress My Slugcat](https://steamcommunity.com/sharedfiles/filedetails/?id=2948971756)。

## 改代码

结构见 [ai-docs/ARCHITECTURE.md](ai-docs/ARCHITECTURE.md)，加角色见 [ai-docs/CHARACTERS.md](ai-docs/CHARACTERS.md)，参数见 [ai-docs/PARAMS.md](ai-docs/PARAMS.md)。
改完跑一下 `python tests/behavior_check.py check`，确认原有的猫行为没变。格式用 ruff：`uv run ruff format` / `uv run ruff check`。

## 素材与版权说明

- 本仓库不包含任何 Rain World 游戏素材。全部游戏图像和音乐在你本机、从你自己的正版安装中提取。
- 皮肤归各自的作者所有。本程序只在你本机读取皮肤，不会打包或分发。
- 此项目为粉丝项目，Rain World 及相关名称、美术均归其权利人所有。
- 本仓库代码以 MIT 许可发布（见 [LICENSE](LICENSE)）；该许可仅覆盖本仓库代码，不授予任何游戏素材相关权利。
- `slugcatpet/audio/fsbogg.py` 部分改写自 [python-fsb5](https://github.com/HearthSim/python-fsb5)（MIT，Simon Pinfold）；`vorbis_setups.py` 中的数据由 libvorbis（BSD，Xiph.Org）生成。

---

A Windows desktop pet that puts Rain World's slugcats on your screen. The .exe is in the release zip.

Demo videos (Bilibili): https://space.bilibili.com/1810584454/lists?sid=8504199

The mass-point system in Rain World that controls the connection and movement of the slugcat's various body chunks is written in C#. After decompiling it, I referred to its constants and main functions, which was enough to create a sufficiently similar simulation. However, effects like particle shaders are hard to replicate to match the original game's rendering, and to boost the desktop pet's performance, I made extensive simplifications.

## About this fork (modded edition)

This is a personal fork of [lingxiaojun/slugcatpet](https://github.com/lingxiaojun/slugcatpet), based on upstream v1.2.0.
The upstream code is MIT-licensed and this repository keeps the same license (see [LICENSE](LICENSE)); copyright belongs to the original author.

What I added or changed on top of the original:

| Feature | Version | Notes |
| --- | --- | --- |
| Chance-based cursor chasing | v1.2.1 | The cat decides whether to chase your cursor based on its affection |
| Plant regrowth | v1.2.1 | Fruit / slime mold regrows where it was eaten; if the cat picks it off, it still regrows there instead of at the cat's feet |
| Window climbing | v1.3.0 → v1.3.2 | Window borders act as virtual poles (left/right verticals, top bar, bottom edge). Every slugcat can climb; they can stand on or hang from a pole. Poles only cover borders that are actually visible, and the end touching the ground is grounded |
| Performance work | v1.4.0 | Per-frame repaint switched from bounding box to an exact rectangle list (merged down to 16); snow drops from 40Hz to 24Hz |
| Spear-planting footholds | v1.5.0 | Cats without a tongue can still climb up by planting a spear |
| Pearls | v1.6.0 → v1.6.1 | Replaced the original "glowfly" with an official Rain World pearl: pixel-by-pixel recreation of the official sprite, random color from the official 33-color palette (white most common), occasional shine, heavier feel. Diameter set to 9px measured against official screenshots. Cats will swat it, pick it up and throw it, and chase the following variant |
| Music sway | v1.7.0 → v1.7.1 | Zero-dependency detection of system audio sessions (`IAudioSessionManager2` + ctypes). When something else is playing sound and the cat is standing around, it sways: 8–12s swaying, 3–5s rest, amplitude scaled by the personality's `activity`. Toggle / BPM / amplitude are in the settings panel |
| Left click breaks cursor hijack | v1.7.2 | When the cat grabs or ascends your cursor, the mouse is locked — now a single left click makes it let go right away (very handy while gaming). Also fixed the mouse possibly staying locked forever because the cursor wasn't released before hiding on fullscreen |
| Petting (enjoyment) | v1.8.0 | Rub the cursor up and down over the cat a few times and it squints, lifts its head slightly and starts swaying slowly; affection rises (with a cap). Pet too long and it gets fed up — it shakes you off and avoids you for a while |

Current version: **v1.8.0**. After a change, run `python tests/behavior_check.py check` to confirm the existing cat behaviors are unchanged. The release package likewise contains no game assets.

## Requirements

- Windows 10 / 11
- Python 3.12+
- Rain World and the Downpour DLC installed. The first launch reads images from the game.

## Install and run

```powershell
pip install PySide6 UnityPy numpy Pillow
python run_slugcatpet.py
```

With uv: `uv sync`, then `uv run run_slugcatpet.py`.

On first launch, pick your Rain World install folder. The images and a few game music tracks the app needs are extracted to `~/.slugcatpet/assets`.

## Skins

Dress My Slugcat skins work. Workshop subscriptions show up on their own; put skins you get elsewhere in the skins folder (Settings → Open skins folder).
Click "Appearance" next to a cat in Settings to change its skin, colors and accessories (scar, gills). Head, face, body, arms, hips, legs and tail can each use a different skin and color, and the tail shape is adjustable. Skin format and drawing: [Dress My Slugcat](https://steamcommunity.com/sharedfiles/filedetails/?id=2948971756).

## Changing the code

Layout: [ai-docs/ARCHITECTURE.md](ai-docs/ARCHITECTURE.md). Adding characters: [ai-docs/CHARACTERS.md](ai-docs/CHARACTERS.md). Parameters: [ai-docs/PARAMS.md](ai-docs/PARAMS.md). These are in Chinese.
After a change, run `python tests/behavior_check.py check` to make sure the existing cats still behave the same. Format with ruff: `uv run ruff format` / `uv run ruff check`.

## Assets and copyright

- This repository contains no Rain World assets. All game images and music are extracted on your machine from your own copy.
- Skins belong to their authors. The app only reads them on your machine and never bundles or redistributes them.
- This is a fan project. Rain World and all related names and artwork belong to their respective owners.
- The code is released under the MIT license (see [LICENSE](LICENSE)). It covers this repository's code only and grants no rights to any game assets.
- `slugcatpet/audio/fsbogg.py` is partly adapted from [python-fsb5](https://github.com/HearthSim/python-fsb5) (MIT, Simon Pinfold); the data in `vorbis_setups.py` was generated with libvorbis (BSD, Xiph.Org).
