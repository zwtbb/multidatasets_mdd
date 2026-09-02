# 工作汇报 PPT 内容与逐字稿

论文题目：Validate the Target Before Aligning Representations: A Measurement-Aware Framework for Cross-Corpus Depression Detection

建议页数：10 页。整体讲法不要像实验流水账，而是讲一个清楚问题：跨语料抑郁检测不能只问“表示是否对齐”，还必须问“临床标签是否真的可比”。

## 第 1 页：标题页

页面放：

- 题目：先验证临床目标，再对齐表示
- 副标题：一个面向跨语料抑郁检测的 measurement-aware framework
- 一句话贡献：我们把 cross-corpus depression detection 从“特征泛化问题”推进到“benchmark validity + measurement-aware prediction”问题。
- 可放图：Figure 1 框架总图，或你手绘的总图。

逐字稿：

今天汇报的是我们当前论文的完整版本。核心观点很简单：跨语料抑郁检测不能只看模型能不能学到更强的表示，还要看不同语料里的 PHQ、HAMD 等临床标签是否可以被当成同一个目标来预测。过去很多工作默认目标是可交换的，主要解决 language、audio、protocol、domain shift。但我们发现，在 mental health benchmark 里，标签本身也是测量过程的一部分。所以这篇论文的主题就是：before aligning representations, validate the target。

## 第 2 页：研究动机

页面放：

- 现有路线：strong encoder / multimodal fusion / domain adaptation。
- 隐含假设：不同 corpus 的 depression label 可以直接比较。
- 我们的问题：当一个模型从 E-DAIC 迁移到 CMDC，或者从 CMDC 迁移到 PDCH，它到底在迁移什么？
- 关键区分：
  - acquisition / representation mechanism：`P_D(X | theta)`
  - measurement mechanism：`P_D(Y | theta)`

逐字稿：

这个领域现在的主流思路是 representation transfer。也就是说，不同数据集有不同语言、录音条件、访谈协议、病人群体，所以我们用更强的 encoder、更强的多模态融合，或者 domain adaptation 来解决。但这里有一个没有被充分检查的假设：这些 corpus 里的 depression score 本身是可比的。PHQ-8、PHQ-9、HAMD-17 都和抑郁有关，但它们不是普通分类标签，而是由量表条目、评分规则、语言和访谈情境共同产生的 clinical measurement。因此我们把问题拆成两层：一层是 depression 如何表现为行为数据 X，另一层是 symptom evidence 如何被转换成观测标签 Y。

## 第 3 页：论文定位与核心问题

页面放：

- 论文定位：AI for mental health benchmark validity audit + lightweight measurement-aware framework。
- 三个 RQ：
  - RQ1：representation heterogeneity
  - RQ2：measurement heterogeneity
  - RQ3：consequence for model generalization
- 主张边界：不是说所有数据集测的是完全不同 construct，而是说 clinical target 不能未经验证就交换使用。

逐字稿：

所以这篇论文不是单纯追求 depression detection 的 SOTA，也不是纯心理测量学论文。我们的定位是一个 AI for mental health benchmark validity audit，同时提出一个轻量的 measurement-aware prediction framework。三个问题依次展开：第一，不同 corpus 的表示层是否仍然带有强烈的语料身份；第二，名义上对齐的临床测量是否真的有相同的 response mechanism；第三，当我们把 measurement layer 显式建模以后，跨语料预测会发生什么变化。这里我们避免过度夸大：我们不是说所有 depression datasets 都测量不同 construct，而是说在跨语料学习里，target comparability 必须成为被验证的对象。

## 第 4 页：数据与实验设计

页面放：

- 可放图：Figure 2 dataset relationship map。
- 主数据视角：
  - E-DAIC：PHQ-8，英文虚拟访谈，主开发 corpus。
  - DAIC-WOZ：同 DAIC lineage 的 PHQ-8 sanity control，不作为独立 corpus 证明。
  - CMDC：中文 PHQ-9，主跨语言 PHQ shared-item 对照。
  - PDCH：HAMD-17，same-HAMD exploratory control。
  - MODMA / EATD / MPDD-AVG：task、emotion、population stress views。
