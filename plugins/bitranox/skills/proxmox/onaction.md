## Steelman Prompt
Consider the planned action or configuration to be executed on the Proxmox server in its ideal, most successful form. 
Imagine this action represents the safest, most efficient, and optimally integrated solution. 
Articulate how this action perfectly fulfills the goals of system administration, increases stability, and fully meets user needs.

## Red-Team Prompt
Review the planned Proxmox action as if you were an experienced admin or security analyst seeking to uncover potential risks. 
Identify possible weaknesses in the configuration, consider outage risks, data loss, or unintended side effects. 
Test the robustness of the plan under worst-case scenarios to ensure it remains safe and reliable even under pressure.

## Decision
At the end of the red-team review, assess whether the identified risks or weaknesses are severe enough to stop the planned action. 
If the action appears safe, logical, and robust, it can be executed immediately. 
If significant uncertainties remain, the user must be explicitly asked for confirmation. 
Conclude with a clear decision: either **"Execute action"** or **"Ask user for confirmation"**.
