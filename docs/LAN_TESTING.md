# PySC2 LAN 验证

## 范围与当前结论

目标环境：Python 3.11、PySC2 4.0.0、protobuf 3.20.3。依赖清单为
`requirements/pysc2.txt`，不要混用 `.venv-bot`。

已修复补丁文件内误存的 shell 命令；`_get_interface` 使用 `interface_format`；
`_requested_races` 在 join 成功、读取 game_info 后，以实际 player_id 建立双方映射，排除观察者。
这些 Python 层修复不能证明 `join_game` WebSocket 断开已解决。

## 离线回归

在仓库根目录执行：

```sh
./.venv-pysc2/bin/python -B -m unittest discover -s tests -p 'test_*.py' -v
./.venv-pysc2/bin/python -B patches/fix_pysc2_lan.py
./.venv-pysc2/bin/python -B patches/fix_pysc2_lan.py --apply
./.venv-pysc2/bin/python -B patches/fix_pysc2_lan.py --check
```

默认只预览；`--check` 在需要补丁时返回 1，已应用返回 0。
应用前保存 `.py.lan.bak`，不同内容的已有备份会阻止写入。
未知源码布局会拒绝写入。`--target /path/to/lan_sc2_env.py` 可对副本验证。
重装 PySC2 后还需要先应用 `patches/fix_pysc2_colors.py`。

测试覆盖原始调用布局、旧补丁迁移、幂等、备份保护、未知布局拒绝，以及真实
LanSC2Env/SC2Env 代码的构造、join 请求端口、种族、观察者过滤、实时/非实时 reset。
SC2 进程、网络、特征转换和观测被模拟，因此不验证游戏引擎或真实 WebSocket。
第二次 reset 应抛 RestartError，这是 LAN 原有约束。
测试 fixture 来自本机 PySC2 4.0.0 源码，撤销之前两项手工修改后保存；保留上游版权头。

## 真人双端复现

两个终端都进入同一个仓库，使用同一解释器和 SC2PATH；先开启真人端，看到 Join 提示后开启 Agent。
首次使用仅特征层，关闭 RGB，缩小图形路径的排查范围。这是对照实验，不能据此认定 RGB 是根因。

真人端：

```sh
export SC2PATH='/Volumes/MacExt/BattleNet/StarCraft II'
mkdir -p logs
./.venv-pysc2/bin/python -u -m pysc2.bin.play_vs_agent \
  --human --map Simple64 --host 127.0.0.1 --config_port 14380 \
  --realtime --render --rgb_screen_size 0 --rgb_minimap_size 0 \
  > logs/lan-human.log 2>&1
```

Agent 端：

```sh
export SC2PATH='/Volumes/MacExt/BattleNet/StarCraft II'
./.venv-pysc2/bin/python -u -m pysc2.bin.play_vs_agent \
  --host 127.0.0.1 --config_port 14380 --realtime --norender \
  --rgb_screen_size 0 --rgb_minimap_size 0 \
  > logs/lan-agent.log 2>&1
```

日志输出被重定向，可另开终端 `tail -f logs/lan-human.log logs/lan-agent.log`。
每次实验前另存旧日志；两个端的 realtime 必须一致（当前 LAN 代码没有自动同步它）。
端口范围是 14380–14384。成功标准：两端 join 成功，Agent 输出
`Connected, starting run_loop.`，真人端进入地图且双方持续推进。2026-11-15 用户已确认完整对局并获胜。
失败时保留两端完整日志、SC2 版本、进程退出码和 macOS DiagnosticReports 中同一时刻的 SC2 报告。
不要把程序结束后的 `sys.meta_path is None` 当成首个故障。

后续对照顺序：特征层基线 → 启用默认 RGB → 两端同时改为非实时。
每次只改变一个条件。无对应崩溃报告时，不能断言 SC2 崩溃；WebSocket 断开只说明连接结束。

## 最新实测记录

真人操作请使用上面的 `--render` 并在 PySC2/Pygame 窗口输入。
后台脚本、停止问题和已跑通的带时间戳日志命令见 [当日记录](SESSION_2026-11-15.md)。