- 强调：不是简单堆七个数据集，而是按 analytical role 组织证据。

逐字稿：

数据设计上，我们不是把所有数据集混在一起做大训练集，而是给每个 corpus 一个明确角色。E-DAIC 和 CMDC 是主线，因为它们有 PHQ family 的 shared symptoms；DAIC-WOZ 和 E-DAIC 是同 lineage、同 PHQ-8 的 sanity control，用来告诉我们在最接近的情况下 measurement difference 应该很小；CMDC 和 PDCH 都有 HAMD 信息，但 CMDC 样本小，所以只作为 exploratory same-scale control；MODMA、EATD 和 MPDD-AVG 不承担正式 invariance 结论，而是用来支持 acquisition、task、emotion 和 population heterogeneity 的背景。这样设计的好处是，论文不是“数据集越多越好”，而是每个数据集都服务于一个 validity question。

## 第 5 页：方法框架

页面放：

- 可放图：Figure 1 或手绘 architecture。
- Direct transfer：
  - `X -> Y_D`
- Measurement-aware path：
  - `X_D -> H_D -> S -> Y_D`
  - `Foundation encoder -> shared representation -> latent symptom layer -> corpus-specific ordinal head`
- 正式模型：
  - frozen Qwen3 text + WavLM speech + OpenFace video
  - shared eight-symptom layer
  - corpus-specific cumulative-logit ordinal heads
- Loss 放一行即可：
  - source ordinal reconstruction + target calibration ordinal reconstruction + mild MMD regularizer

逐字稿：

方法上，我们把传统的 direct transfer 改成 measurement-aware transfer。传统模型直接从输入 X 预测某个 corpus 的标签 Y。我们的框架在中间加了一个 shared symptom layer，先学习可以共享的 symptom evidence，再通过 corpus-specific ordinal head 映射到具体 corpus 的 PHQ item response。正式实验里，我们没有同时讲很多可选 head，而是固定为一个清楚架构：Qwen3、WavLM、OpenFace 的 frozen foundation representation，接一个八维 PHQ shared symptom layer，再接每个 corpus 自己的 cumulative-logit ordinal item head。MMD 只是 mild regularizer，不是方法核心；核心是 shared symptom evidence 和 corpus-specific measurement pathway。

## 第 6 页：结果一，表示差异不是消失了

页面放：

- 可放图：Figure 3 raw-to-controlled corpus identity probes。
- 讲三点：
  - raw identity 很高，说明 corpus signatures 对模型可见。
  - E-DAIC/CMDC 在 length + severity control 后接近 chance，说明 raw 1.000 不能简单解释成 clinical signal。
  - DAIC-lineage same-language control 仍然高，说明 identity 不只是中英文差异。
- 少量数字：
  - E-DAIC/CMDC controlled：Qwen3 0.497, WavLM 0.484, OpenFace 0.522。
  - DAIC-lineage controlled：Qwen3 0.839, WavLM 0.897。

逐字稿：

第一个结果回答 representation heterogeneity。我们一开始看到 raw corpus identity 非常高，但这类结果如果直接写成“模型识别了中文和英文”，会很容易被攻击。所以我们做了 controlled probe。对 E-DAIC 和 CMDC，控制长度和严重程度以后，Qwen3、WavLM、OpenFace 都降到接近 chance。这说明 raw identity 很大一部分来自语言、长度、协议结构，而不是纯 depression evidence。更有价值的是 DAIC-lineage 内部的 same-language control：即使同为英文、同为 DAIC lineage，控制后 Qwen3 和 WavLM 仍然能识别 lineage。这说明 corpus identity 不只是语言差异，也包含 acquisition lineage 和 protocol construction。这个结果支持我们的第一层 claim：表示对齐需要审计，但它不能自动证明临床目标可迁移。

## 第 7 页：结果二，测量差异呈现清楚梯度

