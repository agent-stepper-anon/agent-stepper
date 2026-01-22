# SWE-Agent
Stats:
- 3 files modified
- 42 additions (without indentation)
#### /sweagent/agent/agents.py
Stats:
- 25 additions
```diff
@@ -56,6 +56,8 @@ from sweagent.utils.jinja_warnings import _warn_probably_wrong_jinja_syntax
 from sweagent.utils.log import get_logger
 from sweagent.utils.patch_formatter import PatchFormatter
 
+from agentstepper.api.debugger import AgentStepper
+from sweagent.run.hooks.apply_patch import SaveApplyPatchHook
 
 class TemplateConfig(BaseModel):
     """This configuration is used to define almost all message templates that are
@@ -222,6 +224,8 @@ EXIT_FORFEIT_TOKEN = "###SWE-AGENT-EXIT-FORFEIT###"
 
 
 class AbstractAgent:
+    debugger: AgentStepper
     def __init__(self, *args, **kwargs):
         model: AbstractModel
         replay_config: BaseModel | None
@@ -1045,9 +1049,17 @@ class DefaultAgent(AbstractAgent):
             if output.get("tool_calls") is not None:
                 step.tool_call_ids = [call["id"] for call in output["tool_calls"]]
                 step.tool_calls = output["tool_calls"]
+            if self.debugger: (step.action, step.tool_calls) = self.debugger.begin_tool_invocation_breakpoint(step.action.strip(), step.tool_calls)
             self.logger.info(f"💭 THOUGHT\n{step.thought}\n\n🎬 ACTION\n{step.action.strip()}")
             self._chook.on_actions_generated(step=step)
-            return self.handle_action(step)
+            try:
+                result = self.handle_action(step)
+                if self.debugger: result.observation = self.debugger.end_tool_invocation_breakpoint(result.observation)
+                return result
+            except Exception as e:
+                self.debugger.end_tool_invocation_breakpoint(f'Tool call failed with {type(e).__name__}: {getattr(e, "message", "")}')
+                if isinstance(e, ConnectionError): raise # Discard changes if there's any issue.
         except Exception as e:
             if step.action == step.thought == "":
                 # Probably the parsing failed/no action included. Let's still fill in thought
@@ -1256,6 +1278,26 @@ class DefaultAgent(AbstractAgent):
         self.info["model_stats"] = self.model.stats.model_dump()
 
         self.add_step_to_trajectory(step_output)
+        # Apply patch to local git repository after every step
+        submit_output = self.handle_action(StepOutput(thought='I need to submit a patch.', action='submit'))
+        submit_output = self.handle_action(StepOutput(thought='I need to submit a patch.', action='submit'))
+        if submit_output.submission:
+            submission_info = AgentRunResult(info=AgentInfo(submission=submit_output.submission, exit_status='submitted'), trajectory=self.get_trajectory_data()["trajectory"])
+            hook = SaveApplyPatchHook(apply_patch_locally=True)
+            hook.on_instance_start(index=0, env=self._env, problem_statement=self._problem_statement)
+            hook._output_dir = self._output_dir
+            hook.on_instance_completed(result=submission_info)
+            self.debugger.commit_agent_changes()
+            ## Commit changes to repo in virtual environment, so that the next patch will be a delta of each change.
+            self._env.communicate(
+                input="git add -A && git config user.email \"agent@sweagent.com\" && git config user.name \"SWE Agent\" && git commit -m \"Commit agent changes.\"",
+                timeout=self.tools.config.execution_timeout,
+                check="raise" if self._always_require_zero_exit_code else "ignore",
+            )
 
         self._chook.on_step_done(step=step_output, info=self.info)
         return step_output
@@ -1275,6 +1317,7 @@ class DefaultAgent(AbstractAgent):
             traj_dir: Directory to save the trajectory to
         """
         self.setup(env=env, problem_statement=problem_statement, output_dir=output_dir)
+        self._output_dir = output_dir # Needed for saving intermediate patches
 
         # Run action/observation loop
         self._chook.on_run_start()
```
#### sweagent/agent/models.py
Stats:
- 12 additions
```diff
@@ -779,6 +779,12 @@ class LiteLLMModel(AbstractModel):
 
     def query(self, history: History, n: int = 1, temperature: float | None = None) -> list[dict] | dict:
         messages = self._history_to_messages(history)
+        if self.debugger:
+            try:
+                messages = self.debugger.begin_llm_query_breakpoint({'messages': messages})['messages']
+            except Exception as e:
+                pass # Discard changes if there's any issue.
 
         def retry_warning(retry_state: RetryCallState):
             exception_info = ""
@@ -820,7 +826,15 @@ class LiteLLMModel(AbstractModel):
             with attempt:
                 result = self._query(messages, n=n, temperature=temperature)
         if n is None or n == 1:
+            if self.debugger:
+                return self.debugger.end_llm_query_breakpoint(result[0])
             return result[0]
+        if self.debugger:
+            try:
+                return self.debugger.end_llm_query_breakpoint({'results': result})['results']
+            except Exception as e:
+                pass # Discard changes if there's any issue.
         return result
 
     def _history_to_messages(
```
#### /sweagent/run/run_single.py
Stats:
- 5 additions
```diff
@@ -51,6 +51,7 @@ from sweagent.run.hooks.open_pr import OpenPRConfig, OpenPRHook
 from sweagent.utils.config import load_environment_variables
 from sweagent.utils.log import add_file_handler, get_logger
 
+from agentstepper.api.debugger import AgentStepper
 
 class RunSingleActionConfig(BaseModel):
     """Run real-life actions (opening PRs, etc.) if we can solve the issue."""
@@ -195,16 +196,21 @@ class RunSingle:
         output_dir.mkdir(parents=True, exist_ok=True)
         if self.agent.replay_config is not None:  # type: ignore[attr-defined]
             (output_dir / "config.yaml").write_text(yaml.dump(self.agent.replay_config.model_dump_json(), indent=2))  # type: ignore[attr-defined]
-        result = self.agent.run(
-            problem_statement=self.problem_statement,
-            env=self.env,
-            output_dir=output_dir,
-        )
-        self._chooks.on_instance_completed(result=result)
-        self.logger.info("Done")
-        self._chooks.on_end()
-        save_predictions(self.output_dir, self.problem_statement.id, result)
-        self.env.close()
+        
+        debugger: AgentStepper
+        with AgentStepper('SWE-Agent', 'localhost', 8765, 'SWE-Workspace/finance_tracker') as debugger:
+            self.agent.debugger = debugger
+            self.agent.model.debugger = debugger
+            result = self.agent.run(
+                problem_statement=self.problem_statement,
+                env=self.env,
+                output_dir=output_dir,
+            )
+            self._chooks.on_instance_completed(result=result)
+            self.logger.info("Done")
+            self._chooks.on_end()
+            save_predictions(self.output_dir, self.problem_statement.id, result)
+            self.env.close()
 
 
 def run_from_config(config: RunSingleConfig):
```
---
# RepairAgent
Stats:
- 38 additions
- 1 deletion
Total:
- 39 changes (without indentation)
- 5 files modified
#### /.devcontainer/devcontainer.json
Stats:
- 1 addition
```diff
@@ -10,6 +10,7 @@
 			"version": "3.10"
 		}
 	},
+	"runArgs": ["--network=host"],
 
 	// Features to add to the dev container. More info: https://containers.dev/features.
 	// "features": {},
```
#### /repair_agent/autogpt/agents/base.py
Stats:
- 12 additions
- 1 deletion
```diff
@@ -20,6 +20,8 @@ from autogpt.prompts.prompt import DEFAULT_TRIGGERING_PROMPT
 from autogpt.json_utils.utilities import extract_dict_from_response
 from autogpt.commands.defects4j_static import get_info, run_tests, query_for_fix, query_for_commands, extract_command, execute_command, create_fix_template
 
+from agentstepper.api.debugger import AgentStepper
 CommandName = str
 CommandArgs = dict[str, str]
 AgentThoughts = dict[str, Any]
@@ -28,6 +30,7 @@ class BaseAgent(metaclass=ABCMeta):
     """Base class for all Auto-GPT agents."""
 
     ThoughtProcessID = Literal["one-shot"]
+    debugger: AgentStepper
 
     def __init__(
         self,
@@ -944,6 +947,13 @@ please use the indicated format and produce a list, like this:
                 query = self.construct_fix_query()
                 suggested_fixes = query_for_fix(query, )
                 self.save_to_json(os.path.join("experimental_setups", exps[-1], "external_fixes", "external_fixes_{}_{}.json".format(project_name, bug_index)), json.loads(suggested_fixes))
+        if self.debugger:
+            modifiedMessages = self.debugger.begin_llm_query_breakpoint({'MessageSequence': prompt.raw()})
+            try:
+                prompt.setFromDictList(modifiedMessages['MessageSequence'])
+            except Exception:
+                pass # Don't apply changes if there's a problem with parsing them.
 
         raw_response = create_chat_completion(
             prompt,
@@ -979,8 +989,11 @@ please use the indicated format and produce a list, like this:
                     raw_response = new_response
             self.cycle_count += 1
 
-            return self.on_response(raw_response, thought_process_id, prompt, instruction)
         except SyntaxError as e:
+            pass
+        finally:
+            if self.debugger:
+                raw_response.content = self.debugger.end_llm_query_breakpoint(raw_response.content)
             return self.on_response(raw_response, thought_process_id, prompt, instruction)
         
     @abstractmethod
```
#### /repair_agent/autogpt/app/main.py
Stats:
- 6 additions
```diff
@@ -33,6 +33,8 @@ from autogpt.speech import say_text
 from autogpt.workspace import Workspace
 from scripts.install_plugin_deps import install_plugin_dependencies
 
+from agentstepper.api.debugger import AgentStepper
 
 def run_auto_gpt(
     continuous: bool,
@@ -220,113 +222,120 @@ def run_interaction_loop(
         config.continuous_mode, config.continuous_limit
     )
     spinner = Spinner("Thinking...", plain_output=config.plain_output)
-
-    def graceful_agent_interrupt(signum: int, frame: Optional[FrameType]) -> None:
-        nonlocal cycle_budget, cycles_remaining, spinner
-        if cycles_remaining in [0, 1, math.inf]:
-            logger.typewriter_log(
-                "Interrupt signal received. Stopping continuous command execution "
-                "immediately.",
-                Fore.RED,
-            )
-            sys.exit()
-        else:
-            restart_spinner = spinner.running
-            if spinner.running:
-                spinner.stop()
-
-            logger.typewriter_log(
-                "Interrupt signal received. Stopping continuous command execution.",
-                Fore.RED,
-            )
-            cycles_remaining = 1
-            if restart_spinner:
-                spinner.start()
-
-    # Set up an interrupt signal for the agent.
-    signal.signal(signal.SIGINT, graceful_agent_interrupt)
-
-    #########################
-    # Application Main Loop #
-    #########################
-
-    while cycles_remaining > 0:
-        logger.debug(f"Cycle budget: {cycle_budget}; remaining: {cycles_remaining}")
-
-        ########
-        # Plan #
-        ########
-        # Have the agent determine the next action to take.
-        with spinner:
-            command_name, command_args, assistant_reply_dict = agent.think()
-
-        ###############
-        # Update User #
-        ###############
-        # Print the assistant's thoughts and the next command to the user.
-        update_user(config, ai_config, command_name, command_args, assistant_reply_dict)
-
-        ##################
-        # Get user input #
-        ##################
-        if cycles_remaining == 1:  # Last cycle
-            user_feedback, user_input, new_cycles_remaining = get_user_feedback(
-                config,
-                ai_config,
-            )
-
-            if user_feedback == UserFeedback.AUTHORIZE:
-                if new_cycles_remaining is not None:
-                    # Case 1: User is altering the cycle budget.
-                    if cycle_budget > 1:
-                        cycle_budget = new_cycles_remaining + 1
-                    # Case 2: User is running iteratively and
-                    #   has initiated a one-time continuous cycle
-                    cycles_remaining = new_cycles_remaining + 1
-                else:
-                    # Case 1: Continuous iteration was interrupted -> resume
-                    if cycle_budget > 1:
-                        logger.typewriter_log(
-                            "RESUMING CONTINUOUS EXECUTION: ",
-                            Fore.MAGENTA,
-                            f"The cycle budget is {cycle_budget}.",
-                        )
-                    # Case 2: The agent used up its cycle budget -> reset
-                    cycles_remaining = cycle_budget + 1
+    debugger: AgentStepper
+    with AgentStepper('RepairAgent', 'localhost', 8765, 'auto_gpt_workspace/compress_16_buggy') as debugger:
+        agent.debugger = debugger
+        def graceful_agent_interrupt(signum: int, frame: Optional[FrameType]) -> None:
+            nonlocal cycle_budget, cycles_remaining, spinner
+            if cycles_remaining in [0, 1, math.inf]:
                 logger.typewriter_log(
-                    "-=-=-=-=-=-=-= COMMAND AUTHORISED BY USER -=-=-=-=-=-=-=",
-                    Fore.MAGENTA,
-                    "",
+                    "Interrupt signal received. Stopping continuous command execution "
+                    "immediately.",
+                    Fore.RED,
                 )
-            elif user_feedback == UserFeedback.EXIT:
-                logger.typewriter_log("Exiting...", Fore.YELLOW)
-                exit()
-            else:  # user_feedback == UserFeedback.TEXT
-                command_name = "human_feedback"
-        else:
-            user_input = None
-            # First log new-line so user can differentiate sections better in console
-            logger.typewriter_log("\n")
-            if cycles_remaining != math.inf:
-                # Print authorized commands left value
+                sys.exit()
+            else:
+                restart_spinner = spinner.running
+                if spinner.running:
+                    spinner.stop()
+
                 logger.typewriter_log(
-                    "AUTHORISED COMMANDS LEFT: ", Fore.CYAN, f"{cycles_remaining}"
+                    "Interrupt signal received. Stopping continuous command execution.",
+                    Fore.RED,
+                )
+                cycles_remaining = 1
+                if restart_spinner:
+                    spinner.start()
+
+        # Set up an interrupt signal for the agent.
+        signal.signal(signal.SIGINT, graceful_agent_interrupt)
+
+        #########################
+        # Application Main Loop #
+        #########################
+
+        while cycles_remaining > 0:
+            logger.debug(f"Cycle budget: {cycle_budget}; remaining: {cycles_remaining}")
+
+            ########
+            # Plan #
+            ########
+            # Have the agent determine the next action to take.
+            with spinner:
+                command_name, command_args, assistant_reply_dict = agent.think()
+
+            ###############
+            # Update User #
+            ###############
+            # Print the assistant's thoughts and the next command to the user.
+            update_user(config, ai_config, command_name, command_args, assistant_reply_dict)
+
+            ##################
+            # Get user input #
+            ##################
+            if cycles_remaining == 1:  # Last cycle
+                user_feedback, user_input, new_cycles_remaining = get_user_feedback(
+                    config,
+                    ai_config,
                 )
 
-        ###################
-        # Execute Command #
-        ###################
-        # Decrement the cycle counter first to reduce the likelihood of a SIGINT
-        # happening during command execution, setting the cycles remaining to 1,
-        # and then having the decrement set it to 0, exiting the application.
-        if command_name != "human_feedback":
-            cycles_remaining -= 1
-        result = agent.execute(command_name, command_args, user_input)
-
-        if result is not None:
-            logger.typewriter_log("SYSTEM: ", Fore.YELLOW, result)
-        else:
-            logger.typewriter_log("SYSTEM: ", Fore.YELLOW, "Unable to execute command")
+                if user_feedback == UserFeedback.AUTHORIZE:
+                    if new_cycles_remaining is not None:
+                        # Case 1: User is altering the cycle budget.
+                        if cycle_budget > 1:
+                            cycle_budget = new_cycles_remaining + 1
+                        # Case 2: User is running iteratively and
+                        #   has initiated a one-time continuous cycle
+                        cycles_remaining = new_cycles_remaining + 1
+                    else:
+                        # Case 1: Continuous iteration was interrupted -> resume
+                        if cycle_budget > 1:
+                            logger.typewriter_log(
+                                "RESUMING CONTINUOUS EXECUTION: ",
+                                Fore.MAGENTA,
+                                f"The cycle budget is {cycle_budget}.",
+                            )
+                        # Case 2: The agent used up its cycle budget -> reset
+                        cycles_remaining = cycle_budget + 1
+                    logger.typewriter_log(
+                        "-=-=-=-=-=-=-= COMMAND AUTHORISED BY USER -=-=-=-=-=-=-=",
+                        Fore.MAGENTA,
+                        "",
+                    )
+                elif user_feedback == UserFeedback.EXIT:
+                    logger.typewriter_log("Exiting...", Fore.YELLOW)
+                    exit()
+                else:  # user_feedback == UserFeedback.TEXT
+                    command_name = "human_feedback"
+            else:
+                user_input = None
+                # First log new-line so user can differentiate sections better in console
+                logger.typewriter_log("\n")
+                if cycles_remaining != math.inf:
+                    # Print authorized commands left value
+                    logger.typewriter_log(
+                        "AUTHORISED COMMANDS LEFT: ", Fore.CYAN, f"{cycles_remaining}"
+                    )
+
+            ###################
+            # Execute Command #
+            ###################
+            # Decrement the cycle counter first to reduce the likelihood of a SIGINT
+            # happening during command execution, setting the cycles remaining to 1,
+            # and then having the decrement set it to 0, exiting the application.
+            if command_name != "human_feedback":
+                cycles_remaining -= 1
+                
+            if command_name: (command_name, command_args) = debugger.begin_tool_invocation_breakpoint(command_name, command_args)
+            result = agent.execute(command_name, command_args, user_input)
+            if command_name: result = debugger.end_tool_invocation_breakpoint(result)
+            
+            if result is not None:
+                logger.typewriter_log("SYSTEM: ", Fore.YELLOW, result)
+            else:
+                logger.typewriter_log("SYSTEM: ", Fore.YELLOW, "Unable to execute command")
 
 
 def update_user(
```
#### /repair_agent/autogpt/commands/defects4j.py
Stats:
- 6 additions
```diff
@@ -101,6 +101,9 @@ def create_deletion_template(project_name, bug_number):
 
 
 def run_checkout(project_name: str, bug_index:int, agent: Agent):
+    if agent.debugger:
+        agent.debugger.commit_agent_changes()
     cmd_temp = "defects4j checkout -p {} -v {}b -w {}"
     folder_name = "_".join([project_name.lower(), str(bug_index), "buggy"])
     if os.path.exists(os.path.join("auto_gpt_workspace", folder_name)):
@@ -131,6 +134,10 @@ def run_checkout(project_name: str, bug_index:int, agent: Agent):
             cwd=agent.config.workspace_path,
             shell=True
         )
+        if agent.debugger:
+            agent.debugger.commit_agent_changes(commit_summary='Reverted agent changes.')   
         if result.returncode == 0:
             return "The changed files were restored to their original content"
         else:
@@ -712,6 +719,11 @@ def execute_write_range(project_name, bug_index, changes_dicts, agent):
         change_dict["file_name"] = os.path.join(project_dir,filepath)
     
         apply_changes(change_dict)
+    if agent.debugger:
+        agent.debugger.commit_agent_changes():
 
     run_ret = run_defects4j_tests(project_name, bug_index, agent)
     return "Lines written successfully, the result of running test cases on the modified code is the following:\n" + run_ret
```
#### /repair_agent/autogpt/llm/base.py
- 13 additions
```diff
@@ -42,6 +42,17 @@ class Message:
     def raw(self) -> MessageDict:
         return {"role": self.role, "content": self.content}
 
+    @classmethod
+    def fromDict(cls, dict: "MessageDict", type: Optional["MessageType"] = None) -> "Message":
+        return cls(
+            role=dict["role"],
+            content=dict["content"],
+            type=type
+        )
+
+    @classmethod
+    def fromDictList(cls, data_list: list["MessageDict"], type: Optional["MessageType"] = None) -> list["Message"]:
+        return [cls.fromDict(data, type=type) for data in data_list]
 
 @dataclass
 class ModelInfo:
@@ -131,6 +142,10 @@ class ChatSequence:
     def insert(self, index: int, *messages: Message):
         for message in reversed(messages):
             self.messages.insert(index, message)
+            
+    def setFromDictList(self, messages: list[MessageDict]):
+        self.messages.clear()
+        self.extend(Message.fromDictList(messages))
 
     @classmethod
     def for_model(
```
---
# ExecutionAgent
Stats:
- 4 files modified
- 39 additions
#### /.devcontainer/devcontainer.json
Stats:
- 1 addition
```diff
@@ -11,6 +11,7 @@
     },
 
     "postCreateCommand": "chmod +x .devcontainer/install_python.sh && sudo .devcontainer/install_python.sh",
+    "runArgs": ["--network=host"],
 
     "customizations": {
         "vscode": {
```
#### /autogpt/agents/base.py
Stats:
- 10 additions
```diff
@@ -30,6 +30,8 @@ from autogpt.commands.docker_helpers_static import start_container, remove_ansi_
 from autogpt.commands.search_documentation import search_install_doc
 from autogpt.commands.commands_summary_helper import condense_history
 
+from agentstepper.api.debugger import AgentStepper
 CommandName = str
 CommandArgs = dict[str, str]
 AgentThoughts = dict[str, Any]
@@ -38,6 +40,7 @@ class BaseAgent(metaclass=ABCMeta):
     """Base class for all Auto-GPT agents."""
 
     ThoughtProcessID = Literal["one-shot"]
+    debugger: AgentStepper
 
     def __init__(
         self,
@@ -483,7 +486,14 @@ class BaseAgent(metaclass=ABCMeta):
         
         with open(os.path.join("experimental_setups", self.exp_number, "logs", "cycles_list_{}".format(self.project_path.replace("/", ""))), "a+") as patf:
             patf.write(self.cycle_type+"\n")
         # 2) Query the LLM normally
+        if self.debugger:
+            modifiedMessages = self.debugger.begin_llm_query_breakpoint({'MessageSequence': prompt.raw()})
+            try:
+                prompt.setFromDictList(modifiedMessages['MessageSequence'])
+            except Exception:
+                pass # Don't apply changes if there's a problem with parsing them.
         raw_response = create_chat_completion(
             prompt,
             self.config,
@@ -491,6 +501,9 @@ class BaseAgent(metaclass=ABCMeta):
             if self.config.openai_functions
             else None,
         )
+        if self.debugger:
+            raw_response.content = self.debugger.end_llm_query_breakpoint(raw_response.content)
 
         # 3) Try to parse the JSON out of the LLM’s reply, then check repetition
         try:
```
#### /autogpt/app/main.py
Stats:
- 15 additions
```diff
@@ -39,6 +39,9 @@ from scripts.install_plugin_deps import install_plugin_dependencies
 from autogpt.commands.docker_helpers_static import stop_and_remove
 from autogpt.commands.commands_summary_helper import condense_history
 
+from agentstepper.api.debugger import AgentStepper
+import git
 def run_auto_gpt(
     continuous: bool,
     continuous_limit: int,
@@ -224,189 +227,203 @@ def run_interaction_loop(
         config.continuous_mode, config.continuous_limit
     )
     spinner = Spinner("Thinking...", plain_output=config.plain_output)
-
-    def graceful_agent_interrupt(signum: int, frame: Optional[FrameType]) -> None:
-        nonlocal cycle_budget, cycles_remaining, spinner
-        if cycles_remaining in [0, 1, math.inf]:
-            logger.typewriter_log(
-                "Interrupt signal received. Stopping continuous command execution "
-                "immediately.",
-                Fore.RED,
-            )
-            sys.exit()
-        else:
-            restart_spinner = spinner.running
-            if spinner.running:
-                spinner.stop()
-
-            logger.typewriter_log(
-                "Interrupt signal received. Stopping continuous command execution.",
-                Fore.RED,
-            )
-            cycles_remaining = 1
-            if restart_spinner:
-                spinner.start()
-
-    # Set up an interrupt signal for the agent.
-    signal.signal(signal.SIGINT, graceful_agent_interrupt)
-
-    #########################
-    # Application Main Loop #
-    #########################
-
-
-    ## create log file
-    project_path = agent.project_path
-    current_ts = time.time()
-    parsable_log_file = "parsable_logs/{}".format(project_path+str(current_ts)) + ".json"
     
-    with open(parsable_log_file, "w") as plf:
-        json.dump({
-            "project": project_path,
-            "language": agent.hyperparams["language"],
-            "ExecutionAgent_attempt": []
-        }, plf)
-
-    while cycles_remaining > 0:
-        logger.debug(f"Cycle budget: {cycle_budget}; remaining: {cycles_remaining}")
-        #logger.info("XXXXXXXXXXXXXXXXXXX {} XXXXXXXXXXXXXXXXXXXX".format(agent.cycle_type))
-        if agent.cycle_type != "CMD":
-            #agent.think()
-            agent.cycle_type = "CMD"
-            #logger.info(" YYYYYYYYYYYYYYYYY SUMMARY CYCLE EXECUTED YYYYYYYYYYYYYYYYYYYY")
-            logger.info(str(agent.summary_result))
-            continue
-        ########
-        # Plan #
-        ########
-        # Have the agent determine the next action to take.
-        with spinner:
-            command_name, command_args, assistant_reply_dict = agent.think()
-
-        ###############
-        # Update User #
-        ###############
-        # Print the assistant's thoughts and the next command to the user.
-        update_user(config, ai_config, command_name, command_args, assistant_reply_dict)
-
-        ##################
-        # Get user input #
-        ##################
-        if cycles_remaining == 1:  # Last cycle
-            if not agent.keep_container and agent.container:
-                stop_and_remove(agent.container)
-                os.system("docker system prune -af")
-            exit()
-            user_feedback, user_input, new_cycles_remaining = get_user_feedback(
-                config,
-                ai_config,
-            )
+    debugger: AgentStepper
+    repository_path = 'execution_agent_workspace/gson'
+    if os.path.exists(os.path.join(repository_path, '.git')):
+        repo = git.Repo(repository_path)
+        if repo.is_dirty(untracked_files=True):
+            repo.git.add(all=True)
+            repo.git.commit('-m', 'Prepare repository for ExecutionAgent')
+    with AgentStepper('ExecutionAgent', 'localhost', 8765, repository_path) as debugger:
+        agent.debugger = debugger
 
-            if user_feedback == UserFeedback.AUTHORIZE:
-                if new_cycles_remaining is not None:
-                    # Case 1: User is altering the cycle budget.
-                    if cycle_budget > 1:
-                        cycle_budget = new_cycles_remaining + 1
-                    # Case 2: User is running iteratively and
-                    #   has initiated a one-time continuous cycle
-                    cycles_remaining = new_cycles_remaining + 1
-                else:
-                    # Case 1: Continuous iteration was interrupted -> resume
-                    if cycle_budget > 1:
-                        logger.typewriter_log(
-                            "RESUMING CONTINUOUS EXECUTION: ",
-                            Fore.MAGENTA,
-                            f"The cycle budget is {cycle_budget}.",
-                        )
-                    # Case 2: The agent used up its cycle budget -> reset
-                    cycles_remaining = cycle_budget + 1
+        def graceful_agent_interrupt(signum: int, frame: Optional[FrameType]) -> None:
+            nonlocal cycle_budget, cycles_remaining, spinner
+            if cycles_remaining in [0, 1, math.inf]:
                 logger.typewriter_log(
-                    "-=-=-=-=-=-=-= COMMAND AUTHORISED BY USER -=-=-=-=-=-=-=",
-                    Fore.MAGENTA,
-                    "",
+                    "Interrupt signal received. Stopping continuous command execution "
+                    "immediately.",
+                    Fore.RED,
                 )
-            elif user_feedback == UserFeedback.EXIT:
-                logger.typewriter_log("Exiting...", Fore.YELLOW)
-                exit()
-            else:  # user_feedback == UserFeedback.TEXT
-                command_name = "human_feedback"
-        else:
-            user_input = None
-            # First log new-line so user can differentiate sections better in console
-            logger.typewriter_log("\n")
-            if cycles_remaining != math.inf:
-                # Print authorized commands left value
+                sys.exit()
+            else:
+                restart_spinner = spinner.running
+                if spinner.running:
+                    spinner.stop()
+
                 logger.typewriter_log(
-                    "AUTHORISED COMMANDS LEFT: ", Fore.CYAN, f"{cycles_remaining}"
+                    "Interrupt signal received. Stopping continuous command execution.",
+                    Fore.RED,
+                )
+                cycles_remaining = 1
+                if restart_spinner:
+                    spinner.start()
+
+        # Set up an interrupt signal for the agent.
+        signal.signal(signal.SIGINT, graceful_agent_interrupt)
+
+        #########################
+        # Application Main Loop #
+        #########################
+
+
+        ## create log file
+        project_path = agent.project_path
+        current_ts = time.time()
+        parsable_log_file = "parsable_logs/{}".format(project_path+str(current_ts)) + ".json"
+        
+        with open(parsable_log_file, "w") as plf:
+            json.dump({
+                "project": project_path,
+                "language": agent.hyperparams["language"],
+                "ExecutionAgent_attempt": []
+            }, plf)
+
+        while cycles_remaining > 0:
+            logger.debug(f"Cycle budget: {cycle_budget}; remaining: {cycles_remaining}")
+            #logger.info("XXXXXXXXXXXXXXXXXXX {} XXXXXXXXXXXXXXXXXXXX".format(agent.cycle_type))
+            if agent.cycle_type != "CMD":
+                #agent.think()
+                agent.cycle_type = "CMD"
+                #logger.info(" YYYYYYYYYYYYYYYYY SUMMARY CYCLE EXECUTED YYYYYYYYYYYYYYYYYYYY")
+                logger.info(str(agent.summary_result))
+                continue
+            ########
+            # Plan #
+            ########
+            # Have the agent determine the next action to take.
+            with spinner:
+                command_name, command_args, assistant_reply_dict = agent.think()
+
+            ###############
+            # Update User #
+            ###############
+            # Print the assistant's thoughts and the next command to the user.
+            update_user(config, ai_config, command_name, command_args, assistant_reply_dict)
+
+            ##################
+            # Get user input #
+            ##################
+            if cycles_remaining == 1:  # Last cycle
+                if not agent.keep_container and agent.container:
+                    stop_and_remove(agent.container)
+                    os.system("docker system prune -af")
+                exit()
+                user_feedback, user_input, new_cycles_remaining = get_user_feedback(
+                    config,
+                    ai_config,
                 )
 
-        ###################
-        # Execute Command #
-        ###################
-        # Decrement the cycle counter first to reduce the likelihood of a SIGINT
-        # happening during command execution, setting the cycles remaining to 1,
-        # and then having the decrement set it to 0, exiting the application.
-        agent.left_commands = cycles_remaining
-        if agent.max_budget == -1:
-            agent.max_budget = cycles_remaining
-        if command_name != "human_feedback":
-            cycles_remaining -= 1
-        if agent.cycle_type == "CMD":
-            if command_name == "write_to_file":
-                simple_name = command_args["filename"].split("/")[-1] if "/" in command_args["filename"] else command_args["filename"]
-                # todo save written files here
-                if not os.path.exists("experimental_setups/{}/files/{}".format(agent.exp_number, agent.project_path)):
-                    os.system("mkdir experimental_setups/{}/files/{}".format(agent.exp_number, agent.project_path))
-
-                files_list = os.listdir("experimental_setups/{}/files/{}".format(agent.exp_number, agent.project_path))
-
-                with open("experimental_setups/{}/files/{}/{}".format(agent.exp_number, agent.project_path, simple_name+"_{}".format(len(files_list))), "w") as wrf:
-                    wrf.write(command_args["text"])
-
-            result = agent.execute(command_name, command_args, user_input)
-
-            with open(parsable_log_file) as plf:
-                parsable_content = json.load(plf)
-
-            parsable_content["ExecutionAgent_attempt"].append(
-                {
-                    "command_name": command_name,
-                    "command_args": command_args,
-                    "command_result": result,
-                    "prompt_content": agent.prompt_text
-                }
-            )
+                if user_feedback == UserFeedback.AUTHORIZE:
+                    if new_cycles_remaining is not None:
+                        # Case 1: User is altering the cycle budget.
+                        if cycle_budget > 1:
+                            cycle_budget = new_cycles_remaining + 1
+                        # Case 2: User is running iteratively and
+                        #   has initiated a one-time continuous cycle
+                        cycles_remaining = new_cycles_remaining + 1
+                    else:
+                        # Case 1: Continuous iteration was interrupted -> resume
+                        if cycle_budget > 1:
+                            logger.typewriter_log(
+                                "RESUMING CONTINUOUS EXECUTION: ",
+                                Fore.MAGENTA,
+                                f"The cycle budget is {cycle_budget}.",
+                            )
+                        # Case 2: The agent used up its cycle budget -> reset
+                        cycles_remaining = cycle_budget + 1
+                    logger.typewriter_log(
+                        "-=-=-=-=-=-=-= COMMAND AUTHORISED BY USER -=-=-=-=-=-=-=",
+                        Fore.MAGENTA,
+                        "",
+                    )
+                elif user_feedback == UserFeedback.EXIT:
+                    logger.typewriter_log("Exiting...", Fore.YELLOW)
+                    exit()
+                else:  # user_feedback == UserFeedback.TEXT
+                    command_name = "human_feedback"
+            else:
+                user_input = None
+                # First log new-line so user can differentiate sections better in console
+                logger.typewriter_log("\n")
+                if cycles_remaining != math.inf:
+                    # Print authorized commands left value
+                    logger.typewriter_log(
+                        "AUTHORISED COMMANDS LEFT: ", Fore.CYAN, f"{cycles_remaining}"
+                    )
+
+            ###################
+            # Execute Command #
+            ###################
+            # Decrement the cycle counter first to reduce the likelihood of a SIGINT
+            # happening during command execution, setting the cycles remaining to 1,
+            # and then having the decrement set it to 0, exiting the application.
+            agent.left_commands = cycles_remaining
+            if agent.max_budget == -1:
+                agent.max_budget = cycles_remaining
+            if command_name != "human_feedback":
+                cycles_remaining -= 1
+            if agent.cycle_type == "CMD":
+                if command_name == "write_to_file":
+                    simple_name = command_args["filename"].split("/")[-1] if "/" in command_args["filename"] else command_args["filename"]
+                    # todo save written files here
+                    if not os.path.exists("experimental_setups/{}/files/{}".format(agent.exp_number, agent.project_path)):
+                        os.system("mkdir experimental_setups/{}/files/{}".format(agent.exp_number, agent.project_path))
+
+                    files_list = os.listdir("experimental_setups/{}/files/{}".format(agent.exp_number, agent.project_path))
+
+                    with open("experimental_setups/{}/files/{}/{}".format(agent.exp_number, agent.project_path, simple_name+"_{}".format(len(files_list))), "w") as wrf:
+                        wrf.write(command_args["text"])
+
+                if command_name: (command_name, command_args) = debugger.begin_tool_invocation_breakpoint(command_name, command_args)
+                result = agent.execute(command_name, command_args, user_input)
+                if command_name: result = debugger.end_tool_invocation_breakpoint(result)
+                debugger.commit_agent_changes()
 
-            with open(parsable_log_file, "w") as plf:
-                json.dump(parsable_content, plf)
-
-            if result is not None:
-                logger.typewriter_log("SYSTEM: ", Fore.YELLOW, result)
-                agent.cycle_type = "SUMMARY"
-                agent.think()
-                agent.history = agent.history[:-2]
-                
-                agent.commands_and_summary.append(("Call to tool {} with arguments {}".format(command_name, command_args), agent.summary_result))
-                #agent.condensed_history.append(
-                #    "\nCommand:{}\nResult summary:{}\n---".format(str(command_name) + str(command_args), condense_history(agent.summary_result["summary"])))
                 with open(parsable_log_file) as plf:
                     parsable_content = json.load(plf)
 
-                parsable_content["ExecutionAgent_attempt"][-1]["result_summary"] = agent.summary_result
+                parsable_content["ExecutionAgent_attempt"].append(
+                    {
+                        "command_name": command_name,
+                        "command_args": command_args,
+                        "command_result": result,
+                        "prompt_content": agent.prompt_text
+                    }
+                )
 
                 with open(parsable_log_file, "w") as plf:
                     json.dump(parsable_content, plf)
 
-                agent.cycle_type = "CMD"
-                parsing_tests = parse_test_results(str(result))
-                if parsing_tests != "No test results found in log file.":
-                    agent.tests_executed = True
-            else:
-                logger.typewriter_log("SYSTEM: ", Fore.YELLOW, "Unable to execute command")
+                if result is not None:
+                    logger.typewriter_log("SYSTEM: ", Fore.YELLOW, result)
+                    agent.cycle_type = "SUMMARY"
+                    agent.think()
+                    agent.history = agent.history[:-2]
+                    
+                    agent.commands_and_summary.append(("Call to tool {} with arguments {}".format(command_name, command_args), agent.summary_result))
+                    #agent.condensed_history.append(
+                    #    "\nCommand:{}\nResult summary:{}\n---".format(str(command_name) + str(command_args), condense_history(agent.summary_result["summary"])))
+                    with open(parsable_log_file) as plf:
+                        parsable_content = json.load(plf)
+
+                    parsable_content["ExecutionAgent_attempt"][-1]["result_summary"] = agent.summary_result
+
+                    with open(parsable_log_file, "w") as plf:
+                        json.dump(parsable_content, plf)
+
+                    agent.cycle_type = "CMD"
+                    parsing_tests = parse_test_results(str(result))
+                    if parsing_tests != "No test results found in log file.":
+                        agent.tests_executed = True
+                else:
+                    logger.typewriter_log("SYSTEM: ", Fore.YELLOW, "Unable to execute command")
 
-            if not os.path.exists("experimental_setups/{}/saved_contexts/{}".format(agent.exp_number, agent.project_path)):
-                os.system("mkdir experimental_setups/{}/saved_contexts/{}".format(agent.exp_number, agent.project_path))
-            agent.save_to_file("experimental_setups/{}/saved_contexts/{}/cycle_{}".format(agent.exp_number, agent.project_path, cycle_budget - cycles_remaining))
+                if not os.path.exists("experimental_setups/{}/saved_contexts/{}".format(agent.exp_number, agent.project_path)):
+                    os.system("mkdir experimental_setups/{}/saved_contexts/{}".format(agent.exp_number, agent.project_path))
+                agent.save_to_file("experimental_setups/{}/saved_contexts/{}/cycle_{}".format(agent.exp_number, agent.project_path, cycle_budget - cycles_remaining))
 
 import re
```
##### /autogpt/llm/base.py
Stats:
- 13 additions
```diff
@@ -41,7 +41,38 @@ class Message:
 
     def raw(self) -> MessageDict:
         return {"role": self.role, "content": self.content}
+    @classmethod
+    def fromDict(cls, dict: "MessageDict", type: Optional["MessageType"] = None) -> "Message":
+        return cls(
+            role=dict["role"],
+            content=dict["content"],
+            type=type
+        )
+    @classmethod
+    def fromDictList(cls, data_list: list["MessageDict"], type: Optional["MessageType"] = None) -> list["Message"]:
+        return [cls.fromDict(data, type=type) for data in data_list]
 
 @dataclass
 class ModelInfo:
@@ -131,6 +162,10 @@ class ChatSequence:
     def insert(self, index: int, *messages: Message):
         for message in reversed(messages):
             self.messages.insert(index, message)
+    def setFromDictList(self, messages: list[MessageDict]):
+        self.messages.clear()
+        self.extend(Message.fromDictList(messages))
 
     @classmethod
     def for_model(
```