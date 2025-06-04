# import argparse
# import glob
# import os
# import ntpath
# import shutil
# import numpy as np
# import pyedflib
# import matplotlib.pyplot as plt
#
#
# def main():
#     parser = argparse.ArgumentParser()
#     parser.add_argument("--data_dir", type=str,
#                         default="E:/DREAMT base/sleep-edf/sleep-edf-database-expanded-1.0.0/sleep-cassette",
#                         help="File path to the Sleep-EDF dataset.")
#     parser.add_argument("--output_dir", type=str,
#                         default="E:/DREAMT base/sleep-edf/sleep-edf-database-expanded-1.0.0/sleep-cassette/1",
#                         help="Directory where to save outputs.")
#     parser.add_argument("--select_ch", type=str, default="EEG Fpz-Cz",
#                         help="Name of the channel in the dataset.")
#     parser.add_argument("--plot_file", type=str, default="plot.png",
#                         help="Filename for saving the plot.")
#     args = parser.parse_args()
#
#     # 创建输出目录
#     if not os.path.exists(args.output_dir):
#         os.makedirs(args.output_dir)
#     else:
#         shutil.rmtree(args.output_dir)
#         os.makedirs(args.output_dir)
#
#     # 找到所有PSG文件
#     psg_fnames = glob.glob(os.path.join(args.data_dir, "*PSG.edf"))
#     psg_fnames.sort()
#
#     if not psg_fnames:
#         print(f"No PSG files found in {args.data_dir}")
#         return
#
#     # 只处理第一个患者文件
#     psg_fname = psg_fnames[0]
#
#     print(f"Processing signal file: {psg_fname}")
#
#     # 读取EDF文件
#     psg_f = pyedflib.EdfReader(psg_fname)
#
#     # 获取通道信息
#     ch_names = psg_f.getSignalLabels()
#     select_ch_idx = -1
#     for s, ch_name in enumerate(ch_names):
#         if ch_name == args.select_ch:
#             select_ch_idx = s
#             break
#
#     if select_ch_idx == -1:
#         print(f"Channel {args.select_ch} not found. Available channels: {ch_names}")
#         return
#
#     # 获取采样率和信号数据
#     sampling_rate = psg_f.getSampleFrequency(select_ch_idx)
#
#     # 读取整个通道的信号数据
#     signal = psg_f.readSignal(select_ch_idx)
#
#     # 创建时间轴（秒）
#     time_seconds = np.arange(len(signal)) / sampling_rate
#
#     # 创建绘图
#     plt.figure(figsize=(20, 10))
#
#     # 1. 绘制完整波形图
#     plt.subplot(2, 1, 1)
#     plt.plot(time_seconds, signal, 'b')
#     plt.title(f'Full EEG Fpz-Cz Signal - {ntpath.basename(psg_fname)}')
#     plt.ylabel('Amplitude (μV)')
#     plt.xlabel('Time (seconds)')
#     plt.grid(True)
#
#     # 2. 绘制放大后的片段（60-180秒）
#     plt.subplot(2, 1, 2)
#     zoom_start = 60
#     zoom_end = 180
#     zoom_indices = np.where((time_seconds >= zoom_start) & (time_seconds <= zoom_end))[0]
#
#     # 绘制细节
#     plt.plot(time_seconds[zoom_indices], signal[zoom_indices], 'b')
#
#     # 添加垂直线标记每秒的位置
#     for sec in range(zoom_start, zoom_end + 1):
#         plt.axvline(x=sec, color='gray', linewidth=0.5, linestyle='--')
#
#     # 设置图形参数
#     plt.title(f'Zoomed EEG Signal ({zoom_start}-{zoom_end} seconds)')
#     plt.ylabel('Amplitude (μV)')
#     plt.xlabel('Time (seconds)')
#     plt.grid(True)
#     plt.xlim(zoom_start, zoom_end)
#
#     # 调整布局
#     plt.tight_layout()
#
#     # 保存图形
#     plot_path = os.path.join(args.output_dir, args.plot_file)
#     plt.savefig(plot_path, dpi=150)
#     plt.close()
#
#     print(f"EEG waveform plot saved to: {plot_path}")
#
#
# if __name__ == "__main__":
#     main()

import argparse
import glob
import os
import ntpath
import shutil
import numpy as np
import pyedflib
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_dir", type=str,
                        default="E:/DREAMT base/sleep-edf/sleep-edf-database-expanded-1.0.0/sleep-cassette",
                        help="File path to the Sleep-EDF dataset.")
    parser.add_argument("--output_dir", type=str,
                        default="E:/DREAMT base/sleep-edf/sleep-edf-database-expanded-1.0.0/sleep-cassette/1",
                        help="Directory where to save outputs.")
    parser.add_argument("--select_ch", type=str, default="EEG Fpz-Cz",
                        help="Name of the channel in the dataset.")
    parser.add_argument("--plot_file", type=str, default="plot.png",
                        help="Filename for saving the plot.")
    args = parser.parse_args()

    # 创建输出目录
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    # else:
    #     shutil.rmtree(args.output_dir)
    #     os.makedirs(args.output_dir)

    # 找到所有PSG文件
    psg_fnames = glob.glob(os.path.join(args.data_dir, "*PSG.edf"))
    psg_fnames.sort()

    if not psg_fnames:
        print(f"No PSG files found in {args.data_dir}")
        return

    # 只处理第一个患者文件
    psg_fname = psg_fnames[0]

    print(f"Processing signal file: {psg_fname}")

    # 读取EDF文件
    psg_f = pyedflib.EdfReader(psg_fname)

    # 获取通道信息
    ch_names = psg_f.getSignalLabels()
    select_ch_idx = -1
    for s, ch_name in enumerate(ch_names):
        if ch_name == args.select_ch:
            select_ch_idx = s
            break

    if select_ch_idx == -1:
        print(f"Channel {args.select_ch} not found. Available channels: {ch_names}")
        return

    # 获取采样率和信号数据
    sampling_rate = psg_f.getSampleFrequency(select_ch_idx)

    # 读取整个通道的信号数据
    signal = psg_f.readSignal(select_ch_idx)

    # 创建时间轴（秒）
    time_seconds = np.arange(len(signal)) / sampling_rate

    # 选择60-180秒的数据范围
    zoom_start = 4060
    zoom_end = 4100
    zoom_indices = np.where((time_seconds >= zoom_start) & (time_seconds <= zoom_end))[0]

    # 提取这段范围的信号和时间点
    zoom_time = time_seconds[zoom_indices] - zoom_start  # 从0开始的时间轴
    zoom_signal = signal[zoom_indices]

    # 创建新的图形
    plt.figure(figsize=(10, 4))  # 尺寸可以调整

    # 绘制纯净的波形（60-180秒）
    plt.plot(zoom_time, zoom_signal, 'b', linewidth=1)  # 蓝色线条

    # 移除坐标轴、边框和网格
    plt.axis('off')  # 关闭所有坐标轴

    # 设置边界为紧密贴合波形
    plt.margins(0, 0)  # 移除所有边距

    # 调整布局，确保波形填满整个图形区域
    plt.subplots_adjust(left=0, right=1, bottom=0, top=1)  # 边缘无间距

    # 保存图形（去除白色边缘）
    plot_path = os.path.join(args.output_dir, args.plot_file)
    plt.savefig(plot_path, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.close()

    print(f"EEG waveform plot saved to: {plot_path}")


if __name__ == "__main__":
    main()