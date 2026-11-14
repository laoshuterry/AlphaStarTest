# StarCraft II AI 开发环境问题与补丁记录

## 1. 环境信息

| 项目 | 配置 |
|---|---|
| 操作系统 | macOS |
| 设备 | Mac mini M4（Apple Silicon） |
| Python | 3.11 |
| Python 安装方式 | Homebrew |
| 项目路径 | `/Volumes/MacExt/Developer/sc2-coach` |
| SC2 安装路径 | `/Volumes/MacExt/BattleNet/StarCraft II` |
| Bot 框架 | BurnySc2 |
| 强化学习接口 | PySC2 |
| Replay 解析 | sc2reader |

本文件记录实际安装和测试过程中出现的问题，以及已经采用的修复方法。

---

## PATCH-001：Python 3.15 导致依赖构建失败

**错误信息**

```text
BackendUnavailable: Cannot import 'setuptools.build_meta'
```

**问题分析**

最初使用 Python 3.15 创建虚拟环境。安装 BurnySc2 时，pip 在依赖构建阶段无法导入 setuptools 构建后端。

Python 3.15 过新，可能导致部分旧依赖没有兼容的预编译包。但现有日志不足以证明这是唯一原因。

**解决方法**

改用 Python 3.11。

```bash
brew install python@3.11

cd /Volumes/MacExt/Developer/sc2-coach

$(brew --prefix python@3.11)/bin/python3.11 \
  -m venv .venv-bot

source .venv-bot/bin/activate

python -m pip install --upgrade pip setuptools wheel
python -m pip install burnysc2
```

**验证**

```bash
python --version
python -c "import setuptools.build_meta; print('Build backend OK')"
python -c "import sc2; print('BurnySc2 OK')"
```

**结果：** Python 3.11 环境成功安装 BurnySc2。

---

## PATCH-002：PySC2 与 Protobuf 版本不兼容

**错误信息**

```text
TypeError: Descriptors cannot be created directly.
```

发生位置：

```text
s2clientprotocol/common_pb2.py
google/protobuf/descriptor.py
```

**原因**

PySC2 所依赖的 `s2clientprotocol` 使用较旧的 Protobuf 生成代码，与新版 protobuf 运行库不兼容。

**解决方法**

在 PySC2 虚拟环境中固定 protobuf 版本：

```bash
source .venv-pysc2/bin/activate

python -m pip install --force-reinstall "protobuf==3.20.3"
```

**验证**

```bash
python -c "
import google.protobuf
from s2clientprotocol import sc2api_pb2
print(google.protobuf.__version__)
print('SC2 Protocol OK')
"
```

**结果：** Protobuf 模块成功导入。

**注意：** 不要在升级其他依赖时无意升级 protobuf。

---

## PATCH-003：Python 3.11 移除了 random.shuffle 的第二参数

**错误信息**

```text
TypeError: Random.shuffle() takes 2 positional arguments but 3 were given
```

**问题位置**

```text
.venv-pysc2/lib/python3.11/site-packages/pysc2/lib/colors.py
```

原始代码：

```python
random.shuffle(palette, lambda: 0.5)
```

**原因**

Python 3.11 移除了 `random.shuffle()` 的自定义随机函数参数。

**解决方法**

将上述代码替换为：

```python
for i in range(len(palette) - 1, 0, -1):
    j = int(0.5 * (i + 1))
    palette[i], palette[j] = palette[j], palette[i]
```

该补丁模拟旧实现中使用固定随机值的洗牌行为。

**验证**

```bash
python -c "from pysc2.lib import features; print('Features OK')"
```

**结果：** PySC2 features 模块成功导入。

**注意**

- 这是对已安装第三方库的本地补丁。
- 重新安装 PySC2 可能覆盖该修改。
- 建议后续将补丁制作成自动化脚本。

---

## PATCH-004：PySC2 无法找到 StarCraft II 安装目录

**错误信息**

```text
FileNotFoundError:
'/Applications/StarCraft II/Versions'
```

**原因**

PySC2 默认查找 `/Applications/StarCraft II`，但游戏实际安装在外置磁盘。

**解决方法**

```bash
export SC2PATH="/Volumes/MacExt/BattleNet/StarCraft II"
```

**验证**

```bash
test -d "$SC2PATH/Versions" && echo "SC2 path OK"
```

**结果：** PySC2 能够找到游戏版本目录。

**注意**

`SC2PATH` 应指向游戏数据根目录，而不是 `.app` 文件。

---

