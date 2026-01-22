import pandas as pd
import numpy as np
from scipy.stats import mannwhitneyu

# Documentation:
# This script reads user study data from a CSV file and performs Mann-Whitney U tests
# to determine if there are significant differences between two groups (A and B) across
# specified metrics for three different data filters:
# 1. Overall (all data)
# 2. Without 'None' familiarity (exclude participants with 'None' familiarity)
# 3. Only Moderate and Advanced familiarity
#
# The Mann-Whitney U test is a non-parametric test used to compare differences between
# two independent groups when the data does not necessarily follow a normal distribution.
# It tests the null hypothesis that the distributions of both groups are equal.
#
# Process:
# 1. Read the CSV file using pandas, with ';' as the separator.
# 2. Clean the data:
#    - Replace commas in numeric columns with periods (to handle locale-specific decimals).
#    - Convert relevant columns to float or int as appropriate.
#    - Replace '#N/A' with NaN for missing values.
# 3. Define a function to perform analysis on a filtered DataFrame:
#    - Split into Group A and Group B.
#    - Compute sample sizes.
#    - For each metric, perform the Mann-Whitney U test if possible.
#    - Collect results in a DataFrame.
# 4. Perform the analysis for each of the three filters.
# 5. Generate and print a report with sections for each filter, including sample sizes and results tables.
#
# Notes:
# - Task 1 Performance is treated as a continuous variable (fraction between 0 and 1).
# - Task 2 and Task 3 Scores are binary (0 or 1).
# - NASA TLX parameters are ordinal scales (likely 1-7).
# - The test uses the two-sided alternative hypothesis.
# - If a group has no valid data for a metric, the test is skipped for that metric.
# - The test statistic used is the Mann-Whitney U statistic, which measures the difference
#   between the ranks of the two groups. The p-value indicates the probability of observing
#   the data (or more extreme) under the null hypothesis. A p-value < 0.05 typically indicates
#   statistical significance.

def perform_analysis(df_filtered):
    # Split into groups
    group_a = df_filtered[df_filtered['Group'] == 'A']
    group_b = df_filtered[df_filtered['Group'] == 'B']

    # Sample sizes
    total_size = len(df_filtered)
    a_size = len(group_a)
    b_size = len(group_b)

    # Metrics to test
    metrics = [
        'Task 1 Performance %',
        'Task 2 Score',
        'Task 3 Score',
        'Task 1 Mental Demand', 'Task 1 Temporal Demand', 'Task 1 Perceived Perf.', 'Task 1 Effort', 'Task 1 Frustration',
        'Task 2 Mental Demand', 'Task 2 Temporal Demand', 'Task 2 Perceived Perf.', 'Task 2 Effort', 'Task 2 Frustration',
        'Task 3 Mental Demand', 'Task 3 Temporal Demand', 'Task 3 Perceived Perf.', 'Task 3 Effort', 'Task 3 Frustration'
    ]

    # Perform Mann-Whitney U tests
    results = []
    for metric in metrics:
        a_values = group_a[metric].dropna()
        b_values = group_b[metric].dropna()
        if len(a_values) > 0 and len(b_values) > 0:
            stat, p_value = mannwhitneyu(a_values, b_values, alternative='two-sided')
            significant = 'X' if p_value < 0.05 else ''
            results.append({
                'Metric': metric,
                'U Statistic': stat,
                'p-Value': round(p_value, 4),
                'Significant Difference': significant
            })
        else:
            results.append({
                'Metric': metric,
                'U Statistic': np.nan,
                'p-Value': np.nan,
                'Significant Difference': ''
            })

    results_df = pd.DataFrame(results)
    return results_df, total_size, a_size, b_size

def main():
    # Step 1: Read the CSV file
    file_path = 'UserStudyRawResults.csv'
    df = pd.read_csv(file_path, sep=';')

    # Step 2: Clean the data
    # Replace ',' with '.' in columns that may have decimal commas
    decimal_columns = ['Task 1 Performance %', 'Task 1 Time', 'Task 2 Time', 'Task 3 Time']
    for col in decimal_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '.').replace('#N/A', np.nan).astype(float)

    # Replace '#N/A' with NaN in all columns
    df = df.replace('#N/A', np.nan)

    # Ensure score columns are float (though binary, for consistency)
    score_columns = [
        'Task 1 Mental Demand', 'Task 1 Temporal Demand', 'Task 1 Perceived Perf.', 'Task 1 Effort', 'Task 1 Frustration',
        'Task 2 Mental Demand', 'Task 2 Temporal Demand', 'Task 2 Perceived Perf.', 'Task 2 Effort', 'Task 2 Frustration',
        'Task 3 Mental Demand', 'Task 3 Temporal Demand', 'Task 3 Perceived Perf.', 'Task 3 Effort', 'Task 3 Frustration',
        'Task 2 Score', 'Task 3 Score'
    ]
    for col in score_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Step 3: Perform analyses for each section

    # Section 1: Overall Results
    df_overall = df.copy()
    results_overall, total_overall, a_overall, b_overall = perform_analysis(df_overall)

    # Section 2: Results Without No Familiarity
    df_without_none = df[df['Familiarity Level'].isin(['Basic', 'Moderate', 'Advanced'])]
    results_without_none, total_without_none, a_without_none, b_without_none = perform_analysis(df_without_none)

    # Section 3: Results With Moderate and Advanced Familiarity
    df_moderate_advanced = df[df['Familiarity Level'].isin(['Moderate', 'Advanced'])]
    results_moderate_advanced, total_moderate_advanced, a_moderate_advanced, b_moderate_advanced = perform_analysis(df_moderate_advanced)

    # Step 4: Generate report
    report = "Mann-Whitney U Test Results Report\n"
    report += "=================================\n"
    report += "This report presents the results of Mann-Whitney U tests comparing Group A and Group B for three data filters.\n"
    report += "The test statistic used is the Mann-Whitney U statistic, which ranks all observations from both groups\n"
    report += "and calculates the sum of ranks for the smaller group (adjusted for ties). The p-value is calculated\n"
    report += "using the exact distribution for small samples or an approximation for larger ones.\n"
    report += "A p-value < 0.05 indicates a statistically significant difference between the groups.\n\n"

    # Section 1
    report += "1. Overall Results\n"
    report += f"Sample sizes: Total: {total_overall}, Group A: {a_overall}, Group B: {b_overall}\n"
    report += "Results Table:\n"
    report += results_overall.to_string(index=False) + "\n\n"

    # Section 2
    report += "2. Results Without No Familiarity\n"
    report += f"Sample sizes: Total: {total_without_none}, Group A: {a_without_none}, Group B: {b_without_none}\n"
    report += "Results Table:\n"
    report += results_without_none.to_string(index=False) + "\n\n"

    # Section 3
    report += "3. Results With Moderate and Advanced Familiarity\n"
    report += f"Sample sizes: Total: {total_moderate_advanced}, Group A: {a_moderate_advanced}, Group B: {b_moderate_advanced}\n"
    report += "Results Table:\n"
    report += results_moderate_advanced.to_string(index=False) + "\n\n"

    report += "Notes:\n"
    report += "- 'X' in the Significant Difference column indicates a p-value < 0.05.\n"
    report += "- NaN values indicate that the test was skipped due to insufficient data.\n"

    print(report)

if __name__ == "__main__":
    main()