import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
import os
from matplotlib.patches import Patch

# 睡眠阶段映射（英文）
stage_map = {
    0: "Wake",
    1: "N1",
    2: "N2",
    3: "N3",
    4: "REM"
}

# 更新为低饱和度颜色映射 - 柔和色调
stage_colors = {
    0: (0.4, 0.6, 0.8),  # 浅蓝色 - Wake
    1: (0.6, 0.8, 0.9),  # 淡青色 - N1
    2: (0.6, 0.8, 0.6),  # 淡绿色 - N2
    3: (0.8, 0.5, 0.5),  # 柔红色 - N3
    4: (0.8, 0.7, 1.0)  # 淡紫色 - REM
}

# 设置文件夹路径和目标文件路径
folder_path = 'E:/DREAMT base/sleep-edf/sleep-edf-database-expanded-1.0.0/sleep-cassette/eeg_fpz_cz'
target_file = 'SC4281G0.npz'  # 要分析的单个患者文件

# ========================================================================
# 第一部分：处理所有文件，计算整体睡眠阶段分布（用于左侧柱状图）
# ========================================================================

# 初始化全局计数器
total_stage_counter = Counter()
file_count = 0

# 遍历文件夹中的所有文件
for filename in os.listdir(folder_path):
    if filename.endswith('.npz'):
        file_path = os.path.join(folder_path, filename)
        try:
            # 加载数据
            data = np.load(file_path)
            y = data['y']  # 真实标签

            # 更新全局计数器
            total_stage_counter.update(y)
            file_count += 1

        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")

# 计算总统计信息
total_epochs = sum(total_stage_counter.values())

# 准备柱状图数据
stage_names = [stage_map[i] for i in range(5)]
counts = [total_stage_counter.get(i, 0) for i in range(5)]
colors = [stage_colors[i] for i in range(5)]

# ========================================================================
# 第二部分：处理目标患者文件（用于中间饼图和右侧睡眠变化图）
# ========================================================================

target_file_path = os.path.join(folder_path, target_file)
try:
    # 加载目标患者数据
    data = np.load(target_file_path)
    y_target = data['y']  # 目标患者真实标签

    # 计算目标患者的阶段分布
    stage_counts_target = Counter(y_target)
    total_epochs_target = len(y_target)

    print(f"\nTarget Patient File: {target_file}")
    print("Sleep Stage Distribution:")
    for stage_idx, count in sorted(stage_counts_target.items()):
        stage_name = stage_map.get(stage_idx, f"Unknown({stage_idx})")
        percentage = count / total_epochs_target * 100
        print(f"{stage_name:>5}: {count:>5} epochs ({percentage:.1f}%)")

    # 准备饼图数据
    labels_target = [stage_map.get(i, f"Unknown{i}") for i in sorted(stage_counts_target.keys())]
    sizes_target = [stage_counts_target[i] for i in sorted(stage_counts_target.keys())]
    # 确保饼图使用正确的颜色
    pie_colors = [stage_colors[i] for i in sorted(stage_counts_target.keys())]

except Exception as e:
    print(f"Error processing target file {target_file}: {str(e)}")
    exit()

# ========================================================================
# 第三部分：创建三图合一的综合图表（使用低饱和度颜色）
# ========================================================================

# 创建大图（宽15英寸，高5英寸）
fig = plt.figure(figsize=(15, 5))

# 左侧：整体睡眠阶段分布柱状图 - 子图 (a)
ax1 = plt.subplot(1, 3, 1)  # 1行3列，第1个位置
bars = ax1.bar(stage_names, counts, color=colors, edgecolor='grey', linewidth=0.7)

# 添加数量标签
for bar in bars:
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width() / 2.,
             height + 0.02 * max(counts),
             f'{height:,}',
             ha='center',
             va='bottom',
             fontsize=9,
             color='black')  # 使用深灰色文本提高可读性

# 添加百分比标签
for i, bar in enumerate(bars):
    height = bar.get_height()
    percentage = 100 * height / total_epochs
    ax1.text(bar.get_x() + bar.get_width() / 2.,
             height / 2,
             f'{percentage:.1f}%',
             ha='center',
             va='center',
             color='black',  # 黑色文本确保清晰
             fontweight='bold',
             fontsize=10)

# 美化柱状图
ax1.set_title(f'Overall Sleep Stage Distribution\n({file_count} Files, {total_epochs:,} Epochs)',
          fontsize=12, fontweight='bold', color='black')
ax1.set_xlabel('Sleep Stage', fontsize=10, color='black')
ax1.set_ylabel('Number of Epochs', fontsize=10, color='black')
ax1.grid(axis='y', alpha=0.3, linestyle='--', color='lightgrey')
ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
ax1.tick_params(colors='black')  # 刻度标签也使用深灰色

# # 添加 (a) 索引标签
# ax1.text(0.5, -0.15, '(a)', transform=ax1.transAxes,
#          fontsize=14, fontweight='bold', va='top', ha='right')

# 中间：目标患者睡眠阶段分布饼图
ax2 = plt.subplot(1, 3, 2)  # 1行3列，第2个位置
wedges, texts, autotexts = ax2.pie(sizes_target, labels=labels_target,
                                   autopct='%1.1f%%', startangle=2000, radius=1.1,
                                   colors=pie_colors, wedgeprops={'edgecolor': 'lightgrey', 'linewidth': 0.7})

# 设置文本颜色为深灰色
for text in texts:
    text.set_color('black')
    text.set_fontsize(10)
for autotext in autotexts:
    autotext.set_color('black')  # 百分比文本保持黑色
    autotext.set_fontsize(9)