## PATCH-005：Simple64 地图文件缺失

**错误信息**

```text
ValueError:
Map Melee/Simple64.SC2Map not found in
/Volumes/MacExt/BattleNet/StarCraft II/Maps.
```

**原因**

PySC2 已找到 SC2 客户端，但缺少测试地图。

**解决方法**

从 Blizzard 官方地图包获取 `Simple64.SC2Map`，确保路径为：

```text
$SC2PATH/Maps/Melee/Simple64.SC2Map
```

官方地图资源：

https://github.com/Blizzard/s2client-proto#map-packs

**验证**

```bash
test -f "$SC2PATH/Maps/Melee/Simple64.SC2Map" \
  && echo "Map OK"
```

**结果：** 后续 PySC2 测试成功运行，说明所需地图已经可用。

---

## PATCH-006：SC2 API WebSocket 连接重试

**日志**

```text
Connecting to:
ws://127.0.0.1:58837/sc2api
attempt: 15
running: True
```

**分析**

PySC2 通过本地 WebSocket 连接 SC2 API。

连接重试不一定意味着失败，客户端启动和初始化可能需要一定时间。

在本次调试中，后续明确出现过地图缺失错误，因此不能将全部连接重试归因于网络问题。

**处理建议**

1. 确认 `SC2PATH` 正确。
2. 确认地图存在。
3. 等待客户端初始化。
4. 如果最终超时，再检查 SC2 进程及客户端日志。

**结果：** 后续 PySC2 能够运行完整测试对局。

---

## PATCH-007：BurnySc2 BotAI 不存在 race_worker 属性

**错误信息**

```text
AttributeError:
'FirstBot' object has no attribute 'race_worker'
```

**原因**

示例代码使用了不存在的 `self.race_worker` 属性。

**解决方法**

对于人族 Bot，显式指定 SCV：

```python
from sc2.ids.unit_typeid import UnitTypeId

if self.can_afford(UnitTypeId.SCV):
    command_center.train(UnitTypeId.SCV)
```

**验证**

```bash
source .venv-bot/bin/activate
python bots/first_bot.py
```

**结果：** 用户确认 Bot 成功运行。

---

## PATCH-008：PySC2 Unknown ability 警告

**警告**

```text
Unknown ability 4129 seen as available.
```

**分析**

SC2 客户端报告了 PySC2 当前动作映射无法识别的技能 ID。

这可能与客户端版本和 PySC2 的静态数据不完全匹配有关。

**当前处理**

暂时保留警告，不修改技能映射。

**结果：** 测试仍能继续执行多个 Episode。

**后续风险**

如果需要使用该技能，应进一步检查技能 ID、协议数据及 PySC2 的动作映射。

---

## PATCH-009：程序退出时出现清理异常

**错误信息**

```text
ImportError:
sys.meta_path is None, Python is likely shutting down
```

以及：

```text
Shutdown with return code: -15
```

**分析**

此前的地图加载错误导致程序退出，在解释器关闭过程中又触发了资源清理异常。

**处理方法**

优先修复引发退出的原始错误，不必将清理异常作为独立故障处理。

如果没有其他异常，正常的进程清理日志不代表失败。

---

## PATCH-010：默认 PySC2 Agent 连续高速运行

**日志**

```text
Episode 3 finished after 9216 game steps.
Outcome: [-1], reward: [-1]

Starting episode 4: [random, random] on Simple64
```

**分析**

PySC2 默认测试程序会持续运行多个 Episode，可能明显快于真人游戏节奏。

**处理方法**

在终端使用 `Ctrl+C` 停止。

`--step_mul` 调整每次动作推进的游戏帧数，不等于限制实际运行速度。

**结果：** PySC2 成功执行多局测试。

---

## 当前验证状态

| 项目 | 状态 |
|---|---|
| Python 3.11 | 通过 |
| BurnySc2 安装 | 通过 |
| PySC2 安装 | 通过 |
| Protobuf 导入 | 通过 |
| PySC2 features 导入 | 通过 |
| SC2 游戏启动 | 通过 |
| Simple64 测试 | 通过 |
| BurnySc2 FirstBot | 通过 |
| Replay 测试 | 用户确认通过 |
| 真人与 API Bot 对战 | 尚未验证 |

## 后续维护建议

- 固定 Python 3.11。
- 分别保存两个虚拟环境的依赖清单。
- 保留 PySC2 本地补丁。
- 不要直接升级全部依赖。
- 重要环境变更后重新运行 PySC2、BurnySc2 和 Replay 三项测试。
