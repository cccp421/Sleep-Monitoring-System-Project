import numpy as np
import matplotlib.pyplot as plt
from collections import Counter

# 加载数据
data = np.load('E:/DREAMT base/sleep-edf/sleep-edf-database-expanded-1.0.0/sleep-cassette/eeg_fpz_cz/SC4041E0.npz')  # 替换为实际文件路径
y = data['y']  # 真实标签

# 睡眠阶段映射（英文）
stage_map = {
    0: "Wake",
    1: "N1",
    2: "N2",
    3: "N3",
    4: "REM"
}

# 睡眠阶段颜色映射
stage_colors = {
    0: 'blue',      # Wake - 蓝色
    1: 'cyan',      # N1 - 青色
    2: 'green',     # N2 - 绿色
    3: 'red',       # N3 - 红色
    4: 'purple'     # REM - 紫色
}

# 计算各阶段比例
stage_counts = Counter(y)
total_epochs = len(y)

print("Sleep Stage Distribution:")
for stage_idx, count in sorted(stage_counts.items()):
    stage_name = stage_map.get(stage_idx, f"Unknown({stage_idx})")
    percentage = count / total_epochs * 100
    print(f"{stage_name:>5}: {count:>5} epochs ({percentage:.1f}%)")

# 创建时间轴（每个epoch 30秒）
hours = total_epochs / 120  # 120 epoch/小时

plt.figure(figsize=(15, 6))

# 阶段分布饼图
plt.subplot(1, 2, 1)
labels = [stage_map.get(i, f"Unknown{i}") for i in sorted(stage_counts.keys())]
sizes = [stage_counts[i] for i in sorted(stage_counts.keys())]
plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
plt.title('Sleep Stage Distribution')

# 阶段随时间变化图
plt.subplot(1, 2, 2)
x_axis = np.arange(len(y))  # 横坐标：epoch索引
y_axis = y  # 纵坐标：睡眠阶段

# 为每个点设置颜色
point_colors = [stage_colors.get(stage, 'gray') for stage in y]

# 使用scatter绘制点图
plt.scatter(x_axis / 120, y_axis, c=point_colors, s=3)  # s控制点的大小

plt.yticks(list(stage_map.keys()), list(stage_map.values()))
plt.xlabel('Time (Hours)')
plt.ylabel('Sleep Stage')
plt.title('Sleep Stage Progression')
plt.grid(alpha=0.3)

# 添加图例
from matplotlib.patches import Patch
legend_elements = [
    Patch(facecolor='blue', label='Wake'),
    Patch(facecolor='cyan', label='N1'),
    Patch(facecolor='green', label='N2'),
    Patch(facecolor='red', label='N3'),
    Patch(facecolor='purple', label='REM')
]
plt.legend(handles=legend_elements, loc='best')

plt.tight_layout()

# 保存图像
plt.savefig('sleep_stage_distribution.png', dpi=300)
print("\nGenerated sleep stage distribution: sleep_stage_distribution.png")

# 显示前10个epoch的标签
print("\nTrue labels of first 10 epochs:")
for i, stage in enumerate(y[:10]):
    print(f"Epoch {i+1}: {stage_map.get(stage, f'Unknown({stage})')}")

# 可选：添加一张整夜睡眠阶段趋势图
plt.figure(figsize=(12, 4))

# 创建整夜趋势图（每个点代表5分钟）
minute_intervals = 5  # 每5分钟一个点
points_per_interval = minute_intervals * 2  # 每分钟2个epoch
smoothed_stages = [np.median(y[i:i+points_per_interval]) for i in range(0, len(y), points_per_interval)]

# 创建时间轴
hours_axis = np.arange(len(smoothed_stages)) * minute_intervals / 60

plt.plot(hours_axis, smoothed_stages, linewidth=2)
plt.fill_between(hours_axis, smoothed_stages, alpha=0.3)
plt.yticks(list(stage_map.keys()), list(stage_map.values()))
plt.xlabel('Time (Hours)')
plt.ylabel('Sleep Stage')
plt.title('Smoothed Sleep Stage Progression')
plt.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('sleep_progression_smoothed.png', dpi=300)
print("\nGenerated smoothed sleep progression: sleep_progression_smoothed.png")