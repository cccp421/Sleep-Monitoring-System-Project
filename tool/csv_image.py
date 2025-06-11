import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from matplotlib.patches import Patch
import matplotlib.colors as mcolors

# ================================ CONFIGURATION ================================
CSV_FILE = "E:/DREAMT base/sleep-edf/sleep-edf-database-expanded-1.0.0/sleep-cassette/csv_output/SC4001E0.csv"
OUTPUT_DIR = "E:/DREAMT base/sleep-edf/sleep-edf-database-expanded-1.0.0/sleep-cassette/visualizations"
SHOW_FULL_NIGHT = True
SIGNAL_CHUNK_SIZE = 100


# ============================== FUNCTION DEFINITIONS ==============================
def load_and_prepare_data(filepath):
    """Load and preprocess CSV data"""
    df = pd.read_csv(filepath)

    # Extract basic info
    patient_id = df['Patient_ID'].iloc[0]
    record_id = df['Record_ID'].iloc[0]
    total_epochs = len(df)

    print(f"Loading data: {patient_id}-{record_id}")
    print(f"Total epochs: {total_epochs}")
    stage_counts = df['Stage_Label'].value_counts()
    print("Sleep stage distribution:")
    for stage, count in stage_counts.items():
        percentage = count / total_epochs * 100
        print(f"{stage:4}: {count:4} epochs ({percentage:.1f}%)")

    # Add numerical stage mapping
    stage_mapping = {'W': 0, 'N1': 1, 'N2': 2, 'N3': 3, 'REM': 4, 'MOVE': 5, 'UNK': 6}
    df['Stage_Numeric'] = df['Stage_Label'].map(stage_mapping)

    # Add time axis
    epoch_duration = df['Epoch_Duration(s)'].iloc[0]
    df['Time_Min'] = df['Epoch_Index'] * epoch_duration / 60

    return df, patient_id, record_id


def create_sleep_stage_plot(df, patient_id, record_id):
    """Create sleep stage hypnogram"""
    plt.figure(figsize=(15, 6))

    # Sleep stage color mapping
    stage_colors = {
        0: 'gold',  # Wake
        1: 'lightgreen',  # N1
        2: 'darkgreen',  # N2
        3: 'blue',  # N3
        4: 'purple',  # REM
        5: 'gray',  # Movement
        6: 'lightgray'  # Unknown
    }

    # Plot each epoch as a colored bar
    plt.bar(df['Time_Min'], height=1, width=0.5,
            color=df['Stage_Numeric'].map(stage_colors),
            edgecolor='none')

    # Set plot properties
    plt.title(f'Sleep Stage Hypnogram - {patient_id}-{record_id}', fontsize=16)
    plt.xlabel('Time (minutes)', fontsize=12)
    plt.ylabel('Sleep Stage', fontsize=12)
    plt.yticks([])

    # Create legend
    legend_elements = [
        Patch(facecolor='gold', edgecolor='none', label='Wake (W)'),
        Patch(facecolor='lightgreen', edgecolor='none', label='Stage 1 (N1)'),
        Patch(facecolor='darkgreen', edgecolor='none', label='Stage 2 (N2)'),
        Patch(facecolor='blue', edgecolor='none', label='Stage 3 (N3)'),
        Patch(facecolor='purple', edgecolor='none', label='REM Sleep'),
        Patch(facecolor='gray', edgecolor='none', label='Movement'),
        Patch(facecolor='lightgray', edgecolor='none', label='Unknown')
    ]
    plt.legend(handles=legend_elements, loc='upper right', ncol=4, fontsize=9)

    # Set time range
    if not SHOW_FULL_NIGHT:
        plt.xlim(df['Time_Min'].min(), 120)  # First 2 hours
    else:
        plt.xlim(df['Time_Min'].min(), df['Time_Min'].max())

    # Add grid and format
    plt.grid(axis='x', linestyle='--', alpha=0.3)
    plt.tight_layout()

    return plt


