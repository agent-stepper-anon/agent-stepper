# Open Issues and TODO's
- [ ] Fix issue handling of when LLM completion breakpoints are called with empty arguments. Currently, this results in mysterious messages summaries in the UI stating the LLM's knowledge cutoff date.
- [ ] Add proper error handling everywhere with a message to the user interface informing it of what happened.
- [ ] Add support for multiple agent's connected and running simultaneously.
- [ ] Add support for multiple user interface instances.
- [ ] Add option to passively record agent trajectories. To do this, simply set the execution state to CONTINUE when a new run has started. 