# Contoso Internal API Documentation

## Version: 2.3 | Updated: February 2024 | Classification: Internal

---

## 1. Overview

This document describes the internal REST and gRPC APIs used across Contoso microservices. All APIs require authentication via Microsoft Entra ID (Azure AD) tokens.

**Base URLs**:
- **Production**: `https://api.contoso.internal/v2`
- **Staging**: `https://api-staging.contoso.internal/v2`
- **Development**: `https://api-dev.contoso.internal/v2`

**gRPC Endpoints**: `grpc.contoso.internal:443` (TLS required)

---

## 2. Authentication

### 2.1 Token Acquisition
```bash
# Azure CLI
az account get-access-token --resource api://contoso-internal-api

# MSAL (Python)
from azure.identity import DefaultAzureCredential
credential = DefaultAzureCredential()
token = credential.get_token("api://contoso-internal-api/.default")
```

### 2.2 Token Usage
```http
Authorization: Bearer <access_token>
X-Correlation-ID: <uuid>  # Required for tracing
```

### 2.3 Scopes
| Scope | Description |
|-------|-------------|
| `api://contoso-internal-api/.default` | All internal APIs |
| `api://contoso-hr-api/.default` | HR service only |
| `api://contoso-finance-api/.default` | Finance service only |

---

## 3. Rate Limiting

| Tier | Requests/Minute | Burst |
|------|-----------------|-------|
| **Standard** | 1,000 | 2,000 |
| **Premium** | 10,000 | 20,000 |
| **Internal Tools** | 50,000 | 100,000 |

**Headers**:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1708454400
Retry-After: 60  # On 429
```

---

## 4. Error Handling

### 4.1 Standard Error Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request payload",
    "details": [
      { "field": "email", "issue": "Invalid format" }
    ],
    "correlationId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

### 4.2 Common Error Codes
| HTTP | Code | Description |
|------|------|-------------|
| 400 | `VALIDATION_ERROR` | Request validation failed |
| 401 | `UNAUTHENTICATED` | Invalid/expired token |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource doesn't exist |
| 409 | `CONFLICT` | Resource conflict (e.g., duplicate) |
| 422 | `UNPROCESSABLE_ENTITY` | Semantic error |
| 429 | `RATE_LIMITED` | Too many requests |
| 500 | `INTERNAL_ERROR` | Server error |
| 503 | `SERVICE_UNAVAILABLE` | Temporary outage |

---

## 5. Core APIs

### 5.1 Employee Directory API

#### Get Employee Profile
```http
GET /employees/{employeeId}
Authorization: Bearer <token>
X-Correlation-ID: <uuid>
```

**Response** (200):
```json
{
  "employeeId": "EMP-12345",
  "displayName": "Jane Smith",
  "email": "jane.smith@contoso.com",
  "department": "Engineering",
  "title": "Senior Software Engineer",
  "managerId": "EMP-12340",
  "hireDate": "2022-03-15",
  "location": "Seattle, WA",
  "costCenter": "ENG-100",
  "employmentType": "FullTime",
  "status": "Active"
}
```

#### Search Employees
```http
GET /employees?department=Engineering&status=Active&limit=50&offset=0
```

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `department` | string | - | Filter by department |
| `status` | enum | Active | Active/OnLeave/Terminated |
| `managerId` | string | - | Direct reports of manager |
| `limit` | int | 20 | Max results (max 100) |
| `offset` | int | 0 | Pagination offset |

---

### 5.2 Time Off API

#### Get Vacation Balance
```http
GET /timeoff/balance/{employeeId}
```

**Response** (200):
```json
{
  "employeeId": "EMP-12345",
  "vacationBalanceDays": 12.5,
  "sickBalanceDays": 7.0,
  "accrualRate": "1.25/month",
  "nextAccrualDate": "2024-03-01",
  "carryoverDays": 3.0,
  "usedThisYear": 8.5
}
```

#### Request Time Off
```http
POST /timeoff/requests
Content-Type: application/json

{
  "employeeId": "EMP-12345",
  "type": "Vacation",
  "startDate": "2024-06-15",
  "endDate": "2024-06-21",
  "reason": "Family vacation",
  "managerApprovalRequired": true
}
```

**Response** (201):
```json
{
  "requestId": "TO-789456",
  "status": "PendingApproval",
  "submittedAt": "2024-03-10T14:30:00Z",
  "approverId": "EMP-12340"
}
```

---

### 5.3 IT Service Management API

#### Create Ticket
```http
POST /itsm/tickets
Content-Type: application/json

