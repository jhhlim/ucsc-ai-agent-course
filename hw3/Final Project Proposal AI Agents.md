Jason Lim  
UCSC AI Agent Applications  
Final Project Proposal  
June 2026

# **Multi-Agent Conventional Mortgage Explainer & Scenario Calculator**

## **Use Case**

Buying a home requires evaluating mortgage rates, monthly payments, affordability, debt-to-income (DTI) ratios, loan-to-value (LTV) ratios, PMI requirements, and closing costs. Many buyers struggle to understand how these factors interact and how changes in down payment, interest rate, or income affect affordability.

This project will build a Multi-Agent Conventional Mortgage Explainer & Scenario Calculator using Google ADK. The system helps users analyze mortgage scenarios by coordinating multiple specialized agents that calculate payments, evaluate affordability, retrieve benchmark rates, and verify results. The system is educational only and does not provide financial or lending advice.

Example question:

"Can I afford a $1.28M home with 20% down, a 6% interest rate, and $190,000 household income?"

---

## **Outline of Different Agents**

### **1\. Rate Finder Agent**

Retrieves benchmark mortgage rates using the FRED Mortgage30US dataset and explains differences between common loan products such as 30-year fixed, 15-year fixed, and ARM loans.

### **2\. Payment Calculator Agent**

Calculates loan amount, monthly principal and interest, loan-to-value (LTV), PMI requirements, and estimated cash-to-close costs.

### **3\. Affordability Analyzer Agent**

Evaluates front-end and back-end debt-to-income ratios, analyzes household income, and explains affordability tradeoffs based on common lending guidelines.

### **4\. Synthesizer Agent**

Combines the outputs from the specialist agents into a structured mortgage summary that explains key costs, metrics, and tradeoffs.

### **5\. Compliance Critic Agent**

Reviews calculations and explanations for errors, unsupported assumptions, and recommendation-style language. The critic serves as a final quality-control layer before results are returned to the user.

---

## **Orchestration Pattern**

This project uses a Supervisor \+ Specialist Workers \+ Critic architecture.

1. User submits a mortgage scenario.  
2. Supervisor Agent coordinates the workflow.  
3. Rate Finder, Payment Calculator, and Affordability Analyzer execute specialized tasks.  
4. Synthesizer Agent combines results into a draft summary.  
5. Compliance Critic reviews calculations and language.  
6. Final response is returned to the user.

This architecture allows each agent to focus on a specific responsibility while the Critic Agent improves reliability through independent verification.

---

## **List of Tools**

* FRED Mortgage30US API for benchmark mortgage rate retrieval.  
* Custom mortgage calculation tools for monthly payments, LTV, PMI, DTI, and cash-to-close estimates.  
* Calculation verification tools used by the Compliance Critic Agent.

---

## **Evaluation Plan**

The system will be evaluated based on:

* Accuracy of mortgage calculations.  
* Successful use of external tools.  
* Correct coordination between multiple agents.  
* Ability of the Critic Agent to detect errors or inappropriate recommendation language.  
* Overall completeness and clarity of the final mortgage analysis.

Success will be measured by comparing expected results against generated outputs across multiple mortgage scenarios.

---

## **Motivation**

I selected this project because mortgage decisions involve multiple financial factors that are difficult to evaluate simultaneously. This makes mortgage analysis a strong use case for a multi-agent architecture where specialized agents can focus on different aspects of the problem while a Critic Agent provides an additional layer of validation. The project combines tool usage, financial analysis, agent collaboration, and evaluation within a practical real-world application.

