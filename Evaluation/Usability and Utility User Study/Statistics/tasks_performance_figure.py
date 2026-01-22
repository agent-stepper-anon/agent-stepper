import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import patheffects

# Set global font size
plt.rcParams.update({
    'font.size': 14,          # default font size
    'axes.titlesize': 14,     # title size
    'axes.labelsize': 14,     # x/y label size
    'xtick.labelsize': 12,    # x tick size
    'ytick.labelsize': 12,    # y tick size
    'legend.fontsize': 11,    # legend font size
    'legend.title_fontsize': 12
})

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

# Set up subplots: 1 for Task 1 boxplot, 2 for Task 2 and Task 3 stacked bar plots
fig = plt.figure(figsize=(12, 4))

# Task 1: Boxplot with swarmplot and legend
ax1 = plt.subplot(1, 3, 1)
df_task1 = df.dropna(subset=['Task 1 Performance %'])

# Boxplot for Task 1
sns.boxplot(
    data=df_task1,
    x='Group Label',
    y='Task 1 Performance %',
    ax=ax1,
    color='lavender',
    width=0.4,
    order=['Control Group', 'Debugger Group']
)

# Swarmplot for Task 1
sns.swarmplot(
    data=df_task1,
    x='Group Label',
    y='Task 1 Performance %',
    hue='Familiarity Level',
    hue_order=['Advanced', 'Moderate', 'Basic', 'None'],
    palette = {
        'None': '#d73027',       # worst
        'Basic': '#fc8d59',      # low/moderate
        'Moderate': '#91bfdb',   # moderate/good
        'Advanced': '#4575b4'    # best
    },
    dodge=False,
    size=8,
    ax=ax1,
    order=['Control Group', 'Debugger Group']
)

# Add boxplot boundary labels
for i, group in enumerate(['Control Group', 'Debugger Group']):
    group_data = df_task1[df_task1['Group Label'] == group]['Task 1 Performance %']
    if not group_data.empty:
        stats = group_data.describe()
        median = stats['50%']
        q1 = stats['25%']
        q3 = stats['75%']
        ax1.text(i - 0.23, median, fr'$\tilde{{x}}$: {median:.0f}%', ha='center', va='bottom', fontsize=11, color='black',
                 path_effects=[patheffects.withStroke(linewidth=2, foreground='white')])
        ax1.text(i + 0.27, q1, f'Q1: {q1:.0f}%', ha='center', va='top', fontsize=11, color='black',
                 path_effects=[patheffects.withStroke(linewidth=2, foreground='white')])
        ax1.text(i + 0.27, q3, f'Q3: {q3:.0f}%', ha='center', va='bottom', fontsize=11, color='black',
                 path_effects=[patheffects.withStroke(linewidth=2, foreground='white')])

# Task 1 labels and legend
ax1.set_title('SWE-Agent Trajectory Comprehension')
ax1.set_xlabel('')
ax1.set_ylabel('Overall Performance (%)')
ax1.legend(title='Familiarity', loc='lower center')
ax1.tick_params(axis='x', rotation=0)

# --- Task 2: RepairAgent Bug Identification Task ---
ax2 = plt.subplot(1, 3, 2)
df_task2 = df.dropna(subset=['Task 2 Score'])

# Group & pivot
task2_counts = df_task2.groupby(['Group Label', 'Task 2 Score']).size().unstack(fill_value=0)
task2_counts = task2_counts.reindex(columns=[0.0, 1.0], fill_value=0)
task2_counts = task2_counts.reindex(['Control Group', 'Debugger Group'])

# Plot stacked bars
bars2 = task2_counts.plot(
    kind='bar',
    stacked=True,
    ax=ax2,
    color=['#d73027', '#4575b4']  # red = Failure, blue = Bug Identified
)

# Apply hatching only to the "Failure" bars (first container)
for bar in bars2.containers[0]:
    bar.set_hatch('//')

# Add count labels
for container in bars2.containers:
    for bar in container:
        height = bar.get_height()
        if height > 0:
            ax2.text(
                bar.get_x() + bar.get_width()/2,
                bar.get_y() + height/2,
                str(int(height)),
                ha='center',
                va='center',
                fontsize=12,
                fontweight='bold',
                path_effects=[patheffects.withStroke(linewidth=2, foreground='white')]
            )

ax2.set_title('RepairAgent Bug Identification')
ax2.set_xlabel('')
ax2.set_ylabel('N')
ax2.legend(['Failure', 'Bug Identified'], title='Performance')
ax2.tick_params(axis='x', rotation=0)


# --- Task 3: ExecutionAgent Bug Identification Task ---
ax3 = plt.subplot(1, 3, 3)
df_task3 = df.dropna(subset=['Task 3 Score'])

# Group & pivot
task3_counts = df_task3.groupby(['Group Label', 'Task 3 Score']).size().unstack(fill_value=0)
task3_counts = task3_counts.reindex(columns=[0.0, 1.0], fill_value=0)
task3_counts = task3_counts.reindex(['Control Group', 'Debugger Group'])

# Plot stacked bars
bars3 = task3_counts.plot(
    kind='bar',
    stacked=True,
    ax=ax3,
    color=['#d73027', '#4575b4']
)

# Apply hatching only to the "Failure" bars (first container)
for bar in bars3.containers[0]:
    bar.set_hatch('//')

# Add count labels
for container in bars3.containers:
    for bar in container:
        height = bar.get_height()
        if height > 0:
            ax3.text(
                bar.get_x() + bar.get_width()/2,
                bar.get_y() + height/2,
                str(int(height)),
                ha='center',
                va='center',
                fontsize=12,
                fontweight='bold',
                path_effects=[patheffects.withStroke(linewidth=2, foreground='white')]
            )

ax3.set_title('ExecutionAgent Bug Identification')
ax3.set_xlabel('')
ax3.set_ylabel('N')
ax3.legend(['Failure', 'Bug Identified'], title='Performance')
ax3.tick_params(axis='x', rotation=0)


plt.tight_layout(pad=0)
plt.show()