{
  "title": "Laptop not connecting to VPN",
  "description": "Since this morning, GlobalProtect fails to connect. Error: 'Authentication failed'",
  "category": "Network",
  "priority": "High",
  "requesterId": "EMP-12345",
  "affectedAssetId": "AST-LT-45678"
}
```

**Response** (201):
```json
{
  "ticketId": "INC-20240315-0042",
  "status": "New",
  "assignedGroup": "Service Desk",
  "slaTarget": "2024-03-15T18:30:00Z",
  "createdAt": "2024-03-15T14:32:10Z"
}
```

#### Get Ticket Status
```http
GET /itsm/tickets/{ticketId}
```

---

### 5.4 System Health API

#### Check Service Status
```http
GET /health/services/{serviceName}
```

**Service Names**: `api-gateway`, `employee-directory`, `timeoff`, `itsm`, `payroll`, `auth`

**Response** (200):
```json
{
  "service": "employee-directory",
  "status": "Healthy",
  "lastIncident": null,
  "uptime99": true,
  "latencyP95ms": 45,
  "errorRate": 0.001,
  "checkedAt": "2024-03-15T14:35:00Z"
}
```

**Status Values**: `Healthy`, `Degraded`, `Down`, `Maintenance`

---

## 6. Webhooks

### 6.1 Subscription
```http
POST /webhooks/subscriptions
Content-Type: application/json

{
  "eventTypes": ["employee.hired", "employee.terminated", "timeoff.approved"],
  "callbackUrl": "https://my-service.contoso.internal/webhooks/employee-events",
  "secret": "base64-encoded-secret-for-signature-verification"
}
```

### 6.2 Event Payload
```json
{
  "eventId": "evt_abc123",
  "eventType": "employee.hired",
  "timestamp": "2024-03-15T14:30:00Z",
  "payload": {
    "employeeId": "EMP-99999",
    "department": "Engineering"
  }
}
```

**Verification**: Validate `X-Contoso-Signature` header (HMAC-SHA256 of body with secret)

---

## 7. SDKs & Client Libraries

| Language | Package | Install |
|----------|---------|---------|
| **Python** | `contoso-internal-api` | `pip install --index-url https://pkgs.dev.azure.com/contoso/_packaging/internal/pypi/simple/ contoso-internal-api` |
| **TypeScript** | `@contoso/internal-api-client` | `npm install @contoso/internal-api-client --registry=https://pkgs.dev.azure.com/contoso/_packaging/internal/npm/registry/` |
| **C#** | `Contoso.InternalApi.Client` | `dotnet add package Contoso.InternalApi.Client --source https://pkgs.dev.azure.com/contoso/_packaging/internal/nuget/v3/index.json` |
| **Go** | `github.com/contoso/internal-api-go` | `go get github.com/contoso/internal-api-go@v2.3.0` |

---

## 8. Testing & Development

### 8.1 Local Mock Server
```bash
# Start mock server with recorded responses
docker run -p 8080:8080 contoso/api-mock:v2.3
```

### 8.2 Contract Testing
- **Pact Broker**: `https://pact.contoso.internal`
- **Consumer Contracts**: Published on every CI build
- **Provider Verification**: Runs nightly against staging

---

## 9. Deprecation Policy

- **Notice**: 90 days minimum
- **Headers**: `Sunset: Sat, 01 Jun 2024 00:00:00 GMT`, `Link: <new-url>; rel="successor-version"`
- **Support**: Old version supported during notice period

---

## 10. Support & Contacts

| Team | Channel | SLA |
|------|---------|-----|
| **API Platform** | #api-platform (Teams) | 4hr business hours |
| **HR API** | #hr-systems-support | 8hr business hours |
| **ITSM API** | #itsm-integration | 4hr business hours |
| **On-Call** | PagerDuty: `api-platform-oncall` | 24/7 for SEV-1 |

---

*Generated from OpenAPI spec: `https://api.contoso.internal/v2/openapi.json`*
*Last sync: 2024-02-15 | Owner: API Platform Team | Questions: api-platform@contoso.com*