页面放：

- 可放图：Figure 4 + Figure 5 二选一；建议主放 Figure 5，右下角嵌 Figure 4 的 C02/C06 局部。
- 三层 evidence：
  - DAIC-WOZ / E-DAIC：same-lineage PHQ-8 sanity control，几乎一致。
  - E-DAIC / CMDC：PHQ shared items 有共同结构，但 threshold/response behavior 不完全一致。
  - CMDC / PDCH：same-HAMD exploratory control 显示 scale 相同也可能有 context differences。
- 关键数字只放 3 个：
  - DAIC/E-DAIC all-item exact match 0.993。
  - PHQ loading congruence 0.998，anchors C01/C04/C05/C07，shift C02/C06。
  - HAMD 最大 severity-conditioned delta：HAMD07 为 -0.967。

逐字稿：

第二个结果是论文最核心的 measurement gate。这里我们看到一个很漂亮但不夸张的经验梯度。DAIC-WOZ 和 E-DAIC 是同 lineage、同 PHQ-8，重叠 subjects 的 item response 几乎完全一致，这说明我们的 audit 不会凭空制造 measurement shift。到了 E-DAIC 和 CMDC，八个 PHQ shared items 有很强的共同结构，loading congruence 达到 0.998，说明它们确实共享 depression symptom content；但 threshold 和 response behavior 并不完全可交换，C02 anhedonia 和 C06 self-worth 反复出现为 localized shift items。再往外，CMDC 和 PDCH 虽然都涉及 HAMD，但在 severity-conditioned item behavior 和 correlation structure 上也出现差异。这个结果的表达要稳：不是说差异严格单调增长，也不是说所有数据集测的 construct 完全不同；而是说 observed clinical labels 在跨 corpus 使用前需要 measurement contract。

## 第 8 页：结果三，强 backbone 仍然不能替代 target validation

页面放：

- 可放图：Figure 6 latent-target tradeoff。
- 讲法：
  - latent target 可以降低 output-level corpus identity。
  - upstream feature identity 仍然高。
  - Qwen3 / multimodal foundation stress tests 改善部分预测，但 target-mapping question 仍然存在。
- 可放一句：问题不是“小 encoder 太弱”，而是 representation mechanism 和 measurement mechanism 是两个问题。

逐字稿：

第三个结果回答 foundation model 时代的质疑：是不是换成更强的 encoder 就好了？我们的结论是，不是这么简单。latent target 的确能改变模型输出，比如 output-level corpus identity 可以降到接近 chance；但上游 feature identity 仍然高，说明 representation 层的 corpus signatures 还在。进一步换成 Qwen3，或者加入 WavLM、OpenFace 的多模态 stress view，性能边界会移动，但 target mapping 的问题并没有消失。换句话说，强 backbone 是必要的，但它不能替代对 clinical target 的验证。这个负结果反而是论文贡献：它说明 cross-corpus failure 不是简单的 encoder capacity 问题。

## 第 9 页：正式模型主结果

页面放：

- 可放简化版 Table 3，不要放全表。建议只放每个方向三行：
  - strongest zero-target-label baseline
  - corpus-specific head
  - measurement-aware
- 指标只放 `Recon + Calibration Score` 和一句解释：越低越好，等于 item reconstruction + calibration error。
- 关键结果：
  - CMDC -> E-DAIC：Measurement-aware 1.251 vs corpus-specific head 1.565；+MMD 辅助变体为 1.243。
  - E-DAIC -> CMDC：Measurement-aware 0.987 vs corpus-specific head 2.405；+MMD 辅助变体同为 0.987。
  - Measurement-aware 与 +MMD 非常接近，说明主要增益来自 ordinal measurement pathway，而不是 MMD。
- 加一句公平性说明：zero-target-label baselines 与 target-calibrated rows 不做 same-budget 显著性比较。

逐字稿：

