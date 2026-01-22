# User Study Statistics Evaluation Suite

The **User Study Statistics Evaluation Suite** is a collection of Python scripts designed to analyze and visualize data from user studies.  
It provides statistical testing and graphical representations of participants’ performance and workload (NASA-TLX) across multiple tasks.  

---

## Contents

- **`stat_test.py`**  
  Performs a **Mann–Whitney U test** on the results to assess statistical differences between groups.  

- **`tasks_performance_figure.py`**  
  Generates a figure illustrating participants’ performance across all three tasks.  

- **`tlx_results.py`**  
  Creates individual figures for each task, visualizing the **NASA-TLX workload** results.  

- **`tlx_stacked_results.py`**  
  Produces a single stacked figure that combines and compares the TLX results for all tasks.  

---

## Installation

Before running any scripts, make sure you have all required dependencies installed.  
From the project root directory, run:

```bash
pip install -r requirements.txt
```

## Usage
Each script can be run independently depending on the analysis or visualization you need.
```bash
python3 <script.py>
```
For example:
```bash
python3 stat_test.py
python3 tasks_performance_figure.py
```