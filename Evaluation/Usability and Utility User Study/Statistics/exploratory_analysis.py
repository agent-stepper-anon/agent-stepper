# Import necessary libraries
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import scipy.stats as stats
import numpy as np

# Set seaborn style for better visuals
sns.set(style="whitegrid")

# Load the data from the CSV file
df = pd.read_csv("UserStudyRawResults.csv", sep=';', decimal=',')

# Replace '#N/A' with NaN for proper handling
df.replace('#N/A', np.nan, inplace=True)

# Drop completely empty rows (if any)
df.dropna(how='all', inplace=True)

# Assume Group A: with debugger tool, Group B: without (based on performance differences)
group_labels = {'A': 'With Debugger', 'B': 'Without Debugger'}
df['Group Label'] = df['Group'].map(group_labels)

# Display the cleaned DataFrame
print("Cleaned DataFrame:")
print(df)

# Compute summary statistics for performance and time by group
performance_cols = ['Task 1 Performance %', 'Task 2 Score', 'Task 3 Score']
time_cols = ['Task 1 Time', 'Task 2 Time', 'Task 3 Time']
tlx_cols_task1 = ['Task 1 Mental Demand', 'Task 1 Temporal Demand', 'Task 1 Perceived Perf.', 'Task 1 Effort', 'Task 1 Frustration']
tlx_cols_task2 = ['Task 2 Mental Demand', 'Task 2 Temporal Demand', 'Task 2 Perceived Perf.', 'Task 2 Effort', 'Task 2 Frustration']
tlx_cols_task3 = ['Task 3 Mental Demand', 'Task 3 Temporal Demand', 'Task 3 Perceived Perf.', 'Task 3 Effort', 'Task 3 Frustration']

# Summary stats
summary_performance = df.groupby('Group Label')[performance_cols].agg(['mean', 'std', 'count'])
summary_time = df.groupby('Group Label')[time_cols].agg(['mean', 'std', 'count'])
summary_tlx_task1 = df.groupby('Group Label')[tlx_cols_task1].agg(['mean', 'std', 'count'])
summary_tlx_task2 = df.groupby('Group Label')[tlx_cols_task2].agg(['mean', 'std', 'count'])
summary_tlx_task3 = df.groupby('Group Label')[tlx_cols_task3].agg(['mean', 'std', 'count'])

print("\nSummary Statistics - Performance:")
print(summary_performance)
print("\nSummary Statistics - Time:")
print(summary_time)
print("\nSummary Statistics - TLX Task 1:")
print(summary_tlx_task1)
print("\nSummary Statistics - TLX Task 2:")
print(summary_tlx_task2)
print("\nSummary Statistics - TLX Task 3:")
print(summary_tlx_task3)

# Function to perform Mann-Whitney U test (non-parametric, suitable for small samples)
def mann_whitney_test(group_a, group_b):
    stat, p = stats.mannwhitneyu(group_a, group_b, alternative='two-sided')
    return stat, p

# Statistical tests for differences between groups
print("\nMann-Whitney U Tests for Differences Between Groups:")
for col in performance_cols + time_cols + tlx_cols_task1 + tlx_cols_task2 + tlx_cols_task3:
    group_a = df[df['Group'] == 'A'][col].dropna()
    group_b = df[df['Group'] == 'B'][col].dropna()
    if len(group_a) > 0 and len(group_b) > 0:
        stat, p = mann_whitney_test(group_a, group_b)
        print(f"{col}: U={stat:.2f}, p={p:.4f} (significant if p<0.05)")

# Plot 1: Boxplots for Performance Metrics by Group with Data Points
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for i, col in enumerate(performance_cols):
    # Boxplot
    sns.boxplot(x='Group Label', y=col, data=df, ax=axes[i], color='lightblue')
    # Overlay data points with swarmplot
    sns.swarmplot(x='Group Label', y=col, data=df, ax=axes[i], color='black', size=6)
    axes[i].set_title(f'{col} by Group')
    axes[i].set_ylabel(col)
plt.tight_layout()
plt.show()

# Plot 2: Boxplots for Time Metrics by Group
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for i, col in enumerate(time_cols):
    sns.boxplot(x='Group Label', y=col, data=df, ax=axes[i])
    axes[i].set_title(f'{col} by Group')
    axes[i].set_ylabel(col)
plt.tight_layout()
plt.show()

# Plot 3: Bar Charts for Mean TLX Scores by Task and Group (with error bars)
tlx_tasks = {
    'Task 1': tlx_cols_task1,
    'Task 2': tlx_cols_task2,
    'Task 3': tlx_cols_task3
}

for task, cols in tlx_tasks.items():
    tlx_melted = df.melt(id_vars=['Group Label'], value_vars=cols, var_name='TLX Dimension', value_name='Score')
    plt.figure(figsize=(12, 6))
    sns.barplot(x='TLX Dimension', y='Score', hue='Group Label', data=tlx_melted, errorbar='sd')
    plt.title(f'Mean TLX Scores for {task} by Group (with Std Dev)')
    plt.ylabel('Mean Score (1-7)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# Plot 4: Scatter plots for Performance vs Time for each task
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
for i, task in enumerate([1, 2, 3]):
    perf_col = f'Task {task} Performance %' if task == 1 else f'Task {task} Score'
    time_col = f'Task {task} Time'
    sns.scatterplot(x=time_col, y=perf_col, hue='Group Label', data=df, ax=axes[i])
    axes[i].set_title(f'{perf_col} vs {time_col} by Group')
plt.tight_layout()
plt.show()

# Plot 5: Heatmap of Correlations between all numerical variables
numerical_df = df.select_dtypes(include=[np.number])
corr = numerical_df.corr()
plt.figure(figsize=(14, 12))
sns.heatmap(corr, annot=True, cmap='coolwarm', fmt='.2f')
plt.title('Correlation Heatmap of All Metrics')
plt.show()

# Additional Exploratory Plots: Distribution Histograms for Key Metrics
key_cols = ['Task 1 Performance %', 'Task 2 Score', 'Task 3 Score', 'Task 1 Time', 'Task 2 Time', 'Task 3 Time']
fig, axes = plt.subplots(2, 3, figsize=(15, 10))
axes = axes.flatten()
for i, col in enumerate(key_cols):
    sns.histplot(data=df, x=col, hue='Group Label', kde=True, ax=axes[i])
    axes[i].set_title(f'Distribution of {col} by Group')
plt.tight_layout()
plt.show()