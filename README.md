# StarCraft II AI Coach

基于 StarCraft II 官方 API 的 AI 教练与自适应陪练实验项目。

项目使用 PySC2、BurnySc2 和 sc2reader，分别探索游戏观察与控制、Bot 开发以及 Replay 数据分析。

## 1. 开发环境

**硬件**

- Mac mini M4（Apple Silicon）
- macOS
- 外置磁盘 `/Volumes/MacExt`

**软件**

- StarCraft II
- Homebrew
- Python 3.11
- BurnySc2
- PySC2
- sc2reader

**项目路径**

```text
/Volumes/MacExt/Developer/sc2-coach
```

**游戏路径**

```text
/Volumes/MacExt/BattleNet/StarCraft II
```

## 2. 安装 Python 3.11

安装：

```bash
brew install python@3.11
```

验证：

```bash
$(brew --prefix python@3.11)/bin/python3.11 --version
```

预期输出：

```text
Python 3.11.x
```

> 不建议直接使用系统默认 Python 或 Python 3.15。当前项目已经使用 Python 3.11 完成测试。

## 3. 创建项目目录

```bash
mkdir -p /Volumes/MacExt/Developer/sc2-coach

cd /Volumes/MacExt/Developer/sc2-coach

mkdir -p bots tests replays patches
```

建议目录：

```text
sc2-coach/
├── README.md
├── patch.md
├── bots/
│   └── first_bot.py
├── tests/
│   └── read_replay.py
├── replays/
│   └── 1st.SC2Replay
├── patches/
├── .venv-bot/
└── .venv-pysc2/
```

## 4. 配置 SC2PATH

PySC2 和 BurnySc2 需要知道 SC2 的安装位置。

```bash
export SC2PATH="/Volumes/MacExt/BattleNet/StarCraft II"
```

验证：

```bash
test -d "$SC2PATH/Versions" && echo "SC2 path OK"
```

如果输出：

```text
SC2 path OK
```

说明游戏数据目录正确。

### 永久配置（可选）

macOS 默认使用 zsh，可将环境变量写入 `~/.zshrc`：

```bash
echo 'export SC2PATH="/Volumes/MacExt/BattleNet/StarCraft II"' >> ~/.zshrc
```

重新加载：

```bash
source ~/.zshrc
```

> 注意：外置磁盘必须已挂载，且路径保持不变。

## 5. 安装 BurnySc2

### 5.1 创建独立虚拟环境

```bash
cd /Volumes/MacExt/Developer/sc2-coach

$(brew --prefix python@3.11)/bin/python3.11 \
  -m venv .venv-bot
```

激活：

```bash
source .venv-bot/bin/activate
```

### 5.2 安装依赖

```bash
python -m pip install --upgrade pip setuptools wheel

python -m pip install burnysc2
```

### 5.3 验证

```bash
python --version

python -c "import sc2; print('BurnySc2 OK')"
```

### 5.4 保存依赖版本

```bash
python -m pip freeze > requirements-bot-lock.txt
```

退出虚拟环境：

```bash
deactivate
```

## 6. 安装 PySC2

### 6.1 创建独立环境

```bash
cd /Volumes/MacExt/Developer/sc2-coach

$(brew --prefix python@3.11)/bin/python3.11 \
  -m venv .venv-pysc2
```

激活：

```bash
source .venv-pysc2/bin/activate
```

### 6.2 安装依赖

```bash
python -m pip install --upgrade pip setuptools wheel

python -m pip install pysc2
```

### 6.3 修复 Protobuf 兼容性

当前环境需要使用：

```bash
python -m pip install --force-reinstall "protobuf==3.20.3"
```

验证：

```bash
python -c "
import google.protobuf
from s2clientprotocol import sc2api_pb2
print('Protobuf:', google.protobuf.__version__)
print('SC2 Protocol OK')
"
```

### 6.4 修复 Python 3.11 的 random.shuffle 兼容性

编辑：

```bash
vi .venv-pysc2/lib/python3.11/site-packages/pysc2/lib/colors.py
```

找到：

```python
random.shuffle(palette, lambda: 0.5)
```

替换为：

```python
for i in range(len(palette) - 1, 0, -1):
    j = int(0.5 * (i + 1))
    palette[i], palette[j] = palette[j], palette[i]
```

验证：

```bash
python -c "from pysc2.lib import features; print('Features OK')"
```

> 重要：这是本地源码补丁。重新安装 PySC2 后可能需要重新应用。

### 6.5 保存依赖版本

```bash
python -m pip freeze > requirements-pysc2-lock.txt
```

## 7. 安装 SC2 测试地图

PySC2 测试需要相应的 `.SC2Map` 文件。

官方地图包：

https://github.com/Blizzard/s2client-proto#map-packs

确保 Simple64 位于：

```text
/Volumes/MacExt/BattleNet/StarCraft II/Maps/Melee/Simple64.SC2Map
```

验证：

```bash
test -f "$SC2PATH/Maps/Melee/Simple64.SC2Map" \
  && echo "Map OK"
```

如果要测试其他地图，也需要安装相应地图文件。

## 8. 运行 PySC2

确保激活 PySC2 环境：

```bash
source .venv-pysc2/bin/activate
```

执行：

```bash
python -m pysc2.bin.agent --map Simple64
```

