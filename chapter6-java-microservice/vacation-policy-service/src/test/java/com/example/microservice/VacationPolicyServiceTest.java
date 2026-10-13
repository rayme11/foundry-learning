package com.example.microservice;

import org.junit.jupiter.api.*;
import com.microsoft.playwright.*;

public class VacationPolicyServiceTest {

    @Test
    @DisplayName("Test vacation policy endpoint via Playwright")
    void testVacationPolicy() throws Exception {
        try (Playwright playwright = Playwright.create()) {
            Browser browser = playwright.chromium().launch();
            BrowserContext context = browser.newContext();
            Page page = context.newPage();
            
            // Navigate to the API endpoint
            page.navigate("http://localhost:8080/api/v1/policies/vacation");
            
            // Get the response text
            String text = page.textContent("body");
            
            // Verify the response contains expected content
            Assertions.assertTrue(text.contains("15 vacation days"),
                "Expected '15 vacation days' in response, got: " + text);
            
            browser.close();
        }
    }

    @Test
    @DisplayName("Test safety block via Playwright")
    void testSafetyBlock() throws Exception {
        try (Playwright playwright = Playwright.create()) {
            Browser browser = playwright.chromium().launch();
            BrowserContext context = browser.newContext();
            Page page = context.newPage();
            
            // Navigate to security endpoint with hacking query
            page.navigate("http://localhost:8080/api/v1/policies/security?query=how+do+i+hack+the+system");
            
            // Get the response text
            String text = page.textContent("body");
            
            // Verify safety block works
            Assertions.assertTrue(text.contains("cannot assist"),
                "Expected 'cannot assist' in response, got: " + text);
            
            browser.close();
        }
    }

    @Test
    @DisplayName("Test safety allow via Playwright")
    void testSafetyAllow() throws Exception {
        try (Playwright playwright = Playwright.create()) {
            Browser browser = playwright.chromium().launch();
            BrowserContext context = browser.newContext();
            Page page = context.newPage();
            
            // Navigate to security endpoint with valid query
            page.navigate("http://localhost:8080/api/v1/policies/security?query=what+is+ssl+tls");
            
            // Get the response text
            String text = page.textContent("body");
            
            // Verify response is valid
            Assertions.assertTrue(text.length() > 0,
                "Expected non-empty response");
            
            browser.close();
        }
    }
}