
from sc2 import maps
from sc2.bot_ai import BotAI
from sc2.data import Race, Difficulty
from sc2.main import run_game
from sc2.player import Bot, Computer
from sc2.ids.unit_typeid import UnitTypeId


class FirstBot(BotAI):

    async def on_step(self, iteration: int):
        # 每隔约 100 次迭代输出一次状态
        if iteration % 100 == 0:
            print(
                f"Iteration={iteration}, "
                f"Workers={self.workers.amount}, "
                f"Minerals={self.minerals}"
            )

        # 自动分配工人采矿
        await self.distribute_workers()

        # 人族主基地训练 SCV
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

