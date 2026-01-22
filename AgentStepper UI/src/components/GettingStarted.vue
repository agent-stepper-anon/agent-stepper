<template class="flex-grow-1">
  <v-spacer></v-spacer>
  <v-sheet class="getting-started d-flex flex-column mx-auto px-4 py-4 transition-transform hover:scale-101"
    :elevation="12" border rounded="lg">
    <h1 class="title text-center text-white font-weight-bold text-h5 mb-3 transition-colors hover:text-cyan-lighten-3">
      Start Debugging Your Agent!
    </h1>
    <div class="d-flex justify-center">
      <div class="content">
        <p class="text-left text-white text-body-2 mb-2">
          Launch the AgentStepper Core and your agent with breakpoints to see its run here.
        </p>
        <p class="text-left text-white font-weight-medium text-body-2 mb-3">
          Get started with AgentStepper in these steps:
        </p>
        <ol class="list text-left text-white">
          <li class="mb-1">Import the debugger:</li>
          <v-code class="code-block text-cyan-lighten-4">
            from agentstepper.api.debugger import AgentStepper
          </v-code>
          <li class="mb-1">Create an AgentStepper object:</li>
          <v-code class="code-block text-cyan-lighten-4">
            debugger = AgentStepper(program_name='My Program', address='localhost', port='8765')
          </v-code>
          <li class="mb-1">Pass the debugger to your agent.</li>
          <li class="mb-1">Set breakpoints around events (e.g., LLM query):</li>
          <v-code class="code-block text-cyan-lighten-4">
            prompt = debugger.begin_llm_query_breakpoint('How are you today?') <br>
            result = llm.completion(prompt) <br>
            response = debugger.end_llm_query_breakpoint(result)
          </v-code>
        </ol>
        <p class="text-left text-white text-body-2 mb-2">
          Run your program to watch your agent’s journey unfold!
        </p>
        <p class="text-left text-body-2">
          Learn more in our guide
          <a href="#" class="guide-link text-cyan-lighten-3 font-weight-medium transition-colors hover:text-white">
            here
          </a>.
        </p>
      </div>
    </div>
  </v-sheet>
  <v-spacer></v-spacer>
</template>

<script>
export default {
  name: 'GettingStarted',
};
</script>

<style scoped>
.getting-started {
  width: fit-content;
  max-width: 90vw;
  background: linear-gradient(135deg, #1976d2, #42a5f5);
  animation: gradientShift 8s ease infinite;
  position: relative;
}

.title {
  text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.3);
}

.content {
  max-width: 550px;
  width: 100%;
}

.list {
  list-style-position: inside;
  padding-left: 0;
}

.code-block {
  font-size: 0.8em;
  display: block;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 8px;
  margin-bottom: 8px;
  box-shadow: inset 0 0 5px rgba(0, 0, 0, 0.3);
}

.guide-link {
  text-decoration: none;
}

@keyframes gradientShift {
  0% {
    background-position: 0% 50%;
  }

  50% {
    background-position: 100% 50%;
  }

  100% {
    background-position: 0% 50%;
  }
}
</style>