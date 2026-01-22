<p align="center">
  <img src="AgentStepper UI/src/assets/AgentStepperLogo.svg" alt="Logo" height="200"/>
</p>

Welcome to the repository of **AgentStepper: Interactive Debugging of LLM Agents for Software Development**. This repository contains all artifacts generated pertaining to the thesis including software, documents, documentation, evaluation scripts, etc.

# Abstract
Large language model (LLM) agents are increasingly applied to software engineering tasks, yet their development and maintenance remain challenging, particularly due to difficulties in understanding agent behavior. Developers must reason about trajectories of LLM queries, tool calls, and code modifications, but current tools reveal little of this intermediate process in a comprehensible format. Consequently, diagnosing failures and understanding agent behavior remain major obstacles.

Drawing on parallels with conventional software development, we introduce AgentStepper, an interactive debugging approach for LLM agents that adapts established debugging practices to agent trajectories. AgentStepper records trajectories as structured conversations among the LLM, the agent program, and tools. It supports breakpoints, stepwise execution, and live editing of parameters, while automatically capturing and linking repository-level code changes. The interface follows familiar paradigms from chat applications, AgentSteppers, and IDEs.

Our evaluation shows that AgentStepper integrates with representative agents with modest effort and improves developers’ ability to interpret trajectories and identify bugs, thereby reducing workload and frustration compared to conventional tools.
# Repository Structure
```
.
├── AgentStepper API           # AgentStepper API package of AgentStepper
├── AgentStepper Core          # AgentStepper Core application of AgentStepper
├── AgentStepper UI            # AgentStepper User Interface website of AgentStepper
├── AgentStepper Thesis.pdf    # The AgentStepper thesis document
├── Documents                  # Documents relating to work notes, user study, etc.
├── Evaluation                 # Scripts and raw results from evaluation
├── Thesis                     # Latex source of thesis document
├── LICENSE
├── README.md                  # This document
├── run_debugger_core_only.sh  # AgentStepper Core only start script
├── run_debugger_ui_only.sh    # AgentStepper UI only start script
└── run_debugger.sh            # AgentStepper Core & UI start script
```
The `AgentStepper API` folder contains the source code of the AgentStepper API, which is the component of AgentStepper integrated into agents to instrument them.

The `AgentStepper Core` folder contains the source code of the AgentStepper Core. The core is the persistent component of AgentStepper to which agents connect when being debugged. It facilitates the debugging process and provides the user interface.

The `AgentStepper UI` folder contains the source code of AgentStepper's user interface, implemented as a Vue.js web application and served by the AgentStepper core.

The `Documents` folder contains various materials related to development and the user study. Examples include work notes, the user study script, legal documents, and similar items.

The `Evaluation` folder contains artifacts related to evaluating RQ1 (Agent-Debugger Integration) and RQ2 (Usability and Utility), specifically raw results, statistical analyses, and replication scripts.

The `Thesis` folder contains the LaTeX source code of the thesis document.

# AgentStepper Usage

Using AgentStepper is a two-step process: 1) integrating the AgentStepper API into an agent, and 2) starting the AgentStepper Core and UI.

## Starting the AgentStepper Core & UI

### Requirements
- **Python** 3.9.6+
- **pip** 25.2+
- **Docker** 28.0.1+ (installed and running)

### Deployment Options
Depending on where your agent runs, there are multiple options to start AgentStepper:

- **Local agent execution**: Run both **Core** and **UI** on the same machine.  
- **Remote agent execution**:  
  - Run **Core** on the remote server.  
  - Run **UI** locally.  
  - Use an SSH tunnel to connect the UI with the Core. Example:  
    ```bash
    ssh -L 4567:localhost:4567 user@server
    ```

### Scripts

#### 1. Run Core & UI Together
Use when the LLM agent is executing **locally**.  