def create_eeg_trend_plot(df, patient_id, record_id):
    """Create EEG signal trend plot"""
    plt.figure(figsize=(15, 8))

    # Plot EEG mean and standard deviation
    plt.subplot(2, 1, 1)
    plt.plot(df['Time_Min'], df['EEG_Mean'], label='EEG Mean', linewidth=1.5, color='blue')
    plt.fill_between(df['Time_Min'],
                     df['EEG_Mean'] - df['EEG_Std'],
                     df['EEG_Mean'] + df['EEG_Std'],
                     alpha=0.2, label='Std. Deviation', color='lightblue')

    plt.title(f'EEG Signal Trend - {patient_id}-{record_id}', fontsize=16)
    plt.ylabel('Amplitude (μV)', fontsize=12)
    plt.legend()

    if not SHOW_FULL_NIGHT:
        plt.xlim(df['Time_Min'].min(), 120)  # First 2 hours

    # Boxplot of features by sleep stage
    plt.subplot(2, 1, 2)

    # Group data by sleep stage
    stage_groups = {}
    for stage in ['W', 'N1', 'N2', 'N3', 'REM']:
        stage_data = df[df['Stage_Label'] == stage]['EEG_Mean']
        if not stage_data.empty:
            stage_groups[stage] = stage_data

    # Stage colors
    stage_colors = {
        'W': 'gold',
        'N1': 'lightgreen',
        'N2': 'darkgreen',
        'N3': 'blue',
        'REM': 'purple'
    }

    # Create boxplot
    box = plt.boxplot(stage_groups.values(), patch_artist=True,
                      labels=stage_groups.keys(), widths=0.7)

    # Set box colors
    for patch, stage in zip(box['boxes'], stage_groups.keys()):
        patch.set_facecolor(stage_colors[stage])

    plt.title('EEG Mean Amplitude by Sleep Stage', fontsize=14)
    plt.ylabel('Amplitude (μV)', fontsize=12)
    plt.xlabel('Sleep Stage', fontsize=12)
    plt.grid(alpha=0.3, linestyle=':')

    # Create custom legend
    legend_elements = [Patch(facecolor=color, edgecolor='black', label=stage)
                       for stage, color in stage_colors.items()]
    plt.legend(handles=legend_elements, loc='upper right', title="Sleep Stage")

    plt.tight_layout()

    return plt


def create_eeg_feature_snippets(df, patient_id, record_id):
    """Create EEG feature representations for each stage"""
    plt.figure(figsize=(15, 10))

    # Stages to show
    stages_to_show = ['W', 'N1', 'N2', 'N3', 'REM']

    # Create a subplot for each stage
    for i, stage in enumerate(stages_to_show, 1):
        stage_df = df[df['Stage_Label'] == stage]

        if not stage_df.empty:
            # Get a representative sample
            snippet = stage_df.sample(1).iloc[0]

            # Create subplot
            plt.subplot(len(stages_to_show), 1, i)

            # Plot quartile representation
            features = ['Min', 'Q1', 'Median', 'Q3', 'Max']
            values = [snippet['EEG_Min'], snippet['EEG_Q1'], snippet['EEG_Median'],
                      snippet['EEG_Q3'], snippet['EEG_Max']]

            plt.plot(range(1, 6), values, 'o-', color='blue',
                     linewidth=1.5, label='EEG Distribution')

            # Add mean line and std deviation
            plt.axhline(y=snippet['EEG_Mean'], color='red', linestyle='-',
                        linewidth=1.5, alpha=0.8, label='Mean')

            plt.fill_between(range(1, 6),
                             snippet['EEG_Mean'] - snippet['EEG_Std'],
                             snippet['EEG_Mean'] + snippet['EEG_Std'],
                             color='red', alpha=0.1, label='Std. Dev.')

            # Set labels and title
            plt.title(f'Stage {stage} EEG Characteristics', fontsize=12)
            plt.ylabel('Amplitude (μV)', fontsize=10)
            plt.xticks(range(1, 6), features)

            # Only show legend for first plot
            if i == 1:
                plt.legend(loc='upper left')

    plt.tight_layout()
    plt.suptitle(f'EEG Characteristics by Sleep Stage - {patient_id}-{record_id}',
                 fontsize=16, y=0.98)

    return plt


