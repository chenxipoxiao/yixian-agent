# 极·六爻绝阵与雷牌批次 v67r2

本批以v67r2扩展极·六爻绝阵、风雷涌动、雷震金莲三族九档牌，保留旧源码、契约、候选及失败结果。极·六爻绝阵叠加1/2/3层持续效果并请求追击；实际增加卦象时沿用204非攻击伤害回调，保留占星、梦阵和扇子回调的既有相对顺序。风雷涌动先加1灵气，再独立取1至11/16/21的数值；按当前牌阵首尾循环的物理相邻格判断雷牌，已使用持续牌仍算相邻，最后另判10%追击。雷震金莲先取1至11/13/15攻击，再独立判1%追加5/7/9攻击，最后加2辟邪；数值与概率请求分别消耗卦象。九档身份接入刻纹，并补齐升阶之音原表的空运行ID；升阶条件、开关、时点及隐藏牌排除规则不变。本机和服务器各34项软件检查通过，含36个边界场景；最终先核对9条关联记录和4条固定对照，再各完成一次525条完整开发回归。可执行450→458，四项全一致425→429，阻断75→67；原450场完整输入、输出和结算全部相同，原425条正确结果保留。新增8场，其中4场四项全一致。新增7场独立先手、1场记录先手条件核对。非随机404/407。新增两场确定性差异均相差36点生命差，原因未定；原局参数与卦象保证结果一致，不能归为随机波动。已记录五雷轰顶先完成五次判定再多段攻击的客户端时序差异，但尚未证明它解释这两场偏差，列入下一批。随机结果由固定参考采样器产生，未还原原局随机序列，也未验证服务器概率分布；含随机差异保留，不搜索种子。首候选测试把请求追击当成完成追击，修正测试字段；第二候选局部回放发现升阶之音未绑定新牌身份，版本化补齐依赖后重新测关联集合。两次候选均未运行全量回归。服务器健康，检查点、指标、历史失败和选定权重未改；无GPU任务、原始数据下载、保留集使用或训练标签。结果仍是原64个训练来源整局的单场开发对照；模拟轨迹不是观测行动日志，未出现档位或分支仅获软件覆盖。S2不晋级，不代表独立验收、完整对局强度或实战强度。

- 第11轮：生命差-44，行动11次，败方命元损失19；含随机过程True。记录 `replay-90d264ca9035908a5dee5becd5b9484f6a5b71c4710d045e21c4f2bde13bf579-round-10`；四项对照 `{'winner': True, 'hp_delta': False, 'turns': False, 'destiny_damage': False}`。
- 第15轮：生命差17，行动13次，败方命元损失20；含随机过程False。记录 `replay-90d264ca9035908a5dee5becd5b9484f6a5b71c4710d045e21c4f2bde13bf579-round-14`；四项对照 `{'winner': True, 'hp_delta': True, 'turns': True, 'destiny_damage': True}`。
- 第16轮：生命差-65，行动11次，败方命元损失26；含随机过程False。记录 `replay-31b1405689e334c59cc309fc4808343ab3361710fee1c5bb8f92962d805b66c4-round-15`；四项对照 `{'winner': True, 'hp_delta': False, 'turns': True, 'destiny_damage': False}`。
- 第19轮：生命差82，行动11次，败方命元损失31；含随机过程False。记录 `replay-31b1405689e334c59cc309fc4808343ab3361710fee1c5bb8f92962d805b66c4-round-18`；四项对照 `{'winner': True, 'hp_delta': False, 'turns': True, 'destiny_damage': False}`。
- 第6轮：生命差-17，行动18次，败方命元损失10；含随机过程True。记录 `replay-855c504feae2d4212698d26f1125500fe2c4c1d806a885e14eee4f6623fbe088-round-5`；四项对照 `{'winner': True, 'hp_delta': False, 'turns': True, 'destiny_damage': False}`。
- 第4轮：生命差-16，行动22次，败方命元损失8；含随机过程True。记录 `replay-4a11bf99d745bf53cd4ba5a7c7d608c725c71e653b33f88f5951e0d03b85c0d5-round-3`；四项对照 `{'winner': True, 'hp_delta': True, 'turns': True, 'destiny_damage': True}`。
- 第13轮：生命差-33，行动25次，败方命元损失20；含随机过程False。记录 `replay-54ee4d11c5f64aeed38ef59c7e52953807a5a485600db2bd2e111681fc432bc7-round-12`；四项对照 `{'winner': True, 'hp_delta': True, 'turns': True, 'destiny_damage': True}`。
- 第16轮：生命差40，行动15次，败方命元损失23；含随机过程False。记录 `replay-54ee4d11c5f64aeed38ef59c7e52953807a5a485600db2bd2e111681fc432bc7-round-15`；四项对照 `{'winner': True, 'hp_delta': True, 'turns': True, 'destiny_damage': True}`。

首次候选与依赖修正前的局部结果原样保留。其他未知牌/仙命、350和7121战后资源账本、3013主动使用转换继续待处理。

报告：`runs/stages/20261114T045000Z-s2-hexagram-thunder-batch/candidate-r3/full-battle-report.json`；缺口：`runs/stages/20261114T045000Z-s2-hexagram-thunder-batch/next-gap-queue.json`。