```bash
./run_agentstepper.sh
````

This script will:

* Create and activate a **virtual environment**
* Install all required **Python dependencies**
* Build and launch a **Docker container** for the UI
* Start the **AgentStepper Core**
* Prompt for your **OpenAI API key** (required for event summarization)

#### 2. Run Core Only

Use when the LLM agent is executing **remotely**.

```bash
./run_agentstepper_core_only.sh
```

Run this on the **remote machine** with the agent.

#### 3. Run UI Only

Use when the LLM agent is executing **remotely**.

```bash
./run_agentstepper_ui_only.sh
```

Run this on your **local machine**, and connect to the remote Core using an SSH tunnel:

```bash
ssh -L 4567:localhost:4567 user@server
```

### Default Configuration

* Core listens on `localhost:8765`.
* Default summarization model is `gpt-5-nano`.
* Configuration can be changed either by editing `AgentStepper Core/default.conf` or by passing command-line arguments when starting the Core.

## Agent-Debugger Integration

To instrument an agent with AgentStepper, the AgentStepper API must first be installed. Afterwards, specific API calls can be inserted into the agent program's source code to enable instrumentation.

### 1. Install the AgentStepper API

It is essential to install the AgentStepper API in the same environment in which the agent program will run, so that the API methods are accessible. If the agent operates in the global Python environment, it is sufficient to run `python3 -m pip install -e "AgentStepper API"`. However, ensure that the correct Python version is used.

If the agent operates in a virtual environment, copy the AgentStepper API folder into the agent's code repository, activate the virtual environment, and then run `pip install -e "AgentStepper API"`.

### 2. AgentStepper API Usage
To use AgentStepper, the first instantiate and initialize the `AgentStepper` object, which establishes a connection with the debugger. To capture and debug LLM completions and tool invocations, wrap the corresponding code in begin and end breakpoint API calls. The example below illustrates using the API to instrument and debug an LLM agent.

```python
# my_agent.py
class MyAgent(Agent):
  def think(self) -> Action:
    prompt = self.get_next_prompt()
    
    prompt = self.debugger.begin_llm_query_breakpoint(prompt)
    response = self.llm.get_completion(prompt)
    response = self.debugger.end_llm_query_breakpoint(response)
    
    return self.response_to_action(response)
		
# main.py
def main():
  agent = MyAgent()
	
  with AgentStepper('MyAgent', 'localhost', 8765, 'agent_workspace')
as debugger:
    agent.debugger = debugger
		
    while not agent.is_done():
      action = agent.think()
      
      (action.name, action.args) = debugger.begin_tool_invocation_breakpoint(action.name, action.args)
      result = environment.execute(action)
      result = debugger.end_tool_invocation_breakpoint(result)
      
      agent.add_observation_to_history(result)
```

## AgentStepper API Reference
The `AgentStepper` class defines the interface through which an LLM agent interacts with the debugger. It provides the methods necessary to capture agent events, specifically LLM completions and tool invocations, that are enclosed between begin and end breakpoints according to the multiple API call approach described above. In addition to event handling, the API provides functionality for posting debug messages to the user interface and for committing agent workspace changes to version control.

### Methods

- `__init__(agent_name: str, address: str, port: int, workspace_path: Optional[str])`  
  Establishes a connection to the AgentStepper Core and initializes a new AgentStepper object.  
  - `agent_name`: identifies the agent as a whole  
  - `address` / `port`: specify the AgentStepper Core endpoint  
  - `workspace_path` *(optional)*: track changes if the agent edits a local project directory  

- `begin_llm_query_breakpoint(prompt: Union[str, Dict]) -> Union[str, Dict]`  
  Marks the beginning of an LLM query event. The method sends the query prompt to the debugger and halts execution if a breakpoint is triggered.  
  The user may modify the prompt in the user interface. If modified, the updated prompt is returned; otherwise, the original prompt is returned unchanged.  

- `end_llm_query_breakpoint(response: Union[str, Dict]) -> Union[str, Dict]`  
  Marks the completion of an LLM query event. The method transmits the LLM’s response to the debugger and halts execution if required.  
  The user may modify the response via the UI; the method then returns either the modified or the original response.  

- `begin_tool_invocation_breakpoint(tool: str, args: Dict) -> Tuple[str, Dict]`  
  Encapsulates the beginning of a tool invocation event. The tool identifier and its arguments are sent to the debugger, allowing inspection or modification before execution.  
  Returns the (potentially updated) tool identifier and argument dictionary.  

- `end_tool_invocation_breakpoint(results: Union[str, Dict]) -> Union[str, Dict]`  
  Marks the end of a tool invocation event. The results are provided to the debugger and may be altered in the UI before being returned to the agent.  

- `commit_agent_changes(commit_summary: str, commit_description: str) -> bool`  
  Commits the current state of the agent's workspace to its version control repository and synchronizes the commit with the core.
  - If no summary or description is supplied, they are generated automatically.  
  - Returns `True` if changes were committed, `False` otherwise.  

- `post_debug_message(message: str)`  
  Sends a textual message to the user interface. Useful for providing additional contextual information or debugging notes to the developer.  