def create_stage_distribution_plots(df, patient_id, record_id):
    """Create sleep stage distribution charts"""
    plt.figure(figsize=(13, 6))

    # Calculate stage percentages
    stage_counts = df['Stage_Label'].value_counts()
    total = stage_counts.sum()
    stage_percents = stage_counts / total * 100

    # Ensure all stages are included
    required_stages = ['W', 'N1', 'N2', 'N3', 'REM', 'MOVE', 'UNK']
    for stage in required_stages:
        if stage not in stage_percents.index:
            stage_percents[stage] = 0

    # Reindex to maintain consistent order
    stage_percents = stage_percents.reindex(required_stages)

    # Stage colors
    stage_colors = {
        'W': 'gold',
        'N1': 'lightgreen',
        'N2': 'darkgreen',
        'N3': 'blue',
        'REM': 'purple',
        'MOVE': 'gray',
        'UNK': 'lightgray'
    }

    # Pie chart (percentage distribution)
    plt.subplot(1, 2, 1)
    explode = [0.05 if stage == stage_percents.idxmax() else 0 for stage in stage_percents.index]
    plt.pie(stage_percents, labels=stage_percents.index,
            autopct='%1.1f%%', startangle=90,
            colors=[stage_colors[stage] for stage in stage_percents.index],
            explode=explode, shadow=True)
    plt.title('Sleep Stage Distribution', fontsize=14)

    # Bar chart (count by stage)
    plt.subplot(1, 2, 2)
    bars = plt.bar(stage_percents.index, stage_percents,
                   color=[stage_colors[stage] for stage in stage_percents.index])

    # Add counts above bars
    for bar, count in zip(bars, stage_counts):
        plt.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f'{count}', ha='center', va='bottom', fontsize=9)

    plt.title('Sleep Stage Counts', fontsize=14)
    plt.xlabel('Sleep Stage', fontsize=12)
    plt.ylabel('Percentage', fontsize=12)
    plt.ylim(0, max(stage_percents) * 1.1)

    # Add secondary axis for counts
    ax2 = plt.gca().twinx()
    ax2.set_ylim(0, max(stage_counts) * 1.1)
    ax2.set_ylabel('Count', fontsize=12)

    plt.tight_layout()
    plt.suptitle(f'Sleep Stage Metrics - {patient_id}-{record_id}',
                 fontsize=16, y=0.98)

    return plt


def save_all_visualizations(df, patient_id, record_id, output_dir):
    """Generate and save all visualizations"""
    os.makedirs(output_dir, exist_ok=True)
    outputs = []

    # Sleep stage hypnogram
    plot1 = create_sleep_stage_plot(df, patient_id, record_id)
    output_path1 = os.path.join(output_dir, f"{patient_id}-{record_id}_sleep_stages.png")
    plot1.savefig(output_path1, dpi=300, bbox_inches='tight')
    outputs.append(output_path1)
    print(f"Saved sleep stage plot: {output_path1}")

    # EEG trend plot
    plot2 = create_eeg_trend_plot(df, patient_id, record_id)
    output_path2 = os.path.join(output_dir, f"{patient_id}-{record_id}_eeg_trend.png")
    plot2.savefig(output_path2, dpi=300, bbox_inches='tight')
    outputs.append(output_path2)
    print(f"Saved EEG trend plot: {output_path2}")

    # EEG feature snippets
    plot3 = create_eeg_feature_snippets(df, patient_id, record_id)
    output_path3 = os.path.join(output_dir, f"{patient_id}-{record_id}_eeg_features.png")
    plot3.savefig(output_path3, dpi=300, bbox_inches='tight')
    outputs.append(output_path3)
    print(f"Saved EEG feature plot: {output_path3}")

    # Stage distribution charts
    plot4 = create_stage_distribution_plots(df, patient_id, record_id)
    output_path4 = os.path.join(output_dir, f"{patient_id}-{record_id}_stage_distribution.png")
    plot4.savefig(output_path4, dpi=300, bbox_inches='tight')
    outputs.append(output_path4)
    print(f"Saved stage distribution plot: {output_path4}")

    print(f"\nAll visualizations saved to: {output_dir}")
    return outputs


# ============================== MAIN EXECUTION ==============================
def main():
    # Verify file exists
    if not os.path.exists(CSV_FILE):
        print(f"Error: File not found - {CSV_FILE}")
        return

    print(f"Processing file: {CSV_FILE}")

    try:
        # Load and prepare data
        df, patient_id, record_id = load_and_prepare_data(CSV_FILE)

        # Generate and save visualizations
        saved_files = save_all_visualizations(df, patient_id, record_id, OUTPUT_DIR)

        print("\nProcessing completed successfully!")
        print(f"Generated {len(saved_files)} visualization files")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()