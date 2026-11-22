# 云端训练环境

2026-11-11 已完成 GPU 环境配置和首轮龙瑶牌阵重构预训练。完整龙瑶对局训练尚未启动。

分阶段验收与每30分钟巡检、迭代安排见 [TRAINING_STAGES.md](TRAINING_STAGES.md)。
本对话定时任务已启用，实际配置读 `configs/continuous_training.json`。

## 连接与目录

在本机终端运行：

```powershell
ssh yixian-gpu
```

已为本机配置独立的 Ed25519 密钥登录，私钥在项目目录之外，未保存登录密码。
服务器地址、版本和验证状态见 `configs/cloud_training.json`。

登录后：

```bash
cd /home/ubuntu/yixian-agent
export PATH="$HOME/.local/bin:$PATH"
source .venv/bin/activate
```

项目目录为 `/home/ubuntu/yixian-agent`；安装日志在 `/home/ubuntu/setup-logs`。

## 已安装版本

| 组件 | 版本 |
| --- | --- |
| 系统 | Ubuntu 24.04.4 LTS |
| GPU | NVIDIA Tesla T4 |
| NVIDIA 计算驱动 | 580.178.04，Ubuntu 官方软件源的 580 server open 分支 |
| Python | 3.14.10，项目独立环境，未替换系统 Python |
| PyTorch | 2.11.0+cu130 |
| PyTorch CUDA 运行时 | 13.0 |
| Node.js | 22.23.4，官方发布包及 SHA-256 校验 |
| 后台会话工具 | tmux |

Python 包的实际锁定清单在服务器 `runs/setup/packages.lock.txt`。
Python 依赖通过腾讯云 HTTPS 镜像安装；外部 yisim 按项目固定提交在服务器独立下载和构建。

## 已验证的范围

- 服务器重启后驱动正常，PyTorch 可以使用 T4。
- 18,134,272 参数的合成 Transformer，执行了 8 次 FP16 前向、反向和 AdamW 更新；梯度有效、参数改变、模型和优化器存档恢复检查通过。
- 项目完整软件测试：255 项通过，0 失败、0 错误、0 跳过。
- 云端补齐了测试所需的五份规则配置和一份赛季证据记录；六个文件均按本机 SHA-256 校验。
- 早期缺少规则文件的测试记录保留，最终结果读取 `project-tests-complete.json`。

本机证据目录：`runs/deployment/20261111T112103Z`。
服务器证据目录：`/home/ubuntu/yixian-agent/runs/setup`。

重新验证 GPU（每次使用新的报告名称）：

```bash
python tools/verify_gpu.py --out "runs/setup/gpu-check-$(date -u +%Y%m%dT%H%M%SZ).json"
python -m unittest discover -s tests -v
```

项目源码和所需配置已部署；游戏客户端、完整资源提取目录、原始回放数据集没有整体上传。
完整回放流程仍需准备其来源数据，不能把未部署的数据补成虚构样本。

## 训练状态

首轮辅助预训练 `20261111T124838Z-longyao-v1` 已完成，267项软件测试通过、无跳过。
5,585,153参数的 Transformer 指针模型在 T4 上执行2000次真实优化更新，无FP16跳过，
训练与评测阶段用时约57秒（不含下载、准备数据与软件检查）。验证集连续6次检查未改善后早停，
选择第800步权重。短牌阵、短序列和小数据集使这一阶段很快，不能外推完整对局训练用时。

数据来自固定提交 `b592caa9bc6c3b9fb11bb8b3e7691b9840dd36ce` 的8个HF回放档案，
过滤角色龙瑶、`isAI=false`、内部赛季10、规则版本`001.0008.0005`。
去除同局相同牌阵及以前检查过的8局；同一整局所有视角始终归同一划分。

| 划分 | 整局数 | 去重牌阵数 |
| --- | ---: | ---: |
| 训练 | 349 | 5191 |
| 验证 | 45 | 676 |
| 保留测试 | 45 | 659 |

输入仅为打散后的已记录牌组、构造到当前步的前缀及剩余牌掩码；重复牌目标合并计算概率。
模型学习复现人类记录牌序；没有用回放推造换牌、炼化、升本或仙命操作。
观测不包括隐藏手牌、战斗结果或未来轮次。相同牌阵在同一局的重复视角与重复轮次保守去重，
不声称识别跨回放玩家身份，也不声称这些记录都是最优牌序。

保留测试集的3893个非必然下一张选择中，模型复现准确率63.94%，随机基线26.80%，
仅用训练集建立的位置频率基线44.31%。这些选择来自45局，不能当作3893场独立游戏。
这是给定正确前缀的牌序重构指标，不是自行生成完整牌阵的正确率或对战胜率。
测试集只在按验证集选定权重后运行；后续若据此调参，应另留新测试局。

本机 `runs/pretraining/latest.json` 指向备份报告与所选权重，服务器同名指针指向远端任务。
原始运行报告的 `validation` 为最后一步，所选模型验证结果见本机 `result-summary.json` 的
`selected_validation`；`best.json` 与每200步的历史记录在 `metrics.jsonl`。
服务器保留全部检查点，本机备份第800步检查点并核对SHA-256；快照包含模型、优化器、
随机状态、词表及契约。当前命令还没有自动续训入口，不要把新运行说成续训。

在本机查看已有结果：

```powershell
ssh yixian-gpu 'cat /home/ubuntu/yixian-agent/runs/pretraining/20261111T124838Z-longyao-v1/status.json'
```

在服务器启动一次新的、最多3000步/30分钟的同配置复现实验（已完成的任务不会自动重启）：

```bash
bash tools/start_longyao_pretrain.sh
```

启动器使用tmux后台运行，拒绝同时启动第二个同名任务；SSH断开不影响训练。
配置在 `configs/longyao_pretrain.json`。任何改动都应登记新实验，不能覆盖旧结果。
原始回放档案保留本机，仅上传去除私人状态后的训练牌阵及来源哈希。

读取所选模型、按自身前序选择排完整组牌的入口为 `tools/predict_board_order.py`。
它会检查源码与模型契约、词表、合法掩码和牌组张数守恒，遇到不兼容版本拒绝加载。
下面是训练来源牌阵的一次功能检查，没有评估战斗强弱：

```bash
python tools/predict_board_order.py \
  --checkpoint runs/pretraining/20261111T124838Z-longyao-v1/checkpoint-000800.pt \
  --cards 1010004 1010007 1000008 1000024 1010010 1000029 15 1010031
```

GPU 合成验证网络仅用于检查环境。原有 PPO 仍使用 NumPy/CPU；
完整对局训练还需补齐规则、合法动作、当前版本战斗校准和GPU强化学习流程。

`tools/bootstrap_cloud.sh` 可重建 Python、Node、PyTorch 和固定参考引擎环境。
运行它前需准备 GPU 驱动、`python3-venv`、编译工具和项目源码；规则快照单独部署并校验。
