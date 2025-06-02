# tgam_plotter.py
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import tkinter as tk
import time
import queue
import threading

# 使用Agg后端，避免可能的线程问题
matplotlib.use('Agg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class RealTimePlot:
    def __init__(self, max_points=1000):
        self.max_points = max_points
        self.root = None
        self.thread = threading.Thread(target=self._create_gui)
        self.thread.daemon = True
        self.thread.start()

        # 等待GUI创建完成
        while self.root is None:
            time.sleep(0.1)

        self.data_queue = queue.Queue()
        self.running = True

    def _create_gui(self):
        """创建GUI（必须在主线程中）"""
        self.root = tk.Tk()
        self.root.title("TGAM脑电波实时波形")
        self.root.geometry("1200x800")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 创建matplotlib图形
        plt.rcParams["font.sans-serif"] = ["SimHei"]  # 用来正常显示中文标签
        plt.rcParams["axes.unicode_minus"] = False  # 用来正常显示负号

        self.fig, self.ax = plt.subplots(figsize=(12, 8))
        plt.subplots_adjust(bottom=0.15)

        # 设置波形图标题和标签
        self.ax.set_title('TGAM原始脑电波形')
        self.ax.set_ylabel('振幅(μV)')
        self.ax.set_xlabel('时间')
        self.ax.grid(True)

        # 设置坐标轴范围
        self.ax.set_ylim(-2000, 2000)

        # 初始化数据缓冲区
        self.xdata = np.arange(0, self.max_points)
        self.ydata = np.zeros(self.max_points)

        # 创建曲线
        self.line, = self.ax.plot(self.xdata, self.ydata, 'b-', linewidth=0.5)

        # 在Tkinter窗口中嵌入matplotlib图形
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        # 添加控制按钮
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        self.pause_button = tk.Button(control_frame, text="暂停", command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.clear_button = tk.Button(control_frame, text="清屏", command=self.clear_plot)
        self.clear_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.quit_button = tk.Button(control_frame, text="退出", command=self.quit)
        self.quit_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # 添加状态标签
        self.status_var = tk.StringVar(value="状态: 运行中")
        status_label = tk.Label(self.root, textvariable=self.status_var, anchor='w')
        status_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # 添加带宽指示器
        self.bandwidth_var = tk.StringVar(value="数据传输: 0 Hz")
        bandwidth_label = tk.Label(self.root, textvariable=self.bandwidth_var, anchor='w')
        bandwidth_label.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=2)

        # 绑定键盘事件
        self.root.bind('p', lambda e: self.toggle_pause())
        self.root.bind('c', lambda e: self.clear_plot())
        self.root.bind('q', lambda e: self.quit())

        # 启动更新定时器
        self.root.after(50, self.update_plot)
        self.root.after(1000, self.update_rate)

        # 启动GUI主循环
        self.root.mainloop()

    def on_closing(self):
        """窗口关闭事件处理"""
        self.quit()

    def toggle_pause(self):
        """切换暂停状态"""
        self.paused = not self.paused
        if self.paused:
            self.status_var.set("状态: 已暂停")
            self.pause_button.config(text="继续")
        else:
            self.status_var.set("状态: 运行中")
            self.pause_button.config(text="暂停")

    def clear_plot(self):
        """清空波形图"""
        self.ydata = np.zeros(self.max_points)
        self.line.set_ydata(self.ydata)
        self.canvas.draw()
        self.status_var.set("状态: 波形已清空")
        if hasattr(self.root, 'after'):
            self.root.after(2000, lambda: self.status_var.set("状态: 运行中" if not self.paused else "状态: 已暂停"))

    def quit(self):
        """退出应用"""
        self.running = False
        if hasattr(self, 'root') and self.root:
            self.root.destroy()

    def add_data(self, value):
        """添加新的数据点到队列"""
        if not hasattr(self, 'paused') or not self.paused:
            self.data_queue.put(value)

    def update_rate(self):
        """更新带宽显示"""
        if hasattr(self, 'root') and self.root:
            queue_size = self.data_queue.qsize()
            self.bandwidth_var.set(f"数据传输: {queue_size} Hz")
            self.root.after(1000, self.update_rate)

    def update_plot(self):
        """更新波形图"""
        if not hasattr(self, 'root') or not self.root:
            return

        try:
            # 从队列中获取所有可用数据
            all_data = []
            while not self.data_queue.empty():
                try:
                    value = self.data_queue.get_nowait()
                    all_data.append(value)
                except queue.Empty:
                    break

            if all_data:
                # 更新数据点
                for value in all_data:
                    self.ydata = np.roll(self.ydata, -1)
                    self.ydata[-1] = value

                # 更新图形
                self.line.set_ydata(self.ydata)

                # 计算最新的Y轴范围（动态调整）
                visible_data = self.ydata[-self.max_points:]
                min_val = np.min(visible_data) - 100
                max_val = np.max(visible_data) + 100
                self.ax.set_ylim(min_val, max_val)

                self.canvas.draw()

        except Exception as e:
            pass  # 忽略可能的绘图错误

        # 安排下一次更新
        if hasattr(self.root, 'after'):
            self.root.after(50, self.update_plot)

    def is_running(self):
        """检查GUI是否仍在运行"""
        return hasattr(self, 'root') and self.root and self.root.winfo_exists()


if __name__ == '__main__':
    # 测试绘图窗口
    plotter = RealTimePlot(max_points=1000)


    # 模拟数据生成
    def generate_test_data():
        import math
        t = 0
        while plotter.running and plotter.is_running():
            value = int(2000 * math.sin(t))
            t += 0.1
            plotter.add_data(value)
            time.sleep(0.01)


    test_thread = threading.Thread(target=generate_test_data, daemon=True)
    test_thread.start()

    # 等待主线程结束
    while test_thread.is_alive():
        time.sleep(0.1)