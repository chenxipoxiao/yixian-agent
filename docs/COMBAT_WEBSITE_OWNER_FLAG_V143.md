# 网站本人手牌与五行阵旗完整战斗核对 v143

从固定网站提交中按预登记顺序检查12份花沁蕊回放，找到两份本人牌阵含五行阵旗的记录。共提取35个完整开战边界，其中7个含阵旗。下载压缩回放合计302001字节；所有文件校验Git对象及SHA256，未按胜负选择样本。

阵旗相关7个边界中，7场完整执行，7场实际执行阵旗、共11次；胜者7场一致，命元损失7场一致。

| 对局 / 轮次 | 阵旗等级 | 手牌数 | 阵旗实际执行 | 胜者一致 | 命元：模拟 / 记录 | 先手条件 |
|---|---:|---:|---:|---|---|---|
| [r-050f836bfc5bd2d1/round12](https://sharpobject.github.io/yxp_wiki/zh/recordings_huaqinrui/?season=10&recording=r-050f836bfc5bd2d1&step=265) | 1 | 4 | 2 | 是 | [0, -21] / [0, -21] | 严格速度关系 |
| [r-050f836bfc5bd2d1/round13](https://sharpobject.github.io/yxp_wiki/zh/recordings_huaqinrui/?season=10&recording=r-050f836bfc5bd2d1&step=287) | 1 | 8 | 2 | 是 | [0, -20] / [0, -20] | 严格速度关系 |
| [r-050f836bfc5bd2d1/round14](https://sharpobject.github.io/yxp_wiki/zh/recordings_huaqinrui/?season=10&recording=r-050f836bfc5bd2d1&step=312) | 1 | 10 | 1 | 是 | [-26, 0] / [-26, 0] | 严格速度关系 |
| [r-050f836bfc5bd2d1/round15](https://sharpobject.github.io/yxp_wiki/zh/recordings_huaqinrui/?season=10&recording=r-050f836bfc5bd2d1&step=335) | 2 | 11 | 2 | 是 | [-26, 0] / [-26, 0] | 严格速度关系 |
| [r-050f836bfc5bd2d1/round16](https://sharpobject.github.io/yxp_wiki/zh/recordings_huaqinrui/?season=10&recording=r-050f836bfc5bd2d1&step=367) | 2 | 1 | 1 | 是 | [-26, 0] / [-26, 0] | 记录同速先手 |
| [r-23127fac20f0cf14/round15](https://sharpobject.github.io/yxp_wiki/zh/recordings_huaqinrui/?season=10&recording=r-23127fac20f0cf14&step=270) | 1 | 3 | 2 | 是 | [-22, 0] / [-22, 0] | 记录同速先手 |
| [r-23127fac20f0cf14/round17](https://sharpobject.github.io/yxp_wiki/zh/recordings_huaqinrui/?season=10&recording=r-23127fac20f0cf14&step=308) | 2 | 1 | 1 | 是 | [-32, 0] / [-32, 0] | 严格速度关系 |

手牌取自该战斗事件之前的本人私有状态，核对本人身份、轮次、当前牌阵、手牌原顺序及整份私有状态哈希。另做9种改动或错配拒绝检查；这16项来源检查不代替完整战斗对照。对手私有手牌仍未知，不借用本人手牌。

本批实际触发的阵旗等级为[1, 2]；奇数格执行11次、偶数格执行0次，灵阵等级受上限限制2次、没有灵阵目标1次。每次实际所选灵阵都与原手牌第一张合格牌对照；不能按最高等级或战后手牌选择。

这些手牌来源已接入现有三级阵旗效果，没有改写卡牌效果或战斗运行入口。三级阵旗及偶数格灵印分支的真人覆盖以本表为准，未出现的分支不能据此宣称已验证。模拟中发出的事件用于检查实际走到的分支，不是网站提供的独立行动日志。

7条阵旗记录中，2条使用记录同速先手，5条没有已识别的准备/开战公开状态差异。全部属于两份开发回放的不同轮次，不是7个独立整局。

**网站仍没有终局HP差和行动次数可供逐项对比。报告中的血差、行动次数只是模拟输出；命元由模拟终局计算后与记录比较，未倒灌开战状态。终局一致也不能唯一证明全部内部机制。**

累计17份网站回放、295个边界：完整执行195场，胜者195场一致、命元损失184场一致；输入未决100场，运行中未决0场。原165场网站输入及完整输出重新核对，全部保持不变。原954场完整对照继承上一轮实跑结果，本轮未重复执行；原始回放编译器及运行入口哈希不变。

这轮为来源适配与开发诊断，保留全部不匹配和未决记录。准备开关、五行玉瓶、换牌经营过程没有因为本轮阵旗对照而扩大验证结论。详细的新旧缺口、非随机及随机差异见 next-gap-queue.json。

新35条中还有5条未决：两条缺对手玉瓶内容、两条缺对手7031准备开关，另一条原始开战及之前公开修为均明确为-1，被当前非负修为校验拒绝。这一条不是字段缺失，下一步应核对有符号修为及准备消耗读取后版本化接入，不能补成0。另有两场命元不同：一场随机对照为模拟9、记录10；一场非随机对照为模拟14、记录12。两场胜者均一致，输入时点差异已保留，尚未证明是差异原因。

最初来源检查入口因历史版本导入链触及Python默认递归深度而失败；原脚本和错误日志保留，新入口使用既有完整战斗脚本相同的导入深度后完成检查，没有改变生产规则迁就检查。

服务器健康，无训练进程；64份检查点、5份指标、2份选定权重及180份历史失败文件不变。本轮没有GPU训练、保留测试读取或战斗奖励标签。S2继续保持未验收。

详细证据：本轮 full-battle-report.json、owner-flag-full-battle-audit.json、compiled-regression.json、website-regression.json、historical-battle-regression.json。
