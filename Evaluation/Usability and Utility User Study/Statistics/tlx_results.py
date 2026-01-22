import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import patheffects
import numpy as np
import matplotlib as mpl
from matplotlib.patches import Patch

# Read the data, preserving "None"
df = pd.read_csv(
    "UserStudyRawResults.csv", 
    delimiter=';', 
    keep_default_na=False  # preserve "None" as string
)

# Clean Task 1 Performance column (percentage)
df['Task 1 Performance %'] = df['Task 1 Performance %'].str.replace(',', '.').astype(float) * 100

# Task 2 and Task 3 are binary; convert to numeric, coerce '#N/A' to NaN
df['Task 2 Score'] = pd.to_numeric(df['Task 2 Score'], errors='coerce')
df['Task 3 Score'] = pd.to_numeric(df['Task 3 Score'], errors='coerce')

# Map groups to labels
df['Group Label'] = df['Group'].map({'A': 'Debugger Group', 'B': 'Control Group'})

# Define TLX dimensions
dimensions = ['Mental Demand', 'Temporal Demand', 'Perceived Perf.', 'Effort', 'Frustration']

# Pretty label mapping
dimension_label_map = {
    'Perceived Perf.': 'Perceived Performance'
}

# Significance by task (use the ORIGINAL dimension keys that match your CSV)
significance_map = {
    1: ['Perceived Perf.', 'Effort'],  # Task 1 significant dimensions
    2: ['Frustration'],                # Task 2 significant dimension
    3: []                              # Task 3 none (adjust if needed)
}

task_label = ['SWE-Agent Trajectory Comprehension Task', 'RepairAgent Bug Identification Task', 'ExecutionAgent Bug Identification Task']

# Function to create TLX plot for a given task
def plot_tlx_for_task(task_num):
    # Select columns and convert to numeric...
    tlx_cols = [f'Task {task_num} {dim}' for dim in dimensions]
    for col in tlx_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    tlx_df = df.melt(
        id_vars=['Group Label'],
        value_vars=tlx_cols,
        var_name='Dimension',
        value_name='Score'
    )
    tlx_df['Dimension'] = tlx_df['Dimension'].str.replace(f'Task {task_num} ', '')
    tlx_df['Dimension'] = tlx_df['Dimension'].replace(dimension_label_map)
    tlx_df = tlx_df.dropna(subset=['Score'])

    # Build the display order with pretty labels
    order_labels = [dimension_label_map.get(d, d) for d in dimensions]

    # Which labels are significant (pretty form)
    sig_dims_display = [dimension_label_map.get(d, d) for d in significance_map.get(task_num, [])]

    fig, ax = plt.subplots(figsize=(10, 4))

    sns.barplot(
        data=tlx_df,
        x='Dimension',
        y='Score',
        hue='Group Label',
        ax=ax,
        errorbar='sd',
        order=order_labels,
        hue_order=['Control Group', 'Debugger Group'],
        palette={'Control Group': '#d73027', 'Debugger Group': '#4575b4'}
    )
    
    # --- Apply hatching to Control Group bars (robust) ---
    control_rgb  = np.array(mpl.colors.to_rgb('#d73027'))
    debugger_rgb = np.array(mpl.colors.to_rgb('#4575b4'))

    for bar in ax.patches:
        if not hasattr(bar, "get_facecolor"):
            continue
        rgb = np.array(bar.get_facecolor()[:3])  # ignore alpha
        if np.linalg.norm(rgb - control_rgb) < np.linalg.norm(rgb - debugger_rgb):
            bar.set_hatch('//')
            bar.set_edgecolor('black')
            bar.set_linewidth(0.6)

    # --- Custom legend (with hatch for Control Group) ---
    handles = [
        Patch(facecolor='#d73027', hatch='//', label='Control Group', edgecolor='black'),
        Patch(facecolor='#4575b4', label='Debugger Group', edgecolor='black')
    ]
    ax.legend(handles=handles, title='Group', loc='upper right')

    # Title / axes
    ax.set_title(f'Perceived Difficulty of {task_label[task_num - 1]}')
    ax.set_ylabel('Average Score (with Std Dev)')
    ax.set_xlabel('')

    # Title / axes
    ax.set_title(f'Perceived Difficulty of {task_label[task_num - 1]}')
    ax.set_ylabel('Average Score (with Std Dev)')
    ax.set_xlabel('')
    ax.legend(title='Group', loc='upper right')
    ax.tick_params(axis='x', rotation=0)

    # --- Highlight significant categories ---
    # 1) Shade the column background
    xticks = ax.get_xticks()
    xticklabels = [t.get_text() for t in ax.get_xticklabels()]
    for i, lab in enumerate(xticklabels):
        if lab in sig_dims_display:
            ax.axvspan(i - 0.5, i + 0.5, alpha=0.08, color='grey', zorder=0)

    # 2) Add an asterisk to the x labels
    new_xticklabels = [
        (lab + '*') if (lab in sig_dims_display) else lab
        for lab in xticklabels
    ]
    ax.set_xticklabels(new_xticklabels)

    # Notes under the axis
    ax.text(
        0.25, -0.11,
        '(Scale 1-7) Smaller Better in Every Dimension',
        ha='center', va='top',
        transform=ax.transAxes,
        fontsize=10
    )
    ax.text(
        0.75, -0.11,
        '* Statistically significant difference between groups (p < 0.05)',
        ha='center', va='top',
        transform=ax.transAxes,
        fontsize=10
    )

    # Make room for the footnotes
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.14)

    plt.show()

# Generate plots for each task
for task in [1, 2, 3]:
    plot_tlx_for_task(task)