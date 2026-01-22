# Usability and Utility User Study Evaluation Package

The **Usability and Utility User Study Evaluation Package** provides all necessary resources for analyzing, reproducing, and conducting user studies.
It includes statistical evaluation scripts, participant reports, and a ready-to-use study session package with all required materials.

---

## Contents

- **`Statistics/`**  
  The **Statistical Evaluation Suite**, containing Python scripts for performing statistical analyses and generating visualizations of user study results.
  See the [Statistics README](Statistics/README.md) for details.

- **`Participants Report Cards.pdf`**  
  A compiled report of all participants’ graded answers collected during the study.
  Useful for reviewing individual performance and qualitative feedback.

- **`User Study Session Package.zip`**  
  A comprehensive package for running a full user study session. It includes:  
  - All **task descriptions** and supporting materials.
  - **Agent trajectories** in both raw format and **Agent Debugger export format**.
  - A **session script** that automatically launches tasks in the correct order and with the correct tools based on group assignment.
  - A **snapshot of the Agent Debugger** as it was at the time of the study, ensuring compatibility with the exported trajectories.

  ⚠️ **Important note:** Later versions of the Agent Debugger—specifically all **AgentStepper** versions—are not compatible with these exports.
  For reproducibility, always use the included snapshot.

---

## Usage

- Use the **Statistics suite** for data analysis and figure generation.
- Refer to **Participants Report Cards.pdf** to review participants’ results.
- Extract **User Study Session Package.zip** to conduct or replicate the user study in its original form.