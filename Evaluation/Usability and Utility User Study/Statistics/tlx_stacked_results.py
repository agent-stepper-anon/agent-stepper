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
    3: []                              # Task 3 none
}

task_label = ['SWE-Agent Trajectory Comprehension Task', 'RepairAgent Bug Identification Task', 'ExecutionAgent Bug Identification Task']

# Function to create TLX plot for a given task
def plot_tlx_for_task(task_num, ax):
    # Select columns and convert to numeric
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
    control_rgb = np.array(mpl.colors.to_rgb('#d73027'))
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
    ax.legend(handles=handles, title='Participant Group', loc='upper right')

    # Title / axes
    ax.set_title(f'Perceived Difficulty of {task_label[task_num - 1]}')
    ax.set_ylabel('Avg Score (± SD)')
    ax.set_xlabel('')
    ax.tick_params(axis='x', rotation=0)
    
    # --- Set y-axis limits and ticks ---
    ax.set_ylim(1, 8)  # Start y-axis at 1, end at 8 to include error bars
    ax.set_yticks(range(1, 8, 1))  # Ticks at [1, 2, 3, 4, 5, 6, 7]

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
    if task_num == 3:
        ax.text(
            0.20, -0.2,
            '(Scale 1-7) Smaller Better in Every Dimension',
            ha='center', va='top',
            transform=ax.transAxes,
            fontsize=10
        )
        ax.text(
            0.70, -0.2,
            '* Statistically significant difference between groups (p < 0.05)',
            ha='center', va='top',
            transform=ax.transAxes,
            fontsize=10
        )

# Create a single figure with three subplots
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(9, 7), sharex=False)

# Generate plots for each task
plot_tlx_for_task(1, ax1)
plot_tlx_for_task(2, ax2)
plot_tlx_for_task(3, ax3)

# Adjust layout to prevent overlap and make room for footnotes
plt.tight_layout(pad=0)
plt.subplots_adjust(hspace=0.4, bottom=0.08)

plt.show()