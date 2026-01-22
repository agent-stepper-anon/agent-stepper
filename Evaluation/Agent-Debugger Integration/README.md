# Agent-Debugger Integration Evaluation Package

The **Agent-Debugger Integration Evaluation Package** contains resources for analyzing the integration of **AgentStepper** into multiple agents.  
It provides forked repositories, integration diffs, and tabulated results used to estimate the engineering effort required for integration.  

---

## Contents

- **Forked Repositories (as submodules)**  
  Run `git submodule update --init` to clone them. Includes modified versions of:  
  - **SWE-Agent**  
  - **RepairAgent**  
  - **ExecutionAgent**  
  Each fork contains the **AgentStepper integration** code.  

- **Integration Diffs**  
  Copies of the diffs before and after integration are included.  
  These diffs form the basis for measuring integration effort.  

- **`Agent Integration Changes Tabulation.md`**  
  A summary of the measured results after applying the defined evaluation process.  

---

## Replicating the Effort Statistics

To reproduce the **agent-integration effort statistics** (as reported in the thesis), follow these steps for each agent repository:

1. **Review the integration diff file (git diff <commit_before_integration>..<latest_commit> > integration.diff).**  
2. **Remove non-integration changes**, such as:  
   - Deleted redundant files  
   - `.gitignore` adjustments  
   - Other irrelevant modifications  
3. **Exclude cosmetic or readability-related changes**, including:  
   - Empty lines  
   - Added comments  
   - Debug messages  
4. **Ignore pure indentation changes.**  
5. **Count the remaining lines of change.**  
   These represent the effective lines of code required for integration.  