正常情况下会启动 SC2 游戏客户端，并运行测试 Agent。

终端可能输出：

```text
Starting episode 4: [random, random] on Simple64
```

或者：

```text
Episode 3 finished after 9216 game steps.
```

这表示测试对局正在执行。

停止：

```text
Ctrl+C
```

### 运行 CollectMineralShards 示例

安装相应的 mini-game 地图后，可以运行：

```bash
python -m pysc2.bin.agent \
  --map CollectMineralShards \
  --agent pysc2.agents.scripted_agent.CollectMineralShards
```

如果地图不存在，先确认 mini-game 地图包是否正确安装。

## 9. 编写第一个 BurnySc2 Bot

退出 PySC2 环境：

```bash
deactivate
```

激活 Bot 环境：

```bash
source .venv-bot/bin/activate
```

创建：

```text
bots/first_bot.py
```

示例代码：

```python
from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Race, Difficulty
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2.ids.unit_typeid import UnitTypeId


class FirstBot(BotAI):

    async def on_step(self, iteration: int):
        if iteration % 100 == 0:
            print(
                f"Iteration={iteration}, "
                f"Workers={self.workers.amount}, "
                f"Minerals={self.minerals}"
            )

        await self.distribute_workers()

        for command_center in self.townhalls.ready.idle:
            if (
                self.workers.amount < 20
                and self.supply_left > 0
                and self.can_afford(UnitTypeId.SCV)
            ):
                command_center.train(UnitTypeId.SCV)


if __name__ == "__main__":
    run_game(
        maps.get("Simple64"),
        [
            Bot(Race.Terran, FirstBot()),
            Computer(Race.Terran, Difficulty.Easy),
        ],
        realtime=False,
    )
```

运行：

```bash
python bots/first_bot.py
```

预期可以看到：

```text
Iteration=0, Workers=12, Minerals=50
Iteration=100, Workers=...
```

这个 Bot 可以训练 SCV 和分配采矿工人，但尚不具备完整作战能力。

## 10. Replay 解析

在 Bot 虚拟环境中安装：

```bash
python -m pip install sc2reader
```

如果已经生成过锁定文件，安装后需要重新执行：

```bash
python -m pip freeze > requirements-bot-lock.txt
```

### 10.1 基础解析示例

创建：

```text
tests/read_replay.py
```

示例：

```python
import sys
import sc2reader


def main():
    if len(sys.argv) != 2:
        print("Usage: python tests/read_replay.py <replay>")
        sys.exit(1)

    replay = sc2reader.load_replay(
        sys.argv[1],
        load_level=4,
    )

    print("Map:", replay.map_name)
    print("Game length:", replay.game_length)
    print("Players:")

    for player in replay.players:
        print(
            player.name,
            player.pick_race,
            player.result,
        )


if __name__ == "__main__":
    main()
```

运行：

```bash
python tests/read_replay.py "replays/1st.SC2Replay"
```

实际操作历史显示该测试已经执行，且用户确认测试成功。

> Replay 的具体可用字段取决于文件版本、解析库版本和加载级别。不要假设所有经济、APM 或单位事件都能直接获取。

## 11. 每次开发前的操作

进入项目：

```bash
cd /Volumes/MacExt/Developer/sc2-coach
```

确认游戏路径：

```bash
echo "$SC2PATH"
```

开发 Bot：

```bash
source .venv-bot/bin/activate
python bots/first_bot.py
```

开发 PySC2：

```bash
deactivate
source .venv-pysc2/bin/activate
python -m pysc2.bin.agent --map Simple64
```

注意：两套虚拟环境不要同时激活或混用依赖。

## 12. 项目当前状态

已验证：

- Python 3.11 环境
- PySC2 基础测试
- BurnySc2 FirstBot
- SC2 客户端启动与 API 通信
- Simple64 地图
- sc2reader Replay 基础测试

尚未验证：

- 真人玩家与 API Bot 同局对战
- Replay 深度战术分析
- 自适应难度
- AI 教练反馈
- 机器学习模型控制 Bot

## 13. 下一阶段开发路线

### 阶段一：基础 Bot

- 自动采矿
- 训练工人
- 建造补给站
- 建造兵营
- 训练陆战队员
- 简单进攻

### 阶段二：Replay 分析

- 提取玩家与比赛信息
- 分析建造顺序
- 统计单位损失
- 识别经济和运营问题
- 输出结构化分析结果

### 阶段三：真人陪练验证

验证真人玩家能否与自定义 API Bot 在同一场比赛中对战。

这是陪练功能的关键可行性验证，应优先进行。

### 阶段四：AI 教练

将 Replay 数据转换为可解释的训练建议。

### 阶段五：自适应陪练

根据玩家水平调整 Bot 的运营、进攻和战术策略。

## 14. 参考资料

- BurnySc2：https://github.com/BurnySc2/python-sc2
- PySC2：https://github.com/google-deepmind/pysc2
- Blizzard SC2 Protocol：https://github.com/Blizzard/s2client-proto
- Blizzard SC2 API：https://github.com/Blizzard/s2client-api
- sc2reader：https://github.com/GraylinKim/sc2reader

---

当前项目目标不是复现 AlphaStar，而是建立一个可持续扩展的 SC2 AI 实验平台，逐步实现对战、复盘分析和自适应陪练。

