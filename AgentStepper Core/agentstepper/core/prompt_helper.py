import os
from agentstepper.core.types import Run
from typing import Optional
from agentstepper.api.common import Breakpoint, EventTypes
from openai import OpenAI, OpenAIError

class PromptHelper:
    
    _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    _prompts = {
        'summarize_query_request': os.path.join(_project_root, 'prompts', 'summarize_query_request.prompt'),
        'summarize_query_response': os.path.join(_project_root, 'prompts', 'summarize_query_response.prompt'),
        'summarize_tool_call': os.path.join(_project_root, 'prompts', 'summarize_tool_call.prompt'),
        'summarize_tool_result': os.path.join(_project_root, 'prompts', 'summarize_tool_result.prompt'),
    }
    
    @staticmethod
    def summarize_breakpoint(llm: OpenAI, model: str, run: Run, breakpoint: Breakpoint) -> Optional[str]:
        '''
        Returns a summary of the specified breakpoint of the given event.

        :param Breakpoint breakpoint: The breakpoint to summarize. Must be associated with the event.
        :return: Summary as string or None if the LLM is unavailable or the breakpoint is not summarizable.
        :rtype: Optional[str]
        '''
        assert breakpoint.event_id in run.events
        
        try:
            prompt = None
            if llm:
                event = run.events[breakpoint.event_id]
                
                if event.type == EventTypes.LLM_QUERY:
                    if breakpoint ==  event.get_begin_breakpoint():
                        prompt = PromptHelper.get_query_request_summarization_prompt()
                        
                        previous_queries = run.get_previous_queries(event)
                        previous_prompt = previous_queries[-1].get_begin_breakpoint().get_data() if previous_queries else ''
                        
                        prompt += f'\n\n"{previous_prompt}"\n\nBelow is the message to summarize:'
                    else:
                        prompt = PromptHelper.get_query_response_summarization_prompt()
                elif event.type == EventTypes.TOOL_INVOCATION:
                    prompt = PromptHelper.get_tool_call_summarization_prompt() if (breakpoint == event.get_begin_breakpoint()) else PromptHelper.get_tool_result_summarization_prompt()
                
                if prompt:
                    prompt = llm.chat.completions.create(
                        model=model,
                        messages=[
                            {
                                "role": "system",
                                "content": prompt + f'\n\n"{breakpoint.original_data}"'
                            }
                        ]
                    ).choices[0].message.content
        except FileNotFoundError:
            pass
        except OpenAIError as e:
            PromptHelper.logger.error(f'Error getting completion from OpenAI: {e}')
        return prompt

    @staticmethod
    def get_query_request_summarization_prompt() -> str:
        return PromptHelper._get_prompt_from_file(PromptHelper._prompts['summarize_query_request'])
    
    
    @staticmethod
    def get_query_response_summarization_prompt() -> str:
        return PromptHelper._get_prompt_from_file(PromptHelper._prompts['summarize_query_response'])
    
    
    @staticmethod
    def get_tool_call_summarization_prompt() -> str:
        return PromptHelper._get_prompt_from_file(PromptHelper._prompts['summarize_tool_call'])
    
    
    @staticmethod
    def get_tool_result_summarization_prompt() -> str:
        return PromptHelper._get_prompt_from_file(PromptHelper._prompts['summarize_tool_result'])
    
    
    @staticmethod
    def _get_prompt_from_file(file_path: str) -> str:
        '''
        Extracts the content of a text file, which is assumed to be the prompt.

        :param str file_path: The path to the text file.
        :return: The prompt extracted from the file, or None if an error occurs.
        :rtype: str or None
        '''
        try:
            with open(file_path, 'r') as file:
                return file.read().strip()
        except FileNotFoundError as e:
            PromptHelper.logger.error(f"Error: The file '{file_path}' was not found.")
            raise e