ax2.set_title(f'Subjects: SC4281G0\n(Total Epochs: {total_epochs_target})',
          fontsize=12, fontweight='bold', color='black')

# 右侧：目标患者睡眠阶段随时间变化图 - 子图 (b)
ax3 = plt.subplot(1, 3, 3)  # 1行3列，第3个位置
x_axis = np.arange(len(y_target))
point_colors = [stage_colors.get(stage, (0.8, 0.8, 0.8)) for stage in y_target]  # 灰色表示未知阶段
ax3.scatter(x_axis / 120, y_target, c=point_colors, s=5, alpha=0.8)  # 增大点大小，添加透明度

# 设置坐标轴
ax3.set_yticks(list(stage_map.keys()), list(stage_map.values()))
ax3.set_xlabel('Time (Hours)', fontsize=10, color='black')
ax3.set_ylabel('Sleep Stage', fontsize=10, color='black')
ax3.set_title('Sleep Stage Progression Over Time', fontsize=12, fontweight='bold', color='black')
ax3.grid(alpha=0.3, linestyle='--', color='lightgrey')
ax3.set_facecolor((0.98, 0.98, 0.98))  # 设置背景为非常浅的灰色提高可读性
ax3.tick_params(colors='black')  # 刻度标签也使用深灰色

# # 添加 (b) 索引标签
# ax3.text(-0.1, -0.15, '(b)', transform=ax3.transAxes,
#          fontsize=14, fontweight='bold', va='top', ha='right')

# 添加图例（使用低饱和度颜色）- 放在右侧睡眠变化图上
legend_elements = [
    Patch(facecolor=stage_colors[0], edgecolor='lightgrey', label=stage_map[0]),
    Patch(facecolor=stage_colors[1], edgecolor='lightgrey', label=stage_map[1]),
    Patch(facecolor=stage_colors[2], edgecolor='lightgrey', label=stage_map[2]),
    Patch(facecolor=stage_colors[3], edgecolor='lightgrey', label=stage_map[3]),
    Patch(facecolor=stage_colors[4], edgecolor='lightgrey', label=stage_map[4])
]
ax3.legend(handles=legend_elements, loc='upper right', fontsize=9)

# 调整布局并保存
plt.tight_layout(pad=2.0)  # 添加一些内边距
plt.savefig('combined_sleep_analysis_low_sat.png', dpi=300)
print("\nGenerated combined sleep analysis plot with low saturation colors: combined_sleep_analysis_low_sat.png")

# # ========================================================================
# # 第四部分：生成平滑的睡眠阶段趋势图（使用低饱和度颜色，单独保存）
# # ========================================================================
#
# plt.figure(figsize=(12, 4))
# plt.gca().set_facecolor((0.98, 0.98, 0.98))  # 设置背景为非常浅的灰色
#
# # 创建整夜趋势图（每个点代表5分钟）
# minute_intervals = 5  # 每5分钟一个点
# points_per_interval = minute_intervals * 2  # 每分钟2个epoch
# smoothed_stages = [np.median(y_target[i:i + points_per_interval]) for i in range(0, len(y_target), points_per_interval)]
#
# # 创建时间轴
# hours_axis = np.arange(len(smoothed_stages)) * minute_intervals / 60
#
# # 绘制平滑的睡眠阶段曲线
# plt.plot(hours_axis, smoothed_stages, linewidth=2, color='dimgrey')
# # 填充曲线下的区域
# for stage in sorted(stage_colors.keys()):
#     # 找出该阶段的区域
#     mask = np.array(smoothed_stages) == stage
#     plt.fill_between(hours_axis, smoothed_stages, where=mask, color=stage_colors[stage], alpha=0.3)
#
# # 设置坐标轴和网格
# plt.yticks(list(stage_map.keys()), list(stage_map.values()))
# plt.xlabel('Time (Hours)', fontsize=10, color='dimgrey')
# plt.ylabel('Sleep Stage', fontsize=10, color='dimgrey')
# plt.title('Smoothed Sleep Stage Progression', fontsize=12, color='dimgrey')
# plt.grid(alpha=0.2, linestyle='--', color='lightgrey')
# plt.gca().tick_params(colors='dimgrey')  # 刻度标签也使用深灰色
#
# # 添加图例（使用低饱和度颜色）
# legend_elements = [
#     Patch(facecolor=stage_colors[0], label=stage_map[0]),
#     Patch(facecolor=stage_colors[1], label=stage_map[1]),
#     Patch(facecolor=stage_colors[2], label=stage_map[2]),
#     Patch(facecolor=stage_colors[3], label=stage_map[3]),
#     Patch(facecolor=stage_colors[4], label=stage_map[4])
# ]
# plt.legend(handles=legend_elements, loc='upper right', fontsize=9)
#
# # 添加 (c) 索引标签
# plt.gca().text(-0.05, -0.2, '(c)', transform=plt.gca().transAxes,
#                fontsize=14, fontweight='bold', va='top', ha='right')
#
# # 保存图像
# plt.tight_layout()
# plt.savefig('sleep_progression_smoothed_low_sat.png', dpi=300)
# print("\nGenerated smoothed sleep progression with low saturation colors: sleep_progression_smoothed_low_sat.png")
#
# # 显示前10个epoch的标签
# print("\nFirst 10 epochs for target patient:")
# for i, stage in enumerate(y_target[:10]):
#     print(f"Epoch {i + 1}: {stage_map.get(stage, f'Unknown({stage})')}")
#
# # 显示图表
# plt.show()