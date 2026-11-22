# 狸之力：网站记录时点核对 v146

上一轮392份记录的 lifeDelta 都等于该步公开命元变化，这个测量成立，但它不能证明该步已经包含战斗内所有命元收益。原始网页记录会先写扣血，之后可能恢复旧余额，再写新的净余额；应保留时序，不能按中途变化简单累加奖励。

本轮不改狸之力、玉露瓶、战斗或结算规则。新增只读观察器，以每名玩家第一次胜/负累计恰好增加本场结果为界，最多查看32个源步骤；遇另一场权威战斗、相关准备操作、缺值或异常计数就停止。选取边界不接收模拟命元，不搜索相等结果，后续状态不进入开战输入。

| 回放轮次 | 战斗当步变化 | 模拟净变化 | 后续计数更新时变化 | 比较 |
|---|---|---|---|---|
| [round1](https://sharpobject.github.io/yxp_wiki/zh/recordings_longyao/?season=10&recording=r-6364f949a4e3854c&step=11) | [0, -5] | [3, -5] | [3, -5] | 双方一致 |
| [round2](https://sharpobject.github.io/yxp_wiki/zh/recordings_longyao/?season=10&recording=r-6364f949a4e3854c&step=20) | [-6, 0] | [-3, 0] | [-3, 0] | 双方一致 |
| [round3](https://sharpobject.github.io/yxp_wiki/zh/recordings_longyao/?season=10&recording=r-6364f949a4e3854c&step=46) | [-4, 0] | [-1, 0] | [-1, 0] | 双方一致 |
| [round4](https://sharpobject.github.io/yxp_wiki/zh/recordings_longyao/?season=10&recording=r-6364f949a4e3854c&step=74) | [0, -9] | [3, -6] | [3, -2] | 本人一致，对手仍差4 |
| [round8](https://sharpobject.github.io/yxp_wiki/zh/recordings_longyao/?season=10&recording=r-6364f949a4e3854c&step=156) | [-10, 0] | [-7, 0] | [-7, 0] | 双方一致 |
| [round11](https://sharpobject.github.io/yxp_wiki/zh/recordings_longyao/?season=10&recording=r-6364f949a4e3854c&step=214) | [-15, 0] | [-9, 0] | [-9, 0] | 双方一致 |
| [round18](https://sharpobject.github.io/yxp_wiki/zh/recordings_longyao/?season=10&recording=r-6364f949a4e3854c&step=421) | [-20, 0] | [-14, 0] | [-14, 0] | 双方一致 |

七轮均来自同一整局 r-6364f949a4e3854c，不是七个独立样本。龙瑶一侧7/7对应，双方6/7对应。第4轮对手后续值比战斗预测多4点，未将其扣除、归零或直接解释成已验证的经营奖励。

全体196场采用同一窗口规则：186场有双方计数更新端点，157场双方余额对应；10场因先出现准备操作而保持观察未决。这一窗口可能已经进入下一回合，包含战斗以外的自动收益。因此157/186不替代181/196的战斗当步净变化比较，两者也都不是S2验收准确率。

196场网站战斗已重新执行，原有输出包括命元回执全部相同。原954场回归结果和冻结源码校验保持，本轮未重复执行954场。观察器边界检查10项通过，覆盖只取首次计数、不能寻找后续相等值、阻断新战斗/准备操作、缺值及来源绑定。

开关、阵旗手牌和五行玉瓶的已有战斗对照不变，继续引用v145的按净命元重算子集；本轮没有额外声称换牌、跨轮资源或策略训练已经完成。

当前仍为S2开发诊断。网站版本、完整开战信息、纯战斗结束时点、终局HP和行动次数仍有边界限制；没有新GPU任务或战斗训练标签。

证据：runs/stages/20261117T013800Z-s2-civet-source-timing/。
