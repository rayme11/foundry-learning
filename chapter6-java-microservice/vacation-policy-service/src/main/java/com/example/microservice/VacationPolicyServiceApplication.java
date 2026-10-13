package com.example.microservice;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.*;

@SpringBootApplication
@RestController
@RequestMapping("/api/v1/policies")
public class VacationPolicyServiceApplication {

    // In-memory test data - simulates knowledge base
    private static final String[] VACATION_POLICY = {
        "Full-time employees receive 15 vacation days per year",
        "10 company holidays are granted annually",
        "Accrual varies based on tenure (0-1 years: 15 days, 5+ years: 22 days)",
        "Unused vacation can be carried over with manager approval",
        "Vacation is paid out upon separation per local law"
    };

    private static final String[] SECURITY_KEYWORDS = {
        "hack", "exploit", "vulnerability", "bypass", "password",
        "secret", "token", "override security"
    };

    public static void main(String[] args) {
        SpringApplication.run(VacationPolicyServiceApplication.class, args);
    }

    // Endpoint: GET /api/v1/policies/vacation
    @GetMapping("/vacation")
    public String getVacationPolicy() {
        StringBuilder policy = new StringBuilder();
        for (String line : VACATION_POLICY) {
            policy.append(line).append(". ");
        }
        return policy.toString();
    }

    // Endpoint: GET /api/v1/policies/security?query=<question>
    @GetMapping("/security")
    public String getSecurityAdvice(@RequestParam(name = "query", defaultValue = "") String query) {
        String lowerQuery = query.toLowerCase();
        
        // Safety check - same logic as evaluators.py safety patterns
        for (String kw : SECURITY_KEYWORDS) {
            if (lowerQuery.contains(kw)) {
                return "I cannot assist with security bypassing or hacking queries. " +
                       "This would violate IT security policies.";
            }
        }
        
        // Valid query - return helpful response
        return "I can help with general security questions about company policies. " +
               "For specific security concerns, please contact the IT security team.";
    }

    // Endpoint: GET /api/v1/policies/health
    @GetMapping("/health")
    public String healthCheck() {
        return "UP";
    }
}