最后是正式 measurement-aware ordinal model 的主结果。这里一定要注意公平性叙事：ERM、CORAL、MMD、DANN 和 strongest foundation baseline 都是不使用目标域临床标签的 zero-target-label rows；而 corpus-specific head、measurement-aware 和 measurement-aware + MMD 使用相同的 target calibration split。所以我们不写成 measurement-aware 显著优于所有 baseline，而是写成两个层次。第一，zero-target-label baselines 说明普通 feature alignment 只能作为 representation adaptation context。第二，在同样使用 target calibration labels 的 same-budget comparison 里，核心 measurement-aware 明显优于 corpus-specific head：CMDC 到 E-DAIC 从 1.565 降到 1.251，E-DAIC 到 CMDC 从 2.405 降到 0.987。Measurement-aware + MMD 与核心模型非常接近，一个方向只小幅变好，另一个方向持平；所以真正起作用的是 target-calibrated ordinal measurement pathway，而不是把 MMD 当作方法主角。

## 第 10 页：结论与下一步

页面放：

- Take-home message：
  - Cross-corpus depression detection is not only representation transfer.
  - Clinical targets are measurement contracts.
  - Strong encoders should be paired with corpus-specific measurement heads and calibration-aware evaluation.
- 当前论文贡献：
  - benchmark validity audit
  - measurement heterogeneity evidence
  - fixed measurement-aware ordinal framework
- 下一步：
  - 精修写作与图表
  - 引文最终核验
  - supplementary 整理：raw identity heatmap、MMD sensitivity、更多 stress baselines

逐字稿：

总结一下，这篇论文的最终信息不是“我们做了一个新的抑郁检测 SOTA”，而是更适合当前证据的主张：跨语料抑郁检测不仅是 representation transfer，也包含 target measurement validity。PHQ、HAMD 这些标签不能只因为名字相近就被当成同一个预测目标。我们的贡献是给出系统的 empirical evidence：表示层有 corpus signatures，测量层有 corpus-conditioned response behavior，而预测层显示普通 alignment 和强 backbone 都不能单独解决这个问题。对应的解决方案是 measurement-aware framework：强 encoder 负责表征，shared symptom layer 负责可共享症状证据，corpus-specific ordinal heads 负责量表和语料特定的测量映射。后续工作我建议不再扩实验，而是集中做论文精修、图表压缩、引文核验和 supplement 整理。

## 备用页 A：公式页

页面放：

- 左边：传统假设
  - `f: X_D -> Y_D`
  - 隐含 `P_D1(Y | theta) ≈ P_D2(Y | theta)`
- 右边：我们的拆解
  - `P_D(X,Y | theta)=P_D(X | theta)P_D(Y | theta)`
  - `X_D -> H_D -> S -> Y_D`
- 一句话：representation alignment handles `X`; measurement-aware heads handle `Y`。

逐字稿：

如果需要单独讲公式，可以用这一页。传统跨域学习更多处理的是输入分布，也就是 `P(X|theta)` 怎么变化。但在 depression benchmark 里，标签不是普通 label，`P(Y|theta)` 本身也可能随 corpus 变化。我们的拆解就是把这两层分开：encoder 处理 observable behavior，shared symptom layer 提供中间症状证据，corpus-specific head 处理每个 corpus 的测量规则和 response behavior。

## 备用页 B：临床指标页

页面放：

- 不作为主结果，只作为 secondary clinical endpoint。
- PHQ total >= 10 threshold。
- 指标：Macro-F1、Balanced Accuracy、AUROC、AUPRC、Sensitivity、Specificity。
- 讲法：帮助和 depression detection 文献对话，但不取代 reconstruction/calibration。

逐字稿：

我们也补了二分类 clinical endpoint，是为了让 reviewer 能把结果和传统 MDD detection 文献对上。但这一页不要喧宾夺主。我们的主指标还是 item reconstruction 和 calibration，因为论文创新不是普通二分类，而是 measurement-aware target modeling。二分类结果可以说明方法有临床可读性，同时也暴露 direction asymmetry，比如某个方向 specificity 高但 sensitivity 保守，这反而支持我们不要只看单一 accuracy。
