# **Jason Lim**

**UCSC AI Agent Applications**  
**Final Project Learnings**

**June 30th, 2026**

# **Learnings**

## **GitHub Repository**

https://github.com/jhhlim/ucsc-ai-agent-course/tree/main/hw3

---

## **Interesting Observations**

* Multi-agent architectures produced more structured responses than a single-agent implementation.  
* The Compliance Critic was effective at identifying recommendation-style language that appeared acceptable during initial testing.  
* Agent orchestration and context passing required more effort than implementing the mortgage calculations themselves.

---

## **Surprising Findings**

* Most system errors occurred between agents rather than within the individual calculation tools.  
* The Critic Agent frequently caught issues that were overlooked by the specialized agents.  
* Mortgage calculations were deterministic and reliable, while language-based review tasks showed more variability across runs.

---

## **Challenges Encountered**

* Designing clear responsibilities for each agent without overlapping functionality.  
* Managing latency caused by multiple sequential LLM calls.  
* Ensuring the Critic Agent received enough context to validate calculations and compliance language.

---

## **What I Would Do Differently**

* Add persistent memory to compare mortgage scenarios across sessions.  
* Experiment with Gemini 2.5 Pro and compare reasoning quality against the current model.  
* Build an automated evaluation suite with additional mortgage scenarios and scoring metrics.  
* Add real-world property tax and insurance lookups using external APIs.

---

## **Key Takeaway**

Building a multi-agent system highlighted that agent coordination, validation, and evaluation are often more challenging than the individual tools themselves. The Compliance Critic pattern significantly improved reliability by acting as a final verification layer before presenting results to the user.

