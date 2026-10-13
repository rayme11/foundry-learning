# 📖 Chapter 6: Java Microservice with Playwright Testing & Evaluation

## 🎯 Table of Contents
1. [Project Overview](#-project-overview)
2. [Architecture Diagram](#-architecture-diagram)
3. [Prerequisites](#-prerequisites)
4. [Step-by-Step Guide](#-step-by-step-guide)
   - [Step 1: Environment Setup](#step-1-environment-setup)
   - [Step 2: Project Structure Overview](#step-2-project-structure-overview)
   - [Step 3: The Java Microservice](#step-3-the-java-microservice)
   - [Step 4: Playwright Tests](#step-4-playwright-tests)
   - [Step 5: Test Case Storage](#step-5-test-case-storage)
   - [Step 6: Running & Verification](#step-6-running--verification)
5. [Evaluation Logic](#-evaluation-logic)
6. [Customization Guide](#-customization-guide)
7. [Learning Milestones](#-learning-milestones)

---

## 📡 Project Overview

### What We're Building
A **Java microservice** that functions as a Vacation Policy Assistant, consisting of:

1.  **REST API** (Spring Boot) - Provides endpoints for policy queries.
2.  **Playwright Tests** - Automated API testing using Playwright.
3.  **Evaluation Logic** - Scores responses on groundedness, relevance, and safety.
4.  **Test Case Storage** - JSON files storing test scenarios for evaluation.
5.  **ChromaDB Integration** (optional) - For potential vector storage of test case embeddings.

### How This Connects to Chapter 5
| Chapter 5 Concept         | Chapter 6 Equivalent                             |
| :------------------------ | :----------------------------------------------- |
| `ollama.chat()`           | Spring Boot `@RestController` + HTTP             |
| `ChromaDB.search()`       | In-memory arrays (or future Java ChromaDB client) |
| `evaluators.py`           | Java evaluation logic (groundedness/relevance/safety) |
| `traces_*.jsonl`          | Playwright test reports + console logs           |
| `agent_instructions.md`   | `VacationPolicyServiceApplication.java` + `.env` |
| `sample_documents/`       | `test-cases/*.json` files                        |
| `LocalTracer`             | Playwright test reports                          |

**Key takeaway:** The *patterns* for building, testing, and evaluating AI-driven systems are transferable across technology stacks.

### Real-Life Analogy
This project simulates an **employee self-service portal** where:
-   Employees ask questions about company policies.
-   The microservice retrieves and provides policy answers.
-   Automated tests ensure the API works as expected and adheres to safety rules.
-   Evaluation metrics (groundedness, relevance, safety) are used to assess the quality of the policy responses, mimicking a quality gate in a CI/CD pipeline.

---

## 🏗️ Architecture Diagram

```mermaid
graph TD
    subgraph User Interaction
        Browser["Web Browser (User / Playwright)"]
    end

    subgraph Java Microservice (Spring Boot)
        SpringBootApp["VacationPolicyServiceApplication (REST API)"]
        EvaluationLogic(Evaluation Logic - Java)
    end

    subgraph Data & Storage
        InMemoryKB[In-Memory Knowledge Base]
        TestCasesJSON[test-cases/*.json]
        ChromaDBOptional(ChromaDB - Optional Test Case Embeddings)
    end

    subgraph Testing Framework
        PlaywrightTests["VacationPolicyServiceTest (JUnit 5 + Playwright)"]
    end

    Browser -- HTTP Request --> SpringBootApp
    SpringBootApp -- Provides Policy Data --> InMemoryKB
    SpringBootApp -- Logs / Console --> ConsoleOutput(Console / Logs)

    PlaywrightTests -- HTTP API Calls --> SpringBootApp
    PlaywrightTests -- Assertions --> ConsoleOutput
    
    SpringBootApp -- Responds to Playwright --> PlaywrightTests
    SpringBootApp -- Triggers Evaluation --> EvaluationLogic
    EvaluationLogic -- Stores Results --> TestCasesJSON
    EvaluationLogic -- Embeds & Stores --> ChromaDBOptional

    TestCasesJSON -- Provides Test Data --> PlaywrightTests
    ChromaDBOptional -- Retrieves Test Data --> PlaywrightTests
```

**Data Flow Explained:**
1.  **User/Playwright Test:** Initiates an HTTP request to the Spring Boot microservice.
2.  **Spring Boot Microservice:** Processes the request, retrieves policy information (from its in-memory "knowledge base"), and applies basic safety checks.
3.  **Evaluation Logic:** The microservice (or a separate test step) scores the response on metrics like groundedness, relevance, and safety.
4.  **Test Cases Storage:** These evaluation results, along with the original query and response, are stored in JSON files (`test-cases/`) or optionally as embeddings in ChromaDB.
5.  **Playwright Tests:** Verify the API responses and ensure the microservice behaves as expected, acting as automated quality gates.

---

## 🛠️ Prerequisites

### System Requirements:
-   **Java Development Kit (JDK) 17+**: Essential for compiling and running Java applications.
    ```bash
    java -version
    # Expected: openjdk version "17.0.x" or similar
    ```
-   **Apache Maven 3.9+**: The build automation tool for Java projects.
    ```bash
    mvn --version
    # Expected: Apache Maven 3.9.x
    ```
-   **Node.js 18+ and npm**: Playwright uses Node.js to manage browser binaries.
    ```bash
    node --version # Expected: v18.x.x or higher
    npm --version  # Expected: 9.x.x or higher
    ```
-   **Git**: For version control (already set up).

### IDE Setup:
-   **IntelliJ IDEA Ultimate/Community Edition** or **Eclipse IDE for Java Developers** is highly recommended for working with Spring Boot and Maven.
-   **VS Code with Extension Pack for Java** can also be used.

---

## 📝 Step-by-Step Guide

### Step 1: Environment Setup

**What to DO:**
1.  **Verify Java Installation**:
    ```bash
    java -version
    ```
    *Expectation:* Output showing `openjdk version "17.x.x"` or higher.
2.  **Verify Maven Installation**:
    ```bash
    mvn --version
    ```
    *Expectation:* Output showing `Apache Maven 3.9.x` or higher.
3.  **Verify Git Branch**:
    ```bash
    git branch --show-current
    ```
    *Expectation:* Output showing `chapter-6-microservices`.
4.  **Verify Chapter Directory Structure**:
    ```bash
    ls -la "/Users/raymaldonado/Library/CloudStorage/GoogleDrive-vivachihuahua2004@gmail.com/My Drive/Code/foundry-learning/chapter6-java-microservice/"
    ```
    *Expectation:* Output showing: `.env`, `test-cases/`, `vacation-policy-service/` directories.

**What to EXPECT:** All commands should execute successfully and show the expected versions/directories.

**What to DO Next:** If all checks pass, proceed to Step 2. If any check fails, report the error message to me.

---

### Step 2: Project Structure Overview

**What to READ:**
-   **File:** `chapter6-java-microservice/pom.xml`
-   **Read Section:** Look at the `<dependencies>` block and `<plugins>` block.

**Key Dependencies in `pom.xml`:**
-   **`spring-boot-starter-parent`**: This is a crucial parent POM that provides Spring Boot defaults and dependency management.
-   **`spring-boot-starter-web`**: Enables building RESTful APIs with Spring MVC.
-   **`playwright`**: The Playwright Java library for browser automation.
-   **`junit-jupiter`**: The modern JUnit 5 testing framework.
-   **`commons-lang3`**: A utility library that might be used in evaluation logic.

**What to DO:** No action needed. The `pom.xml` is correctly configured to include these. Just read and understand what each dependency is for.

---

### Step 3: The Java Microservice

**What to READ:**
-   **File:** `chapter6-java-microservice/vacation-policy-service/src/main/java/com/example/microservice/VacationPolicyServiceApplication.java`
-   **Read Section:** The full content of this file, paying attention to annotations and method logic.

**Understanding `VacationPolicyServiceApplication.java`:**
-   **`@SpringBootApplication`**: This is the main entry point for a Spring Boot application, combining `@Configuration`, `@EnableAutoConfiguration`, and `@ComponentScan`.
-   **`@RestController`**: Marks this class as a Spring MVC controller that handles incoming HTTP requests and automatically serializes return values to JSON/XML.
-   **`@RequestMapping("/api/v1/policies")`**: Sets the base URL path for all endpoints in this controller.
-   **`VACATION_POLICY` Array**: An in-memory `String` array that simulates a knowledge base for vacation policies. In a real-world scenario, this would come from a database, a vector store like ChromaDB, or an external API.
-   **`SECURITY_KEYWORDS` Array**: A `String` array containing keywords used for basic safety checks, mimicking the `HARMFUL_PATTERNS` from Chapter 5's `evaluators.py`.
-   **`main(String[] args)`**: The standard Java `main` method that launches the Spring Boot application.
-   **`@GetMapping("/vacation")`**: Defines an endpoint `GET /api/v1/policies/vacation` that returns the aggregated vacation policy text.
-   **`@GetMapping("/security")`**: Defines an endpoint `GET /api/v1/policies/security?query=<question>` that performs a simple safety check on the `query` parameter against `SECURITY_KEYWORDS`.
-   **`@GetMapping("/health")`**: A standard health check endpoint returning "UP".

**How It Works:** The application starts an embedded web server (Tomcat by default) and listens for HTTP requests on port 8080 (default). It then processes requests based on the defined REST endpoints.

**What to DO:** No action needed. The file is already created. Read to understand how the microservice is structured and how its endpoints work.

---

### Step 4: Playwright Tests

**What to READ:**
-   **File:** `chapter6-java-microservice/vacation-policy-service/src/test/java/com/example/microservice/VacationPolicyServiceTest.java`
-   **Read Section:** The full content of this test file.

**Understanding `VacationPolicyServiceTest.java`:**
-   **`import com.microsoft.playwright.*;`**: Imports the necessary Playwright Java API classes.
-   **`@Test` and `@DisplayName`**: Standard JUnit 5 annotations to define test methods and provide human-readable names.
-   **`Playwright.create()`**: Initializes the Playwright library.
-   **`playwright.chromium().launch()`**: Launches a Chromium browser instance (headless by default).
-   **`browser.newContext()`**: Creates a new browser context, which is like an isolated browser session.
-   **`context.newPage()`**: Creates a new browser page (tab) within the context.
-   **`page.navigate("http://localhost:8080/api/v1/policies/vacation")`**: Makes an HTTP GET request to the microservice's endpoint.
-   **`page.textContent("body")`**: Retrieves the text content of the `<body>` tag of the loaded page (which is the API response in this case).
-   **`Assertions.assertTrue(...)`**: Standard JUnit 5 assertion to verify conditions.

**3 Tests Included:**
1.  **`testVacationPolicy()`**: Verifies that the `/vacation` endpoint returns the expected policy text.
2.  **`testSafetyBlock()`**: Sends a "hacking" query to `/security` and verifies that the microservice correctly blocks it with a safety message.
3.  **`testSafetyAllow()`**: Sends a safe query to `/security` and verifies that the microservice provides a general helpful response.

**How It Works:** These tests simulate a user or another service making requests to your microservice's API and assert that the responses are correct and adhere to basic safety rules.

**What to DO:** No action needed. The test file is already created. Read to understand how Playwright is used for API testing.

---

### Step 5: Test Case Storage

**What to READ:**
-   **File:** `chapter6-java-microservice/test-cases/groundedness_cases.json`
-   **Read Section:** The full content of this JSON file.

**Understanding `groundedness_cases.json`:**
This JSON file contains an array of test case objects. Each object represents a scenario to evaluate the microservice's responses.

**Structure of a Test Case:**
-   **`"query"`**: The input question to send to the microservice.
-   **`"response"`**: The *expected* or *agent's simulated* response for evaluation.
-   **`"expectedGroundedness"`**: The target groundedness score (0.0-1.0).
-   **`"expectedRelevance"`**: The target relevance score (0.0-1.0).
-   **`"expectedSafety"`**: The target safety score (0.0-1.0).
-   **`"citations"`**: A list of expected source documents (e.g., `["company_handbook.pdf"]`).
-   **`"reason"`**: A human-readable explanation for the expected scores.

**How It Works:** These JSON files serve as your repository of "approved" test cases. In a more advanced setup, an evaluation runner would read these, execute the queries against your microservice, and compare the actual results to the `expected...` scores.

**What to DO:** No action needed. The JSON file is already created. Read to understand how test cases are structured.

---

### Step 6: Running & Verification

**What to DO:** Now it's time for hands-on action!

1.  **Open two separate terminal windows.**

2.  **In Terminal 1 (Start Server):**
    ```bash
    # Navigate to the microservice project directory
    cd "/Users/raymaldonado/Library/CloudStorage/GoogleDrive-vivachihuahua2004@gmail.com/My Drive/Code/foundry-learning/chapter6-java-microservice/vacation-policy-service"
    
    # Start the Spring Boot server
    mvn spring-boot:run
    ```
    *Expectation in Terminal 1:* You will see the Spring Boot banner and log messages indicating the application has started and is listening on port 8080. Look for: `Started VacationPolicyServiceApplication in X seconds` and `Tomcat initialized with port(s): 8080 (http)`

3.  **In Terminal 2 (Verify Endpoint):**
    ```bash
    # Navigate to the same microservice project directory
    cd "/Users/raymaldonado/Library/CloudStorage/GoogleDrive-vivachihuahua2004@gmail.com/My Drive/Code/foundry-learning/chapter6-java-microservice/vacation-policy-service"

    # Verify the vacation policy endpoint is responding
    curl -s http://localhost:8080/api/v1/policies/vacation
    ```
    *Expectation in Terminal 2:* You should see the full vacation policy text printed:
    `Full-time employees receive 15 vacation days per year. 10 company holidays are granted annually. Accrual varies based on tenure (0-1 years: 15 days, 5+ years: 22 days). Unused vacation can be carried over with manager approval. Vacation is paid out upon separation per local law.`

4.  **In Terminal 2 (Run Playwright Tests):**
    ```bash
    # Ensure the server is still running in Terminal 1!
    # Run the Playwright tests
    mvn test -Dtest=VacationPolicyServiceTest
    ```
    *Expectation in Terminal 2:*
    ```
    [INFO] -------------------------------------------------------
    [INFO]  T E S T S
    [INFO] -------------------------------------------------------
    [INFO] Running com.example.microservice.VacationPolicyServiceTest
    ...
    [INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0
    [INFO]
    [INFO] Results:
    [INFO]
    [INFO] Tests run: 3, Failures: 0, Errors: 0, Skipped: 0
    [INFO] ------------------------------------------------------------------------
    [INFO] BUILD SUCCESS
    ```

**What to DO NEXT:**
-   **✅ SUCCESS:** If all these steps complete successfully, tell me: "Step 6 complete, server and tests working!"
-   **❌ FAILURE:** If any step fails, copy and paste the exact error message, and I will help troubleshoot.

---

## 📊 Evaluation Logic

The microservice incorporates simple evaluation concepts:

### Groundedness (0.0-1.0)
-   **Concept**: How well the response is supported by a knowledge base.
-   **Implementation (Simplified)**: In `VacationPolicyServiceApplication.java`, the `getVacationPolicy()` method directly provides "grounded" information (from `VACATION_POLICY` array). For safety checks, if a query is rejected, it returns a fixed "cannot assist" message which implies it's "grounded" in its own safety rules.
-   **Test Case**: `expectedGroundedness` in `groundedness_cases.json` tracks this.

### Relevance (0.0-1.0)
-   **Concept**: How well the response addresses the user's query.
-   **Implementation (Simplified)**: The `getVacationPolicy()` endpoint is highly relevant to vacation queries. The `getSecurityAdvice()` endpoint tries to be relevant to general security, but rejects harmful queries.
-   **Test Case**: `expectedRelevance` in `groundedness_cases.json` tracks this.

### Safety (0.0-1.0)
-   **Concept**: Whether the response contains harmful or inappropriate content.
-   **Implementation**: The `getSecurityAdvice()` method checks `query` against `SECURITY_KEYWORDS`. If a keyword is found, it returns a safety-blocking message.
-   **Test Case**: `expectedSafety` in `groundedness_cases.json` tracks this. The `testSafetyBlock()` Playwright test specifically checks for this.

---

## 🛠️ Customization Guide

### Changing the Domain
To change from a vacation policy assistant to a different domain:

1.  **Edit `VacationPolicyServiceApplication.java`**:
    -   Modify the `VACATION_POLICY` array content with your new domain's data.
    -   Adjust `SECURITY_KEYWORDS` to be relevant to your new domain's safety concerns.
    -   Change endpoint URLs (`@RequestMapping`, `@GetMapping`) if needed.
2.  **Update `test-cases/groundedness_cases.json`**:
    -   Modify existing test scenarios and add new ones relevant to your domain.
    -   Ensure `expectedGroundedness`, `expectedRelevance`, `expectedSafety`, and `citations` are updated.
3.  **Adjust `.env` thresholds**: If your new domain has different quality expectations.

### Adding Custom Endpoints
To add more functionality to your microservice:
```java
// In VacationPolicyServiceApplication.java, add a new method:
@GetMapping("/api/v1/your-domain/new-policy")
public String getNewPolicy() {
    return "This is a new policy for your domain.";
}
```
Then, write a corresponding Playwright test in `VacationPolicyServiceTest.java`.

### Connecting to Actual ChromaDB
To replace the in-memory data with a real ChromaDB instance for your knowledge base (similar to Chapter 5):

1.  **Add ChromaDB Java client dependency** to `pom.xml`.
2.  **Initialize `chromadb.PersistentClient`** in `VacationPolicyServiceApplication.java`.
3.  **Load policy documents** (e.g., from files) into ChromaDB, creating embeddings.
4.  **Modify policy retrieval**: Instead of `VACATION_POLICY` array, query ChromaDB semantically based on the user's input query.
5.  **Extract citations** from ChromaDB retrieval results and include them in the API response.

---

## 📊 Learning Milestones

### Milestone 1: Foundation (Current)
-   [x] Step 1: Environment Setup
-   [x] Step 2: Project Structure Overview
-   [x] Step 3: The Java Microservice
-   [x] Step 4: Playwright Tests
-   [x] Step 5: Test Case Storage
-   [ ] Step 6: Running & Verification (Your current task!)

### Milestone 2: Evaluation Integration
-   [ ] Fully integrate evaluation logic (Java code to score responses against test cases).
-   [ ] Automate test case execution from `test-cases/*.json`.

### Milestone 3: Azure Migration Research
-   [ ] Study migration patterns from Chapter 5 (`mcp_server.py` vs `local_mcp_server.py`).
-   [ ] Research replacing in-memory data with **Azure AI Search**.
-   [ ] Explore integrating **Azure OpenAI** as the LLM if you extend beyond simple policy retrieval.

---

## 🎯 Your Immediate Next Step

**Right now, complete Step 6:**

1.  **Start the server** in Terminal 1:
    ```bash
    cd "/Users/raymaldonado/Library/CloudStorage/GoogleDrive-vivachihuahua2004@gmail.com/My Drive/Code/foundry-learning/chapter6-java-microservice/vacation-policy-service"
    mvn spring-boot:run
    ```
2.  **Verify the endpoint** in Terminal 2:
    ```bash
    curl -s http://localhost:8080/api/v1/policies/vacation
    ```
3.  **Run the Playwright tests** in Terminal 2 (while server is still running):
    ```bash
    mvn test -Dtest=VacationPolicyServiceTest
    ```

**Then tell me:** "Step 6 complete, server and tests working!" or describe any error you encounter.
